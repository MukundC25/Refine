from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class JobDescriptionInput(BaseModel):
    job_description: str = Field(..., description="The job description text.")

class ResumeInput(BaseModel):
    job_description: str = Field(..., description="The job description text.")
    resume_latex_code: str = Field(..., description="The resume as LaTeX code.")

class RefinementInput(BaseModel):
    job_description: str = Field(..., description="The job description text.")
    original_resume_latex_code: str = Field(..., description="The original resume as LaTeX code.")
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


# ── Ranking system schemas (Issue 001) ───────────────────────────────────── #

class CandidateRankSchema(BaseModel):
    """Ranked candidate entry returned by the /rank endpoint."""

    candidate_id: str = Field(..., description="Unique identifier for the candidate.")
    rank: int = Field(..., ge=1, description="Final rank position (1 = best).")
    score: float = Field(..., ge=0.0, le=1.0, description="Normalised composite score [0, 1].")
    shortlisted: bool = Field(..., description="Whether the candidate is in the top-K shortlist.")
    score_breakdown: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Per-signal score breakdown (skill, embedding, career, signal).",
    )


class RankingRequest(BaseModel):
    """Request body for POST /rank."""

    job_description: str = Field(..., description="Raw job description text.")
    top_k: int = Field(default=100, ge=1, le=10_000, description="Number of candidates to shortlist.")


class RankingResponse(BaseModel):
    """Response body for POST /rank."""

    total_candidates: int = Field(..., description="Total number of candidates evaluated.")
    shortlisted: int = Field(..., description="Number of candidates in the shortlist.")
    results: list[CandidateRankSchema]
