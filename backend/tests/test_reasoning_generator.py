from __future__ import annotations

import json
import pathlib
import tempfile
import time

import pytest

from backend.app.core.candidate_loader import CandidateRecord, validate_candidate
from backend.app.core.career_analyzer import CareerTrajectoryScore, analyze_career
from backend.app.core.honeypot_detector import HoneypotResult, detect_honeypot
from backend.app.core.jd_parser import ParsedJD
from backend.app.core.reasoning_generator import (
    MAX_REASONING_CHARS,
    build_behavioral_clause,
    build_experience_clause,
    build_flag_clause,
    build_role_clause,
    build_skills_clause,
    generate_reasoning,
    generate_rich_reasoning_batch,
    load_cached_rich_reasoning,
    truncate_reasoning,
)
from backend.app.core.rule_scorer import score_candidate
from backend.app.core.signal_scorer import BehavioralScore, compute_behavioral_score
from backend.app.core.skill_matcher import SkillsMatchScore


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
def sample_records(sample_raw) -> list[CandidateRecord]:
    return [r for r in (validate_candidate(d) for d in sample_raw) if r is not None]


@pytest.fixture(scope="module")
def senior_ai_jd() -> ParsedJD:
    return ParsedJD(
        raw_text="Senior AI Engineer with 5-9 years experience.",
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
        role_embedding_text="Senior AI engineer with embeddings, retrieval, NLP, Python.",
        jd_hash="test011",
        vibe_signals=[],
        hiring_context="",
    )


def _make_skills_score(cid: str, total: float = 50.0) -> SkillsMatchScore:
    return SkillsMatchScore(candidate_id=cid, skills_match=total / 100.0,
                            career_semantic=0.0, total=total)


def _build_inputs(record: CandidateRecord, jd: ParsedJD):
    """Build the full set of scoring inputs needed by generate_reasoning."""
    rule = score_candidate(record, jd)
    honeypot = detect_honeypot(record)
    skills = _make_skills_score(record.candidate_id)
    career = analyze_career(record, jd)
    behavioral = compute_behavioral_score(record)
    return rule, 0.5, skills, career, behavioral, honeypot


class TestBuildExperienceClause:
    def test_formats_yoe_one_decimal(self, sample_records):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        clause = build_experience_clause(rec)
        assert "6.9 yrs exp" == clause

    def test_zero_yoe(self, sample_records):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rec_zero = rec.model_copy(update={
            "profile": rec.profile.model_copy(update={"years_of_experience": 0.0})
        })
        assert build_experience_clause(rec_zero) == "0.0 yrs exp"


class TestBuildRoleClause:
    def test_includes_title_company_trajectory(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        career = analyze_career(rec, senior_ai_jd)
        clause = build_role_clause(rec, career)
        assert "Backend Engineer" in clause
        assert "Mindtree" in clause
        assert career.trajectory_label in clause
        assert "current " in clause


class TestBuildSkillsClause:
    def test_returns_non_empty_when_skills_present(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        clause = build_skills_clause(rec, jd=senior_ai_jd)
        assert clause and clause != "no skills listed"

    def test_returns_placeholder_when_no_skills(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rec_no_skills = rec.model_copy(update={"skills": []})
        assert build_skills_clause(rec_no_skills, jd=senior_ai_jd) == "no skills listed"

    def test_shows_at_most_3_skills(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        clause = build_skills_clause(rec, jd=senior_ai_jd)
        # Skills are separated by ", " — but a single skill entry may contain commas
        # inside its parens, e.g. "Python (expert, 51 endorsements)". Count top-level
        # entries by splitting on "), " (closing paren before separator).
        entries = clause.split("), ")
        assert len(entries) <= 3

    def test_format_includes_proficiency(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        clause = build_skills_clause(rec, jd=senior_ai_jd)
        # CAND_0000001 has at least one advanced skill in the JD-matching set
        assert any(p in clause for p in ("beginner", "intermediate", "advanced", "expert"))

    def test_endorsements_shown_when_high(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        clause = build_skills_clause(rec, jd=senior_ai_jd)
        # CAND_0000001 has skills like Milvus(40), NLP(37) — endorsements ≥ 20 should show
        assert "endorsements" in clause or "mo" in clause

    def test_falls_back_to_top_skills_when_no_jd_match(self, sample_records):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        unrelated_jd = ParsedJD(
            raw_text="", role_title="", required_skills=["welding", "soldering"],
            preferred_skills=[], disqualifying_signals=[], min_years_experience=0.0,
            max_years_experience=0.0, preferred_locations=[],
            notice_period_preference_days=30, seniority_level="senior",
            industry_preference="any", work_mode="hybrid",
            role_embedding_text="", jd_hash="", vibe_signals=[], hiring_context="",
        )
        clause = build_skills_clause(rec, jd=unrelated_jd)
        assert clause != "no skills listed"


class TestBuildBehavioralClause:
    def test_open_to_work_appears_when_flag_set(self, sample_records):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        behavioral = compute_behavioral_score(rec)
        # CAND_0000001 has open_to_work_flag=True
        clause = build_behavioral_clause(rec, behavioral)
        assert "open to work" in clause

    def test_falls_back_to_generic_when_no_strong_signals(self, sample_records):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        # Override signals to be weak across the board
        sig = rec.redrob_signals.model_copy(update={
            "open_to_work_flag": False,
            "recruiter_response_rate": 0.2,
            "github_activity_score": 5.0,
            "interview_completion_rate": 0.5,
            "verified_email": False,
            "verified_phone": False,
        })
        rec_weak = rec.model_copy(update={"redrob_signals": sig})
        behavioral = compute_behavioral_score(rec_weak)
        assert build_behavioral_clause(rec_weak, behavioral) == "moderate platform engagement"

    def test_github_shown_when_high(self, sample_records):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        sig = rec.redrob_signals.model_copy(update={"github_activity_score": 81.0})
        rec_strong = rec.model_copy(update={"redrob_signals": sig})
        behavioral = compute_behavioral_score(rec_strong)
        clause = build_behavioral_clause(rec_strong, behavioral)
        assert "GitHub 81" in clause


class TestBuildFlagClause:
    def test_empty_when_no_flags(self):
        hp = HoneypotResult(is_suspicious=False, confidence=0.0, flags=[],
                            penalty_multiplier=1.0)
        assert build_flag_clause(hp) == ""

    def test_warning_prefix_when_flags_present(self):
        hp = HoneypotResult(is_suspicious=True, confidence=0.4,
                            flags=["signal_sanity:unverified", "skill_inflation:bulk"],
                            penalty_multiplier=0.4)
        clause = build_flag_clause(hp)
        assert clause.startswith("⚠ flags:")
        assert "signal_sanity:unverified" in clause

    def test_shows_at_most_two_flags(self):
        hp = HoneypotResult(is_suspicious=True, confidence=0.4,
                            flags=["a", "b", "c", "d"], penalty_multiplier=0.0)
        clause = build_flag_clause(hp)
        assert "a" in clause and "b" in clause
        assert "c" not in clause and "d" not in clause


class TestTruncateReasoning:
    def test_short_text_unchanged(self):
        text = "short message"
        assert truncate_reasoning(text) == text

    def test_truncates_at_semicolon_boundary(self):
        text = "; ".join(["clause " + str(i) for i in range(30)])
        out = truncate_reasoning(text, max_chars=100)
        assert len(out) <= 100
        assert out.endswith("…")
        assert "; …" not in out  # truncation point is clean, no orphaned separator

    def test_hard_truncate_when_no_semicolon(self):
        text = "a" * 400
        out = truncate_reasoning(text, max_chars=100)
        assert len(out) == 100
        assert out.endswith("…")

    def test_exact_max_chars(self):
        text = "x" * 300
        assert truncate_reasoning(text, max_chars=300) == text


class TestGenerateReasoning:
    def test_returns_non_empty(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
        result = generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                    final_score=50.0, jd=senior_ai_jd)
        assert result
        assert len(result) > 10

    def test_no_generic_placeholder(self, sample_records, senior_ai_jd):
        for rec in sample_records[:5]:
            rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
            result = generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                        final_score=50.0, jd=senior_ai_jd)
            generic = {"Strong candidate", "High match", "Good candidate", "n/a"}
            assert result not in generic
            assert result.strip() not in {""}

    def test_references_at_least_two_data_points(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
        result = generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                    final_score=50.0, jd=senior_ai_jd)
        # Always contains YoE
        assert f"{rec.profile.years_of_experience:.1f} yrs exp" in result
        # And at least one other concrete reference (company or title or "flags")
        other = (rec.profile.current_company in result
                 or rec.profile.current_title in result
                 or "trajectory" in result)
        assert other

    def test_honeypot_flagged_candidate_shows_warning(self, sample_records, senior_ai_jd):
        # CAND_0000002 has penalty 0.7 with one flag
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000002")
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
        assert honeypot.penalty_multiplier < 1.0
        result = generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                    final_score=30.0, jd=senior_ai_jd)
        assert "⚠ flags:" in result

    def test_clean_candidate_says_no_flags(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
        assert honeypot.penalty_multiplier == 1.0
        result = generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                    final_score=70.0, jd=senior_ai_jd)
        assert "no flags" in result
        assert "⚠ flags:" not in result

    def test_max_300_chars(self, sample_records, senior_ai_jd):
        for rec in sample_records:
            rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
            result = generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                        final_score=50.0, jd=senior_ai_jd)
            assert len(result) <= MAX_REASONING_CHARS

    def test_different_candidates_produce_different_strings(self, sample_records, senior_ai_jd):
        outputs = set()
        for rec in sample_records[:10]:
            rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
            outputs.add(generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                           final_score=50.0, jd=senior_ai_jd))
        # At least 8 of 10 should be unique (allow rare collisions for similar profiles)
        assert len(outputs) >= 8

    def test_strong_signal_candidate_has_more_clauses_than_weak(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)

        strong_sig = rec.redrob_signals.model_copy(update={
            "open_to_work_flag": True, "recruiter_response_rate": 0.9,
            "avg_response_time_hours": 2.0, "github_activity_score": 85.0,
            "interview_completion_rate": 0.95, "verified_email": True, "verified_phone": True,
        })
        rec_strong = rec.model_copy(update={"redrob_signals": strong_sig})
        beh_strong = compute_behavioral_score(rec_strong)

        weak_sig = rec.redrob_signals.model_copy(update={
            "open_to_work_flag": False, "recruiter_response_rate": 0.1,
            "github_activity_score": 0.0, "interview_completion_rate": 0.3,
            "verified_email": False, "verified_phone": False,
        })
        rec_weak = rec.model_copy(update={"redrob_signals": weak_sig})
        beh_weak = compute_behavioral_score(rec_weak)

        r_strong = generate_reasoning(rec_strong, rule, sim, skills, career, beh_strong,
                                      honeypot, final_score=80.0, jd=senior_ai_jd)
        r_weak = generate_reasoning(rec_weak, rule, sim, skills, career, beh_weak,
                                    honeypot, final_score=20.0, jd=senior_ai_jd)
        # Strong signals produce more positive content
        strong_signal_count = sum(s in r_strong for s in
                                  ["open to work", "GitHub", "interview completion", "verified profile"])
        weak_signal_count = sum(s in r_weak for s in
                                ["open to work", "GitHub", "interview completion", "verified profile"])
        assert strong_signal_count > weak_signal_count

    def test_works_without_jd(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec, senior_ai_jd)
        result = generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                    final_score=50.0, jd=None)
        assert result and len(result) <= MAX_REASONING_CHARS


class TestRichReasoningBatch:
    def test_no_gemini_service_falls_back_to_templates(self, sample_records, senior_ai_jd, tmp_path):
        # Build a small set of RankedCandidate stubs
        from backend.app.core.ranking_engine import (
            RankedCandidate, stage1_from_records, stage2_semantic_rerank,
            stage3_behavioral_boost,
        )
        from backend.app.core.embedding_service import EmbeddingService
        from backend.tests.test_ranking_engine import FakeEmbeddingService

        svc = FakeEmbeddingService()
        s1 = stage1_from_records(sample_records[:3], senior_ai_jd, top_n=3)
        jd_emb = svc.embed_text(senior_ai_jd.role_embedding_text)
        s2 = stage2_semantic_rerank(s1, senior_ai_jd, jd_emb, svc, top_n=3)
        ranked = stage3_behavioral_boost(s2, senior_ai_jd, top_n=3)

        cache_path = tmp_path / "rich.json"
        result = generate_rich_reasoning_batch(ranked, senior_ai_jd,
                                               gemini_service=None,
                                               cache_path=str(cache_path))
        assert len(result) == len(ranked)
        for rc in ranked:
            assert result[rc.candidate.candidate_id] == rc.reasoning
        # File was written
        assert cache_path.exists()
        loaded = json.loads(cache_path.read_text())
        assert loaded == result

    def test_uses_gemini_when_provided(self, sample_records, senior_ai_jd, tmp_path):
        from backend.app.core.ranking_engine import (
            stage1_from_records, stage2_semantic_rerank, stage3_behavioral_boost,
        )
        from backend.tests.test_ranking_engine import FakeEmbeddingService

        svc = FakeEmbeddingService()
        s1 = stage1_from_records(sample_records[:2], senior_ai_jd, top_n=2)
        jd_emb = svc.embed_text(senior_ai_jd.role_embedding_text)
        s2 = stage2_semantic_rerank(s1, senior_ai_jd, jd_emb, svc, top_n=2)
        ranked = stage3_behavioral_boost(s2, senior_ai_jd, top_n=2)

        class FakeGemini:
            def generate(self, prompt: str) -> str:
                return "Fake rich reasoning for the candidate based on prompt."

        result = generate_rich_reasoning_batch(ranked, senior_ai_jd,
                                               gemini_service=FakeGemini(),
                                               cache_path=str(tmp_path / "rich.json"))
        for rc in ranked:
            assert "Fake rich reasoning" in result[rc.candidate.candidate_id]

    def test_gemini_failure_falls_back_to_template(self, sample_records, senior_ai_jd, tmp_path):
        from backend.app.core.ranking_engine import (
            stage1_from_records, stage2_semantic_rerank, stage3_behavioral_boost,
        )
        from backend.tests.test_ranking_engine import FakeEmbeddingService

        svc = FakeEmbeddingService()
        s1 = stage1_from_records(sample_records[:1], senior_ai_jd, top_n=1)
        jd_emb = svc.embed_text(senior_ai_jd.role_embedding_text)
        s2 = stage2_semantic_rerank(s1, senior_ai_jd, jd_emb, svc, top_n=1)
        ranked = stage3_behavioral_boost(s2, senior_ai_jd, top_n=1)

        class BrokenGemini:
            def generate(self, prompt: str) -> str:
                raise RuntimeError("API down")

        result = generate_rich_reasoning_batch(ranked, senior_ai_jd,
                                               gemini_service=BrokenGemini(),
                                               cache_path=str(tmp_path / "rich.json"))
        # Falls back to template — same as ranked[0].reasoning
        assert result[ranked[0].candidate.candidate_id] == ranked[0].reasoning


class TestLoadCachedRichReasoning:
    def test_missing_file_returns_empty(self):
        assert load_cached_rich_reasoning("/nonexistent/path.json") == {}

    def test_loads_valid_json(self, tmp_path):
        cache = tmp_path / "rich.json"
        cache.write_text(json.dumps({"CAND_0000001": "rich reasoning text"}))
        assert load_cached_rich_reasoning(str(cache)) == {"CAND_0000001": "rich reasoning text"}

    def test_malformed_json_returns_empty(self, tmp_path):
        cache = tmp_path / "rich.json"
        cache.write_text("not valid json {")
        assert load_cached_rich_reasoning(str(cache)) == {}


class TestPerformance:
    def test_runs_under_1ms_per_candidate(self, sample_records, senior_ai_jd):
        # Pre-build all inputs to exclude scoring overhead
        prepared = [(rec, *_build_inputs(rec, senior_ai_jd)) for rec in sample_records]
        start = time.perf_counter()
        n_iter = 100
        for _ in range(n_iter):
            for rec, rule, sim, skills, career, behavioral, honeypot in prepared:
                generate_reasoning(rec, rule, sim, skills, career, behavioral, honeypot,
                                   final_score=50.0, jd=senior_ai_jd)
        elapsed = time.perf_counter() - start
        per_call_ms = (elapsed / (n_iter * len(prepared))) * 1000
        assert per_call_ms < 1.0, f"{per_call_ms:.3f} ms per call exceeds 1 ms budget"


class TestOrchestratorIntegration:
    def test_ranked_candidate_has_reasoning_populated(self, sample_records, senior_ai_jd):
        from backend.app.core.ranking_engine import RankingEngine
        from backend.tests.test_ranking_engine import FakeEmbeddingService

        engine = RankingEngine(embedding_service=FakeEmbeddingService())
        ranked = engine.rank_records(sample_records[:5], senior_ai_jd, top_n_final=5)
        for rc in ranked:
            assert rc.reasoning
            assert len(rc.reasoning) <= MAX_REASONING_CHARS
            assert f"{rc.candidate.profile.years_of_experience:.1f} yrs exp" in rc.reasoning

    def test_rich_reasoning_cache_overrides_template(self, sample_records, senior_ai_jd, tmp_path):
        from backend.app.core.ranking_engine import RankingEngine
        from backend.tests.test_ranking_engine import FakeEmbeddingService

        target_id = sample_records[0].candidate_id
        custom = "Custom pre-computed rich reasoning for this candidate."
        cache = tmp_path / "rich.json"
        cache.write_text(json.dumps({target_id: custom}))

        engine = RankingEngine(
            embedding_service=FakeEmbeddingService(),
            rich_reasoning_path=str(cache),
        )
        ranked = engine.rank_records(sample_records[:5], senior_ai_jd, top_n_final=5)
        target = next(rc for rc in ranked if rc.candidate.candidate_id == target_id)
        assert target.reasoning == custom


class TestEdgeCases:
    def test_candidate_with_empty_skills(self, sample_records, senior_ai_jd):
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        rec_no_skills = rec.model_copy(update={"skills": []})
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(rec_no_skills, senior_ai_jd)
        result = generate_reasoning(rec_no_skills, rule, sim, skills, career, behavioral,
                                    honeypot, final_score=50.0, jd=senior_ai_jd)
        assert "no skills listed" in result
        assert len(result) <= MAX_REASONING_CHARS

    def test_candidate_with_no_career_history(self, sample_records, senior_ai_jd):
        # CandidateRecord requires min 1 career entry, so we can't truly empty it.
        # Verify the function still works with a single-entry career instead.
        rec = next(r for r in sample_records if r.candidate_id == "CAND_0000001")
        single = rec.model_copy(update={"career_history": [rec.career_history[0]]})
        rule, sim, skills, career, behavioral, honeypot = _build_inputs(single, senior_ai_jd)
        result = generate_reasoning(single, rule, sim, skills, career, behavioral,
                                    honeypot, final_score=50.0, jd=senior_ai_jd)
        assert result and len(result) <= MAX_REASONING_CHARS
