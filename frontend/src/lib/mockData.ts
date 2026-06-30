import { RankingResult } from './types';

// Dummy data for visual layout and fallback when backend is unavailable
export const dummyResult: RankingResult = {
  run_id: "run_fallback_123",
  status: "completed",
  elapsed_seconds: 4.2,
  total_candidates_processed: 100,
  honeypots_excluded: 2,
  ranked_candidates: Array.from({ length: 100 }, (_, i) => ({
    rank: i + 1,
    candidate_id: `cand_${(i + 1).toString().padStart(7, '0')}`,
    final_score: Math.max(0, 100 - (i * 0.8)),
    reasoning: "Candidate demonstrates strong matching skills for the role. Their experience aligns well with the requirements, particularly in React and TypeScript.",
    score_breakdown: {
      rule_score: 95,
      embedding_similarity: 88,
      skills_score: 92,
      career_score: 85,
      behavioral_score: 90
    },
    profile_snapshot: {
      headline: ["Senior Frontend Engineer", "Full Stack Developer", "Software Engineer"][i % 3],
      current_title: ["Senior Frontend Engineer", "Full Stack Developer", "Software Engineer"][i % 3],
      current_company: ["Tech Corp", "Startup Inc", "Global Solutions"][i % 3],
      years_of_experience: 3 + (i % 8),
      top_skills: ["React", "TypeScript", "Node.js", "Python", "AWS"].slice(0, 3 + (i % 2))
    }
  }))
};
