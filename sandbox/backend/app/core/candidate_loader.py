"""
candidate_loader.py — Streaming loader for candidates.jsonl / candidates.jsonl.gz.

Streams 100 K candidate profiles without loading the full file into RAM.
Supports gzip-compressed input transparently, validates every record against
the CandidateRecord schema, and exposes both a one-at-a-time iterator and a
configurable batch iterator for embedding pipelines.

Memory budget
─────────────
  Raw JSON (100 K × ~4.5 KB)       ≈ 450 MB
  Python dict overhead              ≈ 1.5–2 GB  ← averted by streaming
  Pydantic objects (one batch)      ≈ 512 × ~5 KB ≈ 2.5 MB per batch
  Embeddings pre-computed to numpy  ≈ 100 K × 384 × 4 B ≈ 147 MB

Streaming + batching keeps peak RSS well under the 16 GB budget.
"""

from __future__ import annotations

import gzip
import json
import logging
from collections.abc import Iterator
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models — mirror candidate_schema.json exactly
# ---------------------------------------------------------------------------

CompanySize = str  # enum values vary; keep as str for forward-compat


class ProfileBlock(BaseModel):
    anonymized_name: str
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: float = Field(ge=0, le=50)
    current_title: str
    current_company: str
    current_company_size: str
    current_industry: str


class CareerEntry(BaseModel):
    company: str
    title: str
    start_date: str
    end_date: Optional[str] = None
    duration_months: int = Field(ge=0)
    is_current: bool
    industry: str
    company_size: str
    description: str


class EducationEntry(BaseModel):
    institution: str
    degree: str
    field_of_study: str
    start_year: int
    end_year: int
    grade: Optional[str] = None
    tier: Optional[str] = None


class SkillEntry(BaseModel):
    name: str
    proficiency: str  # beginner | intermediate | advanced | expert
    endorsements: int = Field(ge=0)
    duration_months: Optional[int] = Field(default=None, ge=0)


class CertEntry(BaseModel):
    name: str
    issuer: str
    year: int


class LanguageEntry(BaseModel):
    language: str
    proficiency: str  # basic | conversational | professional | native


class SalaryRange(BaseModel):
    min: float = Field(ge=0)
    max: float = Field(ge=0)


class RedrobSignals(BaseModel):
    profile_completeness_score: float = Field(ge=0, le=100)
    signup_date: str
    last_active_date: str
    open_to_work_flag: bool
    profile_views_received_30d: int = Field(ge=0)
    applications_submitted_30d: int = Field(ge=0)
    recruiter_response_rate: float = Field(ge=0, le=1)
    avg_response_time_hours: float = Field(ge=0)
    skill_assessment_scores: dict[str, float] = Field(default_factory=dict)
    connection_count: int = Field(ge=0)
    endorsements_received: int = Field(ge=0)
    notice_period_days: int = Field(ge=0, le=180)
    expected_salary_range_inr_lpa: SalaryRange
    preferred_work_mode: str  # remote | hybrid | onsite | flexible
    willing_to_relocate: bool
    github_activity_score: float = Field(ge=-1, le=100)
    search_appearance_30d: int = Field(ge=0)
    saved_by_recruiters_30d: int = Field(ge=0)
    interview_completion_rate: float = Field(ge=0, le=1)
    offer_acceptance_rate: float = Field(ge=-1, le=1)
    verified_email: bool
    verified_phone: bool
    linkedin_connected: bool


class CandidateRecord(BaseModel):
    candidate_id: str = Field(pattern=r"^CAND_\d{7}$")
    profile: ProfileBlock
    career_history: list[CareerEntry] = Field(min_length=1)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[SkillEntry] = Field(default_factory=list)
    certifications: list[CertEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    redrob_signals: RedrobSignals


# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def validate_candidate(raw: dict) -> Optional[CandidateRecord]:
    """Parse and validate a raw dict into a CandidateRecord.

    Returns None (and logs a warning) if validation fails, so the pipeline
    never hard-crashes on a malformed or honeypot-adjacent record.
    """
    try:
        return CandidateRecord.model_validate(raw)
    except ValidationError as exc:
        cid = raw.get("candidate_id", "<unknown>")
        # Log only the first error to keep noise down on large files.
        first_err = exc.errors()[0]
        logger.warning(
            "Skipping invalid candidate %s — %s at %s",
            cid,
            first_err.get("msg"),
            " -> ".join(str(p) for p in first_err.get("loc", [])),
        )
        return None


# ---------------------------------------------------------------------------
# Streaming iterators
# ---------------------------------------------------------------------------

def stream_candidates(path: str) -> Iterator[CandidateRecord]:
    """Yield one validated CandidateRecord at a time from *path*.

    Supports both plain ``.jsonl`` and gzip-compressed ``.jsonl.gz``.
    Malformed lines are skipped with a warning; the stream never raises.

    Args:
        path: Absolute or relative path to the ``.jsonl`` or ``.jsonl.gz`` file.

    Yields:
        Validated :class:`CandidateRecord` instances.
    """
    opener = gzip.open if path.endswith(".gz") else open

    with opener(path, "rb") as fh:
        for lineno, raw_bytes in enumerate(fh, start=1):
            line = raw_bytes.strip()
            if not line:
                continue  # skip blank lines

            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning("Line %d — JSON decode error: %s", lineno, exc)
                continue

            record = validate_candidate(raw)
            if record is not None:
                yield record


def load_candidates_batched(
    path: str,
    batch_size: int = 512,
) -> Iterator[list[CandidateRecord]]:
    """Yield lists of up to *batch_size* validated records.

    Designed for embedding pipelines that process candidates in fixed-size
    chunks — keeps only one batch in RAM at a time.

    Args:
        path: Path to ``.jsonl`` or ``.jsonl.gz``.
        batch_size: Maximum records per yielded batch (default: 512).

    Yields:
        Non-empty lists of :class:`CandidateRecord`.
    """
    batch: list[CandidateRecord] = []

    for record in stream_candidates(path):
        batch.append(record)
        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch:  # flush the final partial batch
        yield batch


def load_all_candidates(path: str) -> list[CandidateRecord]:
    """Load every candidate into a single list.

    .. warning::
        This materialises all records in RAM simultaneously.  Use only for
        small sample files (≤ 10 K records) or when you have confirmed that
        available RAM is sufficient.  Prefer :func:`stream_candidates` or
        :func:`load_candidates_batched` for the full 100 K dataset.

    Args:
        path: Path to ``.jsonl`` or ``.jsonl.gz``.

    Returns:
        List of all valid :class:`CandidateRecord` objects.
    """
    return list(stream_candidates(path))


# ---------------------------------------------------------------------------
# Text builder for embedding
# ---------------------------------------------------------------------------

def build_candidate_text(c: CandidateRecord) -> str:
    """Assemble a rich, embedding-ready text string for a candidate.

    Combines headline, summary, current role, industry, experience, the three
    most recent career descriptions, advanced/expert skills, and education into
    a single pipe-delimited string.  Quality here directly affects ranking
    accuracy — keep all meaningful fields in the output.

    Args:
        c: A validated :class:`CandidateRecord`.

    Returns:
        Non-empty string suitable for passing to a sentence-transformer or
        other embedding model.
    """
    p = c.profile
    parts: list[str] = [
        p.headline,
        p.summary,
        f"Current role: {p.current_title} at {p.current_company}",
        f"Industry: {p.current_industry}",
        f"Experience: {p.years_of_experience} years",
        f"Location: {p.location}, {p.country}",
    ]

    # Most recent 3 career entries (index 0 = most recent in the data)
    for job in c.career_history[:3]:
        role_str = f"{job.title} at {job.company}: {job.description}"
        parts.append(role_str)

    # Expert / advanced skills with proficiency label
    expert_skills = [
        f"{s.name} ({s.proficiency})"
        for s in c.skills
        if s.proficiency in ("advanced", "expert")
    ]
    if expert_skills:
        parts.append(f"Expert skills: {', '.join(expert_skills)}")

    # All skills (names only) for broader semantic coverage
    all_skill_names = [s.name for s in c.skills]
    if all_skill_names:
        parts.append(f"Skills: {', '.join(all_skill_names)}")

    # Education
    for edu in c.education:
        edu_str = f"{edu.degree} in {edu.field_of_study} from {edu.institution}"
        if edu.tier and edu.tier != "unknown":
            edu_str += f" ({edu.tier})"
        parts.append(edu_str)

    # Certifications
    cert_names = [cert.name for cert in c.certifications]
    if cert_names:
        parts.append(f"Certifications: {', '.join(cert_names)}")

    # Redrob engagement signals as lightweight text hints
    sig = c.redrob_signals
    if sig.open_to_work_flag:
        parts.append("Open to work")
    parts.append(f"Preferred work mode: {sig.preferred_work_mode}")
    if sig.willing_to_relocate:
        parts.append("Willing to relocate")

    return " | ".join(filter(None, parts))
