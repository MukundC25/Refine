from __future__ import annotations

import copy
import json
import pathlib
import time

import pytest

from backend.app.core.candidate_loader import CandidateRecord, validate_candidate
from backend.app.core.jd_parser import ParsedJD
from backend.app.core.rule_scorer import (
    RuleScore,
    apply_disqualifiers,
    batch_score,
    score_candidate,
    score_experience,
    score_industry_background,
    score_skills_overlap,
    score_title,
)

from backend.tests.test_schemas import _SAMPLE_JSON


@pytest.fixture(scope="module")
def sample_raw() -> list[dict]:
    return json.loads(_SAMPLE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sample_records(sample_raw) -> list[CandidateRecord]:
    return [r for r in (validate_candidate(d) for d in sample_raw) if r is not None]


def _get(raw_list: list[dict], cid: str) -> CandidateRecord:
    for d in raw_list:
        if d["candidate_id"] == cid:
            r = validate_candidate(d)
            assert r is not None
            return r
    raise KeyError(cid)


def _clone(raw_list: list[dict], cid: str, **overrides) -> CandidateRecord:
    base = next(d for d in raw_list if d["candidate_id"] == cid)
    d = copy.deepcopy(base)
    for key, val in overrides.items():
        parts = key.split(".")
        node = d
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = val
    r = validate_candidate(d)
    assert r is not None
    return r


@pytest.fixture(scope="module")
def senior_ai_jd() -> ParsedJD:
    return ParsedJD(
        raw_text="Senior AI Engineer with 5-9 years experience in embeddings, vector databases, Python.",
        role_title="Senior AI Engineer",
        required_skills=[
            "embeddings", "vector database", "python", "retrieval", "nlp",
            "ranking", "transformer", "search", "bert", "information retrieval",
        ],
        preferred_skills=["rag", "llm", "fine-tuning", "huggingface", "learning to rank"],
        disqualifying_signals=[],
        min_years_experience=5.0,
        max_years_experience=9.0,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="product_company",
        work_mode="hybrid",
        role_embedding_text="Senior AI Engineer role.",
        jd_hash="abc123",
        vibe_signals=[],
        hiring_context="",
    )


@pytest.fixture(scope="module")
def empty_jd() -> ParsedJD:
    return ParsedJD(
        raw_text="Looking for a strong engineer.",
        role_title="Engineer",
        required_skills=[],
        preferred_skills=[],
        disqualifying_signals=[],
        min_years_experience=0.0,
        max_years_experience=0.0,
        preferred_locations=[],
        notice_period_preference_days=30,
        seniority_level="senior",
        industry_preference="any",
        work_mode="hybrid",
        role_embedding_text="Strong engineer needed.",
        jd_hash="empty",
        vibe_signals=[],
        hiring_context="",
    )


class TestScoreExperience:
    def test_in_range_scores_30(self, sample_raw, senior_ai_jd):
        r = _get(sample_raw, "CAND_0000001")  # yoe = 6.9, inside [5,9]
        assert score_experience(r, senior_ai_jd) == 30.0

    def test_slightly_junior_scores_20(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.years_of_experience": 4.0})
        assert score_experience(r, senior_ai_jd) == 20.0

    def test_very_junior_scores_at_most_10(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.years_of_experience": 1.5})
        assert score_experience(r, senior_ai_jd) <= 10.0

    def test_slightly_over_scores_20(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.years_of_experience": 11.0})
        assert score_experience(r, senior_ai_jd) == 20.0

    def test_significantly_over_scores_12(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.years_of_experience": 18.0})
        assert score_experience(r, senior_ai_jd) == 12.0

    def test_fallback_range_when_jd_empty(self, sample_raw, empty_jd):
        r_ideal = _clone(sample_raw, "CAND_0000001", **{"profile.years_of_experience": 7.0})
        r_junior = _clone(sample_raw, "CAND_0000001", **{"profile.years_of_experience": 1.0})
        assert score_experience(r_ideal, empty_jd) == 30.0
        assert score_experience(r_junior, empty_jd) < 15.0

    def test_bounded_0_to_30(self, sample_raw, senior_ai_jd):
        for yoe in [0, 3, 7, 12, 25]:
            r = _clone(sample_raw, "CAND_0000001", **{"profile.years_of_experience": float(yoe)})
            assert 0.0 <= score_experience(r, senior_ai_jd) <= 30.0


class TestScoreTitle:
    def test_ai_ml_title_scores_20(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.current_title": "ML Engineer"})
        assert score_title(r, senior_ai_jd) == 20.0

    def test_senior_ai_engineer_scores_20(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.current_title": "Senior AI Engineer"})
        assert score_title(r, senior_ai_jd) == 20.0

    def test_nlp_engineer_scores_20(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.current_title": "NLP Engineer"})
        assert score_title(r, senior_ai_jd) == 20.0

    def test_senior_software_engineer_scores_16(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.current_title": "Senior Software Engineer"})
        assert score_title(r, senior_ai_jd) == 16.0

    def test_software_engineer_scores_12(self, sample_raw, senior_ai_jd):
        r = _clone(sample_raw, "CAND_0000001", **{"profile.current_title": "Software Engineer"})
        assert score_title(r, senior_ai_jd) == 12.0

    def test_backend_engineer_scores_12(self, sample_raw, senior_ai_jd):
        r = _get(sample_raw, "CAND_0000001")
        assert score_title(r, senior_ai_jd) == 12.0

    def test_data_analyst_scores_12(self, sample_raw, senior_ai_jd):
        # "data" is a technical keyword so Data Analyst → 12, not 8
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["profile"]["current_title"] = "Data Analyst"
        for j in d["career_history"]:
            j["title"] = "Data Analyst"
        r = validate_candidate(d)
        assert score_title(r, senior_ai_jd) == 12.0

    def test_business_analyst_scores_8(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["profile"]["current_title"] = "Business Analyst"
        for j in d["career_history"]:
            j["title"] = "Business Analyst"
        r = validate_candidate(d)
        assert score_title(r, senior_ai_jd) == 8.0

    def test_fully_nontechnical_career_scores_0(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["profile"]["current_title"] = "Marketing Manager"
        for j in d["career_history"]:
            j["title"] = "Marketing Manager"
        r = validate_candidate(d)
        assert score_title(r, senior_ai_jd) == 0.0

    def test_nontechnical_current_but_technical_career_uses_fallback(self, sample_raw, senior_ai_jd):
        # Career history[0] is still Backend Engineer → fallback gives ≥12
        r = _clone(sample_raw, "CAND_0000001", **{"profile.current_title": "Marketing Manager"})
        assert score_title(r, senior_ai_jd) >= 12.0

    def test_bounded_0_to_20(self, sample_raw, senior_ai_jd):
        for title in ["ML Engineer", "Backend Engineer", "Accountant", "Data Scientist"]:
            r = _clone(sample_raw, "CAND_0000001", **{"profile.current_title": title})
            assert 0.0 <= score_title(r, senior_ai_jd) <= 20.0


class TestScoreSkillsOverlap:
    def test_milvus_covers_vector_database_alias(self, sample_raw, senior_ai_jd):
        r = _get(sample_raw, "CAND_0000001")
        assert score_skills_overlap(r, senior_ai_jd) > 0.0

    def test_nlp_skill_direct_match(self, sample_raw, senior_ai_jd):
        r = _get(sample_raw, "CAND_0000001")
        assert score_skills_overlap(r, senior_ai_jd) > 5.0

    def test_no_skills_no_prose_scores_zero(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["skills"] = []
        d["profile"]["headline"] = "Professional"
        d["profile"]["summary"] = "Experienced professional."
        for j in d["career_history"]:
            j["description"] = "Managed teams."
        r = validate_candidate(d)
        assert score_skills_overlap(r, senior_ai_jd) == 0.0

    def test_full_required_coverage_approaches_20(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["skills"] = [
            {"name": s, "proficiency": "advanced", "endorsements": 10, "duration_months": 24}
            for s in senior_ai_jd.required_skills
        ]
        r = validate_candidate(d)
        assert score_skills_overlap(r, senior_ai_jd) >= 18.0

    def test_preferred_coverage_adds_5(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["skills"] = [
            {"name": s, "proficiency": "expert", "endorsements": 5, "duration_months": 12}
            for s in list(senior_ai_jd.required_skills) + list(senior_ai_jd.preferred_skills)
        ]
        r = validate_candidate(d)
        assert score_skills_overlap(r, senior_ai_jd) >= 24.0

    def test_bounded_0_to_25(self, sample_raw, senior_ai_jd):
        r = _get(sample_raw, "CAND_0000001")
        assert 0.0 <= score_skills_overlap(r, senior_ai_jd) <= 25.0

    def test_uses_default_skills_when_jd_empty(self, sample_raw, empty_jd):
        r = _get(sample_raw, "CAND_0000001")
        assert 0.0 <= score_skills_overlap(r, empty_jd) <= 25.0

    def test_pinecone_covers_vector_database(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["skills"] = [{"name": "Pinecone", "proficiency": "advanced", "endorsements": 10, "duration_months": 18}]
        d["profile"]["headline"] = ""
        d["profile"]["summary"] = ""
        for j in d["career_history"]:
            j["description"] = ""
        r = validate_candidate(d)
        assert score_skills_overlap(r, senior_ai_jd) > 0.0


class TestScoreIndustryBackground:
    def test_all_product_scores_15(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        for job in d["career_history"]:
            job["company"] = "Meesho"
            job["duration_months"] = max(job["duration_months"], 1)
        r = validate_candidate(d)
        assert score_industry_background(r) == 15.0

    def test_all_outsourcing_scores_2(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        for job in d["career_history"]:
            job["company"] = "TCS"
            job["duration_months"] = 24
        r = validate_candidate(d)
        assert score_industry_background(r) == 2.0

    def test_50_50_split_scores_10(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["career_history"] = [
            {"company": "Meesho", "title": "SWE", "start_date": "2020-01-01",
             "end_date": "2022-01-01", "duration_months": 24, "is_current": False,
             "industry": "E-commerce", "company_size": "1001-5000", "description": "Built APIs."},
            {"company": "TCS", "title": "SWE", "start_date": "2022-01-01",
             "end_date": None, "duration_months": 24, "is_current": True,
             "industry": "IT Services", "company_size": "10001+", "description": "Consulting."},
        ]
        r = validate_candidate(d)
        assert score_industry_background(r) == 10.0

    def test_bounded_0_to_15(self, sample_raw):
        r = _get(sample_raw, "CAND_0000001")
        assert 0.0 <= score_industry_background(r) <= 15.0

    def test_zero_duration_no_crash(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        for job in d["career_history"]:
            job["duration_months"] = 0
        r = validate_candidate(d)
        assert 0.0 <= score_industry_background(r) <= 15.0


class TestApplyDisqualifiers:
    def test_technical_candidate_clean(self, sample_raw, senior_ai_jd):
        r = _get(sample_raw, "CAND_0000001")
        assert apply_disqualifiers(r, senior_ai_jd) == 0.0

    def test_keyword_stuffer_disqualified(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000002")
        d = copy.deepcopy(base)
        for j in d["career_history"]:
            j["title"] = "Marketing Manager"
            j["description"] = "Managed campaigns. Coordinated with vendors."
        d["profile"]["current_title"] = "Marketing Manager"
        d["skills"] = [
            {"name": n, "proficiency": "expert", "endorsements": 0, "duration_months": 0}
            for n in ["TensorFlow", "PyTorch", "NLP", "Deep Learning", "Hugging Face Transformers"]
        ]
        assert apply_disqualifiers(validate_candidate(d), senior_ai_jd) == -50.0

    def test_technical_prose_prevents_disqualification(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000002")
        d = copy.deepcopy(base)
        for j in d["career_history"]:
            j["title"] = "Marketing Manager"
            j["description"] = "Used Python scripts to automate data pipelines and model reporting."
        d["profile"]["current_title"] = "Marketing Manager"
        d["skills"] = [
            {"name": n, "proficiency": "expert", "endorsements": 5, "duration_months": 12}
            for n in ["TensorFlow", "PyTorch", "NLP", "Deep Learning"]
        ]
        assert apply_disqualifiers(validate_candidate(d), senior_ai_jd) == 0.0

    def test_nontechnical_junior_no_history_disqualified(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000002")
        d = copy.deepcopy(base)
        d["profile"]["current_title"] = "Accountant"
        d["profile"]["years_of_experience"] = 1.0
        for j in d["career_history"]:
            j["title"] = "Accountant"
            j["description"] = "Prepared financial statements."
        d["skills"] = []
        assert apply_disqualifiers(validate_candidate(d), senior_ai_jd) == -50.0

    def test_returns_only_0_or_minus50(self, sample_raw, senior_ai_jd):
        for cid in ["CAND_0000001", "CAND_0000002"]:
            assert apply_disqualifiers(_get(sample_raw, cid), senior_ai_jd) in (0.0, -50.0)


class TestScoreCandidate:
    def test_returns_rule_score(self, sample_raw, senior_ai_jd):
        assert isinstance(score_candidate(_get(sample_raw, "CAND_0000001"), senior_ai_jd), RuleScore)

    def test_candidate_id_preserved(self, sample_raw, senior_ai_jd):
        assert score_candidate(_get(sample_raw, "CAND_0000001"), senior_ai_jd).candidate_id == "CAND_0000001"

    def test_total_never_negative(self, sample_raw, senior_ai_jd):
        for cid in ["CAND_0000001", "CAND_0000002"]:
            assert score_candidate(_get(sample_raw, cid), senior_ai_jd).total >= 0.0

    def test_strong_ml_engineer_scores_above_70(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["profile"]["current_title"] = "ML Engineer"
        d["profile"]["years_of_experience"] = 6.0
        d["profile"]["current_company"] = "Meesho"
        d["career_history"][0]["company"] = "Meesho"
        d["career_history"][0]["title"] = "ML Engineer"
        d["skills"] = [
            {"name": "embeddings", "proficiency": "expert", "endorsements": 30, "duration_months": 36},
            {"name": "Python", "proficiency": "expert", "endorsements": 50, "duration_months": 72},
            {"name": "vector database", "proficiency": "advanced", "endorsements": 15, "duration_months": 24},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 20, "duration_months": 30},
            {"name": "retrieval", "proficiency": "advanced", "endorsements": 10, "duration_months": 18},
            {"name": "transformer", "proficiency": "advanced", "endorsements": 12, "duration_months": 24},
            {"name": "RAG", "proficiency": "advanced", "endorsements": 8, "duration_months": 12},
        ]
        result = score_candidate(validate_candidate(d), senior_ai_jd)
        assert result.total >= 70.0, f"scored {result.total:.1f}, expected ≥70"

    def test_nontechnical_career_suppressed_by_title_and_industry(self, sample_raw, senior_ai_jd):
        # exp=30 (in-range), title=0, skills~0, industry=2, disq=0 → total ≤35
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000002")
        d = copy.deepcopy(base)
        d["profile"]["current_title"] = "Marketing Manager"
        d["profile"]["years_of_experience"] = 8.0
        for j in d["career_history"]:
            j["title"] = "Marketing Manager"
            j["company"] = "TCS"
            j["description"] = "Managed brand campaigns and vendor relationships."
        d["profile"]["headline"] = "Marketing Professional"
        d["profile"]["summary"] = "Experienced marketing manager."
        d["skills"] = [{"name": "SEO", "proficiency": "expert", "endorsements": 10, "duration_months": 48}]
        result = score_candidate(validate_candidate(d), senior_ai_jd)
        assert result.total <= 35.0
        assert result.title_score == 0.0
        assert result.industry_score == 2.0

    def test_components_sum_to_total(self, sample_raw, senior_ai_jd):
        for cid in ["CAND_0000001", "CAND_0000002"]:
            rs = score_candidate(_get(sample_raw, cid), senior_ai_jd)
            expected = max(0.0, rs.experience_score + rs.title_score + rs.skills_score
                           + rs.industry_score + rs.disqualifier_penalty)
            assert abs(rs.total - expected) < 0.001

    def test_deterministic(self, sample_raw, senior_ai_jd):
        r = _get(sample_raw, "CAND_0000001")
        r1 = score_candidate(r, senior_ai_jd)
        r2 = score_candidate(r, senior_ai_jd)
        assert r1.total == r2.total


class TestBatchScore:
    def test_preserves_length(self, sample_records, senior_ai_jd):
        assert len(batch_score(sample_records, senior_ai_jd)) == len(sample_records)

    def test_preserves_order(self, sample_records, senior_ai_jd):
        scores = batch_score(sample_records, senior_ai_jd)
        for record, score in zip(sample_records, scores):
            assert score.candidate_id == record.candidate_id

    def test_empty_list(self, senior_ai_jd):
        assert batch_score([], senior_ai_jd) == []

    def test_matches_individual_calls(self, sample_records, senior_ai_jd):
        for record, bs in zip(sample_records, batch_score(sample_records, senior_ai_jd)):
            assert bs.total == score_candidate(record, senior_ai_jd).total

    def test_deterministic_across_calls(self, sample_records, senior_ai_jd):
        a = batch_score(sample_records, senior_ai_jd)
        b = batch_score(sample_records, senior_ai_jd)
        assert all(x.total == y.total for x, y in zip(a, b))


class TestPerformance:
    def test_10k_in_under_5_seconds(self, sample_raw, senior_ai_jd):
        base = [r for r in (validate_candidate(d) for d in sample_raw) if r is not None]
        candidates = (base * ((10_000 // len(base)) + 1))[:10_000]
        start = time.perf_counter()
        scores = batch_score(candidates, senior_ai_jd)
        elapsed = time.perf_counter() - start
        assert len(scores) == 10_000
        assert elapsed < 5.0, f"took {elapsed:.2f}s, expected <5s"


class TestEdgeCases:
    def test_zero_skills_no_crash(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["skills"] = []
        result = score_candidate(validate_candidate(d), senior_ai_jd)
        assert isinstance(result, RuleScore)
        assert result.total >= 0.0

    def test_zero_skills_and_no_prose_skills_score_zero(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["skills"] = []
        d["profile"]["headline"] = "Professional"
        d["profile"]["summary"] = "Experienced professional."
        for j in d["career_history"]:
            j["description"] = "Managed team and delivered projects."
        assert score_candidate(validate_candidate(d), senior_ai_jd).skills_score == 0.0

    def test_single_career_entry_no_crash(self, sample_raw, senior_ai_jd):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["career_history"] = d["career_history"][:1]
        result = score_candidate(validate_candidate(d), senior_ai_jd)
        assert 0.0 <= result.industry_score <= 15.0

    def test_all_components_in_range(self, sample_records, senior_ai_jd):
        for record in sample_records:
            rs = score_candidate(record, senior_ai_jd)
            assert 0.0 <= rs.experience_score <= 30.0
            assert 0.0 <= rs.title_score <= 20.0
            assert 0.0 <= rs.skills_score <= 25.0
            assert 0.0 <= rs.industry_score <= 15.0
            assert rs.disqualifier_penalty in (0.0, -50.0)
            assert rs.total >= 0.0
