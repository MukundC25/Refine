"""
honeypot_detector.py — Honeypot and anomaly detector for candidate profiles.

The challenge dataset contains ~80 honeypot profiles out of 100 K that must be
caught before ranking.  Missed honeypots inflate the top-100 with irrelevant
candidates; over-flagging valid profiles shrinks the usable pool.

Design goals
────────────
  • False-negative rate: catch ≥ 90 % of the ~80 known honeypots.
  • False-positive rate: at most ~40 legitimate candidates flagged across 100 K
    (0.04 %), keeping total flagged in the 50–120 range per spec.
  • Each check is independent; flags from multiple checks accumulate.
  • Penalty multiplier converts flag count to a score damper, not a hard binary
    (except at 3+ flags where the profile is effectively disqualified).
  • All flags are logged with candidate_id for full audit.

Penalty table
─────────────
  0 flags  → 1.0  (clean)
  1 flag   → 0.7  (soft penalty)
  2 flags  → 0.4  (strong penalty)
  3+ flags → 0.0  (disqualified from top-100)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from backend.app.core.candidate_loader import CandidateRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Reference date — treat "today" as the dataset cutoff
# ---------------------------------------------------------------------------

_REFERENCE_DATE = date(2026, 6, 21)

# ---------------------------------------------------------------------------
# Domain keyword sets
# ---------------------------------------------------------------------------

# Technical roles — careers in these domains are coherent with AI/ML skills.
_TECHNICAL_TITLE_KEYWORDS: frozenset[str] = frozenset({
    "engineer", "developer", "scientist", "analyst", "architect",
    "data", "ml", "ai", "research", "devops", "sre", "platform",
    "backend", "frontend", "fullstack", "full stack", "software",
    "cloud", "infra", "infrastructure", "qa", "tester", "testing",
    "nlp", "computer vision", "mlops", "quantitative",
})

# Non-technical roles — careers *exclusively* in these with no technical
# crossover AND a heavy AI skill list is a keyword-stuffer signal.
_NON_TECHNICAL_TITLE_KEYWORDS: frozenset[str] = frozenset({
    "marketing", "sales", "hr", "human resource", "recruiter",
    "accountant", "accounting", "finance", "operations manager",
    "content writer", "graphic designer", "civil engineer",
    "mechanical engineer", "brand", "customer support",
    "supply chain", "logistics", "procurement",
})

# AI/ML skills that are specific enough to be meaningful (not generic like
# "Python" or "Excel") — used only in the career-skill coherence check.
_SPECIFIC_AI_SKILLS: frozenset[str] = frozenset({
    "tensorflow", "pytorch", "keras", "jax",
    "hugging face", "hugging face transformers",
    "bert", "gpt", "llm", "llms", "fine-tuning llms",
    "transformers", "diffusion models",
    "nlp", "natural language processing",
    "computer vision", "object detection", "image classification",
    "deep learning", "neural networks",
    "reinforcement learning",
    "mlops", "kubeflow", "mlflow", "bentoml",
    "recommendation systems",
    "speech recognition", "tts",
    "gans", "lora",
})

# Technical keywords we look for *inside career descriptions*.
# Rules for this set:
#   - Multi-word phrases are safe (no false sub-string matches).
#   - Single-word tokens must be specific enough that they won't hit
#     non-technical prose — e.g. "git" hits "digital", "software" hits
#     industry labels, "model" hits "business model".
#   - Matching is done with word-boundary regex (see _career_is_technical).
_CAREER_TECH_KEYWORDS: frozenset[str] = frozenset({
    # Explicit programming / infra tokens
    "python", "sql", "spark", "kafka", "airflow", "dbt",
    "tensorflow", "pytorch", "scikit", "pandas", "numpy",
    "kubernetes", "docker", "terraform",
    "aws", "gcp", "azure",
    "llm", "mlops", "kubeflow", "mlflow",
    # Multi-word phrases (safe from sub-string collisions)
    "machine learning", "deep learning", "neural network",
    "model training", "data pipeline", "data warehouse",
    "feature engineering", "natural language processing",
    "computer vision", "data science",
    "software engineer", "backend engineer", "frontend engineer",
    "full stack", "data engineer", "ml engineer",
    "api development", "microservice", "codebase",
    "github", "version control",
})

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class HoneypotResult:
    """Detection result for a single candidate.

    Attributes:
        is_suspicious: True when at least one flag was raised.
        confidence:    Suspicion score in [0.0, 1.0]; higher = more suspicious.
        flags:         Human-readable list of triggered flag descriptions.
        penalty_multiplier:
            Score multiplier applied to the candidate's final rank score.
            1.0 = no penalty; 0.0 = disqualified from top-100.
    """
    is_suspicious: bool
    confidence: float
    flags: list[str] = field(default_factory=list)
    penalty_multiplier: float = 1.0


# ---------------------------------------------------------------------------
# Penalty computation
# ---------------------------------------------------------------------------

def compute_penalty(flags: list[str]) -> float:
    """Map flag count to a penalty multiplier.

    Args:
        flags: List of triggered flag strings (length determines penalty tier).

    Returns:
        Multiplier in {1.0, 0.7, 0.4, 0.0}.
    """
    n = len(flags)
    if n == 0:
        return 1.0
    if n == 1:
        return 0.7
    if n == 2:
        return 0.4
    return 0.0  # 3+ flags → disqualified


# ---------------------------------------------------------------------------
# Individual check functions
# ---------------------------------------------------------------------------

def check_temporal_consistency(candidate: CandidateRecord) -> list[str]:
    """Detect impossible timelines in career history and education.

    Checks performed:
    1. ``years_of_experience`` is significantly larger than the implied
       career span (earliest start_date → reference_date).
    2. ``duration_months`` on a role is materially wrong vs. the actual
       date arithmetic (catches fabricated tenure numbers).
    3. Education ``end_year`` is in the future (after reference year).

    Only raises flags when the discrepancy is large enough to be
    implausible rather than a rounding artefact.  Legitimate data shows
    ±1–2 month drift between stated and computed durations.

    Args:
        candidate: Validated candidate record.

    Returns:
        List of flag strings; empty list = no issues found.
    """
    flags: list[str] = []

    # ── 1. YOE vs career span ────────────────────────────────────────────── #
    start_dates: list[date] = []
    for job in candidate.career_history:
        try:
            start_dates.append(datetime.strptime(job.start_date, "%Y-%m-%d").date())
        except ValueError:
            pass  # malformed date; already survived Pydantic, skip silently

    if start_dates:
        earliest_start = min(start_dates)
        career_span_years = (_REFERENCE_DATE - earliest_start).days / 365.25
        yoe = candidate.profile.years_of_experience
        # Allow 2-year buffer for pre-career freelance, internships, etc.
        if yoe > career_span_years + 2.0:
            flags.append(
                f"temporal:yoe_exceeds_span — claims {yoe:.1f} yrs experience "
                f"but earliest career entry only {career_span_years:.1f} yrs ago"
            )

    # ── 2. duration_months vs actual date range ──────────────────────────── #
    duration_violations = 0
    for job in candidate.career_history:
        try:
            start = datetime.strptime(job.start_date, "%Y-%m-%d").date()
            end = (
                datetime.strptime(job.end_date, "%Y-%m-%d").date()
                if job.end_date
                else _REFERENCE_DATE
            )
            actual_months = (end.year - start.year) * 12 + (end.month - start.month)
            diff = abs(actual_months - job.duration_months)
            # Legitimate rounding produces ≤ 2-month drift; flag at ≥ 4.
            if diff >= 4:
                duration_violations += 1
        except ValueError:
            pass

    if duration_violations >= 2:
        # Require ≥ 2 violations to avoid flagging single data-entry errors.
        flags.append(
            f"temporal:duration_mismatch — {duration_violations} role(s) have "
            f"duration_months inconsistent with start/end dates by ≥4 months"
        )

    # ── 3. Future education end year ─────────────────────────────────────── #
    future_edu = [
        e.institution
        for e in candidate.education
        if e.end_year > _REFERENCE_DATE.year
    ]
    if future_edu:
        flags.append(
            f"temporal:future_education — end_year after {_REFERENCE_DATE.year} "
            f"for: {', '.join(future_edu)}"
        )

    return flags


def check_skill_inflation(candidate: CandidateRecord) -> list[str]:
    """Detect fabricated or inflated skill proficiency claims.

    Checks performed:
    1. Expert/advanced proficiency with ``duration_months = 0`` — impossible
       to be expert in something you've never used.
    2. ≥ 6 skills all declared expert with zero endorsements — bulk inflation.
    3. Skill assessment score < 35 for a skill claimed as advanced/expert
       *when an assessment score exists* — objective evidence of overstatement.

    Args:
        candidate: Validated candidate record.

    Returns:
        List of flag strings; empty list = clean.
    """
    flags: list[str] = []

    expert_zero_duration = [
        s.name
        for s in candidate.skills
        if s.proficiency in ("advanced", "expert")
        and s.duration_months is not None
        and s.duration_months == 0
    ]
    if expert_zero_duration:
        flags.append(
            f"skill_inflation:expert_zero_duration — expert/advanced proficiency "
            f"with 0 months usage: {', '.join(expert_zero_duration)}"
        )

    expert_no_endorsements = [
        s.name
        for s in candidate.skills
        if s.proficiency in ("advanced", "expert")
        and s.endorsements == 0
    ]
    # Require a cluster of ≥ 6 to avoid flagging a single legitimate outlier.
    if len(expert_no_endorsements) >= 6:
        flags.append(
            f"skill_inflation:bulk_unendorsed_expertise — "
            f"{len(expert_no_endorsements)} skills claimed advanced/expert with "
            f"0 endorsements: {', '.join(expert_no_endorsements[:5])}…"
        )

    # Assessment-score contradiction
    assessment_scores = candidate.redrob_signals.skill_assessment_scores
    contradictions = []
    for s in candidate.skills:
        if s.proficiency in ("advanced", "expert") and s.name in assessment_scores:
            score = assessment_scores[s.name]
            if score < 35:
                contradictions.append(f"{s.name}={score:.0f}")
    if len(contradictions) >= 2:
        # Require ≥ 2 contradictions; a single low score may be an off day.
        flags.append(
            f"skill_inflation:assessment_contradiction — claims advanced/expert "
            f"but scored <35 on: {', '.join(contradictions)}"
        )

    return flags


def _career_is_technical(candidate: CandidateRecord) -> bool:
    """Return True if *any* specific technical signal exists in career history.

    Uses word-boundary matching for single-word tokens to avoid false hits
    like 'git' inside 'digital' or 'sql' inside a company name.  Multi-word
    phrases (which already carry enough context) are matched as substrings.

    Used to distinguish genuine career changers (who have at least some
    technical job history) from pure keyword stuffers (none at all).
    """
    all_text = " ".join(
        f"{j.title} {j.description} {j.industry}"
        for j in candidate.career_history
    ).lower()

    for kw in _CAREER_TECH_KEYWORDS:
        if " " in kw:
            # Multi-word phrase — substring match is safe
            if kw in all_text:
                return True
        else:
            # Single token — require word boundaries to prevent sub-string hits
            if re.search(r"\b" + re.escape(kw) + r"\b", all_text):
                return True
    return False


def _has_recent_technical_role(candidate: CandidateRecord, lookback_years: float = 5.0) -> bool:
    """Return True if the candidate held a technical role in recent history.

    A role is "recent" if its end_date (or None for current) falls within
    *lookback_years* of the reference date.  This guards against flagging
    someone who was a marketing manager 8 years ago but has been a data
    scientist for the past 4 years.
    """
    cutoff = date(
        _REFERENCE_DATE.year - int(lookback_years),
        _REFERENCE_DATE.month,
        _REFERENCE_DATE.day,
    )
    for job in candidate.career_history:
        title_lower = job.title.lower()
        if any(kw in title_lower for kw in _TECHNICAL_TITLE_KEYWORDS):
            try:
                end = (
                    datetime.strptime(job.end_date, "%Y-%m-%d").date()
                    if job.end_date
                    else _REFERENCE_DATE
                )
                if end >= cutoff:
                    return True
            except ValueError:
                pass
    return False


def check_career_skill_coherence(candidate: CandidateRecord) -> list[str]:
    """Detect candidates whose claimed skills are disconnected from career.

    This is the "keyword stuffer" check.  It is intentionally conservative
    to avoid penalising legitimate career changers:

    A flag is raised only when ALL of the following are true:
      a) Current title (and all career titles) are exclusively non-technical.
      b) No technical keywords appear anywhere in career descriptions.
      c) The candidate lists ≥ 4 specific AI/ML skills (not generic ones).
      d) They do NOT have any technical role in the last 5 years.

    Condition (d) provides the career-changer escape hatch.

    Args:
        candidate: Validated candidate record.

    Returns:
        List of flag strings; empty list = coherent or ambiguous.
    """
    flags: list[str] = []

    all_titles_lower = [j.title.lower() for j in candidate.career_history]
    current_title_lower = candidate.profile.current_title.lower()

    # ── (a) Check if all titles are non-technical ────────────────────────── #
    def _is_nontechnical_title(t: str) -> bool:
        # A title is non-technical if it contains no technical keyword.
        return not any(kw in t for kw in _TECHNICAL_TITLE_KEYWORDS)

    all_nontechnical = all(_is_nontechnical_title(t) for t in all_titles_lower)
    if not all_nontechnical:
        return flags  # has at least one technical title → not a keyword stuffer

    # ── (b) No technical keywords in career descriptions ─────────────────── #
    if _career_is_technical(candidate):
        return flags  # technical work appears in descriptions → not a stuffer

    # ── (c) Claims ≥ 4 specific AI/ML skills ────────────────────────────── #
    skill_names_lower = {s.name.lower() for s in candidate.skills}
    ai_skill_hits = [s for s in skill_names_lower if s in _SPECIFIC_AI_SKILLS]
    if len(ai_skill_hits) < 4:
        return flags  # not enough AI skills to constitute stuffing

    # ── (d) No technical role in last 5 years ────────────────────────────── #
    if _has_recent_technical_role(candidate, lookback_years=5.0):
        return flags  # genuine career changer with recent technical work

    flags.append(
        f"career_skill_mismatch:keyword_stuffer — "
        f"entire career history is non-technical ({current_title_lower}) but "
        f"claims {len(ai_skill_hits)} specific AI/ML skills: "
        f"{', '.join(sorted(ai_skill_hits)[:6])}"
    )
    return flags


def check_signal_sanity(candidate: CandidateRecord) -> list[str]:
    """Detect manipulated or internally inconsistent platform signals.

    Checks performed:
    1. All three verifications false (no email, phone, or LinkedIn) — strong
       low-trust signal.  Combined with a non-technical profile it becomes a
       meaningful honeypot indicator, but alone it's just a single flag.
    2. Suspiciously perfect signal combination: both interview_completion_rate
       and offer_acceptance_rate are 1.0 simultaneously.  Real users rarely
       achieve both simultaneously at 1.0.
    3. github_activity_score = 100 with no technical career history — someone
       who has never worked in tech shouldn't have a perfect GitHub score.

    Args:
        candidate: Validated candidate record.

    Returns:
        List of flag strings.
    """
    flags: list[str] = []
    sig = candidate.redrob_signals

    # ── 1. Triple verification failure ───────────────────────────────────── #
    if not sig.verified_email and not sig.verified_phone and not sig.linkedin_connected:
        flags.append(
            "signal_sanity:unverified_profile — "
            "verified_email=False, verified_phone=False, linkedin_connected=False"
        )

    # ── 2. Suspiciously perfect completion + acceptance ───────────────────── #
    if sig.interview_completion_rate == 1.0 and sig.offer_acceptance_rate == 1.0:
        flags.append(
            "signal_sanity:perfect_engagement — "
            "interview_completion_rate=1.0 AND offer_acceptance_rate=1.0"
        )

    # ── 3. Perfect GitHub score with no technical background ─────────────── #
    if sig.github_activity_score == 100.0 and not _career_is_technical(candidate):
        flags.append(
            "signal_sanity:github_score_mismatch — "
            "github_activity_score=100 but no technical keywords in career history"
        )

    return flags


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def detect_honeypot(candidate: CandidateRecord) -> HoneypotResult:
    """Run all honeypot checks on a candidate and return a :class:`HoneypotResult`.

    Checks are independent; flags from all checkers are accumulated before the
    penalty multiplier is computed.  Results are logged at WARNING level for
    any suspicious candidate to provide a full audit trail.

    Args:
        candidate: A validated :class:`~backend.app.core.candidate_loader.CandidateRecord`.

    Returns:
        :class:`HoneypotResult` with ``is_suspicious``, ``confidence``,
        ``flags``, and ``penalty_multiplier`` populated.
    """
    all_flags: list[str] = []

    all_flags.extend(check_temporal_consistency(candidate))
    all_flags.extend(check_skill_inflation(candidate))
    all_flags.extend(check_career_skill_coherence(candidate))
    all_flags.extend(check_signal_sanity(candidate))

    multiplier = compute_penalty(all_flags)

    # Confidence: 0 flags → 0.0, 1 → 0.4, 2 → 0.7, 3+ → 1.0
    # (Non-linear: small confidence for single flags to reflect genuine uncertainty.)
    n = len(all_flags)
    if n == 0:
        confidence = 0.0
    elif n == 1:
        confidence = 0.4
    elif n == 2:
        confidence = 0.7
    else:
        confidence = min(1.0, 0.7 + 0.1 * (n - 2))

    is_suspicious = n > 0

    if is_suspicious:
        logger.warning(
            "Honeypot suspect %s — multiplier=%.1f confidence=%.2f flags=%s",
            candidate.candidate_id,
            multiplier,
            confidence,
            all_flags,
        )

    return HoneypotResult(
        is_suspicious=is_suspicious,
        confidence=confidence,
        flags=all_flags,
        penalty_multiplier=multiplier,
    )
