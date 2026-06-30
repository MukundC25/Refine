import React from 'react';
import { RankedCandidate } from '../../lib/types';
import { ScoreBadge } from './ScoreBadge';
import { ReasoningCell } from './ReasoningCell';

export const CandidateRow: React.FC<{ candidate: RankedCandidate; onClick: () => void }> = ({ candidate, onClick }) => (
  <tr
    className="border-b border-zinc-800 hover:bg-zinc-800/50 cursor-pointer transition-colors"
    onClick={onClick}
  >
    <td className="px-3 py-3 font-mono text-zinc-400 w-10">#{candidate.rank}</td>
    <td className="px-3 py-3">
      <div className="font-medium text-white">{candidate.profile_snapshot.headline}</div>
      <div className="text-xs text-zinc-400">{candidate.candidate_id}</div>
    </td>
    <td className="px-3 py-3 text-zinc-300">
      <div>{candidate.profile_snapshot.current_title}</div>
      <div className="text-xs text-zinc-500">{candidate.profile_snapshot.current_company}</div>
    </td>
    <td className="px-3 py-3 text-center text-zinc-300">
      {candidate.profile_snapshot.years_of_experience.toFixed(1)}
    </td>
    <td className="px-3 py-3">
      <ScoreBadge score={candidate.final_score} />
    </td>
    <td className="px-3 py-3">
      <div className="flex flex-wrap gap-1">
        {candidate.profile_snapshot.top_skills.slice(0, 3).map(s => (
          <span key={s} className="px-1.5 py-0.5 bg-zinc-700 rounded text-xs text-zinc-200">{s}</span>
        ))}
      </div>
    </td>
    <td className="px-3 py-3 max-w-xs">
      <ReasoningCell reasoning={candidate.reasoning} />
    </td>
  </tr>
);
