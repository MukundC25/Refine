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
