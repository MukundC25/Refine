"""Hybrid ranking orchestrator — 3-stage pipeline that wires together every
scoring component into a single end-to-end ranker.

Stage 1: honeypot filter + rule pre-score (all 100K)        → top 5000
Stage 2: embedding sim + skills trust + career trajectory   → top 200
Stage 3: behavioral signals + final composite score         → top 100

Final score is a weighted blend of all five signal sources, multiplied by the
honeypot penalty (1.0 clean, 0.7/0.4 suspicious, 0.0 hard-disqualified).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from backend.app.core.candidate_loader import (
    CandidateRecord,
    build_candidate_text,
    stream_candidates,
)
from backend.app.core.career_analyzer import CareerTrajectoryScore, analyze_career
from backend.app.core.embedding_service import EmbeddingService, load_embeddings
from backend.app.core.honeypot_detector import HoneypotResult, detect_honeypot
from backend.app.core.rule_scorer import RuleScore, score_candidate
from backend.app.core.signal_scorer import BehavioralScore, compute_behavioral_score
from backend.app.core.skill_matcher import SkillsMatchScore, combined_skills_score

if TYPE_CHECKING:
    from backend.app.core.jd_parser import ParsedJD

logger = logging.getLogger(__name__)


STAGE_WEIGHTS: dict[str, float] = {
    "rule_score": 0.20,
    "embedding_similarity": 0.25,
    "skills_trust": 0.20,
    "career_trajectory": 0.15,
    "behavioral": 0.20,
}


@dataclass
class RankedCandidate:
    candidate: CandidateRecord
    rule_score: RuleScore
    embedding_similarity: float
    skills_score: SkillsMatchScore
    career_score: CareerTrajectoryScore
    behavioral_score: BehavioralScore
    honeypot_result: HoneypotResult
    final_score: float
    rank: int = 0


def compute_final_score(
    rule: RuleScore,
    embedding_sim: float,
    skills: SkillsMatchScore,
    career: CareerTrajectoryScore,
    behavioral: BehavioralScore,
    honeypot: HoneypotResult,
    weights: dict[str, float] | None = None,
) -> float:
    """Blend all stage signals into a 0-100 composite score.

    Honeypot penalty_multiplier == 0 (hard disqualified) returns 0 immediately.
    Otherwise raw = sum(component * weight), scaled by penalty_multiplier.
    """
    if honeypot.penalty_multiplier == 0.0:
        return 0.0
    w = weights or STAGE_WEIGHTS
    raw = (
        rule.total * w["rule_score"]
        + embedding_sim * 100.0 * w["embedding_similarity"]
        + skills.total * w["skills_trust"]
        + career.total * w["career_trajectory"]
        + behavioral.total * w["behavioral"]
    )
    return round(max(0.0, raw * honeypot.penalty_multiplier), 4)


def _normalise(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(_normalise(a.flatten()), _normalise(b.flatten())))


def _candidate_embedding_similarity(
    candidate: CandidateRecord,
    jd_embedding: np.ndarray,
    embedding_service: EmbeddingService,
    embeddings_matrix: np.ndarray | None,
    candidate_id_index: dict[str, int] | None,
) -> float:
    """Use pre-computed matrix when the candidate is indexed; otherwise embed inline."""
    if embeddings_matrix is not None and candidate_id_index is not None:
        idx = candidate_id_index.get(candidate.candidate_id)
        if idx is not None:
            return _cosine_sim(embeddings_matrix[idx], jd_embedding)
    text = build_candidate_text(candidate)
    return _cosine_sim(embedding_service.embed_text(text), jd_embedding)


def stage1_prescreening(
    candidates_path: str,
    jd: ParsedJD,
    top_n: int = 5000,
) -> list[tuple[CandidateRecord, RuleScore, HoneypotResult]]:
    """Stream candidates, drop honeypot disqualifications, sort by rule.total."""
    return stage1_from_records(
        list(stream_candidates(candidates_path)), jd, top_n=top_n
    )


def stage1_from_records(
    candidates: list[CandidateRecord],
    jd: ParsedJD,
    top_n: int = 5000,
) -> list[tuple[CandidateRecord, RuleScore, HoneypotResult]]:
    """Same as stage1_prescreening but takes already-validated records."""
    results: list[tuple[CandidateRecord, RuleScore, HoneypotResult]] = []
    for candidate in candidates:
        honeypot = detect_honeypot(candidate)
        if honeypot.penalty_multiplier == 0.0:
            continue
        rule = score_candidate(candidate, jd)
        results.append((candidate, rule, honeypot))
    results.sort(key=lambda x: (-x[1].total, x[0].candidate_id))
    return results[:top_n]


def stage2_semantic_rerank(
    stage1_results: list[tuple[CandidateRecord, RuleScore, HoneypotResult]],
    jd: ParsedJD,
    jd_embedding: np.ndarray,
    embedding_service: EmbeddingService,
    embeddings_matrix: np.ndarray | None = None,
    candidate_id_index: dict[str, int] | None = None,
    top_n: int = 200,
    weights: dict[str, float] | None = None,
) -> list[tuple[CandidateRecord, RuleScore, HoneypotResult, float, SkillsMatchScore, CareerTrajectoryScore]]:
    """Add embedding similarity, skills trust, career trajectory; partial-sort top_n."""
    w = weights or STAGE_WEIGHTS
    results = []
    for candidate, rule, honeypot in stage1_results:
        emb_sim = _candidate_embedding_similarity(
            candidate, jd_embedding, embedding_service,
            embeddings_matrix, candidate_id_index,
        )
        skills = combined_skills_score(candidate, jd, jd_embedding, embedding_service)
        career = analyze_career(candidate, jd)
        results.append((candidate, rule, honeypot, emb_sim, skills, career))

    results.sort(key=lambda x: (
        -(x[1].total * w["rule_score"]
          + x[3] * 100.0 * w["embedding_similarity"]
          + x[4].total * w["skills_trust"]
          + x[5].total * w["career_trajectory"]),
        x[0].candidate_id,
    ))
    return results[:top_n]


def stage3_behavioral_boost(
    stage2_results: list[tuple[CandidateRecord, RuleScore, HoneypotResult, float, SkillsMatchScore, CareerTrajectoryScore]],
    jd: ParsedJD,
    top_n: int = 100,
    weights: dict[str, float] | None = None,
) -> list[RankedCandidate]:
    """Compute behavioral scores, final composite, sort, assign ranks 1..N."""
    ranked: list[RankedCandidate] = []
    for candidate, rule, honeypot, emb_sim, skills, career in stage2_results:
        behavioral = compute_behavioral_score(candidate)
        final = compute_final_score(rule, emb_sim, skills, career, behavioral, honeypot, weights)
        ranked.append(RankedCandidate(
            candidate=candidate,
            rule_score=rule,
            embedding_similarity=emb_sim,
            skills_score=skills,
            career_score=career,
            behavioral_score=behavioral,
            honeypot_result=honeypot,
            final_score=final,
        ))
    ranked.sort(key=lambda x: (-x.final_score, x.candidate.candidate_id))
    ranked = ranked[:top_n]
    for i, rc in enumerate(ranked, start=1):
        rc.rank = i
    return ranked


class RankingEngine:
    """3-stage hybrid ranker.

    Pre-computed embeddings are loaded if a path is provided. Without them,
    Stage 2 falls back to on-the-fly embedding via the embedding service.
    """

    def __init__(
        self,
        embeddings_path: str | None = None,
        ids_path: str | None = None,
        model_name: str = "all-MiniLM-L6-v2",
        embedding_service: EmbeddingService | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.model_name = model_name
        self.weights = weights or STAGE_WEIGHTS
        self.embedding_service = embedding_service or EmbeddingService(model_name=model_name)
        self.embeddings_matrix: np.ndarray | None = None
        self.candidate_id_index: dict[str, int] | None = None

        if embeddings_path is not None:
            self._load_precomputed(embeddings_path, ids_path)

    def _load_precomputed(self, embeddings_path: str, ids_path: str | None) -> None:
        if not Path(embeddings_path).exists():
            raise FileNotFoundError(
                f"Embeddings file not found: {embeddings_path}. "
                "Run precompute_candidate_embeddings() first."
            )
        if ids_path is not None:
            if not Path(ids_path).exists():
                raise FileNotFoundError(f"IDs file not found: {ids_path}")
            self.embeddings_matrix = np.load(embeddings_path).astype(np.float32)
            with open(ids_path, encoding="utf-8") as fh:
                ids = json.load(fh)
            if len(ids) != self.embeddings_matrix.shape[0]:
                raise ValueError(
                    f"Embedding matrix has {self.embeddings_matrix.shape[0]} rows "
                    f"but ids file has {len(ids)} entries."
                )
        else:
            self.embeddings_matrix, ids = load_embeddings(embeddings_path)
        self.candidate_id_index = {cid: i for i, cid in enumerate(ids)}

    def _jd_embedding(self, jd: ParsedJD) -> np.ndarray:
        text = jd.role_embedding_text or jd.raw_text
        return self.embedding_service.embed_text(text)

    def run(
        self,
        candidates_path: str,
        jd: ParsedJD,
        top_n_stage1: int = 5000,
        top_n_stage2: int = 200,
        top_n_final: int = 100,
    ) -> list[RankedCandidate]:
        """Full pipeline driven from a candidates.jsonl path."""
        logger.info("Stage 1: rule pre-screen → top %d", top_n_stage1)
        stage1 = stage1_prescreening(candidates_path, jd, top_n=top_n_stage1)
        logger.info("Stage 1 survivors: %d", len(stage1))

        jd_embedding = self._jd_embedding(jd)
        logger.info("Stage 2: semantic rerank → top %d", top_n_stage2)
        stage2 = stage2_semantic_rerank(
            stage1, jd, jd_embedding, self.embedding_service,
            embeddings_matrix=self.embeddings_matrix,
            candidate_id_index=self.candidate_id_index,
            top_n=top_n_stage2,
            weights=self.weights,
        )
        logger.info("Stage 2 survivors: %d", len(stage2))

        logger.info("Stage 3: behavioral boost → top %d", top_n_final)
        return stage3_behavioral_boost(stage2, jd, top_n=top_n_final, weights=self.weights)

    def rank_records(
        self,
        candidates: list[CandidateRecord],
        jd: ParsedJD,
        top_n_stage1: int = 5000,
        top_n_stage2: int = 200,
        top_n_final: int = 100,
    ) -> list[RankedCandidate]:
        """Same as run() but accepts pre-validated records (test entry point)."""
        stage1 = stage1_from_records(candidates, jd, top_n=top_n_stage1)
        jd_embedding = self._jd_embedding(jd)
        stage2 = stage2_semantic_rerank(
            stage1, jd, jd_embedding, self.embedding_service,
            embeddings_matrix=self.embeddings_matrix,
            candidate_id_index=self.candidate_id_index,
            top_n=top_n_stage2,
            weights=self.weights,
        )
        return stage3_behavioral_boost(stage2, jd, top_n=top_n_final, weights=self.weights)
