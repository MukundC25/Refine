from datetime import date
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class JobDescriptionInput(BaseModel):
    job_description: str = Field(..., description="The job description text.")


class ResumeInput(BaseModel):
    job_description: str = Field(..., description="The job description text.")
    resume_latex_code: str = Field(..., description="The resume as LaTeX code.")


class RefinementInput(BaseModel):
    job_description: str = Field(..., description="The job description text.")
    original_resume_latex_code: str = Field(
        ..., description="The original resume as LaTeX code."
    )
    evaluation: Dict[str, Any] = Field(..., description="The evaluation JSON object.")


class EvaluationOutput(BaseModel):
    experience_match: Dict[str, Any]
    skills_and_techstack_match: Dict[str, Any]
    projects_match: Dict[str, Any]
    education_match: Dict[str, Any]
    profile_match: Dict[str, Any]
    industry_and_domain_match: Dict[str, Any]
    certifications_and_achievements_match: Dict[str, Any]
    overall_match: Dict[str, Any]


class RefinedResumeOutput(BaseModel):
    refined_latex_code: str
    overall_improvements_summary: Optional[str] = None


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    resume_latex: Optional[str] = None


class UserLogin(UserBase):
    password: str


class User(UserBase):
    id: int
    full_name: Optional[str] = None
    is_active: bool
    is_google_user: bool
    is_admin: bool = False
    is_pro: bool = False
    picture: Optional[str] = None
    resume_latex: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class GoogleLogin(BaseModel):
    token: str


class RuleScoreSchema(BaseModel):
    candidate_id: str
    experience_score: float = Field(..., ge=0.0, le=30.0)
    title_score: float = Field(..., ge=0.0, le=20.0)
    skills_score: float = Field(..., ge=0.0, le=25.0)
    industry_score: float = Field(..., ge=0.0, le=15.0)
    disqualifier_penalty: float
    total: float = Field(..., ge=0.0)


class ScoreBreakdown(BaseModel):
    rule_score: float
    embedding_similarity: float
    skills_score: float
    career_score: float
    behavioral_score: float


class ProfileSnapshot(BaseModel):
    headline: str
    current_title: str
    current_company: str
    years_of_experience: float
    top_skills: list[str]


class RankedCandidateResponse(BaseModel):
    rank: int
    candidate_id: str
    final_score: float
    reasoning: str
    score_breakdown: ScoreBreakdown
    profile_snapshot: ProfileSnapshot


class RankingResponse(BaseModel):
    run_id: str
    status: str
    elapsed_seconds: float
    total_candidates_processed: int
    honeypots_excluded: int
    ranked_candidates: list[RankedCandidateResponse]


class RankingStatusResponse(BaseModel):
    run_id: str
    status: str
    stage: str
    progress_pct: float
    elapsed_seconds: float
    message: str


class ReRankRequest(BaseModel):
    job_description: Optional[str] = None
    weight_overrides: Optional[Dict[str, float]] = None


# ---------------------------------------------------------------------------
# Candidate-dataset models (Issue 003)
# Single source of truth for the ranking pipeline — Issues 003–013.
# ---------------------------------------------------------------------------

#: Company-size buckets from candidate_schema.json — shared by ProfileBlock
#: and CareerEntry.
_CompanySize = Literal[
    "1-10",
    "11-50",
    "51-200",
    "201-500",
    "501-1000",
    "1001-5000",
    "5001-10000",
    "10001+",
]


class ProfileBlock(BaseModel):
    """Top-level profile snapshot — mirrors the ``profile`` block in candidate_schema.json."""

    anonymized_name: str
    headline: str
    summary: str
    location: str
    country: str
    years_of_experience: float = Field(ge=0, le=50)
    current_title: str
    current_company: str
    current_company_size: _CompanySize
    current_industry: str


class CareerEntry(BaseModel):
    """One employment entry in a candidate's career history."""

    company: str
    title: str
    start_date: date
    end_date: date | None
    duration_months: int = Field(ge=0)
    is_current: bool
    industry: str
    company_size: _CompanySize
    description: str


class EducationEntry(BaseModel):
    """One education entry."""

    institution: str
    degree: str
    field_of_study: str
    start_year: int = Field(ge=1970, le=2030)
    end_year: int = Field(ge=1970, le=2035)
    grade: str | None = None
    tier: Literal["tier_1", "tier_2", "tier_3", "tier_4", "unknown"] = "unknown"


class SkillEntry(BaseModel):
    """A single skill with proficiency, endorsement count, and usage duration."""

    name: str
    proficiency: Literal["beginner", "intermediate", "advanced", "expert"]
    endorsements: int = Field(ge=0)
    duration_months: int = Field(ge=0, default=0)


class CertEntry(BaseModel):
    """A professional certification."""

    name: str
    issuer: str
    year: int


class LanguageEntry(BaseModel):
    """A spoken/written language and the candidate's proficiency level."""

    language: str
    proficiency: Literal["basic", "conversational", "professional", "native"]


class RedrobSignals(BaseModel):
    """Verified, behavioural, and platform-derived data from the Redrob ecosystem.

    Two fields use a ``-1`` sentinel to mean "not available":

    * ``github_activity_score = -1``  — no GitHub account linked
    * ``offer_acceptance_rate = -1``  — no offer history on record

    These must not be treated as zero in downstream scoring.
    """

    profile_completeness_score: float = Field(ge=0, le=100)
    signup_date: date
    last_active_date: date
    open_to_work_flag: bool
    profile_views_received_30d: int = Field(ge=0)
    applications_submitted_30d: int = Field(ge=0)
    recruiter_response_rate: float = Field(ge=0, le=1)
    avg_response_time_hours: float = Field(ge=0)
    skill_assessment_scores: Dict[str, float] = Field(default_factory=dict)
    connection_count: int = Field(ge=0)
    endorsements_received: int = Field(ge=0)
    notice_period_days: int = Field(ge=0, le=180)
    expected_salary_range_inr_lpa: Dict[str, float]
    preferred_work_mode: Literal["remote", "hybrid", "onsite", "flexible"]
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
    """Top-level candidate profile — directly mirrors candidate_schema.json.

    This is the canonical Pydantic model for the ranking pipeline
    (Issues 003–013). Every pipeline component that needs a type-safe
    representation of a candidate should import and use this class.
    """

    candidate_id: str = Field(pattern=r"^CAND_[0-9]{7}$")
    profile: ProfileBlock
    career_history: list[CareerEntry] = Field(min_length=1, max_length=10)
    education: list[EducationEntry] = Field(default_factory=list, max_length=5)
    skills: list[SkillEntry] = Field(default_factory=list)
    certifications: list[CertEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    redrob_signals: RedrobSignals


# ---------------------------------------------------------------------------
# Parsed JD (output of Issue 002)
# ---------------------------------------------------------------------------


class ParsedJD(BaseModel):
    """Structured representation of a parsed job description.

    ``embedding`` is ``None`` until the embedding service (Issue 006) processes
    the JD — it is then a 384-dimensional float list.
    """

    full_text: str
    role_title: str
    required_skills: list[str]
    preferred_skills: list[str]
    min_years_experience: int
    max_years_experience: int
    seniority_level: str
    domains: list[str]
    disqualifiers: list[str]
    embedding: list[float] | None = None


# ---------------------------------------------------------------------------
# Scoring result types (Issues 006–011)
# ---------------------------------------------------------------------------


class RuleScore(BaseModel):
    """Structured output of the rule-based pre-scorer (Issue 007)."""

    candidate_id: str
    experience_score: float
    title_score: float
    skills_score: float
    industry_score: float
    disqualifier_penalty: float
    total: float


class HoneypotResult(BaseModel):
    """Result of the honeypot / fake-profile detector (Issue 008).

    ``penalty_multiplier`` of 0 means the candidate is excluded from ranking;
    1.0 means no penalty applied.
    """

    is_suspicious: bool
    confidence: float = Field(ge=0, le=1)
    flags: list[str]
    penalty_multiplier: float = Field(ge=0, le=1)
