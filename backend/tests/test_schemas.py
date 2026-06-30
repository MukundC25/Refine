"""
test_schemas.py — Tests for backend/app/models/schemas.py.

Acceptance criteria verified
-----------------------------
  AC1  All sample candidates in sample_candidates.json parse via
       CandidateRecord.model_validate()
  AC2  CandidateRecord with an invalid candidate_id raises ValidationError
  AC3  SkillEntry with negative endorsements raises ValidationError
  AC4  RedrobSignals.offer_acceptance_rate = -1 is valid (no-history sentinel)
  AC5  RedrobSignals.github_activity_score = -1 is valid (not-linked sentinel)
  AC6  All existing schemas in schemas.py are unchanged and importable
  AC7  CandidateRecord round-trips: model_dump() → model_validate() losslessly
  AC8  Import of new models does not break existing resume-processing router
       imports (ResumeInput, RefinementInput, EvaluationOutput, etc.)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SAMPLE_JSON = (
    _REPO_ROOT
    / "[PUB] India_runs_data_and_ai_challenge"
    / "[PUB] India_runs_data_and_ai_challenge"
    / "India_runs_data_and_ai_challenge"
    / "sample_candidates.json"
)

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from backend.app.models.schemas import (
    # ── New candidate-dataset models ──────────────────────────────────────── #
    CandidateRecord,
    CareerEntry,
    CertEntry,
    EducationEntry,
    # ── Existing resume-optimisation models (must remain unchanged) ────────── #
    EvaluationOutput,
    HoneypotResult,
    LanguageEntry,
    ParsedJD,
    ProfileBlock,
    # ── Existing ranking API models ──────────────────────────────────────── #
    RankedCandidateResponse,
    RankingResponse,
    RankingStatusResponse,
    RedrobSignals,
    RefinedResumeOutput,
    RefinementInput,
    ReRankRequest,
    ResumeInput,
    RuleScore,
    RuleScoreSchema,
    ScoreBreakdown,
    SkillEntry,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def schema_sample_records() -> list[dict]:
    """Raw candidate dicts from sample_candidates.json — fixture name is unique
    to avoid collisions with same-named fixtures in other test modules."""
    with open(_SAMPLE_JSON, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# AC1 — All sample candidates parse correctly
# ---------------------------------------------------------------------------


class TestSampleCandidatesParse:
    """CandidateRecord.model_validate() must succeed for every sample record."""

    def test_all_records_parse(self, schema_sample_records):
        """Every record in sample_candidates.json must validate without error."""
        for raw in schema_sample_records:
            cid = raw.get("candidate_id", "<unknown>")
            try:
                rec = CandidateRecord.model_validate(raw)
                assert rec.candidate_id == cid
            except ValidationError as exc:
                pytest.fail(f"{cid} failed validation:\n{exc}")

    def test_parse_count_matches_file(self, schema_sample_records):
        """The number of successfully parsed records equals the file's record count."""
        parsed = [CandidateRecord.model_validate(r) for r in schema_sample_records]
        assert len(parsed) == len(schema_sample_records)

    def test_career_history_is_list_of_career_entries(self, schema_sample_records):
        for raw in schema_sample_records:
            rec = CandidateRecord.model_validate(raw)
            assert isinstance(rec.career_history, list)
            assert all(isinstance(e, CareerEntry) for e in rec.career_history)

    def test_dates_are_date_objects(self, schema_sample_records):
        """Date strings must be coerced to datetime.date, not remain as strings."""
        rec = CandidateRecord.model_validate(schema_sample_records[0])
        assert isinstance(rec.redrob_signals.signup_date, date)
        assert isinstance(rec.redrob_signals.last_active_date, date)
        assert isinstance(rec.career_history[0].start_date, date)

    def test_nullable_end_date_accepted(self, schema_sample_records):
        """Career entries for current roles have end_date=None — must not error."""
        for raw in schema_sample_records:
            rec = CandidateRecord.model_validate(raw)
            for entry in rec.career_history:
                if entry.is_current:
                    assert entry.end_date is None

    def test_profile_block_fields_populated(self, schema_sample_records):
        rec = CandidateRecord.model_validate(schema_sample_records[0])
        assert rec.profile.anonymized_name
        assert rec.profile.headline
        assert rec.profile.current_title
        assert rec.profile.years_of_experience >= 0

    def test_redrob_signals_present(self, schema_sample_records):
        rec = CandidateRecord.model_validate(schema_sample_records[0])
        sig = rec.redrob_signals
        assert 0 <= sig.profile_completeness_score <= 100
        assert sig.preferred_work_mode in {"remote", "hybrid", "onsite", "flexible"}

    def test_education_entries_have_valid_tiers(self, schema_sample_records):
        valid_tiers = {"tier_1", "tier_2", "tier_3", "tier_4", "unknown"}
        for raw in schema_sample_records:
            rec = CandidateRecord.model_validate(raw)
            for edu in rec.education:
                assert edu.tier in valid_tiers

    def test_skill_entries_have_valid_proficiency(self, schema_sample_records):
        valid = {"beginner", "intermediate", "advanced", "expert"}
        for raw in schema_sample_records:
            rec = CandidateRecord.model_validate(raw)
            for sk in rec.skills:
                assert sk.proficiency in valid

    def test_language_entries_have_valid_proficiency(self, schema_sample_records):
        valid = {"basic", "conversational", "professional", "native"}
        for raw in schema_sample_records:
            rec = CandidateRecord.model_validate(raw)
            for lang in rec.languages:
                assert lang.proficiency in valid


# ---------------------------------------------------------------------------
# AC2 — Invalid candidate_id raises ValidationError
# ---------------------------------------------------------------------------


class TestCandidateIdValidation:
    """candidate_id must match '^CAND_[0-9]{7}$'."""

    def _minimal_record(self, **overrides) -> dict:
        """Build the smallest valid raw candidate record, with optional overrides."""
        base = {
            "candidate_id": "CAND_0000001",
            "profile": {
                "anonymized_name": "Test User",
                "headline": "Engineer",
                "summary": "Summary.",
                "location": "Delhi",
                "country": "India",
                "years_of_experience": 3.0,
                "current_title": "SWE",
                "current_company": "Acme",
                "current_company_size": "51-200",
                "current_industry": "Software",
            },
            "career_history": [
                {
                    "company": "Acme",
                    "title": "SWE",
                    "start_date": "2022-01-01",
                    "end_date": None,
                    "duration_months": 24,
                    "is_current": True,
                    "industry": "Software",
                    "company_size": "51-200",
                    "description": "Built things.",
                }
            ],
            "education": [],
            "skills": [],
            "certifications": [],
            "languages": [],
            "redrob_signals": {
                "profile_completeness_score": 70.0,
                "signup_date": "2024-01-01",
                "last_active_date": "2026-01-01",
                "open_to_work_flag": True,
                "profile_views_received_30d": 5,
                "applications_submitted_30d": 1,
                "recruiter_response_rate": 0.5,
                "avg_response_time_hours": 8.0,
                "skill_assessment_scores": {},
                "connection_count": 50,
                "endorsements_received": 5,
                "notice_period_days": 30,
                "expected_salary_range_inr_lpa": {"min": 10.0, "max": 20.0},
                "preferred_work_mode": "remote",
                "willing_to_relocate": False,
                "github_activity_score": 0.0,
                "search_appearance_30d": 10,
                "saved_by_recruiters_30d": 2,
                "interview_completion_rate": 0.7,
                "offer_acceptance_rate": 0.6,
                "verified_email": True,
                "verified_phone": True,
                "linkedin_connected": False,
            },
        }
        base.update(overrides)
        return base

    def test_valid_id_parses(self):
        raw = self._minimal_record(candidate_id="CAND_0000001")
        rec = CandidateRecord.model_validate(raw)
        assert rec.candidate_id == "CAND_0000001"

    def test_missing_cand_prefix_raises(self):
        """Missing 'CAND_' prefix → ValidationError. AC2"""
        raw = self._minimal_record(candidate_id="0000001")
        with pytest.raises(ValidationError):
            CandidateRecord.model_validate(raw)

    def test_wrong_prefix_raises(self):
        raw = self._minimal_record(candidate_id="CAND0000001")  # missing underscore
        with pytest.raises(ValidationError):
            CandidateRecord.model_validate(raw)

    def test_too_few_digits_raises(self):
        raw = self._minimal_record(candidate_id="CAND_123")  # only 3 digits
        with pytest.raises(ValidationError):
            CandidateRecord.model_validate(raw)

    def test_too_many_digits_raises(self):
        raw = self._minimal_record(candidate_id="CAND_00000001")  # 8 digits
        with pytest.raises(ValidationError):
            CandidateRecord.model_validate(raw)

    def test_max_valid_id_parses(self):
        raw = self._minimal_record(candidate_id="CAND_9999999")
        rec = CandidateRecord.model_validate(raw)
        assert rec.candidate_id == "CAND_9999999"

    def test_empty_string_raises(self):
        raw = self._minimal_record(candidate_id="")
        with pytest.raises(ValidationError):
            CandidateRecord.model_validate(raw)


# ---------------------------------------------------------------------------
# AC3 — SkillEntry negative endorsements raises ValidationError
# ---------------------------------------------------------------------------


class TestSkillEntryValidation:
    """SkillEntry.endorsements must be ≥ 0."""

    def test_zero_endorsements_valid(self):
        s = SkillEntry(name="Python", proficiency="expert", endorsements=0)
        assert s.endorsements == 0

    def test_positive_endorsements_valid(self):
        s = SkillEntry(name="ML", proficiency="advanced", endorsements=99)
        assert s.endorsements == 99

    def test_negative_endorsements_raises(self):
        """Negative endorsements must raise ValidationError. AC3"""
        with pytest.raises(ValidationError):
            SkillEntry(name="Python", proficiency="expert", endorsements=-1)

    def test_invalid_proficiency_raises(self):
        with pytest.raises(ValidationError):
            SkillEntry(name="Python", proficiency="godlike", endorsements=0)

    def test_duration_months_defaults_to_zero(self):
        s = SkillEntry(name="SQL", proficiency="beginner", endorsements=0)
        assert s.duration_months == 0

    def test_duration_months_negative_raises(self):
        with pytest.raises(ValidationError):
            SkillEntry(
                name="SQL",
                proficiency="beginner",
                endorsements=0,
                duration_months=-5,
            )


# ---------------------------------------------------------------------------
# AC4 & AC5 — Sentinel values are valid
# ---------------------------------------------------------------------------


class TestSentinelValues:
    """Sentinel -1 values must be accepted, not raise ValidationError."""

    def _minimal_signals(self, **overrides) -> dict:
        base = {
            "profile_completeness_score": 70.0,
            "signup_date": "2024-01-01",
            "last_active_date": "2026-01-01",
            "open_to_work_flag": True,
            "profile_views_received_30d": 5,
            "applications_submitted_30d": 1,
            "recruiter_response_rate": 0.5,
            "avg_response_time_hours": 8.0,
            "skill_assessment_scores": {},
            "connection_count": 50,
            "endorsements_received": 5,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 10.0, "max": 20.0},
            "preferred_work_mode": "remote",
            "willing_to_relocate": False,
            "github_activity_score": 0.0,
            "search_appearance_30d": 10,
            "saved_by_recruiters_30d": 2,
            "interview_completion_rate": 0.7,
            "offer_acceptance_rate": 0.6,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": False,
        }
        base.update(overrides)
        return base

    def test_offer_acceptance_rate_minus_one_valid(self):
        """offer_acceptance_rate = -1 is a valid sentinel value. AC4"""
        sig = RedrobSignals.model_validate(
            self._minimal_signals(offer_acceptance_rate=-1)
        )
        assert sig.offer_acceptance_rate == -1

    def test_offer_acceptance_rate_zero_valid(self):
        sig = RedrobSignals.model_validate(
            self._minimal_signals(offer_acceptance_rate=0.0)
        )
        assert sig.offer_acceptance_rate == 0.0

    def test_offer_acceptance_rate_one_valid(self):
        sig = RedrobSignals.model_validate(
            self._minimal_signals(offer_acceptance_rate=1.0)
        )
        assert sig.offer_acceptance_rate == 1.0

    def test_offer_acceptance_rate_below_minus_one_raises(self):
        with pytest.raises(ValidationError):
            RedrobSignals.model_validate(
                self._minimal_signals(offer_acceptance_rate=-1.1)
            )

    def test_github_activity_score_minus_one_valid(self):
        """github_activity_score = -1 is a valid sentinel (not linked). AC5"""
        sig = RedrobSignals.model_validate(
            self._minimal_signals(github_activity_score=-1)
        )
        assert sig.github_activity_score == -1

    def test_github_activity_score_zero_valid(self):
        sig = RedrobSignals.model_validate(
            self._minimal_signals(github_activity_score=0.0)
        )
        assert sig.github_activity_score == 0.0

    def test_github_activity_score_100_valid(self):
        sig = RedrobSignals.model_validate(
            self._minimal_signals(github_activity_score=100.0)
        )
        assert sig.github_activity_score == 100.0

    def test_github_activity_score_above_100_raises(self):
        with pytest.raises(ValidationError):
            RedrobSignals.model_validate(
                self._minimal_signals(github_activity_score=100.1)
            )

    def test_github_activity_score_below_minus_one_raises(self):
        with pytest.raises(ValidationError):
            RedrobSignals.model_validate(
                self._minimal_signals(github_activity_score=-2)
            )


# ---------------------------------------------------------------------------
# AC6 — Existing schemas unchanged
# ---------------------------------------------------------------------------


class TestExistingSchemasSurvive:
    """The four original resume-processing models must remain intact. AC6"""

    def test_resume_input_fields(self):
        r = ResumeInput(
            job_description="Software engineer role",
            resume_latex_code=r"\documentclass{article}",
        )
        assert r.job_description
        assert r.resume_latex_code

    def test_refinement_input_fields(self):
        r = RefinementInput(
            job_description="Role",
            original_resume_latex_code=r"\documentclass{article}",
            evaluation={"score": 80},
        )
        assert r.evaluation == {"score": 80}

    def test_evaluation_output_fields(self):
        e = EvaluationOutput(
            experience_match={"score": 70},
            skills_and_techstack_match={"score": 80},
            projects_match={"score": 60},
            education_match={"score": 90},
            profile_match={"score": 85},
            industry_and_domain_match={"score": 75},
            certifications_and_achievements_match={"score": 50},
            overall_match={"score": 73},
        )
        assert e.overall_match["score"] == 73

    def test_refined_resume_output_fields(self):
        r = RefinedResumeOutput(
            refined_latex_code=r"\documentclass{article}\begin{document}\end{document}"
        )
        assert r.overall_improvements_summary is None

    def test_rule_score_schema_unchanged(self):
        rs = RuleScoreSchema(
            candidate_id="CAND_0000001",
            experience_score=25.0,
            title_score=15.0,
            skills_score=20.0,
            industry_score=10.0,
            disqualifier_penalty=0.0,
            total=70.0,
        )
        assert rs.total == 70.0

    def test_score_breakdown_model(self):
        sb = ScoreBreakdown(
            rule_score=0.7,
            embedding_similarity=0.85,
            skills_score=0.9,
            career_score=0.75,
            behavioral_score=0.8,
        )
        assert sb.embedding_similarity == 0.85


# ---------------------------------------------------------------------------
# AC7 — Round-trip: model_dump() → model_validate()
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """CandidateRecord must survive a full Python-object round-trip losslessly."""

    def test_python_object_round_trip(self, schema_sample_records):
        """model_dump() → model_validate() must produce an equal model. AC7"""
        for raw in schema_sample_records:
            original = CandidateRecord.model_validate(raw)
            dumped = original.model_dump()
            restored = CandidateRecord.model_validate(dumped)
            assert original == restored, (
                f"Round-trip failed for {original.candidate_id}"
            )

    def test_json_string_round_trip(self, schema_sample_records):
        """model_dump_json() → model_validate_json() must also be lossless."""
        for raw in schema_sample_records:
            original = CandidateRecord.model_validate(raw)
            json_str = original.model_dump_json()
            restored = CandidateRecord.model_validate_json(json_str)
            assert original == restored

    def test_dumped_dict_has_expected_keys(self, schema_sample_records):
        rec = CandidateRecord.model_validate(schema_sample_records[0])
        d = rec.model_dump()
        assert set(d.keys()) == {
            "candidate_id",
            "profile",
            "career_history",
            "education",
            "skills",
            "certifications",
            "languages",
            "redrob_signals",
        }

    def test_dates_serialise_as_strings_in_json(self, schema_sample_records):
        """Dates inside the JSON output must be ISO-8601 strings, not Python objects."""
        rec = CandidateRecord.model_validate(schema_sample_records[0])
        json_str = rec.model_dump_json()
        data = json.loads(json_str)
        signup = data["redrob_signals"]["signup_date"]
        assert isinstance(signup, str), f"Expected str date, got {type(signup)}"
        # Must be parseable as ISO-8601
        date.fromisoformat(signup)


# ---------------------------------------------------------------------------
# AC8 — Import does not break resume router
# ---------------------------------------------------------------------------


class TestRouterImportsUnbroken:
    """Importing the router-required symbols must not raise. AC8"""

    def test_resume_router_imports_work(self):
        """Importing the same symbols that resume_processing.py needs must succeed."""
        from backend.app.models.schemas import (
            EvaluationOutput,
            RefinedResumeOutput,
            RefinementInput,
            ResumeInput,
        )

        assert ResumeInput
        assert RefinementInput
        assert EvaluationOutput
        assert RefinedResumeOutput

    def test_ranking_router_imports_work(self):
        """Importing the same symbols that ranking.py needs must succeed."""
        from backend.app.models.schemas import (
            ProfileSnapshot,
            RankedCandidateResponse,
            RankingResponse,
            RankingStatusResponse,
            ReRankRequest,
            RuleScoreSchema,
            ScoreBreakdown,
        )

        assert ProfileSnapshot
        assert RankedCandidateResponse

    def test_new_models_coexist_with_existing(self):
        """All new and existing models must be importable from the same module."""
        from backend.app.models.schemas import (
            CandidateRecord,
            EvaluationOutput,
            HoneypotResult,
            ParsedJD,
            ProfileBlock,
            RuleScore,
        )

        assert CandidateRecord
        assert ProfileBlock
        assert ParsedJD
        assert RuleScore
        assert HoneypotResult
        assert EvaluationOutput


# ---------------------------------------------------------------------------
# Bonus — sub-model validation correctness
# ---------------------------------------------------------------------------


class TestSubModelValidation:
    """Edge-case constraints on individual sub-models."""

    def test_profile_block_years_out_of_range(self):
        with pytest.raises(ValidationError):
            ProfileBlock(
                anonymized_name="X",
                headline="H",
                summary="S",
                location="L",
                country="IN",
                years_of_experience=51.0,  # max is 50
                current_title="SWE",
                current_company="Co",
                current_company_size="51-200",
                current_industry="SW",
            )

    def test_profile_block_invalid_company_size(self):
        with pytest.raises(ValidationError):
            ProfileBlock(
                anonymized_name="X",
                headline="H",
                summary="S",
                location="L",
                country="IN",
                years_of_experience=5.0,
                current_title="SWE",
                current_company="Co",
                current_company_size="giant",  # not a valid Literal
                current_industry="SW",
            )

    def test_education_entry_defaults(self):
        edu = EducationEntry(
            institution="IIT Delhi",
            degree="B.Tech",
            field_of_study="CS",
            start_year=2018,
            end_year=2022,
        )
        assert edu.tier == "unknown"
        assert edu.grade is None

    def test_education_invalid_tier_raises(self):
        with pytest.raises(ValidationError):
            EducationEntry(
                institution="IIT Delhi",
                degree="B.Tech",
                field_of_study="CS",
                start_year=2018,
                end_year=2022,
                tier="elite",  # not a valid Literal
            )

    def test_cert_entry_fields(self):
        cert = CertEntry(name="AWS SAA", issuer="Amazon", year=2023)
        assert cert.name == "AWS SAA"

    def test_language_entry_invalid_proficiency(self):
        with pytest.raises(ValidationError):
            LanguageEntry(
                language="English", proficiency="fluent"
            )  # not a valid Literal

    def test_career_entry_company_size_validated(self):
        with pytest.raises(ValidationError):
            CareerEntry(
                company="Acme",
                title="SWE",
                start_date="2022-01-01",
                end_date=None,
                duration_months=24,
                is_current=True,
                industry="Software",
                company_size="huge",  # not a valid Literal
                description="Built stuff.",
            )

    def test_parsed_jd_embedding_defaults_none(self):
        jd = ParsedJD(
            full_text="We are hiring.",
            role_title="ML Engineer",
            required_skills=["Python"],
            preferred_skills=["Go"],
            min_years_experience=3,
            max_years_experience=8,
            seniority_level="senior",
            domains=["ML", "NLP"],
            disqualifiers=["no experience"],
        )
        assert jd.embedding is None

    def test_parsed_jd_with_embedding(self):
        jd = ParsedJD(
            full_text="We are hiring.",
            role_title="ML Engineer",
            required_skills=["Python"],
            preferred_skills=[],
            min_years_experience=3,
            max_years_experience=8,
            seniority_level="senior",
            domains=[],
            disqualifiers=[],
            embedding=[0.1] * 384,
        )
        assert len(jd.embedding) == 384

    def test_rule_score_fields(self):
        rs = RuleScore(
            candidate_id="CAND_0000001",
            experience_score=20.0,
            title_score=15.0,
            skills_score=18.0,
            industry_score=10.0,
            disqualifier_penalty=5.0,
            total=58.0,
        )
        assert rs.total == 58.0

    def test_honeypot_result_valid(self):
        hr = HoneypotResult(
            is_suspicious=True,
            confidence=0.92,
            flags=["inconsistent_yoe", "bulk_unendorsed"],
            penalty_multiplier=0.0,
        )
        assert hr.is_suspicious
        assert hr.confidence == 0.92

    def test_honeypot_result_confidence_out_of_range(self):
        with pytest.raises(ValidationError):
            HoneypotResult(
                is_suspicious=False,
                confidence=1.1,  # > 1.0
                flags=[],
                penalty_multiplier=1.0,
            )

    def test_redrob_signals_notice_period_max(self):
        """notice_period_days has a hard cap of 180."""
        with pytest.raises(ValidationError):
            from backend.app.models.schemas import RedrobSignals as RS

            RS.model_validate(
                {
                    "profile_completeness_score": 70.0,
                    "signup_date": "2024-01-01",
                    "last_active_date": "2026-01-01",
                    "open_to_work_flag": True,
                    "profile_views_received_30d": 5,
                    "applications_submitted_30d": 1,
                    "recruiter_response_rate": 0.5,
                    "avg_response_time_hours": 8.0,
                    "skill_assessment_scores": {},
                    "connection_count": 50,
                    "endorsements_received": 5,
                    "notice_period_days": 181,  # max is 180
                    "expected_salary_range_inr_lpa": {"min": 10.0, "max": 20.0},
                    "preferred_work_mode": "remote",
                    "willing_to_relocate": False,
                    "github_activity_score": 0.0,
                    "search_appearance_30d": 10,
                    "saved_by_recruiters_30d": 2,
                    "interview_completion_rate": 0.7,
                    "offer_acceptance_rate": 0.6,
                    "verified_email": True,
                    "verified_phone": True,
                    "linkedin_connected": False,
                }
            )
