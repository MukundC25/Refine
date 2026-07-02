"""Skills trust scorer and career semantic matcher for Stage 2 of the ranking pipeline.

Two complementary signals:
  - skill_trust_score: cross-validates self-declared skills against endorsements,
    usage duration, and platform assessment scores. Harder to game than raw keywords.
  - career_semantic_score: cosine similarity between the JD embedding and the
    candidate's actual career descriptions — what they DID, not what they claim.
  - combined_skills_score: blended 0-100 composite of both signals.

Dimensions:
    skill_trust_score        0.0–1.0  per skill
    compute_skills_match     0.0–1.0  aggregate across JD-required skills
    career_semantic_score    0.0–1.0  max-pool cosine over top-3 career descriptions
    combined_skills_score    0–100    60% skills_match + 40% career_semantic
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from backend.app.core.candidate_loader import CandidateRecord, SkillEntry
    from backend.app.core.embedding_service import EmbeddingService
    from backend.app.core.jd_parser import ParsedJD


PROFICIENCY_WEIGHTS: dict[str, float] = {
    "beginner": 0.25,
    "intermediate": 0.5,
    "advanced": 0.8,
    "expert": 1.0,
}

# Duration (months) at which the credibility factor saturates to 1.0
_DURATION_SATURATION = 36.0


@dataclass
class SkillsMatchScore:
    candidate_id: str
    skills_match: float      # 0.0–1.0 trust-weighted skills coverage
    career_semantic: float   # 0.0–1.0 cosine similarity of career descriptions vs JD
    total: float             # 0–100 composite


def skill_trust_score(skill: "SkillEntry", assessment_scores: dict[str, float]) -> float:
    """Return 0.0–1.0 trust score for a single skill.

    Assessment score (platform-verified) is the strongest signal when present:
    blended 60/40 with self-declared proficiency × duration.
    Without an assessment: proficiency × duration × endorsement boost.
    """
    base = PROFICIENCY_WEIGHTS.get(skill.proficiency, 0.25)
    duration = skill.duration_months if skill.duration_months is not None else 0
    duration_factor = min(duration / _DURATION_SATURATION, 1.0)
    endorsement_boost = 1.0 + math.log1p(skill.endorsements) / 10.0

    if skill.name in assessment_scores:
        assessment = assessment_scores[skill.name] / 100.0
        trust = 0.6 * assessment + 0.4 * (base * duration_factor)
    else:
        trust = base * duration_factor * endorsement_boost

    return min(trust, 1.0)


def _normalise(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(_normalise(a.flatten()), _normalise(b.flatten())))


def compute_skills_match(candidate: "CandidateRecord", jd: "ParsedJD") -> float:
    """Return 0.0–1.0: trust-weighted fraction of JD required skills the candidate covers.

    Each JD required skill is matched case-insensitively against the candidate's
    skill list. Matched skills contribute their trust score; unmatched contribute 0.
    The final score is the average trust score across all required skills.
    """
    required = [s.lower() for s in jd.required_skills]
    if not required:
        return 0.0
    if not candidate.skills:
        return 0.0

    assessment_scores = candidate.redrob_signals.skill_assessment_scores
    skill_lookup: dict[str, "SkillEntry"] = {s.name.lower(): s for s in candidate.skills}

    total_trust = 0.0
    for jd_skill in required:
        # Direct name match
        if matched := skill_lookup.get(jd_skill):
            total_trust += skill_trust_score(matched, assessment_scores)
            continue
        # Fuzzy match: substring containment, shared token subset, or matching first word
        jd_tokens = set(jd_skill.split())
        jd_first = jd_skill.split()[0]
        for cname, cskill in skill_lookup.items():
            c_tokens = set(cname.split())
            c_first = cname.split()[0]
            if (jd_skill in cname or cname in jd_skill
                    or jd_tokens <= c_tokens or c_tokens <= jd_tokens
                    or (jd_first == c_first and len(jd_first) > 3)):
                total_trust += skill_trust_score(cskill, assessment_scores)
                break

    return min(total_trust / len(required), 1.0)


def career_semantic_score(
    candidate: "CandidateRecord",
    jd_embedding: np.ndarray,
    embedding_service: "EmbeddingService",
) -> float:
    """Return 0.0–1.0: max-pool cosine similarity of top-3 career descriptions vs JD.

    Uses only career_history descriptions — what the candidate actually built —
    not the full profile text. Max pooling surfaces the single best-matching role.
    """
    descriptions = [j.description for j in candidate.career_history[:3] if j.description.strip()]
    if not descriptions:
        return 0.0

    desc_embeddings = embedding_service.embed_batch(descriptions)  # (N, 384)
    jd_norm = _normalise(jd_embedding.flatten())

    # Normalise each row then dot with jd_norm
    row_norms = np.linalg.norm(desc_embeddings, axis=1, keepdims=True)
    row_norms = np.where(row_norms == 0, 1.0, row_norms)
    similarities = (desc_embeddings / row_norms) @ jd_norm  # (N,)

    return float(max(np.max(similarities), 0.0))  # clamp negatives to 0


def combined_skills_score(
    candidate: "CandidateRecord",
    jd: "ParsedJD",
    jd_embedding: np.ndarray,
    embedding_service: "EmbeddingService",
) -> SkillsMatchScore:
    """Return a SkillsMatchScore combining trust-weighted skills and career semantics.

    Blend: 60% trust-weighted skills match + 40% career semantic similarity.
    Output total is scaled 0–100 for compatibility with the hybrid scoring formula.
    """
    sm = compute_skills_match(candidate, jd)
    cs = career_semantic_score(candidate, jd_embedding, embedding_service)
    total = (0.6 * sm + 0.4 * cs) * 100.0
    return SkillsMatchScore(
        candidate_id=candidate.candidate_id,
        skills_match=sm,
        career_semantic=cs,
        total=round(total, 4),
    )
