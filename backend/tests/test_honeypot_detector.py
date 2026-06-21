"""
test_honeypot_detector.py — Tests for honeypot_detector.py.

Coverage:
  - compute_penalty()                   — all penalty tiers
  - check_temporal_consistency()        — YOE > career span, duration mismatch, future education
  - check_skill_inflation()             — expert + 0 duration, bulk unendorsed, assessment contradiction
  - check_career_skill_coherence()      — keyword stuffer vs legitimate career changer
  - check_signal_sanity()               — triple unverified, perfect engagement, GitHub mismatch
  - detect_honeypot()                   — end-to-end: CAND_0000002 flagged, no false-positives
  - 100 K scale plausibility            — sample population flag rate stays in 50–120 range
"""

from __future__ import annotations

import copy
import json
import pathlib

import pytest

from backend.app.core.candidate_loader import (
    CandidateRecord,
    validate_candidate,
)
from backend.app.core.honeypot_detector import (
    HoneypotResult,
    check_career_skill_coherence,
    check_signal_sanity,
    check_skill_inflation,
    check_temporal_consistency,
    compute_penalty,
    detect_honeypot,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SAMPLE_JSON = (
    _REPO_ROOT
    / "[PUB] India_runs_data_and_ai_challenge"
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


def _record(raw_list: list[dict], cid: str) -> CandidateRecord:
    """Fetch a specific candidate by ID from raw list and validate."""
    for d in raw_list:
        if d["candidate_id"] == cid:
            r = validate_candidate(d)
            assert r is not None
            return r
    raise KeyError(f"{cid} not found in sample data")


def _mutate(base: dict, **overrides) -> CandidateRecord:
    """Deep-copy *base* raw dict, apply nested overrides, and validate."""
    import copy as _copy
    d = _copy.deepcopy(base)
    # Apply top-level key overrides; nested path "a.b" → d["a"]["b"]
    for key, val in overrides.items():
        parts = key.split(".")
        node = d
        for part in parts[:-1]:
            node = node[part]
        node[parts[-1]] = val
    r = validate_candidate(d)
    assert r is not None, f"mutated record failed validation: {d.get('candidate_id')}"
    return r


# ---------------------------------------------------------------------------
# compute_penalty
# ---------------------------------------------------------------------------

class TestComputePenalty:
    def test_zero_flags(self):
        assert compute_penalty([]) == 1.0

    def test_one_flag(self):
        assert compute_penalty(["flag1"]) == 0.7

    def test_two_flags(self):
        assert compute_penalty(["flag1", "flag2"]) == 0.4

    def test_three_flags(self):
        assert compute_penalty(["a", "b", "c"]) == 0.0

    def test_many_flags(self):
        assert compute_penalty(["a"] * 10) == 0.0


# ---------------------------------------------------------------------------
# check_temporal_consistency
# ---------------------------------------------------------------------------

class TestTemporalConsistency:

    def test_clean_candidate_no_flags(self, sample_raw):
        """CAND_0000001 has consistent YOE and durations — should be clean."""
        r = _record(sample_raw, "CAND_0000001")
        flags = check_temporal_consistency(r)
        assert flags == []

    def test_yoe_exceeds_span(self, sample_raw):
        """Inject YOE 10 years above career span."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["profile"]["years_of_experience"] = 25.0  # career span is ~7 yrs
        r = validate_candidate(d)
        flags = check_temporal_consistency(r)
        temporal_flags = [f for f in flags if "yoe_exceeds_span" in f]
        assert len(temporal_flags) >= 1

    def test_yoe_within_buffer_not_flagged(self, sample_raw):
        """YOE = career_span + 1.5 (under the 2-year buffer) → no flag."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        # CAND_0000001 career span ≈ 7.0 yrs, so 8.5 is within 2-yr buffer
        d["profile"]["years_of_experience"] = 8.5
        r = validate_candidate(d)
        flags = check_temporal_consistency(r)
        yoe_flags = [f for f in flags if "yoe_exceeds_span" in f]
        assert yoe_flags == []

    def test_duration_mismatch_triggers(self, sample_raw):
        """Inject two roles with duration_months way off from date arithmetic."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000002")
        d = copy.deepcopy(base)
        # Artificially inflate duration_months on first two roles by 12 months each
        d["career_history"][0]["duration_months"] = d["career_history"][0]["duration_months"] + 12
        d["career_history"][1]["duration_months"] = d["career_history"][1]["duration_months"] + 12
        r = validate_candidate(d)
        flags = check_temporal_consistency(r)
        dur_flags = [f for f in flags if "duration_mismatch" in f]
        assert len(dur_flags) >= 1

    def test_single_duration_mismatch_not_flagged(self, sample_raw):
        """Single bad duration is tolerated (data-entry error, not fabrication)."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["career_history"][0]["duration_months"] = d["career_history"][0]["duration_months"] + 12
        r = validate_candidate(d)
        flags = check_temporal_consistency(r)
        dur_flags = [f for f in flags if "duration_mismatch" in f]
        assert dur_flags == []

    def test_future_education_flagged(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["education"][0]["end_year"] = 2030
        r = validate_candidate(d)
        flags = check_temporal_consistency(r)
        edu_flags = [f for f in flags if "future_education" in f]
        assert len(edu_flags) >= 1

    def test_past_education_not_flagged(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["education"][0]["end_year"] = 2020  # definitely in the past
        r = validate_candidate(d)
        flags = check_temporal_consistency(r)
        edu_flags = [f for f in flags if "future_education" in f]
        assert edu_flags == []


# ---------------------------------------------------------------------------
# check_skill_inflation
# ---------------------------------------------------------------------------

class TestSkillInflation:

    def test_clean_candidate_no_flags(self, sample_raw):
        r = _record(sample_raw, "CAND_0000001")
        flags = check_skill_inflation(r)
        # CAND_0000001 has advanced skills with endorsements and duration — clean
        assert not any("expert_zero_duration" in f for f in flags)

    def test_expert_zero_duration_flagged(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        # Set first advanced skill to duration=0
        for s in d["skills"]:
            if s["proficiency"] in ("advanced", "expert"):
                s["duration_months"] = 0
                break
        r = validate_candidate(d)
        flags = check_skill_inflation(r)
        zero_flags = [f for f in flags if "expert_zero_duration" in f]
        assert len(zero_flags) >= 1

    def test_bulk_unendorsed_expert_flagged(self, sample_raw):
        """Inject 6 expert skills all with 0 endorsements."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        for s in d["skills"]:
            s["proficiency"] = "expert"
            s["endorsements"] = 0
            s["duration_months"] = 24
        # Make sure we have at least 6
        while len(d["skills"]) < 6:
            d["skills"].append({
                "name": f"FakeSkill{len(d['skills'])}",
                "proficiency": "expert",
                "endorsements": 0,
                "duration_months": 12,
            })
        r = validate_candidate(d)
        flags = check_skill_inflation(r)
        bulk_flags = [f for f in flags if "bulk_unendorsed" in f]
        assert len(bulk_flags) >= 1

    def test_five_unendorsed_expert_not_flagged(self, sample_raw):
        """Five unendorsed expert skills is under the threshold (need ≥ 6)."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        # Replace skills with exactly 5 unendorsed expert skills
        d["skills"] = [
            {"name": f"Skill{i}", "proficiency": "expert", "endorsements": 0, "duration_months": 12}
            for i in range(5)
        ]
        r = validate_candidate(d)
        flags = check_skill_inflation(r)
        bulk_flags = [f for f in flags if "bulk_unendorsed" in f]
        assert bulk_flags == []

    def test_assessment_contradiction_two_failures(self, sample_raw):
        """Two advanced skills with assessment scores < 35 triggers the flag."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        # Ensure two advanced skills exist and give them bad assessment scores
        adv_names = []
        for s in d["skills"]:
            if s["proficiency"] in ("advanced", "expert") and len(adv_names) < 2:
                adv_names.append(s["name"])
        for name in adv_names:
            d["redrob_signals"]["skill_assessment_scores"][name] = 20.0
        r = validate_candidate(d)
        flags = check_skill_inflation(r)
        contra_flags = [f for f in flags if "assessment_contradiction" in f]
        assert len(contra_flags) >= 1

    def test_single_assessment_failure_not_flagged(self, sample_raw):
        """One contradictory assessment is tolerated (bad day)."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        adv_names = [s["name"] for s in d["skills"] if s["proficiency"] in ("advanced", "expert")]
        if adv_names:
            d["redrob_signals"]["skill_assessment_scores"][adv_names[0]] = 10.0
        # Remove all other assessment scores
        for name in list(d["redrob_signals"]["skill_assessment_scores"].keys()):
            if name != adv_names[0]:
                del d["redrob_signals"]["skill_assessment_scores"][name]
        r = validate_candidate(d)
        flags = check_skill_inflation(r)
        contra_flags = [f for f in flags if "assessment_contradiction" in f]
        assert contra_flags == []


# ---------------------------------------------------------------------------
# check_career_skill_coherence
# ---------------------------------------------------------------------------

class TestCareerSkillCoherence:

    def test_technical_candidate_not_flagged(self, sample_raw):
        """CAND_0000001 (Backend Engineer with data skills) must not be flagged."""
        r = _record(sample_raw, "CAND_0000001")
        flags = check_career_skill_coherence(r)
        assert flags == []

    def test_non_technical_no_ai_skills_not_flagged(self, sample_raw):
        """CAND_0000005 (Accountant) has no AI skills — not a keyword stuffer."""
        r = _record(sample_raw, "CAND_0000005")
        flags = check_career_skill_coherence(r)
        assert flags == []

    def test_keyword_stuffer_flagged(self, sample_raw):
        """Inject a non-technical candidate with ≥4 specific AI/ML skills."""
        # Use CAND_0000005 (Accountant) as base — fully non-technical career
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000005")
        d = copy.deepcopy(base)
        # Replace skills with specific AI skills (ones in _SPECIFIC_AI_SKILLS)
        d["skills"] = [
            {"name": "TensorFlow", "proficiency": "expert", "endorsements": 10, "duration_months": 24},
            {"name": "PyTorch", "proficiency": "expert", "endorsements": 8, "duration_months": 18},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 5, "duration_months": 20},
            {"name": "Deep Learning", "proficiency": "advanced", "endorsements": 6, "duration_months": 15},
            {"name": "Hugging Face Transformers", "proficiency": "advanced", "endorsements": 3, "duration_months": 12},
        ]
        r = validate_candidate(d)
        flags = check_career_skill_coherence(r)
        stuffer_flags = [f for f in flags if "keyword_stuffer" in f]
        assert len(stuffer_flags) >= 1

    def test_career_changer_with_recent_technical_role_not_flagged(self, sample_raw):
        """Someone who was in marketing 5 yrs ago but is now a data engineer → clean."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000005")
        d = copy.deepcopy(base)
        # Add a recent (2022–present) data engineer role to career history
        d["career_history"].insert(0, {
            "company": "TechCo",
            "title": "Data Engineer",
            "start_date": "2022-01-01",
            "end_date": None,
            "duration_months": 30,
            "is_current": True,
            "industry": "Software",
            "company_size": "51-200",
            "description": "Built machine learning pipelines using Python, Spark, and TensorFlow.",
        })
        d["profile"]["current_title"] = "Data Engineer"
        # Add AI skills
        d["skills"] = [
            {"name": "TensorFlow", "proficiency": "expert", "endorsements": 10, "duration_months": 24},
            {"name": "PyTorch", "proficiency": "expert", "endorsements": 8, "duration_months": 18},
            {"name": "NLP", "proficiency": "advanced", "endorsements": 5, "duration_months": 20},
            {"name": "Deep Learning", "proficiency": "advanced", "endorsements": 6, "duration_months": 15},
        ]
        r = validate_candidate(d)
        flags = check_career_skill_coherence(r)
        stuffer_flags = [f for f in flags if "keyword_stuffer" in f]
        assert stuffer_flags == [], (
            "Career changer with recent technical role should NOT be flagged as keyword stuffer"
        )

    def test_few_ai_skills_not_flagged(self, sample_raw):
        """Non-technical candidate with only 2 specific AI skills is not a stuffer."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000005")
        d = copy.deepcopy(base)
        d["skills"] = [
            {"name": "TensorFlow", "proficiency": "intermediate", "endorsements": 2, "duration_months": 6},
            {"name": "PyTorch", "proficiency": "beginner", "endorsements": 1, "duration_months": 3},
        ]
        r = validate_candidate(d)
        flags = check_career_skill_coherence(r)
        stuffer_flags = [f for f in flags if "keyword_stuffer" in f]
        assert stuffer_flags == []


# ---------------------------------------------------------------------------
# check_signal_sanity
# ---------------------------------------------------------------------------

class TestSignalSanity:

    def test_triple_unverified_flagged(self, sample_raw):
        """CAND_0000002 has all three verifications False."""
        r = _record(sample_raw, "CAND_0000002")
        flags = check_signal_sanity(r)
        unver_flags = [f for f in flags if "unverified_profile" in f]
        assert len(unver_flags) >= 1

    def test_clean_candidate_not_flagged(self, sample_raw):
        """CAND_0000001 has verified_email=True, verified_phone=True."""
        r = _record(sample_raw, "CAND_0000001")
        flags = check_signal_sanity(r)
        unver_flags = [f for f in flags if "unverified_profile" in f]
        assert unver_flags == []

    def test_partial_verification_not_flagged(self, sample_raw):
        """One or two verifications False is normal — flag only when all three fail."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["redrob_signals"]["verified_email"] = False
        d["redrob_signals"]["verified_phone"] = False
        d["redrob_signals"]["linkedin_connected"] = True  # at least one True
        r = validate_candidate(d)
        flags = check_signal_sanity(r)
        unver_flags = [f for f in flags if "unverified_profile" in f]
        assert unver_flags == []

    def test_perfect_engagement_flagged(self, sample_raw):
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["redrob_signals"]["interview_completion_rate"] = 1.0
        d["redrob_signals"]["offer_acceptance_rate"] = 1.0
        r = validate_candidate(d)
        flags = check_signal_sanity(r)
        perf_flags = [f for f in flags if "perfect_engagement" in f]
        assert len(perf_flags) >= 1

    def test_high_but_not_perfect_not_flagged(self, sample_raw):
        """0.95 and 0.95 are high but not 1.0 — no flag."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["redrob_signals"]["interview_completion_rate"] = 0.95
        d["redrob_signals"]["offer_acceptance_rate"] = 0.95
        r = validate_candidate(d)
        flags = check_signal_sanity(r)
        perf_flags = [f for f in flags if "perfect_engagement" in f]
        assert perf_flags == []

    def test_github_100_no_tech_career_flagged(self, sample_raw):
        """github_activity_score=100 with no technical career descriptions."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000005")
        d = copy.deepcopy(base)
        d["redrob_signals"]["github_activity_score"] = 100.0
        r = validate_candidate(d)
        flags = check_signal_sanity(r)
        github_flags = [f for f in flags if "github_score_mismatch" in f]
        assert len(github_flags) >= 1

    def test_github_100_with_tech_career_not_flagged(self, sample_raw):
        """github_activity_score=100 is fine for a Backend Engineer."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000001")
        d = copy.deepcopy(base)
        d["redrob_signals"]["github_activity_score"] = 100.0
        r = validate_candidate(d)
        flags = check_signal_sanity(r)
        github_flags = [f for f in flags if "github_score_mismatch" in f]
        assert github_flags == []


# ---------------------------------------------------------------------------
# detect_honeypot — end-to-end
# ---------------------------------------------------------------------------

class TestDetectHoneypot:

    def test_returns_honeypot_result(self, sample_raw):
        r = _record(sample_raw, "CAND_0000001")
        result = detect_honeypot(r)
        assert isinstance(result, HoneypotResult)

    def test_cand_0000002_flagged(self, sample_raw):
        """Acceptance criterion: CAND_0000002 (Operations Manager, all verifications False)."""
        r = _record(sample_raw, "CAND_0000002")
        result = detect_honeypot(r)
        assert result.is_suspicious, (
            "CAND_0000002 should be flagged (all verifications False)"
        )
        assert len(result.flags) >= 1
        assert result.penalty_multiplier < 1.0

    def test_cand_0000001_clean(self, sample_raw):
        """CAND_0000001 (Backend Engineer, verified, coherent) must not be penalised."""
        r = _record(sample_raw, "CAND_0000001")
        result = detect_honeypot(r)
        assert result.penalty_multiplier == 1.0
        assert result.flags == []

    def test_penalty_multiplier_zero_at_three_flags(self, sample_raw):
        """A candidate with 3+ flags gets multiplier=0.0."""
        base = next(d for d in sample_raw if d["candidate_id"] == "CAND_0000005")
        d = copy.deepcopy(base)
        # Trigger temporal flag: inflate YOE
        d["profile"]["years_of_experience"] = 30.0
        # Trigger skill inflation: 6 expert skills with 0 endorsements
        d["skills"] = [
            {"name": f"SkillX{i}", "proficiency": "expert", "endorsements": 0, "duration_months": 0}
            for i in range(7)
        ]
        # Trigger signal sanity: perfect engagement
        d["redrob_signals"]["interview_completion_rate"] = 1.0
        d["redrob_signals"]["offer_acceptance_rate"] = 1.0
        r = validate_candidate(d)
        result = detect_honeypot(r)
        assert result.penalty_multiplier == 0.0
        assert result.confidence >= 0.7

    def test_confidence_zero_for_clean(self, sample_raw):
        r = _record(sample_raw, "CAND_0000001")
        result = detect_honeypot(r)
        assert result.confidence == 0.0

    def test_no_false_positive_frontend_engineer(self, sample_raw):
        """CAND_0000018: Frontend Engineer, all verifications False but legitimate."""
        r = _record(sample_raw, "CAND_0000018")
        result = detect_honeypot(r)
        # All-false verifications will trigger 1 signal_sanity flag → penalty=0.7, not 0.0
        # The candidate should NOT be disqualified (multiplier > 0)
        assert result.penalty_multiplier > 0.0, (
            "CAND_0000018 is a legitimate Frontend Engineer and must NOT be disqualified"
        )

    def test_sample_population_flag_rate(self, sample_records):
        """Across the 50-candidate sample, total disqualified should be 0–5 (≤10%)."""
        disqualified = [r for r in sample_records if detect_honeypot(r).penalty_multiplier == 0.0]
        # In the sample we expect 0–5 outright disqualifications (honeypots are ~0.08% of 100K)
        assert len(disqualified) <= 5, (
            f"Too many disqualifications ({len(disqualified)}/50) — "
            f"likely over-flagging legitimate candidates: "
            f"{[r.candidate_id for r in disqualified]}"
        )

    def test_result_fields_populated(self, sample_raw):
        r = _record(sample_raw, "CAND_0000002")
        result = detect_honeypot(r)
        assert isinstance(result.is_suspicious, bool)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.flags, list)
        assert 0.0 <= result.penalty_multiplier <= 1.0

    def test_penalty_decreases_monotonically_with_flag_count(self):
        assert compute_penalty([]) > compute_penalty(["a"])
        assert compute_penalty(["a"]) > compute_penalty(["a", "b"])
        assert compute_penalty(["a", "b"]) > compute_penalty(["a", "b", "c"])
