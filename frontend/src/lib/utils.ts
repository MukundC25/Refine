import { ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility function to merge Tailwind classes
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// Real API call to backend for evaluation
export async function evaluateResume(resumeLatexCode: string, jobDescription: string) {
  const formData = new FormData();
  formData.append("job_description", jobDescription);
  formData.append("resume_latex_code", resumeLatexCode);

  const response = await fetch(`${API_BASE}/evaluate`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error("Failed to evaluate resume");
  }
  const backendResult = await response.json();
  return mapEvaluationOutputToResult(backendResult);
}

// Map backend EvaluationOutput to frontend EvaluationResult
export function mapEvaluationOutputToResult(backend: any): import("./types").EvaluationResult {
  // Map each section to a ScoreCategory
  const categories = [
    {
      name: "Experience",
      score: backend.experience_match?.score ?? 0,
      feedback: backend.experience_match?.reasoning ?? "",
    },
    {
      name: "Skills/Techstack",
      score: backend.skills_and_techstack_match?.score ?? 0,
      feedback: backend.skills_and_techstack_match?.reasoning ?? "",
    },
    {
      name: "Projects",
      score: backend.projects_match?.score ?? 0,
      feedback: backend.projects_match?.reasoning ?? "",
    },
    {
      name: "Education",
      score: backend.education_match?.score ?? 0,
      feedback: backend.education_match?.reasoning ?? "",
    },
    {
      name: "Profile",
      score: backend.profile_match?.score ?? 0,
      feedback: backend.profile_match?.reasoning ?? "",
    },
    {
      name: "Industry/Domain",
      score: backend.industry_and_domain_match?.score ?? 0,
      feedback: backend.industry_and_domain_match?.reasoning ?? "",
    },
    {
      name: "Certifications/Achievements",
      score: backend.certifications_and_achievements_match?.score ?? 0,
      feedback: backend.certifications_and_achievements_match?.reasoning ?? "",
    },
  ];

  const overall = backend.overall_match || {};
  return {
    overallScore: overall.score ?? 0,
    categories,
    pros: overall.pros ? (typeof overall.pros === "string" ? [overall.pros] : overall.pros) : [],
    cons: overall.cons ? (typeof overall.cons === "string" ? [overall.cons] : overall.cons) : [],
    fitDecision: overall.fit?.decision
      ? (overall.fit.decision === true
          ? "good"
          : overall.fit.decision === false
          ? "poor"
          : "moderate")
      : "moderate",
    summary: overall.reasoning ?? "",
  };
}

// Real API call to backend for refinement
export async function refineResume(resumeText: string, jobDescription: string, evaluationResult: any) {
  const response = await fetch(`${API_BASE}/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      job_description: jobDescription,
      original_resume_latex_code: resumeText,
      evaluation: evaluationResult,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to refine resume");
  }
  const backendResult = await response.json();
  // Map snake_case to camelCase for frontend
  return {
    refinedLatexCode: backendResult.refined_latex_code || "",
    overallImprovementsSummary: backendResult.overall_improvements_summary || "",
  };
}

// Format the score as a percentage
export function formatScore(score: number): string {
  return `${Math.round(score)}%`;
}

// Get the color class based on score
export function getScoreColorClass(score: number): string {
  if (score >= 80) return 'text-success-600';
  if (score >= 60) return 'text-warning-500';
  return 'text-error-600';
}

// Get the background color class based on score
export function getScoreBgClass(score: number): string {
  if (score >= 80) return 'bg-success-100';
  if (score >= 60) return 'bg-warning-100';
  return 'bg-error-100';
}

// Convert fit decision to a more user-friendly string
export function formatFitDecision(decision: string): string {
  switch (decision) {
    case 'poor': return 'Poor Fit';
    case 'moderate': return 'Moderate Fit';
    case 'good': return 'Good Fit';
    case 'excellent': return 'Excellent Fit';
    default: return 'Unknown';
  }
}

// Get color for fit decision
export function getFitDecisionColor(decision: string): string {
  switch (decision) {
    case 'poor': return 'text-error-600';
    case 'moderate': return 'text-warning-500';
    case 'good': return 'text-primary-600';
    case 'excellent': return 'text-success-600';
    default: return 'text-gray-600';
  }
}

// Create a blob URL for a string (for text download)
export function createTextFileUrl(text: string): string {
  const blob = new Blob([text], { type: 'text/plain' });
  return URL.createObjectURL(blob);
}
