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
