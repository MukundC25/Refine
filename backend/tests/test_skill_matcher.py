from __future__ import annotations

import copy
import json
import math
import pathlib
from unittest.mock import MagicMock

import numpy as np
import pytest

from backend.app.core.candidate_loader import SkillEntry, validate_candidate
from backend.app.core.jd_parser import ParsedJD
from backend.app.core.skill_matcher import (
    PROFICIENCY_WEIGHTS,
    SkillsMatchScore,
    career_semantic_score,
    combined_skills_score,
    compute_skills_match,
    skill_trust_score,
)

_SAMPLE_JSON = (
    pathlib.Path(__file__).resolve().parents[3]
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "sample_candidates.json"
)


@pytest.fixture(scope="module")
def sample_raw() -> list[dict]:
    return json.loads(_SAMPLE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cand_0001(sample_raw):
    return validate_candidate(next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001"))


@pytest.fixture(scope="module")
def cand_0002(sample_raw):
    return validate_candidate(next(d for d in sample_raw if d["candidate_id"] == "CAND_0000002"))


@pytest.fixture(scope="module")
def senior_ai_jd() -> ParsedJD:
    return ParsedJD(
        raw_text="Senior AI Engineer, embeddings, vector databases, Python, NLP, retrieval.",
        role_title="Senior AI Engineer",
        required_skills=["embeddings", "vector database", "python", "nlp", "retrieval"],
        preferred_skills=["rag", "llm", "fine-tuning"],
        disqualifying_signals=[],
        min_years_experience=5.0,
        max_years_experience=9.0,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="product_company",
        work_mode="hybrid",
        role_embedding_text="Senior AI engineer skilled in embeddings, vector databases, Python, NLP.",
        jd_hash="test",
        vibe_signals=[],
        hiring_context="",
    )


def _make_skill(name, proficiency, endorsements, duration_months) -> SkillEntry:
    return SkillEntry(name=name, proficiency=proficiency,
                      endorsements=endorsements, duration_months=duration_months)


def _fake_embedding_service(return_matrix: np.ndarray) -> MagicMock:
    svc = MagicMock()
    svc.embed_batch.return_value = return_matrix
    return svc


class TestSkillTrustScore:
    def test_expert_zero_duration_zero_endorsements_low(self):
        skill = _make_skill("Python", "expert", endorsements=0, duration_months=0)
        score = skill_trust_score(skill, {})
        # base=1.0, duration_factor=0.0, endorsement_boost=1.0 → trust = 0.0
        assert score == 0.0

    def test_advanced_50_endorsements_24_months_higher_than_expert_zeros(self):
        stuffer = _make_skill("Python", "expert", endorsements=0, duration_months=0)
        genuine = _make_skill("Python", "advanced", endorsements=50, duration_months=24)
        assert skill_trust_score(genuine, {}) > skill_trust_score(stuffer, {})

    def test_assessment_overrides_self_declared(self):
        # advanced self-declared but assessed at 20/100 → downgraded
        skill = _make_skill("NLP", "advanced", endorsements=30, duration_months=24)
        without_assessment = skill_trust_score(skill, {})
        with_low_assessment = skill_trust_score(skill, {"NLP": 20.0})
        assert with_low_assessment < without_assessment

    def test_high_assessment_boosts_score(self):
        skill = _make_skill("Python", "intermediate", endorsements=5, duration_months=12)
        low = skill_trust_score(skill, {})
        high = skill_trust_score(skill, {"Python": 95.0})
        assert high > low

    def test_duration_saturation_at_36_months(self):
        skill_36 = _make_skill("Python", "expert", endorsements=0, duration_months=36)
        skill_72 = _make_skill("Python", "expert", endorsements=0, duration_months=72)
        # Both should produce the same trust score (duration_factor caps at 1.0)
        assert skill_trust_score(skill_36, {}) == skill_trust_score(skill_72, {})

    def test_endorsement_boost_is_log_scale(self):
        base = _make_skill("Go", "intermediate", endorsements=0, duration_months=12)
        ten = _make_skill("Go", "intermediate", endorsements=10, duration_months=12)
        hundred = _make_skill("Go", "intermediate", endorsements=100, duration_months=12)
        s0 = skill_trust_score(base, {})
        s10 = skill_trust_score(ten, {})
        s100 = skill_trust_score(hundred, {})
        assert s0 < s10 < s100
        # log scale: gain from 0→10 > gain from 10→100 is NOT guaranteed with log1p,
        # but both increments must be positive
        assert s10 - s0 > 0
        assert s100 - s10 > 0

    def test_none_duration_treated_as_zero(self):
        skill_none = SkillEntry(name="Rust", proficiency="expert", endorsements=0, duration_months=None)
        skill_zero = _make_skill("Rust", "expert", endorsements=0, duration_months=0)
        assert skill_trust_score(skill_none, {}) == skill_trust_score(skill_zero, {})

    def test_result_bounded_0_to_1(self):
        for prof in PROFICIENCY_WEIGHTS:
            skill = _make_skill("X", prof, endorsements=999, duration_months=999)
            s = skill_trust_score(skill, {"X": 100.0})
            assert 0.0 <= s <= 1.0, f"out of bounds for proficiency={prof}: {s}"

    def test_all_proficiency_levels_ordered(self):
        # expert > advanced > intermediate > beginner (same duration/endorsements)
        scores = [
            skill_trust_score(_make_skill("S", p, endorsements=10, duration_months=24), {})
            for p in ["beginner", "intermediate", "advanced", "expert"]
        ]
        assert scores == sorted(scores)


class TestComputeSkillsMatch:
    def test_empty_skills_returns_zero(self, sample_raw, senior_ai_jd):
        d = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))
        d["skills"] = []
        r = validate_candidate(d)
        assert compute_skills_match(r, senior_ai_jd) == 0.0

    def test_empty_jd_required_skills_returns_zero(self, cand_0001):
        jd = ParsedJD(
            raw_text="", role_title="", required_skills=[], preferred_skills=[],
            disqualifying_signals=[], min_years_experience=0.0, max_years_experience=0.0,
            preferred_locations=[], notice_period_preference_days=30,
            seniority_level="senior", industry_preference="any", work_mode="hybrid",
            role_embedding_text="", jd_hash="", vibe_signals=[], hiring_context="",
        )
        assert compute_skills_match(cand_0001, jd) == 0.0

    def test_result_bounded_0_to_1(self, cand_0001, senior_ai_jd):
        score = compute_skills_match(cand_0001, senior_ai_jd)
        assert 0.0 <= score <= 1.0

    def test_more_relevant_skills_scores_higher(self, sample_raw, senior_ai_jd):
        # Candidate with NLP + retrieval + Python vs candidate with only SEO
        base = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))

        d_strong = copy.deepcopy(base)
        d_strong["skills"] = [
            {"name": "nlp", "proficiency": "expert", "endorsements": 40, "duration_months": 36},
            {"name": "retrieval", "proficiency": "advanced", "endorsements": 20, "duration_months": 24},
            {"name": "python", "proficiency": "expert", "endorsements": 60, "duration_months": 48},
            {"name": "embeddings", "proficiency": "advanced", "endorsements": 15, "duration_months": 18},
        ]
        d_weak = copy.deepcopy(base)
        d_weak["skills"] = [
            {"name": "SEO", "proficiency": "expert", "endorsements": 40, "duration_months": 36},
            {"name": "Content Marketing", "proficiency": "advanced", "endorsements": 20, "duration_months": 24},
        ]
        strong = compute_skills_match(validate_candidate(d_strong), senior_ai_jd)
        weak = compute_skills_match(validate_candidate(d_weak), senior_ai_jd)
        assert strong > weak

    def test_keyword_stuffer_scores_lower_than_genuine(self, sample_raw, senior_ai_jd):
        # Stuffer: 5 relevant skills, all expert + 0 endorsements + 0 duration
        # Genuine: same skills, advanced + 30 endorsements + 24 months
        base = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))
        skill_names = ["nlp", "python", "embeddings", "retrieval", "vector database"]

        d_stuffer = copy.deepcopy(base)
        d_stuffer["skills"] = [
            {"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 0}
            for n in skill_names
        ]
        d_genuine = copy.deepcopy(base)
        d_genuine["skills"] = [
            {"name": n, "proficiency": "advanced", "endorsements": 30, "duration_months": 24}
            for n in skill_names
        ]
        stuffer_score = compute_skills_match(validate_candidate(d_stuffer), senior_ai_jd)
        genuine_score = compute_skills_match(validate_candidate(d_genuine), senior_ai_jd)
        assert genuine_score > stuffer_score

    def test_assessment_downgrade_reduces_score(self, sample_raw, senior_ai_jd):
        base = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))
        base["skills"] = [
            {"name": "nlp", "proficiency": "advanced", "endorsements": 20, "duration_months": 24},
            {"name": "python", "proficiency": "advanced", "endorsements": 30, "duration_months": 36},
        ]
        # Without assessment scores
        base["redrob_signals"]["skill_assessment_scores"] = {}
        score_no_assessment = compute_skills_match(validate_candidate(base), senior_ai_jd)

        # Add bad assessment scores for both skills
        base["redrob_signals"]["skill_assessment_scores"] = {"nlp": 15.0, "python": 10.0}
        score_bad_assessment = compute_skills_match(validate_candidate(base), senior_ai_jd)

        assert score_bad_assessment < score_no_assessment

    def test_substring_match_works(self, sample_raw, senior_ai_jd):
        # JD requires "vector database"; candidate has "vector db" — substring match
        base = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))
        base["skills"] = [
            {"name": "vector db", "proficiency": "advanced", "endorsements": 10, "duration_months": 12}
        ]
        base["redrob_signals"]["skill_assessment_scores"] = {}
        r = validate_candidate(base)
        # "vector db" should partially match "vector database" via substring
        assert compute_skills_match(r, senior_ai_jd) > 0.0


class TestCareerSemanticScore:
    def test_returns_float_between_0_and_1(self, cand_0001):
        # Mock embedding service returning random unit vectors
        np.random.seed(42)
        desc_count = min(len(cand_0001.career_history), 3)
        matrix = np.random.randn(desc_count, 384).astype(np.float32)
        jd_emb = np.random.randn(384).astype(np.float32)
        svc = _fake_embedding_service(matrix)
        score = career_semantic_score(cand_0001, jd_emb, svc)
        assert 0.0 <= score <= 1.0

    def test_no_career_history_returns_zero(self, sample_raw):
        d = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))
        # Keep one entry but blank description to trigger the empty-description guard
        for j in d["career_history"]:
            j["description"] = "   "
        r = validate_candidate(d)
        svc = _fake_embedding_service(np.empty((0, 384), dtype=np.float32))
        assert career_semantic_score(r, np.zeros(384, dtype=np.float32), svc) == 0.0

    def test_high_similarity_embedding_scores_near_1(self, cand_0001):
        # Make the career embedding identical to the JD embedding → cosine = 1.0
        jd_emb = np.ones(384, dtype=np.float32)
        # All descriptions map to the same vector as the JD
        desc_count = min(len(cand_0001.career_history), 3)
        matrix = np.tile(jd_emb, (desc_count, 1))
        svc = _fake_embedding_service(matrix)
        score = career_semantic_score(cand_0001, jd_emb, svc)
        assert score > 0.99

    def test_orthogonal_embeddings_score_near_0(self, cand_0001):
        jd_emb = np.zeros(384, dtype=np.float32)
        jd_emb[0] = 1.0
        desc_count = min(len(cand_0001.career_history), 3)
        # All zeros except dim 1 — orthogonal to jd_emb
        matrix = np.zeros((desc_count, 384), dtype=np.float32)
        matrix[:, 1] = 1.0
        svc = _fake_embedding_service(matrix)
        score = career_semantic_score(cand_0001, jd_emb, svc)
        assert score < 0.05

    def test_uses_max_pooling_over_descriptions(self, cand_0001):
        # One description matches perfectly, others are orthogonal
        jd_emb = np.zeros(384, dtype=np.float32)
        jd_emb[0] = 1.0
        matrix = np.zeros((3, 384), dtype=np.float32)
        matrix[0, 1] = 1.0   # orthogonal
        matrix[1, 0] = 1.0   # identical to JD → cosine = 1.0
        matrix[2, 2] = 1.0   # orthogonal
        svc = _fake_embedding_service(matrix)
        score = career_semantic_score(cand_0001, jd_emb, svc)
        assert score > 0.99  # max-pool picks the matching description

    def test_embed_batch_called_with_non_empty_descriptions(self, cand_0001):
        svc = _fake_embedding_service(np.random.randn(3, 384).astype(np.float32))
        career_semantic_score(cand_0001, np.random.randn(384).astype(np.float32), svc)
        svc.embed_batch.assert_called_once()
        texts_arg = svc.embed_batch.call_args[0][0]
        assert isinstance(texts_arg, list)
        assert all(t.strip() for t in texts_arg)  # no blank descriptions passed in


class TestCombinedSkillsScore:
    def test_returns_skills_match_score_dataclass(self, cand_0001, senior_ai_jd):
        svc = _fake_embedding_service(np.random.randn(3, 384).astype(np.float32))
        result = combined_skills_score(cand_0001, senior_ai_jd,
                                       np.random.randn(384).astype(np.float32), svc)
        assert isinstance(result, SkillsMatchScore)

    def test_candidate_id_preserved(self, cand_0001, senior_ai_jd):
        svc = _fake_embedding_service(np.random.randn(3, 384).astype(np.float32))
        result = combined_skills_score(cand_0001, senior_ai_jd,
                                       np.random.randn(384).astype(np.float32), svc)
        assert result.candidate_id == "CAND_0000001"

    def test_total_bounded_0_to_100(self, cand_0001, senior_ai_jd):
        svc = _fake_embedding_service(np.random.randn(3, 384).astype(np.float32))
        result = combined_skills_score(cand_0001, senior_ai_jd,
                                       np.random.randn(384).astype(np.float32), svc)
        assert 0.0 <= result.total <= 100.0

    def test_blend_formula_correct(self, cand_0001, senior_ai_jd):
        # Set up controlled embeddings so career_semantic is predictable
        jd_emb = np.ones(384, dtype=np.float32)
        desc_count = min(len(cand_0001.career_history), 3)
        matrix = np.tile(jd_emb, (desc_count, 1))  # cosine = 1.0 → career_semantic = 1.0
        svc = _fake_embedding_service(matrix)

        result = combined_skills_score(cand_0001, senior_ai_jd, jd_emb, svc)
        expected_total = (0.6 * result.skills_match + 0.4 * result.career_semantic) * 100.0
        assert abs(result.total - round(expected_total, 4)) < 0.001

    def test_genuine_engineer_scores_higher_than_stuffer(self, sample_raw, senior_ai_jd):
        base = next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001")
        skill_names = ["nlp", "python", "embeddings", "retrieval", "vector database"]

        d_stuffer = copy.deepcopy(base)
        d_stuffer["skills"] = [
            {"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 0}
            for n in skill_names
        ]
        d_genuine = copy.deepcopy(base)
        d_genuine["skills"] = [
            {"name": n, "proficiency": "advanced", "endorsements": 30, "duration_months": 24}
            for n in skill_names
        ]
        # Use identical embeddings for both so career_semantic is the same
        jd_emb = np.ones(384, dtype=np.float32)
        desc_count = 3
        matrix = np.tile(jd_emb, (desc_count, 1))
        svc_s = _fake_embedding_service(matrix)
        svc_g = _fake_embedding_service(matrix)

        stuffer = combined_skills_score(validate_candidate(d_stuffer), senior_ai_jd, jd_emb, svc_s)
        genuine = combined_skills_score(validate_candidate(d_genuine), senior_ai_jd, jd_emb, svc_g)
        assert genuine.total > stuffer.total

    def test_career_semantic_component_contributes(self, sample_raw, senior_ai_jd):
        # Same skills, but one candidate has semantically matching career text
        base = next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["skills"] = [{"name": "python", "proficiency": "intermediate",
                        "endorsements": 5, "duration_months": 12}]
        d["redrob_signals"]["skill_assessment_scores"] = {}
        r = validate_candidate(d)

        jd_emb = np.ones(384, dtype=np.float32)
        desc_count = 3

        # High career semantic
        high_matrix = np.tile(jd_emb, (desc_count, 1))
        result_high = combined_skills_score(r, senior_ai_jd, jd_emb,
                                            _fake_embedding_service(high_matrix))

        # Zero career semantic (orthogonal embeddings)
        zero_vec = np.zeros(384, dtype=np.float32)
        zero_vec[1] = 1.0
        low_matrix = np.tile(zero_vec, (desc_count, 1))
        result_low = combined_skills_score(r, senior_ai_jd, jd_emb,
                                           _fake_embedding_service(low_matrix))

        assert result_high.total > result_low.total


class TestEdgeCases:
    def test_zero_skills_zero_career_semantic(self, sample_raw, senior_ai_jd):
        d = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))
        d["skills"] = []
        for j in d["career_history"]:
            j["description"] = "  "
        r = validate_candidate(d)
        svc = _fake_embedding_service(np.empty((0, 384), dtype=np.float32))
        result = combined_skills_score(r, senior_ai_jd, np.ones(384, dtype=np.float32), svc)
        assert result.total == 0.0
        assert result.skills_match == 0.0
        assert result.career_semantic == 0.0

    def test_skill_trust_score_single_description_candidate(self, sample_raw, senior_ai_jd):
        d = copy.deepcopy(next(x for x in sample_raw if x["candidate_id"] == "CAND_0000001"))
        d["career_history"] = d["career_history"][:1]
        r = validate_candidate(d)
        svc = _fake_embedding_service(np.random.randn(1, 384).astype(np.float32))
        result = combined_skills_score(r, senior_ai_jd, np.random.randn(384).astype(np.float32), svc)
        assert isinstance(result, SkillsMatchScore)
        assert 0.0 <= result.total <= 100.0

    def test_negative_cosine_clamped_to_zero(self, cand_0001):
        jd_emb = np.ones(384, dtype=np.float32)
        # Negated vector → cosine = -1.0 → should be clamped to 0
        desc_count = min(len(cand_0001.career_history), 3)
        matrix = np.tile(-jd_emb, (desc_count, 1))
        svc = _fake_embedding_service(matrix)
        score = career_semantic_score(cand_0001, jd_emb, svc)
        assert score == 0.0
