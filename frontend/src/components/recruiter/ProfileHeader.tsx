import React from 'react';
import { X, MapPin } from 'lucide-react';
import { CandidateRecord } from '../../lib/types';
import { ScoreBadge } from './ScoreBadge';

interface Props {
  candidate: CandidateRecord;
  rank: number;
  finalScore: number;
  onClose: () => void;
}

export const ProfileHeader: React.FC<Props> = ({ candidate, rank, finalScore, onClose }) => {
  const p = candidate.profile;
  return (
    <header className="sticky top-0 z-10 border-b border-zinc-800 bg-zinc-900/95 px-6 pb-5 pt-5 backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs text-zinc-400">
            <span className="rounded-full bg-violet-500/15 px-2 py-0.5 font-mono font-semibold text-violet-300">
              #{rank}
            </span>
            <span className="font-mono">{candidate.candidate_id}</span>
          </div>

          <h2 className="mt-2 truncate text-xl font-semibold text-white">
            {p.headline || p.anonymized_name}
          </h2>

          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-zinc-300">
            <span className="font-medium">{p.current_title}</span>
            <span className="text-zinc-500">@</span>
            <span>{p.current_company}</span>
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[11px] text-zinc-400">
              {p.current_company_size}
            </span>
          </div>

          <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-zinc-500">
            <span className="rounded-full bg-zinc-800 px-2 py-0.5">
              {p.years_of_experience.toFixed(1)} yrs exp
            </span>
            {(p.location || p.country) && (
              <span className="inline-flex items-center gap-1">
                <MapPin size={11} />
                {[p.location, p.country].filter(Boolean).join(', ')}
              </span>
            )}
            <span>{p.current_industry}</span>
          </div>
        </div>

        <div className="flex flex-col items-end gap-2">
          <button
            type="button"
            onClick={onClose}
            aria-label="Close candidate detail"
            className="rounded-full p-1.5 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-white"
          >
            <X size={18} />
          </button>
          <div className="flex flex-col items-end">
            <span className="text-[10px] uppercase tracking-wider text-zinc-500">Score</span>
            <ScoreBadge score={finalScore} />
          </div>
        </div>
      </div>

      {p.summary && (
        <p className="mt-3 text-sm leading-relaxed text-zinc-400 line-clamp-3">
          {p.summary}
        </p>
      )}
    </header>
  );
};
