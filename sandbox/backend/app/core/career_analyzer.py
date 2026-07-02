"""
career_analyzer.py — Career trajectory scorer.

Analyses a candidate's employment history to derive five orthogonal trajectory
signals and combines them into a 0–100 composite score.

Five scoring dimensions
-----------------------
  seniority_progression  0–25  — IC title arc (ascending / lateral / declining)
  company_type           0–25  — product company ratio vs. pure outsourcing shops
  domain_convergence     0–30  — depth of AI/ML vocabulary in career descriptions
  tenure_stability       0–10  — penalise serial job-hopping (< 12 months per role)
  industry_relevance     0–10  — % of career in tech-adjacent industries

Public API
----------
  analyze_career(candidate, jd)          → CareerTrajectoryScore
  progression_score(career_history)      → float  (0–25)
  company_type_score(career_history)     → float  (0–25)
  domain_convergence_score(career_history) → float (0–30)
  tenure_stability_score(career_history) → float  (0–10)
  industry_relevance_score(career_history) → float (0–10)
  label_trajectory(scores)              → str

All functions are pure — no side effects, identical inputs always produce
identical outputs.

Implementation: Issue 009
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain constants
# ---------------------------------------------------------------------------

# Job title keywords mapped to an IC seniority level (0 = intern, 5 = executive).
# Level 5 represents the management / director track (non-IC for technical roles).
SENIORITY_MAP: dict[str, int] = {
    "intern": 0,
    "trainee": 0,
    "junior": 1,
    "analyst": 1,
    "associate": 1,
    "engineer": 2,
    "developer": 2,
    "programmer": 2,
    "senior": 3,
    "specialist": 3,
    "lead": 3,
    "staff": 4,
    "principal": 4,
    "architect": 4,
    "manager": 5,
    "director": 5,
    "head": 5,
    "vp": 5,
}

# Well-known Indian IT outsourcing / services firms.
OUTSOURCING_FIRMS: frozenset[str] = frozenset(
    {
        "tcs",
        "infosys",
        "wipro",
        "accenture",
        "cognizant",
        "capgemini",
        "hcl",
        "tech mahindra",
        "mphasis",
        "hexaware",
        "mastek",
        "niit",
    }
)

# Three-tier vocabulary for domain convergence scoring.
# Tier 1 = core AI/ML; Tier 2 = data-engineering feeder; Tier 3 = basic analytics.
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "tier_1": [
        "machine learning",
        "nlp",
        "embeddings",
        "retrieval",
        "ranking",
        "recommendation",
        "search",
        "vector",
        "bert",
        "transformer",
        "fine-tuning",
        "rag",
        "llm",
        "model training",
        "feature engineering",
    ],
    "tier_2": [
        "python",
        "spark",
        "airflow",
        "data engineering",
        "etl",
        "pipeline",
    ],
    "tier_3": [
        "sql",
        "excel",
        "reporting",
        "tableau",
        "data entry",
    ],
}

# Industry substrings that indicate a technically relevant company.
HIGH_RELEVANCE_INDUSTRIES: frozenset[str] = frozenset(
    {
        "technology",
        "software",
        "saas",
        "fintech",
        "edtech",
        "healthtech",
        "e-commerce",
        "ecommerce",
        "ai",
        "data",
        "analytics",
    }
)

# Scoring weights per tier and the recency multiplier
_TIER_WEIGHTS: dict[str, float] = {"tier_1": 4.0, "tier_2": 2.5, "tier_3": 0.5}
_RECENCY_MULTIPLIER: float = 2.0
_RECENCY_WINDOW_MONTHS: int = 24


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class CareerTrajectoryScore:
    """Structured career-trajectory result for a single candidate."""

    candidate_id: str
    seniority_progression: float  # 0–25
    company_type: float  # 0–25
    domain_convergence: float  # 0–30
    tenure_stability: float  # 0–10
    industry_relevance: float  # 0–10
    total: float  # 0–100 weighted composite
    trajectory_label: str  # "ascending" | "lateral" | "declining" | "pivot"


# ---------------------------------------------------------------------------
# Private date helpers
# ---------------------------------------------------------------------------


def _parse_date(date_str: str | None) -> date | None:
    """Parse an ISO-8601 date string; returns ``None`` on any failure."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(date_str.strip()[:10], "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def _career_reference_date(career_history: list) -> date:
    """Return the effective 'today' from the latest date found in the career.

    Uses the maximum of all start_date and end_date values across all entries.
    Falls back to the actual system date if no dates can be parsed.
    """
    all_dates: list[date] = []
    for entry in career_history:
        for attr in ("start_date", "end_date"):
            d = _parse_date(getattr(entry, attr, None))
            if d:
                all_dates.append(d)
    return max(all_dates) if all_dates else date.today()


def _is_recent(
    entry: Any, ref_date: date, months: int = _RECENCY_WINDOW_MONTHS
) -> bool:
    """True if *entry* was active within *months* before *ref_date*.

    A role is always considered recent if ``is_current is True`` or ``end_date``
    is absent.
    """
    if getattr(entry, "is_current", False) or not getattr(entry, "end_date", None):
        return True
    end = _parse_date(entry.end_date)
    if end is None:
        return getattr(entry, "is_current", False)
    months_elapsed = (ref_date.year - end.year) * 12 + (ref_date.month - end.month)
    return months_elapsed <= months


# ---------------------------------------------------------------------------
# Private seniority helper
# ---------------------------------------------------------------------------


def _title_to_seniority(title: str) -> int:
    """Map a job title string to a seniority level integer.

    Scans all SENIORITY_MAP keywords as substrings of the lowercased title
    and returns the maximum matching level.  Defaults to 2 (engineer) when
    no keyword matches, since most unrecognised titles are IC individual roles.
    """
    t = title.lower()
    matches = [lvl for kw, lvl in SENIORITY_MAP.items() if kw in t]
    return max(matches) if matches else 2


# ---------------------------------------------------------------------------
# Sub-scorers — all pure functions
# ---------------------------------------------------------------------------


def progression_score(career_history: list) -> float:
    """Score the seniority arc across the career history (0–25 pts).

    Sorts entries chronologically and extracts a seniority level per title,
    then awards points based on the direction and consistency of the arc.

    Rules
    -----
    - Steady upward IC arc (last level > first, ≥ 50 % of moves are up) → 25
    - Lateral (last == first) or mildly upward → 15
    - IC → manager → IC detour → 10 (shows management exposure but not pure IC)
    - Declining or chaotic → 5
    - Single role: scaled by its absolute level (0–20)
    - Empty history → 0

    Args:
        career_history: List of CareerEntry objects.

    Returns:
        Float in [0, 25].
    """
    if not career_history:
        return 0.0

    sorted_history = sorted(
        career_history,
        key=lambda e: getattr(e, "start_date", "") or "",
    )
    levels = [_title_to_seniority(e.title) for e in sorted_history]

    if len(levels) == 1:
        lvl = levels[0]
        if lvl >= 4:
            return 20.0
        if lvl >= 3:
            return 15.0
        if lvl >= 2:
            return 10.0
        return 5.0

    first, last = levels[0], levels[-1]
    n_moves = len(levels) - 1
    upward = sum(1 for a, b in zip(levels, levels[1:]) if b > a)
    upward_ratio = upward / n_moves

    # Detect management detour: any IC → manager → IC pattern
    mgmt_positions = [i for i, lvl in enumerate(levels) if lvl == 5]
    has_mgmt_detour = any(
        i < len(levels) - 1 and levels[i + 1] < 5 for i in mgmt_positions
    )

    if last > first and upward_ratio >= 0.5 and not has_mgmt_detour:
        return 25.0
    if has_mgmt_detour:
        return 10.0
    if last >= first:
        return 15.0
    return 5.0


def company_type_score(career_history: list) -> float:
    """Score based on the proportion of time spent at product companies (0–25 pts).

    Outsourcing firms (TCS, Infosys, Wipro, …) are identified by matching the
    lowercased company name against OUTSOURCING_FIRMS.  All other employers are
    treated as product / tech companies.

    Tiers
    -----
    ≥ 60 % product experience → 25 pts
    30–60 %                   → 15 pts
    < 30 % (mostly services)  → 5 pts

    Args:
        career_history: List of CareerEntry objects.

    Returns:
        Float in {5.0, 15.0, 25.0}.
    """
    total_months = sum(getattr(e, "duration_months", 0) for e in career_history)
    if total_months == 0:
        return 15.0  # neutral — no duration data

    product_months = sum(
        getattr(e, "duration_months", 0)
        for e in career_history
        if getattr(e, "company", "").lower().strip() not in OUTSOURCING_FIRMS
    )
    ratio = product_months / total_months

    if ratio >= 0.6:
        return 25.0
    if ratio >= 0.3:
        return 15.0
    return 5.0


def domain_convergence_score(career_history: list) -> float:
    """Score the depth of AI/ML vocabulary across career descriptions (0–30 pts).

    Checks each tier of DOMAIN_KEYWORDS against the lowercased concatenation of
    all career descriptions.  Keywords found in *recent* roles (within the last
    24 months of the career's effective end date) receive a 2× weight, rewarding
    candidates whose AI/ML exposure is current rather than historical.

    Algorithm
    ---------
    For each keyword in each tier:
      base_pts = tier_weight  (4.0 / 2.5 / 0.5 for tier 1 / 2 / 3)
      if keyword appears in recent descriptions → pts = base_pts × 2.0
      else if keyword appears in any description → pts = base_pts
    Sum all pts, clamp to [0, 30].

    Args:
        career_history: List of CareerEntry objects.

    Returns:
        Float in [0, 30].
    """
    if not career_history:
        return 0.0

    all_text = " ".join(getattr(e, "description", "").lower() for e in career_history)
    if not all_text.strip():
        return 0.0

    ref_date = _career_reference_date(career_history)
    recent_text = " ".join(
        getattr(e, "description", "").lower()
        for e in career_history
        if _is_recent(e, ref_date)
    )

    score = 0.0
    for tier_name, keywords in DOMAIN_KEYWORDS.items():
        weight = _TIER_WEIGHTS[tier_name]
        for kw in keywords:
            if kw in all_text:
                pts = weight * (_RECENCY_MULTIPLIER if kw in recent_text else 1.0)
                score += pts

    return min(score, 30.0)


def tenure_stability_score(career_history: list) -> float:
    """Penalise serial job-hopping by scoring tenure stability (0–10 pts).

    Short stint = any role with duration_months < 12.

    Tiers
    -----
    > 50 % of roles under 12 months → 3 pts
    25–50 %                          → 7 pts
    ≤ 25 %                           → 10 pts
    Fewer than 2 roles               → 10 pts (insufficient data to judge)

    Args:
        career_history: List of CareerEntry objects.

    Returns:
        Float in {3.0, 7.0, 10.0}.
    """
    if len(career_history) < 2:
        return 10.0

    short_stints = sum(
        1 for e in career_history if getattr(e, "duration_months", 12) < 12
    )
    ratio = short_stints / len(career_history)

    if ratio > 0.5:
        return 3.0
    if ratio > 0.25:
        return 7.0
    return 10.0


def industry_relevance_score(career_history: list) -> float:
    """Score the proportion of career spent in tech-relevant industries (0–10 pts).

    Checks each entry's ``industry`` field against HIGH_RELEVANCE_INDUSTRIES using
    case-insensitive substring matching so that "AI/ML", "E-Commerce Fintech", etc.
    are captured correctly.

    Tiers
    -----
    ≥ 60 % of career months in relevant industries → 10 pts
    30–60 %                                        → 6 pts
    < 30 %                                         → 2 pts

    Args:
        career_history: List of CareerEntry objects.

    Returns:
        Float in {2.0, 6.0, 10.0}.
    """
    total_months = sum(getattr(e, "duration_months", 0) for e in career_history)
    if total_months == 0:
        return 6.0  # neutral

    relevant_months = sum(
        getattr(e, "duration_months", 0)
        for e in career_history
        if any(
            kw in getattr(e, "industry", "").lower() for kw in HIGH_RELEVANCE_INDUSTRIES
        )
    )
    ratio = relevant_months / total_months

    if ratio >= 0.6:
        return 10.0
    if ratio >= 0.3:
        return 6.0
    return 2.0


# ---------------------------------------------------------------------------
# Trajectory labeler
# ---------------------------------------------------------------------------


def label_trajectory(scores: CareerTrajectoryScore) -> str:
    """Classify the career trajectory into a human-readable label.

    Labels
    ------
    "ascending"  — strong upward IC arc AND deep domain convergence
    "lateral"    — domain deepening even if title progression is flat
    "declining"  — weak seniority growth AND thin domain signal
    "pivot"      — active career changer; needs human review

    Args:
        scores: A ``CareerTrajectoryScore`` (trajectory_label field is ignored).

    Returns:
        One of "ascending", "lateral", "declining", "pivot".
    """
    if scores.seniority_progression >= 20 and scores.domain_convergence >= 20:
        return "ascending"
    if scores.domain_convergence >= 15 and scores.seniority_progression >= 10:
        return "lateral"
    if scores.seniority_progression < 10 or scores.domain_convergence < 8:
        return "declining"
    return "pivot"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def analyze_career(candidate: Any, jd: Any) -> CareerTrajectoryScore:
    """Score a candidate's career trajectory against the JD.

    Computes all five sub-scores, derives the composite total, and assigns a
    trajectory label.  All computation is pure and runs in O(k × |keywords|)
    where k is the number of career entries — well under the 2-second budget
    for 5 K candidates.

    The ``jd`` argument is used here as context (seniority_level, required_skills)
    and is available for downstream enhancement; the core scoring uses fixed
    keyword lists independent of the JD.

    Args:
        candidate: A ``CandidateRecord`` (or any object with a ``career_history``
                   list and a ``candidate_id`` attribute).
        jd:        A ``ParsedJD`` (used for context; not required for basic scoring).

    Returns:
        A fully populated ``CareerTrajectoryScore``.
    """
    history = candidate.career_history

    s_prog = progression_score(history)
    s_comp = company_type_score(history)
    s_domain = domain_convergence_score(history)
    s_tenure = tenure_stability_score(history)
    s_industry = industry_relevance_score(history)

    total = min(100.0, max(0.0, s_prog + s_comp + s_domain + s_tenure + s_industry))

    scores = CareerTrajectoryScore(
        candidate_id=candidate.candidate_id,
        seniority_progression=s_prog,
        company_type=s_comp,
        domain_convergence=s_domain,
        tenure_stability=s_tenure,
        industry_relevance=s_industry,
        total=total,
        trajectory_label="",  # populated next
    )
    scores.trajectory_label = label_trajectory(scores)
    return scores


# ---------------------------------------------------------------------------
# Backward-compat class wrapper
# ---------------------------------------------------------------------------


class CareerAnalyzer:
    """Thin class wrapper around the module-level ``analyze_career`` function.

    Kept for backward compatibility with code that instantiates a
    ``CareerAnalyzer`` object.  Prefer calling ``analyze_career()`` directly.
    """

    def analyze(self, candidate: Any, jd: Any) -> CareerTrajectoryScore:
        """Return a :class:`CareerTrajectoryScore` for *candidate* against *jd*.

        Args:
            candidate: A ``CandidateRecord``.
            jd:        A ``ParsedJD``.

        Returns:
            :class:`CareerTrajectoryScore`.
        """
        return analyze_career(candidate, jd)
