"""Per-candidate reasoning string generator for the submission CSV.

Produces concise, evidence-based explanations of why each candidate ranked
where they did. Assembled from structured profile data — no network calls,
no LLM at ranking time. Suitable for the no-network constraint of rank.py.

Each reasoning string is composed of up to 5 clauses joined by `; `:
    [experience]; [role/company]; [skills]; [behavioral]; [flags]
Truncated to <= 300 characters at the last semicolon boundary.

An optional rich-reasoning batch (Gemini-powered, offline pre-compute) is
provided for the top-N candidates and cached to disk; cached rich reasoning
is used at ranking time when available, otherwise the template path runs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from backend.app.core.skill_matcher import skill_trust_score

if TYPE_CHECKING:
    from backend.app.core.candidate_loader import CandidateRecord, SkillEntry
    from backend.app.core.career_analyzer import CareerTrajectoryScore
    from backend.app.core.honeypot_detector import HoneypotResult
    from backend.app.core.jd_parser import ParsedJD
    from backend.app.core.ranking_engine import RankedCandidate
    from backend.app.core.rule_scorer import RuleScore
    from backend.app.core.signal_scorer import BehavioralScore
    from backend.app.core.skill_matcher import SkillsMatchScore

logger = logging.getLogger(__name__)


MAX_REASONING_CHARS: int = 300
TOP_SKILLS_TO_SHOW: int = 3
MAX_FLAGS_TO_SHOW: int = 2


def build_experience_clause(candidate: "CandidateRecord") -> str:
    yoe = candidate.profile.years_of_experience
    return f"{yoe:.1f} yrs exp"


def build_role_clause(
    candidate: "CandidateRecord",
    career: "CareerTrajectoryScore",
) -> str:
    title = candidate.profile.current_title
    company = candidate.profile.current_company
    label = career.trajectory_label or "stable"
    return f"current {title} at {company} ({label} trajectory)"


def _skill_jd_match(skill_name: str, jd_required: list[str]) -> bool:
    """Same fuzzy match logic as compute_skills_match: direct / substring / shared first word."""
    s = skill_name.lower()
    s_first = s.split()[0] if s.split() else ""
    s_tokens = set(s.split())
    for jd_skill in jd_required:
        j = jd_skill.lower()
        if not j:
            continue
        j_tokens = set(j.split())
        j_first = j.split()[0] if j.split() else ""
        if (s == j or s in j or j in s
                or s_tokens <= j_tokens or j_tokens <= s_tokens
                or (s_first == j_first and len(s_first) > 3)):
            return True
    return False


def _format_skill(skill: "SkillEntry") -> str:
    """Format one skill with the strongest secondary signal (endorsements or duration)."""
    base = f"{skill.name} ({skill.proficiency}"
    if skill.endorsements >= 20:
        return f"{base}, {skill.endorsements} endorsements)"
    dur = skill.duration_months or 0
    if dur >= 12:
        return f"{base}, {dur}mo)"
    if skill.endorsements > 0:
        return f"{base}, {skill.endorsements} endorsements)"
    return f"{base})"


def build_skills_clause(
    candidate: "CandidateRecord",
    jd: "ParsedJD | None" = None,
) -> str:
    """Pick top skills by trust score and format them.

    When *jd* is provided, restrict to skills matching the JD's required list
    via the same fuzzy match rules used by `compute_skills_match`. When no
    JD-matching skills exist (or *jd* is None), fall back to the top skills
    overall by trust score so the clause is never empty.
    """
    if not candidate.skills:
        return "no skills listed"

    assessment_scores = candidate.redrob_signals.skill_assessment_scores
    pool = list(candidate.skills)

    if jd is not None and jd.required_skills:
        matched = [s for s in pool if _skill_jd_match(s.name, jd.required_skills)]
        if matched:
            pool = matched

    ranked_skills = sorted(
        pool,
        key=lambda s: skill_trust_score(s, assessment_scores),
        reverse=True,
    )[:TOP_SKILLS_TO_SHOW]

    return ", ".join(_format_skill(s) for s in ranked_skills)


def build_behavioral_clause(
    candidate: "CandidateRecord",
    behavioral: "BehavioralScore",
) -> str:
    """Surface the most impactful positive signals. Falls back to a generic
    description when no strong positive signal is present.
    """
    sig = candidate.redrob_signals
    parts: list[str] = []

    if sig.open_to_work_flag:
        parts.append("open to work")
    if sig.recruiter_response_rate >= 0.7:
        parts.append(f"responds {sig.avg_response_time_hours:.0f}h avg")
    if sig.github_activity_score > 50:
        parts.append(f"GitHub {sig.github_activity_score:.0f}")
    if sig.interview_completion_rate >= 0.85:
        parts.append(f"interview completion {sig.interview_completion_rate:.0%}")
    if sig.verified_email and sig.verified_phone:
        parts.append("verified profile")

    if parts:
        return ", ".join(parts)
    return "moderate platform engagement"


def build_flag_clause(honeypot: "HoneypotResult") -> str:
    if not honeypot.flags:
        return ""
    shown = honeypot.flags[:MAX_FLAGS_TO_SHOW]
    return "⚠ flags: " + "; ".join(shown)


def truncate_reasoning(text: str, max_chars: int = MAX_REASONING_CHARS) -> str:
    """Clip at the last `; ` boundary before max_chars; append `…` if truncated."""
    if len(text) <= max_chars:
        return text
    cut = text.rfind("; ", 0, max_chars - 1)
    if cut == -1:
        return text[: max_chars - 1] + "…"
    return text[:cut] + "…"


def generate_reasoning(
    candidate: "CandidateRecord",
    rule: "RuleScore",
    embedding_sim: float,
    skills: "SkillsMatchScore",
    career: "CareerTrajectoryScore",
    behavioral: "BehavioralScore",
    honeypot: "HoneypotResult",
    final_score: float,
    jd: "ParsedJD | None" = None,
) -> str:
    """Build a 5-clause evidence-based reasoning string for one candidate.

    Pure string-ops; no I/O, no network. Output is always non-empty and at
    most 300 characters (clipped at the nearest `; ` boundary).
    """
    clauses = [
        build_experience_clause(candidate),
        build_role_clause(candidate, career),
        build_skills_clause(candidate, jd=jd),
        build_behavioral_clause(candidate, behavioral),
    ]
    flag = build_flag_clause(honeypot)
    if flag:
        clauses.append(flag)
    elif honeypot.penalty_multiplier == 1.0:
        clauses.append("no flags")

    return truncate_reasoning("; ".join(clauses))


def generate_rich_reasoning_batch(
    top_candidates: list["RankedCandidate"],
    jd: "ParsedJD",
    gemini_service: Any | None = None,
    cache_path: str | Path = "precomputed/rich_reasoning.json",
) -> dict[str, str]:
    """Pre-compute richer reasoning via Gemini for the top-N candidates.

    Intended to run offline (e.g. in a setup script) BEFORE rank.py executes,
    since the ranking sandbox has no network access. Results are persisted to
    *cache_path* and loaded by `load_cached_rich_reasoning` at ranking time.

    Falls back to template-based reasoning when *gemini_service* is None or
    a call fails for an individual candidate.
    """
    out: dict[str, str] = {}
    for rc in top_candidates:
        template = generate_reasoning(
            rc.candidate, rc.rule_score, rc.embedding_similarity,
            rc.skills_score, rc.career_score, rc.behavioral_score,
            rc.honeypot_result, rc.final_score, jd=jd,
        )
        if gemini_service is None:
            out[rc.candidate.candidate_id] = template
            continue
        try:
            rich = _call_gemini_for_reasoning(rc, jd, template, gemini_service)
            out[rc.candidate.candidate_id] = rich or template
        except Exception as exc:  # noqa: BLE001 — best-effort, fall back to template
            logger.warning("Gemini reasoning failed for %s: %s", rc.candidate.candidate_id, exc)
            out[rc.candidate.candidate_id] = template

    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def load_cached_rich_reasoning(cache_path: str | Path) -> dict[str, str]:
    """Load the cache produced by `generate_rich_reasoning_batch`; empty dict if missing."""
    path = Path(cache_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load rich reasoning cache from %s: %s", path, exc)
        return {}


def _call_gemini_for_reasoning(
    rc: "RankedCandidate",
    jd: "ParsedJD",
    template_fallback: str,
    gemini_service: Any,
) -> str:
    """Build a structured prompt and ask Gemini for one richer reasoning line.

    The gemini_service is duck-typed: any object exposing a `generate(prompt: str) -> str`
    method works. The orchestrator owns the actual Gemini client; this module
    stays decoupled and easy to test with a fake.
    """
    prompt = (
        "You are evaluating a candidate against a job description. Write a single "
        "sentence (<=280 characters) explaining why this candidate matches or "
        "does not match the role. Reference specific evidence from their profile. "
        "Do NOT invent facts.\n\n"
        f"Job description: {jd.role_title} — required skills: "
        f"{', '.join(jd.required_skills[:8])}\n\n"
        f"Candidate: {rc.candidate.profile.current_title} at "
        f"{rc.candidate.profile.current_company}, "
        f"{rc.candidate.profile.years_of_experience:.1f} yrs exp.\n"
        f"Career trajectory: {rc.career_score.trajectory_label}.\n"
        f"Top skills: {', '.join(s.name for s in rc.candidate.skills[:5])}.\n"
        f"Template summary (for reference): {template_fallback}\n\n"
        "Output: one sentence only, no markdown, no quotes."
    )
    raw = gemini_service.generate(prompt)
    if not raw or not raw.strip():
        return template_fallback
    cleaned = raw.strip().strip('"').strip("'").replace("\n", " ")
    return truncate_reasoning(cleaned, max_chars=MAX_REASONING_CHARS)
