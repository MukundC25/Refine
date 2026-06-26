"""
test_signal_scorer.py — Tests for signal_scorer.py.

Acceptance criteria verified
-----------------------------
  AC1  High-signal candidate (open_to_work, short notice, responsive, verified)
       scores ≥ 75 total
  AC2  Low-signal candidate (unverified, low response rate, accepts nothing)
       scores ≤ 20 total
  AC3  offer_acceptance_rate == -1 → offer_reliability == 7.5 (neutral)
  AC4  github_activity_score == -1 → 3.0 pts in that sub-component
  AC5  compute_behavioral_score() never raises on any valid RedrobSignals
  AC6  All scores clamped to their stated ranges (no negatives, no overflow)
  AC7  500 candidates scored in < 0.5 seconds
  AC8  Behavioural twins (identical profile, different signals) produce
       meaningfully different behavioral scores (delta ≥ 30 pts)

Helpers
-------
  _sig(**overrides)       — build a minimal signals namespace
  _candidate(sig, id)    — build a minimal candidate namespace
"""

from __future__ import annotations

import time
import types

import pytest

from backend.app.core.signal_scorer import (
    BehavioralScore,
    SignalScorer,
    availability_score,
    batch_behavioral_scores,
    compute_behavioral_score,
    offer_reliability_score,
    platform_engagement_score,
    profile_trust_score,
    responsiveness_score,
    technical_credibility_score,
)

# ---------------------------------------------------------------------------
# Synthetic helpers
# ---------------------------------------------------------------------------

_SIG_DEFAULTS = dict(
    profile_completeness_score=70.0,
    signup_date="2024-01-01",
    last_active_date="2026-01-01",
    open_to_work_flag=True,
    profile_views_received_30d=10,
    applications_submitted_30d=2,
    recruiter_response_rate=0.5,
    avg_response_time_hours=8.0,
    skill_assessment_scores={},
    connection_count=100,
    endorsements_received=10,
    notice_period_days=30,
    expected_salary_range_inr_lpa=types.SimpleNamespace(min=10.0, max=20.0),
    preferred_work_mode="remote",
    willing_to_relocate=False,
    github_activity_score=0.0,
    search_appearance_30d=10,
    saved_by_recruiters_30d=2,
    interview_completion_rate=0.6,
    offer_acceptance_rate=0.5,
    verified_email=True,
    verified_phone=True,
    linkedin_connected=False,
)


def _sig(**overrides) -> types.SimpleNamespace:
    """Return a signals namespace starting from neutral defaults."""
    data = {**_SIG_DEFAULTS, **overrides}
    return types.SimpleNamespace(**data)


def _candidate(
    sig: types.SimpleNamespace | None = None,
    candidate_id: str = "CAND_0000099",
) -> types.SimpleNamespace:
    """Return a minimal candidate-like namespace."""
    return types.SimpleNamespace(
        candidate_id=candidate_id,
        redrob_signals=sig if sig is not None else _sig(),
    )


# ---------------------------------------------------------------------------
# TestAvailabilityScore
# ---------------------------------------------------------------------------


class TestAvailabilityScore:
    """availability_score() — 0–15 pts."""

    def test_maximum_score_open_to_work_zero_notice(self):
        """open_to_work + 0-day notice → 15 pts (8 + 7)."""
        s = _sig(open_to_work_flag=True, notice_period_days=0)
        assert availability_score(s) == 15.0

    def test_not_open_to_work_zero_notice(self):
        """Not open + 0-day notice → 7 pts (just notice component)."""
        s = _sig(open_to_work_flag=False, notice_period_days=0)
        assert availability_score(s) == pytest.approx(7.0)

    def test_open_to_work_only_no_notice_bonus(self):
        """Long notice erodes the notice component to 0."""
        # 105 days → max(0, 7 - 7) = 0 → only the +8 for open_to_work
        s = _sig(open_to_work_flag=True, notice_period_days=105)
        assert availability_score(s) == pytest.approx(8.0)

    def test_notice_15_days(self):
        """notice=15 → max(0, 7 − 1) = 6 → 8 + 6 = 14."""
        s = _sig(open_to_work_flag=True, notice_period_days=15)
        assert availability_score(s) == pytest.approx(14.0)

    def test_notice_30_days(self):
        """notice=30 → max(0, 7 − 2) = 5 → 8 + 5 = 13."""
        s = _sig(open_to_work_flag=True, notice_period_days=30)
        assert availability_score(s) == pytest.approx(13.0)

    def test_notice_60_days(self):
        """notice=60 → max(0, 7 − 4) = 3 → 8 + 3 = 11."""
        s = _sig(open_to_work_flag=True, notice_period_days=60)
        assert availability_score(s) == pytest.approx(11.0)

    def test_notice_90_days(self):
        """notice=90 → max(0, 7 − 6) = 1 → 8 + 1 = 9."""
        s = _sig(open_to_work_flag=True, notice_period_days=90)
        assert availability_score(s) == pytest.approx(9.0)

    def test_capped_at_15(self):
        """Result never exceeds 15."""
        s = _sig(open_to_work_flag=True, notice_period_days=0)
        assert availability_score(s) <= 15.0

    def test_never_negative(self):
        """Result is always ≥ 0."""
        for days in (0, 60, 120, 180):
            assert availability_score(_sig(notice_period_days=days)) >= 0.0


# ---------------------------------------------------------------------------
# TestResponsivenessScore
# ---------------------------------------------------------------------------


class TestResponsivenessScore:
    """responsiveness_score() — 0–20 pts."""

    def test_perfect_score(self):
        """Rate=1, fast response, interview=1 → 12 + 8 = 20."""
        s = _sig(
            recruiter_response_rate=1.0,
            avg_response_time_hours=1.0,
            interview_completion_rate=1.0,
        )
        assert responsiveness_score(s) == pytest.approx(20.0)

    def test_penalty_none_under_4h(self):
        """< 4h response → zero penalty."""
        s = _sig(
            recruiter_response_rate=0.5,
            avg_response_time_hours=2.0,
            interview_completion_rate=0.5,
        )
        # 6 + 4 - 0 = 10
        assert responsiveness_score(s) == pytest.approx(10.0)

    def test_penalty_1_between_4_and_24h(self):
        """4–24h response → −1 penalty."""
        s = _sig(
            recruiter_response_rate=0.5,
            avg_response_time_hours=10.0,
            interview_completion_rate=0.5,
        )
        # 6 + 4 - 1 = 9
        assert responsiveness_score(s) == pytest.approx(9.0)

    def test_penalty_3_between_24_and_72h(self):
        """24–72h response → −3 penalty."""
        s = _sig(
            recruiter_response_rate=0.5,
            avg_response_time_hours=48.0,
            interview_completion_rate=0.5,
        )
        # 6 + 4 - 3 = 7
        assert responsiveness_score(s) == pytest.approx(7.0)

    def test_penalty_6_above_72h(self):
        """> 72h response → −6 penalty."""
        s = _sig(
            recruiter_response_rate=0.5,
            avg_response_time_hours=100.0,
            interview_completion_rate=0.5,
        )
        # 6 + 4 - 6 = 4
        assert responsiveness_score(s) == pytest.approx(4.0)

    def test_clamped_to_zero_when_penalty_exceeds_pts(self):
        """Very low rates + heavy penalty → clamped to 0, never negative."""
        s = _sig(
            recruiter_response_rate=0.1,
            avg_response_time_hours=200.0,
            interview_completion_rate=0.2,
        )
        assert responsiveness_score(s) >= 0.0

    def test_capped_at_20(self):
        """Cannot exceed 20 regardless of inputs."""
        s = _sig(
            recruiter_response_rate=1.0,
            avg_response_time_hours=0.0,
            interview_completion_rate=1.0,
        )
        assert responsiveness_score(s) <= 20.0

    def test_boundary_exactly_4h(self):
        """Exactly 4h → no penalty (strictly > 4)."""
        s = _sig(
            recruiter_response_rate=0.5,
            avg_response_time_hours=4.0,
            interview_completion_rate=0.5,
        )
        # 6 + 4 - 0 = 10
        assert responsiveness_score(s) == pytest.approx(10.0)

    def test_boundary_exactly_24h(self):
        """Exactly 24h → −1 penalty (strictly > 24 triggers −3)."""
        s = _sig(
            recruiter_response_rate=0.5,
            avg_response_time_hours=24.0,
            interview_completion_rate=0.5,
        )
        # 6 + 4 - 1 = 9
        assert responsiveness_score(s) == pytest.approx(9.0)

    def test_boundary_exactly_72h(self):
        """Exactly 72h → −3 penalty (strictly > 72 triggers −6)."""
        s = _sig(
            recruiter_response_rate=0.5,
            avg_response_time_hours=72.0,
            interview_completion_rate=0.5,
        )
        # 6 + 4 - 3 = 7
        assert responsiveness_score(s) == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# TestOfferReliabilityScore
# ---------------------------------------------------------------------------


class TestOfferReliabilityScore:
    """offer_reliability_score() — 0–15 pts."""

    def test_sentinel_minus_one_returns_neutral(self):
        """offer_acceptance_rate == -1 → 7.5 (neutral, not penalised). AC3"""
        s = _sig(offer_acceptance_rate=-1)
        assert offer_reliability_score(s) == pytest.approx(7.5)

    def test_zero_acceptance_rate(self):
        """rate == 0.0 → 0 pts (always declines)."""
        s = _sig(offer_acceptance_rate=0.0)
        assert offer_reliability_score(s) == pytest.approx(0.0)

    def test_full_acceptance_rate(self):
        """rate == 1.0 → 15 pts."""
        s = _sig(offer_acceptance_rate=1.0)
        assert offer_reliability_score(s) == pytest.approx(15.0)

    def test_half_acceptance_rate(self):
        """rate == 0.5 → 7.5 pts."""
        s = _sig(offer_acceptance_rate=0.5)
        assert offer_reliability_score(s) == pytest.approx(7.5)

    def test_point_eight_acceptance(self):
        """rate == 0.8 → 12 pts."""
        s = _sig(offer_acceptance_rate=0.8)
        assert offer_reliability_score(s) == pytest.approx(12.0)

    def test_never_negative(self):
        """Result is always ≥ 0."""
        for rate in (-1, 0.0, 0.1, 0.5, 1.0):
            assert offer_reliability_score(_sig(offer_acceptance_rate=rate)) >= 0.0

    def test_capped_at_15(self):
        """Cannot exceed 15."""
        assert offer_reliability_score(_sig(offer_acceptance_rate=1.0)) <= 15.0


# ---------------------------------------------------------------------------
# TestTechnicalCredibilityScore
# ---------------------------------------------------------------------------


class TestTechnicalCredibilityScore:
    """technical_credibility_score() — 0–25 pts."""

    def test_github_minus_one_gives_3_pts(self):
        """github_activity_score == -1 → exactly 3.0 pts from GitHub. AC4"""
        s = _sig(github_activity_score=-1, skill_assessment_scores={})
        score = technical_credibility_score(s)
        # github: 3.0, no assessments: 2.0 → total 5.0
        assert score == pytest.approx(5.0)

    def test_github_minus_one_sub_component_is_3(self):
        """The GitHub sub-component specifically returns 3.0 when score == -1. AC4"""
        # Isolate: zero everything else
        s = _sig(github_activity_score=-1, skill_assessment_scores={"X": 0.0})
        # github: 3.0; assessment: (0/100)*10 = 0 → total 3.0
        score = technical_credibility_score(s)
        assert score == pytest.approx(3.0)

    def test_github_zero_gives_zero_pts(self):
        """github_activity_score == 0 → 0 pts (linked but inactive)."""
        s = _sig(github_activity_score=0, skill_assessment_scores={})
        # github: 0, no assessments: 2.0 → 2.0
        assert technical_credibility_score(s) == pytest.approx(2.0)

    def test_github_100_gives_15_pts(self):
        """github_activity_score == 100 → 15 pts from that sub-component."""
        s = _sig(github_activity_score=100, skill_assessment_scores={})
        # github: 15, no assessments: 2.0 → min(17, 25) = 17
        assert technical_credibility_score(s) == pytest.approx(17.0)

    def test_github_50_linear(self):
        """github_activity_score == 50 → 7.5 pts from GitHub."""
        s = _sig(github_activity_score=50, skill_assessment_scores={})
        # github: 7.5, no assessments: 2.0 → 9.5
        assert technical_credibility_score(s) == pytest.approx(9.5)

    def test_no_assessments_gives_2_pts_neutral(self):
        """Empty skill_assessment_scores → 2.0 pts neutral default."""
        s = _sig(github_activity_score=0, skill_assessment_scores={})
        # github: 0, no assessments: 2.0 → 2.0
        assert technical_credibility_score(s) == pytest.approx(2.0)

    def test_assessments_averaged(self):
        """Average of assessment scores × (10/100)."""
        s = _sig(
            github_activity_score=0,
            skill_assessment_scores={"Python": 80.0, "ML": 60.0},
        )
        # avg = 70, (70/100)*10 = 7.0; github=0 → 7.0
        assert technical_credibility_score(s) == pytest.approx(7.0)

    def test_perfect_github_and_assessments_capped(self):
        """Max GitHub + max assessments must not exceed 25."""
        s = _sig(
            github_activity_score=100,
            skill_assessment_scores={"Python": 100.0},
        )
        # 15 + 10 = 25
        assert technical_credibility_score(s) == pytest.approx(25.0)

    def test_never_exceeds_25(self):
        """Capped at 25 regardless of inputs."""
        s = _sig(
            github_activity_score=100,
            skill_assessment_scores={"A": 100.0, "B": 100.0, "C": 100.0},
        )
        assert technical_credibility_score(s) <= 25.0

    def test_never_negative(self):
        """Always ≥ 0."""
        for gh in (-1, 0, 50, 100):
            assert technical_credibility_score(_sig(github_activity_score=gh)) >= 0.0


# ---------------------------------------------------------------------------
# TestProfileTrustScore
# ---------------------------------------------------------------------------


class TestProfileTrustScore:
    """profile_trust_score() — 0–15 pts."""

    def test_all_verified_full_completeness(self):
        """email + phone + LinkedIn + 100% complete → 4+4+3+4 = 15."""
        s = _sig(
            verified_email=True,
            verified_phone=True,
            linkedin_connected=True,
            profile_completeness_score=100.0,
        )
        assert profile_trust_score(s) == pytest.approx(15.0)

    def test_none_verified_zero_completeness(self):
        """No verification + 0% completeness → 0 pts."""
        s = _sig(
            verified_email=False,
            verified_phone=False,
            linkedin_connected=False,
            profile_completeness_score=0.0,
        )
        assert profile_trust_score(s) == pytest.approx(0.0)

    def test_email_only(self):
        """Only email verified → 4 pts + completeness contribution."""
        s = _sig(
            verified_email=True,
            verified_phone=False,
            linkedin_connected=False,
            profile_completeness_score=0.0,
        )
        assert profile_trust_score(s) == pytest.approx(4.0)

    def test_phone_only(self):
        """Only phone verified → 4 pts."""
        s = _sig(
            verified_email=False,
            verified_phone=True,
            linkedin_connected=False,
            profile_completeness_score=0.0,
        )
        assert profile_trust_score(s) == pytest.approx(4.0)

    def test_linkedin_only(self):
        """Only LinkedIn → 3 pts."""
        s = _sig(
            verified_email=False,
            verified_phone=False,
            linkedin_connected=True,
            profile_completeness_score=0.0,
        )
        assert profile_trust_score(s) == pytest.approx(3.0)

    def test_completeness_half(self):
        """50% completeness → 2 pts from that component."""
        s = _sig(
            verified_email=False,
            verified_phone=False,
            linkedin_connected=False,
            profile_completeness_score=50.0,
        )
        assert profile_trust_score(s) == pytest.approx(2.0)

    def test_capped_at_15(self):
        """Cannot exceed 15."""
        s = _sig(
            verified_email=True,
            verified_phone=True,
            linkedin_connected=True,
            profile_completeness_score=100.0,
        )
        assert profile_trust_score(s) <= 15.0

    def test_never_negative(self):
        """Always ≥ 0."""
        s = _sig(
            verified_email=False,
            verified_phone=False,
            linkedin_connected=False,
            profile_completeness_score=0.0,
        )
        assert profile_trust_score(s) >= 0.0

    def test_low_verification_low_score(self):
        """All flags false + low completeness matches honeypot pattern → very low."""
        s = _sig(
            verified_email=False,
            verified_phone=False,
            linkedin_connected=False,
            profile_completeness_score=20.0,
        )
        score = profile_trust_score(s)
        assert score < 2.0  # (20/100)*4 = 0.8


# ---------------------------------------------------------------------------
# TestPlatformEngagementScore
# ---------------------------------------------------------------------------


class TestPlatformEngagementScore:
    """platform_engagement_score() — 0–10 pts."""

    def test_maximum_engagement(self):
        """Maximum values → 5 + 3 + 2 = 10."""
        s = _sig(
            saved_by_recruiters_30d=10,  # 10/2 = 5 (capped at 5)
            search_appearance_30d=30,  # 30/10 = 3
            applications_submitted_30d=10,  # 10/5 = 2
        )
        assert platform_engagement_score(s) == pytest.approx(10.0)

    def test_zero_engagement(self):
        """All zero → 0 pts."""
        s = _sig(
            saved_by_recruiters_30d=0,
            search_appearance_30d=0,
            applications_submitted_30d=0,
        )
        assert platform_engagement_score(s) == pytest.approx(0.0)

    def test_saved_cap_at_5(self):
        """saved_by_recruiters_30d = 100 → capped at 5."""
        s = _sig(
            saved_by_recruiters_30d=100,
            search_appearance_30d=0,
            applications_submitted_30d=0,
        )
        assert platform_engagement_score(s) == pytest.approx(5.0)

    def test_search_cap_at_3(self):
        """search_appearance_30d = 1000 → capped at 3."""
        s = _sig(
            saved_by_recruiters_30d=0,
            search_appearance_30d=1000,
            applications_submitted_30d=0,
        )
        assert platform_engagement_score(s) == pytest.approx(3.0)

    def test_apps_cap_at_2(self):
        """applications_submitted_30d = 100 → capped at 2."""
        s = _sig(
            saved_by_recruiters_30d=0,
            search_appearance_30d=0,
            applications_submitted_30d=100,
        )
        assert platform_engagement_score(s) == pytest.approx(2.0)

    def test_never_negative(self):
        """Always ≥ 0."""
        s = _sig(
            saved_by_recruiters_30d=0,
            search_appearance_30d=0,
            applications_submitted_30d=0,
        )
        assert platform_engagement_score(s) >= 0.0

    def test_partial_saves(self):
        """4 saves → 4/2 = 2 pts."""
        s = _sig(
            saved_by_recruiters_30d=4,
            search_appearance_30d=0,
            applications_submitted_30d=0,
        )
        assert platform_engagement_score(s) == pytest.approx(2.0)

    def test_partial_search(self):
        """20 appearances → 20/10 = 2 pts."""
        s = _sig(
            saved_by_recruiters_30d=0,
            search_appearance_30d=20,
            applications_submitted_30d=0,
        )
        assert platform_engagement_score(s) == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# TestComputeBehavioralScore — integration
# ---------------------------------------------------------------------------


class TestComputeBehavioralScore:
    """compute_behavioral_score() integration tests."""

    def test_returns_behavioral_score_type(self):
        result = compute_behavioral_score(_candidate())
        assert isinstance(result, BehavioralScore)

    def test_candidate_id_preserved(self):
        cand = _candidate(candidate_id="CAND_0012345")
        result = compute_behavioral_score(cand)
        assert result.candidate_id == "CAND_0012345"

    def test_sub_scores_match_individual_functions(self):
        """compute_behavioral_score must agree with each sub-scorer called directly."""
        sig = _sig()
        cand = _candidate(sig)
        result = compute_behavioral_score(cand)

        assert result.availability == pytest.approx(availability_score(sig))
        assert result.responsiveness == pytest.approx(responsiveness_score(sig))
        assert result.offer_reliability == pytest.approx(offer_reliability_score(sig))
        assert result.technical_credibility == pytest.approx(
            technical_credibility_score(sig)
        )
        assert result.profile_trust == pytest.approx(profile_trust_score(sig))
        assert result.platform_engagement == pytest.approx(
            platform_engagement_score(sig)
        )

    def test_total_is_sum_of_sub_scores(self):
        """total must equal sum of all six sub-scores (clamped to [0, 100])."""
        sig = _sig()
        cand = _candidate(sig)
        result = compute_behavioral_score(cand)
        expected = min(
            100.0,
            result.availability
            + result.responsiveness
            + result.offer_reliability
            + result.technical_credibility
            + result.profile_trust
            + result.platform_engagement,
        )
        assert result.total == pytest.approx(expected)

    def test_total_never_negative(self):
        """Composite total is always ≥ 0. AC6"""
        worst = _sig(
            open_to_work_flag=False,
            recruiter_response_rate=0.0,
            avg_response_time_hours=300.0,
            interview_completion_rate=0.0,
            offer_acceptance_rate=0.0,
            github_activity_score=0,
            skill_assessment_scores={},
            verified_email=False,
            verified_phone=False,
            linkedin_connected=False,
            profile_completeness_score=0.0,
            saved_by_recruiters_30d=0,
            search_appearance_30d=0,
            applications_submitted_30d=0,
            notice_period_days=180,
        )
        result = compute_behavioral_score(_candidate(worst))
        assert result.total >= 0.0

    def test_total_never_exceeds_100(self):
        """Composite total is always ≤ 100. AC6"""
        best = _sig(
            open_to_work_flag=True,
            notice_period_days=0,
            recruiter_response_rate=1.0,
            avg_response_time_hours=0.0,
            interview_completion_rate=1.0,
            offer_acceptance_rate=1.0,
            github_activity_score=100,
            skill_assessment_scores={"A": 100.0},
            verified_email=True,
            verified_phone=True,
            linkedin_connected=True,
            profile_completeness_score=100.0,
            saved_by_recruiters_30d=100,
            search_appearance_30d=1000,
            applications_submitted_30d=100,
        )
        result = compute_behavioral_score(_candidate(best))
        assert result.total <= 100.0

    def test_deterministic(self):
        """Same input always produces identical output."""
        sig = _sig()
        cand = _candidate(sig)
        r1 = compute_behavioral_score(cand)
        r2 = compute_behavioral_score(cand)
        assert r1.total == r2.total

    def test_all_sub_scores_in_range(self):
        """Each sub-score must stay within its documented [0, max]. AC6"""
        sig = _sig()
        cand = _candidate(sig)
        r = compute_behavioral_score(cand)
        assert 0.0 <= r.availability <= 15.0
        assert 0.0 <= r.responsiveness <= 20.0
        assert 0.0 <= r.offer_reliability <= 15.0
        assert 0.0 <= r.technical_credibility <= 25.0
        assert 0.0 <= r.profile_trust <= 15.0
        assert 0.0 <= r.platform_engagement <= 10.0


# ---------------------------------------------------------------------------
# TestAcceptanceCriteria — explicit named AC tests
# ---------------------------------------------------------------------------


class TestAcceptanceCriteria:
    """Named acceptance-criteria tests from the spec."""

    # --- AC1: high-signal candidate scores ≥ 75 ---

    def _high_signal_candidate(self) -> types.SimpleNamespace:
        """AC1 candidate: all mandatory fields + generous supporting fields."""
        sig = _sig(
            # Mandatory fields per spec
            open_to_work_flag=True,
            notice_period_days=15,
            interview_completion_rate=0.9,
            offer_acceptance_rate=0.8,
            verified_email=True,
            verified_phone=True,
            # Supporting fields set to high values to reach ≥ 75
            recruiter_response_rate=1.0,
            avg_response_time_hours=1.0,  # fast, no penalty
            github_activity_score=80.0,
            skill_assessment_scores={"Python": 90.0, "ML": 85.0},
            profile_completeness_score=90.0,
            linkedin_connected=True,
            saved_by_recruiters_30d=10,
            search_appearance_30d=30,
            applications_submitted_30d=10,
        )
        return _candidate(sig, "CAND_HIGH")

    def test_ac1_high_signal_ge_75(self):
        """High-signal candidate must score ≥ 75 total. AC1"""
        result = compute_behavioral_score(self._high_signal_candidate())
        assert result.total >= 75.0, (
            f"AC1 high-signal score={result.total:.2f}; expected ≥ 75. "
            f"Breakdown: avail={result.availability:.1f} "
            f"resp={result.responsiveness:.1f} "
            f"offer={result.offer_reliability:.1f} "
            f"tech={result.technical_credibility:.1f} "
            f"trust={result.profile_trust:.1f} "
            f"engage={result.platform_engagement:.1f}"
        )

    # --- AC2: low-signal candidate scores ≤ 20 ---

    def _low_signal_candidate(self) -> types.SimpleNamespace:
        """AC2 candidate: all mandatory fields + minimal supporting fields."""
        sig = _sig(
            # Mandatory fields per spec
            verified_email=False,
            verified_phone=False,
            linkedin_connected=False,
            recruiter_response_rate=0.1,
            interview_completion_rate=0.2,
            offer_acceptance_rate=0.0,
            # Supporting fields set low
            open_to_work_flag=False,
            notice_period_days=90,
            avg_response_time_hours=100.0,  # >72h → −6 penalty
            github_activity_score=-1,  # not linked → 3 pts
            skill_assessment_scores={},  # no assessments → 2 pts
            profile_completeness_score=20.0,
            saved_by_recruiters_30d=0,
            search_appearance_30d=0,
            applications_submitted_30d=0,
        )
        return _candidate(sig, "CAND_LOW")

    def test_ac2_low_signal_le_20(self):
        """Low-signal candidate must score ≤ 20 total. AC2"""
        result = compute_behavioral_score(self._low_signal_candidate())
        assert result.total <= 20.0, (
            f"AC2 low-signal score={result.total:.2f}; expected ≤ 20. "
            f"Breakdown: avail={result.availability:.1f} "
            f"resp={result.responsiveness:.1f} "
            f"offer={result.offer_reliability:.1f} "
            f"tech={result.technical_credibility:.1f} "
            f"trust={result.profile_trust:.1f} "
            f"engage={result.platform_engagement:.1f}"
        )

    # --- AC3: offer_acceptance_rate == -1 → 7.5 ---

    def test_ac3_offer_sentinel_returns_neutral(self):
        """offer_acceptance_rate == -1 → offer_reliability == 7.5. AC3"""
        s = _sig(offer_acceptance_rate=-1)
        assert offer_reliability_score(s) == pytest.approx(7.5), "AC3"

    def test_ac3_reflected_in_full_score(self):
        """Sentinel propagates correctly through compute_behavioral_score."""
        cand = _candidate(_sig(offer_acceptance_rate=-1))
        result = compute_behavioral_score(cand)
        assert result.offer_reliability == pytest.approx(7.5)

    # --- AC4: github_activity_score == -1 → 3.0 pts ---

    def test_ac4_github_not_linked_gives_3(self):
        """github_activity_score == -1 → 3.0 pts in that sub-component. AC4"""
        # Isolate: assessments = {"X": 0} → 0 pts from assessments
        s = _sig(github_activity_score=-1, skill_assessment_scores={"X": 0.0})
        score = technical_credibility_score(s)
        assert score == pytest.approx(3.0), (
            f"Expected 3.0 for github=-1 with zero-score assessments, got {score}"
        )

    # --- AC5: never raises on any valid RedrobSignals ---

    def test_ac5_does_not_raise_on_boundary_values(self):
        """compute_behavioral_score never raises for any valid field values. AC5"""
        boundary_cases = [
            dict(offer_acceptance_rate=-1, github_activity_score=-1),
            dict(offer_acceptance_rate=0.0, github_activity_score=0.0),
            dict(offer_acceptance_rate=1.0, github_activity_score=100.0),
            dict(skill_assessment_scores={}),
            dict(skill_assessment_scores={"Only": 0.0}),
            dict(skill_assessment_scores={"A": 100.0, "B": 50.0}),
            dict(notice_period_days=0),
            dict(notice_period_days=180),
            dict(avg_response_time_hours=0.0),
            dict(avg_response_time_hours=999.0),
            dict(profile_completeness_score=0.0),
            dict(profile_completeness_score=100.0),
            dict(
                verified_email=False,
                verified_phone=False,
                linkedin_connected=False,
            ),
            dict(
                verified_email=True,
                verified_phone=True,
                linkedin_connected=True,
            ),
        ]
        for overrides in boundary_cases:
            sig = _sig(**overrides)
            cand = _candidate(sig)
            # Must not raise
            result = compute_behavioral_score(cand)
            assert isinstance(result, BehavioralScore)

    # --- AC6: all scores clamped to stated ranges ---

    def test_ac6_sub_scores_clamped(self):
        """Every sub-score must stay within [0, max] for extreme inputs. AC6"""
        extremes = [
            _sig(open_to_work_flag=False, notice_period_days=180),
            _sig(open_to_work_flag=True, notice_period_days=0),
            _sig(recruiter_response_rate=0.0, avg_response_time_hours=999.0),
            _sig(recruiter_response_rate=1.0, avg_response_time_hours=0.0),
            _sig(offer_acceptance_rate=-1),
            _sig(offer_acceptance_rate=0.0),
            _sig(offer_acceptance_rate=1.0),
            _sig(github_activity_score=-1, skill_assessment_scores={}),
            _sig(github_activity_score=0, skill_assessment_scores={"X": 100.0}),
            _sig(github_activity_score=100, skill_assessment_scores={"A": 100.0}),
        ]
        for sig in extremes:
            r = compute_behavioral_score(_candidate(sig))
            assert 0.0 <= r.availability <= 15.0, f"availability OOB: {r.availability}"
            assert 0.0 <= r.responsiveness <= 20.0, f"resp OOB: {r.responsiveness}"
            assert 0.0 <= r.offer_reliability <= 15.0, (
                f"offer OOB: {r.offer_reliability}"
            )
            assert 0.0 <= r.technical_credibility <= 25.0, (
                f"tech OOB: {r.technical_credibility}"
            )
            assert 0.0 <= r.profile_trust <= 15.0, f"trust OOB: {r.profile_trust}"
            assert 0.0 <= r.platform_engagement <= 10.0, (
                f"engage OOB: {r.platform_engagement}"
            )
            assert 0.0 <= r.total <= 100.0, f"total OOB: {r.total}"

    # --- AC8: behavioural twins diverge meaningfully ---

    def test_ac8_behavioral_twins_diverge(self):
        """Two 'identical on paper' candidates with very different signals
        must have a meaningful gap (≥ 30 pts) in their behavioural scores. AC8
        """
        # Twin A: exemplary signals
        twin_a_sig = _sig(
            open_to_work_flag=True,
            notice_period_days=0,
            recruiter_response_rate=1.0,
            avg_response_time_hours=1.0,
            interview_completion_rate=1.0,
            offer_acceptance_rate=1.0,
            github_activity_score=90.0,
            skill_assessment_scores={"Python": 95.0, "ML": 90.0},
            verified_email=True,
            verified_phone=True,
            linkedin_connected=True,
            profile_completeness_score=100.0,
            saved_by_recruiters_30d=10,
            search_appearance_30d=30,
            applications_submitted_30d=10,
        )
        # Twin B: poor signals — everything minimal
        twin_b_sig = _sig(
            open_to_work_flag=False,
            notice_period_days=90,
            recruiter_response_rate=0.05,
            avg_response_time_hours=200.0,
            interview_completion_rate=0.05,
            offer_acceptance_rate=0.0,
            github_activity_score=0,
            skill_assessment_scores={},
            verified_email=False,
            verified_phone=False,
            linkedin_connected=False,
            profile_completeness_score=15.0,
            saved_by_recruiters_30d=0,
            search_appearance_30d=0,
            applications_submitted_30d=0,
        )
        score_a = compute_behavioral_score(_candidate(twin_a_sig, "TWIN_A")).total
        score_b = compute_behavioral_score(_candidate(twin_b_sig, "TWIN_B")).total
        delta = score_a - score_b

        assert delta >= 30.0, (
            f"Twins should diverge by ≥ 30 pts; got {score_a:.1f} vs {score_b:.1f} "
            f"(delta={delta:.1f}). AC8"
        )


# ---------------------------------------------------------------------------
# TestBatchBehavioralScores — batch processing
# ---------------------------------------------------------------------------


class TestBatchBehavioralScores:
    """batch_behavioral_scores() — list processing."""

    def test_returns_list_of_behavioral_scores(self):
        candidates = [_candidate(_sig(), f"CAND_{i:07d}") for i in range(5)]
        results = batch_behavioral_scores(candidates)
        assert isinstance(results, list)
        assert all(isinstance(r, BehavioralScore) for r in results)

    def test_result_length_matches_input(self):
        candidates = [_candidate() for _ in range(10)]
        results = batch_behavioral_scores(candidates)
        assert len(results) == 10

    def test_order_preserved(self):
        """Output order must match input order."""
        ids = [f"CAND_{i:07d}" for i in range(20)]
        candidates = [_candidate(_sig(), cid) for cid in ids]
        results = batch_behavioral_scores(candidates)
        assert [r.candidate_id for r in results] == ids

    def test_empty_list_returns_empty(self):
        assert batch_behavioral_scores([]) == []

    def test_results_match_individual_compute(self):
        """batch result must equal compute_behavioral_score called individually."""
        sigs = [
            _sig(open_to_work_flag=True),
            _sig(open_to_work_flag=False, github_activity_score=-1),
            _sig(offer_acceptance_rate=-1),
        ]
        candidates = [_candidate(s, f"CAND_{i:07d}") for i, s in enumerate(sigs)]
        batch = batch_behavioral_scores(candidates)
        individual = [compute_behavioral_score(c) for c in candidates]
        for b, ind in zip(batch, individual):
            assert b.total == pytest.approx(ind.total)


# ---------------------------------------------------------------------------
# TestPerformance — AC7
# ---------------------------------------------------------------------------


class TestPerformance:
    """500 candidates must be scored in < 0.5 seconds. AC7"""

    def _make_500_candidates(self) -> list:
        varied_sigs = [
            _sig(open_to_work_flag=True, github_activity_score=80),
            _sig(offer_acceptance_rate=-1, verified_email=False),
            _sig(github_activity_score=-1, skill_assessment_scores={}),
            _sig(avg_response_time_hours=200, interview_completion_rate=0.1),
            _sig(
                verified_email=True,
                verified_phone=True,
                linkedin_connected=True,
                profile_completeness_score=95.0,
            ),
        ]
        candidates = []
        for i in range(500):
            sig = varied_sigs[i % len(varied_sigs)]
            candidates.append(_candidate(sig, f"CAND_{i:07d}"))
        return candidates

    def test_500_candidates_under_0_5s(self):
        """batch_behavioral_scores(500) must complete in < 0.5 s. AC7"""
        candidates = self._make_500_candidates()

        t0 = time.perf_counter()
        results = batch_behavioral_scores(candidates)
        elapsed = time.perf_counter() - t0

        assert elapsed < 0.5, (
            f"batch_behavioral_scores(500) took {elapsed:.3f}s; expected < 0.5s. AC7"
        )
        assert len(results) == 500

    def test_all_totals_in_range_under_load(self):
        """No overflow or underflow during bulk scoring. AC6"""
        candidates = self._make_500_candidates()
        for r in batch_behavioral_scores(candidates):
            assert 0.0 <= r.total <= 100.0


# ---------------------------------------------------------------------------
# TestSignalScorerClass — backward-compat class wrapper
# ---------------------------------------------------------------------------


class TestSignalScorerClass:
    """SignalScorer class must delegate correctly to module-level functions."""

    def test_score_returns_float_in_0_1(self):
        scorer = SignalScorer()
        cand = _candidate()
        result = scorer.score(cand)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_score_is_total_over_100(self):
        scorer = SignalScorer()
        cand = _candidate()
        assert scorer.score(cand) == pytest.approx(
            compute_behavioral_score(cand).total / 100.0
        )

    def test_compute_returns_behavioral_score(self):
        scorer = SignalScorer()
        cand = _candidate()
        result = scorer.compute(cand)
        assert isinstance(result, BehavioralScore)
