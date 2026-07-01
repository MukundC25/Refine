// Core types for the application

export type Step = 'upload' | 'preview' | 'evaluation' | 'refinement' | 'download';

export interface ResumeData {
  latexCode: string;
}

export interface ScoreCategory {
  name: string;
  score: number;
  feedback: string;
}

export interface EvaluationResult {
  overallScore: number;
  categories: ScoreCategory[];
  pros: string[];
  cons: string[];
  fitDecision: 'poor' | 'moderate' | 'good' | 'excellent';
  summary: string;
}

export interface SectionImprovement {
  original: string;
  improved: string;
  explanation: string;
}

export interface RefinementResult {
  refinedLatexCode: string;
  overallImprovementsSummary?: string;
}

export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_google_user: boolean;
  picture?: string;
  is_admin?: boolean;
  is_pro?: boolean;
  resume_latex?: string;
}

export interface AppState {
  user: User | null;
  currentStep: Step;
  originalResume: ResumeData | null;
  jobDescription: string;
  evaluationResult: EvaluationResult | null;
  refinementResult: RefinementResult | null;
  refinedEvaluationResult: EvaluationResult | null;
  isLoading: boolean;
  error: string | null;
}

export interface ScoreBreakdown {
  rule_score: number;
  embedding_similarity: number;
  skills_score: number;
  career_score: number;
  behavioral_score: number;
}

export interface ProfileSnapshot {
  headline: string;
  current_title: string;
  current_company: string;
  years_of_experience: number;
  top_skills: string[];
}

export interface RankedCandidate {
  rank: number;
  candidate_id: string;
  final_score: number;
  reasoning: string;
  score_breakdown: ScoreBreakdown;
  profile_snapshot: ProfileSnapshot;
}

export interface RankingResult {
  run_id: string;
  status: string;
  elapsed_seconds: number;
  total_candidates_processed: number;
  honeypots_excluded: number;
  ranked_candidates: RankedCandidate[];
}

export interface CandidateFilters {
  minYoe: number;
  maxYoe: number;
  minScore: number;
  skills: string[];
  workMode: string[];
  maxNoticeDays: number;
  searchQuery: string;
}

// Candidate detail types — mirror the Pydantic schema in candidate_loader.py
// so a payload from GET /api/ranking/candidate/{id} lands cleanly on the FE.

export type Proficiency = 'beginner' | 'intermediate' | 'advanced' | 'expert';
export type LanguageProficiency = 'basic' | 'conversational' | 'professional' | 'native';
export type CompanySize =
  | '1-10' | '11-50' | '51-200' | '201-500'
  | '501-1000' | '1001-5000' | '5001-10000' | '10001+';

export interface SkillEntry {
  name: string;
  proficiency: Proficiency;
  endorsements: number;
  duration_months?: number | null;
}

export interface CareerEntry {
  company: string;
  title: string;
  start_date: string;        // ISO date
  end_date: string | null;
  duration_months: number;
  is_current: boolean;
  industry: string;
  company_size: CompanySize;
  description: string;
}

export interface EducationEntry {
  institution: string;
  degree: string;
  field_of_study: string;
  start_year: number;
  end_year: number;
  grade?: string | null;
  tier: 'tier_1' | 'tier_2' | 'tier_3' | 'tier_4' | 'unknown';
}

export interface CertEntry {
  name: string;
  issuer: string;
  year: number;
}

export interface LanguageEntry {
  language: string;
  proficiency: LanguageProficiency;
}

export interface ProfileBlock {
  anonymized_name: string;
  headline: string;
  summary: string;
  location: string;
  country: string;
  years_of_experience: number;
  current_title: string;
  current_company: string;
  current_company_size: CompanySize;
  current_industry: string;
}

export interface RedrobSignals {
  profile_completeness_score: number;
  signup_date: string;
  last_active_date: string;
  open_to_work_flag: boolean;
  profile_views_received_30d: number;
  applications_submitted_30d: number;
  recruiter_response_rate: number;
  avg_response_time_hours: number;
  skill_assessment_scores: Record<string, number>;
  connection_count: number;
  endorsements_received: number;
  notice_period_days: number;
  expected_salary_range_inr_lpa: { min: number; max: number };
  preferred_work_mode: 'remote' | 'hybrid' | 'onsite' | 'flexible';
  willing_to_relocate: boolean;
  github_activity_score: number;   // -1 = not linked
  search_appearance_30d: number;
  saved_by_recruiters_30d: number;
  interview_completion_rate: number;
  offer_acceptance_rate: number;   // -1 = no history
  verified_email: boolean;
  verified_phone: boolean;
  linkedin_connected: boolean;
}

export interface CandidateRecord {
  candidate_id: string;
  profile: ProfileBlock;
  career_history: CareerEntry[];
  education: EducationEntry[];
  skills: SkillEntry[];
  certifications: CertEntry[];
  languages: LanguageEntry[];
  redrob_signals: RedrobSignals;
}

export interface CandidateDetailResponse {
  candidate: CandidateRecord;
  rank: number;
  final_score: number;
  reasoning: string;
  score_breakdown: ScoreBreakdown;
  honeypot_flags: string[];
}
