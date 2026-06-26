"""
signal_scorer.py — Behavioural signal scorer.

Converts the ``redrob_signals`` block on every candidate profile into a
calibrated 0–100 behavioural score across six orthogonal dimensions.

This is the highest-differentiation component in the ranking system.
Keyword matchers ignore these signals entirely; this module surfaces the
"behavioural twin" separation that no plain skills-matcher can reproduce.

Six scoring dimensions
-----------------------
  availability         0–15  — actively looking + low notice-period friction
  responsiveness       0–20  — funnel-completion probability (response rate,
                               speed, interview reliability)
  offer_reliability    0–15  — historical offer-acceptance behaviour
  technical_credibility 0–25 — GitHub activity + platform assessment scores
  profile_trust        0–15  — verification signals + profile completeness
  platform_engagement  0–10  — social proof + discoverability + active use

Total max:  100 pts

Public API
----------
  availability_score(signals)         → float (0–15)
  responsiveness_score(signals)       → float (0–20)
  offer_reliability_score(signals)    → float (0–15)
  technical_credibility_score(signals) → float (0–25)
  profile_trust_score(signals)        → float (0–15)
  platform_engagement_score(signals)  → float (0–10)
  compute_behavioral_score(candidate) → BehavioralScore
  batch_behavioral_scores(candidates) → list[BehavioralScore]

All functions are pure (no I/O, no global state, deterministic output).

Implementation: Issue 005
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class BehavioralScore:
    """Structured behavioural-signal result for a single candidate."""

    candidate_id: str
    availability: float  # 0–15
    responsiveness: float  # 0–20
    offer_reliability: float  # 0–15
    technical_credibility: float  # 0–25
    profile_trust: float  # 0–15
    platform_engagement: float  # 0–10
    total: float  # 0–100  weighted composite


# ---------------------------------------------------------------------------
# Sub-scorers — all pure functions
# ---------------------------------------------------------------------------


def availability_score(signals: Any) -> float:
    """Score candidate availability and immediacy of start (0–15 pts).

    Components
    ----------
    open_to_work_flag  → +8 pts  (active seeker, reduces time-to-hire)
    notice_period_days → 0–7 pts via ``max(0, 7 − days/15)``
                         0 days ≈ 7 pts   (can start immediately)
                         15 days ≈ 6 pts
                         105+ days ≈ 0 pts

    Args:
        signals: A ``RedrobSignals`` object (or any object with the same
                 attribute names).

    Returns:
        Float in [0, 15].
    """
    score = 0.0

    if signals.open_to_work_flag:
        score += 8.0

    # Notice period: lower is better — linear decay capped at 0
    notice_pts = max(0.0, 7.0 - (signals.notice_period_days / 15.0))
    score += notice_pts

    return min(score, 15.0)


def responsiveness_score(signals: Any) -> float:
    """Score the probability that the candidate will complete the hiring funnel
    (0–20 pts).

    Components
    ----------
    recruiter_response_rate  → 0–12 pts  (historical engagement rate)
    avg_response_time_hours  → 0 / −1 / −3 / −6 penalty tiers
                               ≤ 4 h   →  0 penalty
                               4–24 h  → −1
                               24–72 h → −3
                               > 72 h  → −6
    interview_completion_rate → 0–8 pts  (reliability once scheduled)

    Result is clamped to [0, 20]; slow responders cannot score below 0.

    Args:
        signals: A ``RedrobSignals`` object.

    Returns:
        Float in [0, 20].
    """
    response_pts = signals.recruiter_response_rate * 12.0

    # Graduated penalty for slow response times
    hours = signals.avg_response_time_hours
    if hours > 72.0:
        time_penalty = 6.0
    elif hours > 24.0:
        time_penalty = 3.0
    elif hours > 4.0:
        time_penalty = 1.0
    else:
        time_penalty = 0.0

    interview_pts = signals.interview_completion_rate * 8.0

    raw = response_pts + interview_pts - time_penalty
    return max(0.0, min(20.0, raw))


def offer_reliability_score(signals: Any) -> float:
    """Score historical offer-acceptance behaviour (0–15 pts).

    A candidate who always declines offers after accepting them wastes recruiter
    time. Conversely, a candidate with no offer history should not be penalised.

    Edge case
    ---------
    ``offer_acceptance_rate == -1`` → no offer history on record.
    Returns the neutral midpoint 7.5 so the candidate is neither rewarded
    nor penalised for an empty track record.

    Args:
        signals: A ``RedrobSignals`` object.

    Returns:
        Float in [0, 15].
    """
    rate = signals.offer_acceptance_rate

    # Sentinel value: no historical offer data — treat as neutral
    if rate == -1:
        return 7.5

    # Linear: 0.0 → 0 pts,  1.0 → 15 pts
    return max(0.0, min(15.0, rate * 15.0))


def technical_credibility_score(signals: Any) -> float:
    """Score independently-verified technical output (0–25 pts).

    Components
    ----------
    github_activity_score (0–100 or −1)
      > 0   → (score / 100) × 15  (real engineering output)
      == 0  → 0 pts               (linked but inactive)
      == −1 → 3 pts               (not linked — neutral, small discount)

    skill_assessment_scores  (dict[str, float], values 0–100)
      Non-empty → average × (10/100)  (platform-verified competency)
      Empty     → 2 pts               (no assessments — neutral default)

    Args:
        signals: A ``RedrobSignals`` object.

    Returns:
        Float in [0, 25].
    """
    score = 0.0

    gh = signals.github_activity_score
    if gh > 0:
        score += (gh / 100.0) * 15.0
    elif gh == -1:
        # Not linked — give a small neutral credit rather than zero
        score += 3.0
    # gh == 0: actively linked but no activity → 0 pts (legitimate signal)

    assessments = signals.skill_assessment_scores
    if assessments:
        avg = sum(assessments.values()) / len(assessments)
        score += (avg / 100.0) * 10.0
    else:
        # No assessments taken — neutral default so absence isn't a hard penalty
        score += 2.0

    return min(score, 25.0)


def profile_trust_score(signals: Any) -> float:
    """Score identity-verification and platform trust signals (0–15 pts).

    A fully verified, complete profile suggests a serious candidate.
    Profiles with zero verification and low completeness are consistent with
    honeypot-adjacent entries.

    Components
    ----------
    verified_email           → +4 pts
    verified_phone           → +4 pts
    linkedin_connected       → +3 pts
    profile_completeness_score (0–100) → 0–4 pts

    Args:
        signals: A ``RedrobSignals`` object.

    Returns:
        Float in [0, 15].
    """
    score = 0.0

    if signals.verified_email:
        score += 4.0
    if signals.verified_phone:
        score += 4.0
    if signals.linkedin_connected:
        score += 3.0

    score += (signals.profile_completeness_score / 100.0) * 4.0

    return min(score, 15.0)


def platform_engagement_score(signals: Any) -> float:
    """Score active engagement with the Redrob platform (0–10 pts).

    Passive candidates who keep their profile up but never use the platform
    are less likely to respond. Engagement shows intent.

    Components
    ----------
    saved_by_recruiters_30d  → min(saves / 2, 5.0)   (recruiter social proof)
    search_appearance_30d    → min(count / 10, 3.0)   (discoverability)
    applications_submitted_30d → min(apps / 5, 2.0)   (active job-seeking)

    Args:
        signals: A ``RedrobSignals`` object.

    Returns:
        Float in [0, 10].
    """
    saved_pts = min(signals.saved_by_recruiters_30d / 2.0, 5.0)
    search_pts = min(signals.search_appearance_30d / 10.0, 3.0)
    app_pts = min(signals.applications_submitted_30d / 5.0, 2.0)
    return saved_pts + search_pts + app_pts


# ---------------------------------------------------------------------------
# Composite scorer
# ---------------------------------------------------------------------------


def compute_behavioral_score(candidate: Any) -> BehavioralScore:
    """Compute the full behavioural score for a single candidate.

    Calls all six sub-scorers on ``candidate.redrob_signals``, sums the
    results, and clamps the composite total to [0, 100].

    Args:
        candidate: A ``CandidateRecord`` (or any object with ``candidate_id``
                   and ``redrob_signals`` attributes).

    Returns:
        A fully populated :class:`BehavioralScore`.

    Raises:
        AttributeError: If the required signal fields are missing.
    """
    sig = candidate.redrob_signals

    avail = availability_score(sig)
    resp = responsiveness_score(sig)
    offer = offer_reliability_score(sig)
    tech = technical_credibility_score(sig)
    trust = profile_trust_score(sig)
    engage = platform_engagement_score(sig)

    total = min(100.0, max(0.0, avail + resp + offer + tech + trust + engage))

    return BehavioralScore(
        candidate_id=candidate.candidate_id,
        availability=avail,
        responsiveness=resp,
        offer_reliability=offer,
        technical_credibility=tech,
        profile_trust=trust,
        platform_engagement=engage,
        total=total,
    )


def batch_behavioral_scores(candidates: list[Any]) -> list[BehavioralScore]:
    """Score a list of candidates, returning one :class:`BehavioralScore` each.

    Designed for the top-500 stage of the hybrid ranking pipeline.  All
    operations are pure arithmetic — 500 candidates completes in well under
    0.5 seconds even on a single CPU core.

    Args:
        candidates: List of ``CandidateRecord`` objects (or compatible ducks).

    Returns:
        List of :class:`BehavioralScore` in the same order as *candidates*.
    """
    return [compute_behavioral_score(c) for c in candidates]


# ---------------------------------------------------------------------------
# Backward-compat class wrapper
# ---------------------------------------------------------------------------


class SignalScorer:
    """Thin class wrapper around the module-level scoring functions.

    Retained for backward compatibility with code that instantiates a
    ``SignalScorer`` object.  Prefer calling ``compute_behavioral_score()``
    directly.
    """

    def score(self, candidate: Any) -> float:
        """Return ``BehavioralScore.total`` (normalised to [0, 1]) for *candidate*.

        Kept for backward compatibility.  The original stub returned a float
        in [0, 1]; this implementation divides the 0–100 total by 100.

        Args:
            candidate: A ``CandidateRecord`` or compatible duck-type.

        Returns:
            Float in [0, 1].
        """
        return compute_behavioral_score(candidate).total / 100.0

    def compute(self, candidate: Any) -> BehavioralScore:
        """Return the full :class:`BehavioralScore` for *candidate*.

        Args:
            candidate: A ``CandidateRecord`` or compatible duck-type.

        Returns:
            :class:`BehavioralScore`.
        """
        return compute_behavioral_score(candidate)
