import React from 'react';
import { EducationEntry } from '../../lib/types';
import { GraduationCap } from 'lucide-react';

const TIER_LABEL: Record<EducationEntry['tier'], string> = {
  tier_1: 'Tier 1',
  tier_2: 'Tier 2',
  tier_3: 'Tier 3',
  tier_4: 'Tier 4',
  unknown: 'Tier ?',
};

const TIER_COLOR: Record<EducationEntry['tier'], string> = {
  tier_1: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/60',
  tier_2: 'bg-violet-900/40 text-violet-300 border-violet-700/60',
  tier_3: 'bg-blue-900/40 text-blue-300 border-blue-700/60',
  tier_4: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  unknown: 'bg-zinc-800 text-zinc-500 border-zinc-700',
};

interface Props {
  education: EducationEntry[];
}

export const EducationList: React.FC<Props> = ({ education }) => {
  if (!education || education.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-500">
        No education records on file.
      </div>
    );
  }

  const sorted = [...education].sort((a, b) => b.end_year - a.end_year);

  return (
    <section aria-labelledby="education-heading">
      <h3 id="education-heading" className="mb-3 text-sm font-semibold text-zinc-300">
        Education
      </h3>
      <ul className="space-y-2">
        {sorted.map((entry, i) => (
          <li
            key={`${entry.institution}-${entry.end_year}-${i}`}
            className="flex gap-3 rounded-lg border border-zinc-800 bg-zinc-900 p-3"
          >
            <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800">
              <GraduationCap size={14} className="text-violet-400" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="font-semibold text-white">{entry.institution}</span>
                <span
                  className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${TIER_COLOR[entry.tier]}`}
                >
                  {TIER_LABEL[entry.tier]}
                </span>
              </div>
              <div className="mt-0.5 text-sm text-zinc-300">
                {entry.degree}
                {entry.field_of_study && (
                  <span className="text-zinc-500"> · {entry.field_of_study}</span>
                )}
              </div>
              <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-zinc-500">
                <span>{entry.start_year} → {entry.end_year}</span>
                {entry.grade && <span>Grade: {entry.grade}</span>}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
};
