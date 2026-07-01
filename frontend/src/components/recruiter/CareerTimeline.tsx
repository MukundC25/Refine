import React, { useState } from 'react';
import { CareerEntry } from '../../lib/types';
import { Briefcase, ChevronDown, ChevronUp } from 'lucide-react';

function formatMonths(months: number): string {
  if (months < 12) return `${months} mo`;
  const years = Math.floor(months / 12);
  const rem = months % 12;
  return rem === 0 ? `${years}y` : `${years}y ${rem}m`;
}

function formatDateRange(start: string, end: string | null): string {
  const s = start ? start.slice(0, 7) : '';
  const e = end ? end.slice(0, 7) : 'Present';
  return `${s} → ${e}`;
}

const TimelineEntry: React.FC<{ entry: CareerEntry; isLast: boolean }> = ({ entry, isLast }) => {
  const [expanded, setExpanded] = useState(false);
  const description = entry.description || '';
  const truncated = description.length > 220;
  const shown = expanded || !truncated ? description : description.slice(0, 220) + '…';

  return (
    <li className="relative pl-10 pb-6">
      {!isLast && (
        <span
          aria-hidden
          className="absolute left-[15px] top-8 bottom-0 w-px bg-zinc-700"
        />
      )}
      <span
        aria-hidden
        className="absolute left-0 top-1 flex h-8 w-8 items-center justify-center rounded-full border border-zinc-700 bg-zinc-900"
      >
        <Briefcase size={14} className="text-violet-400" />
      </span>

      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="font-semibold text-white">{entry.title}</span>
        <span className="text-zinc-500">@</span>
        <span className="text-zinc-200">{entry.company}</span>
        {entry.is_current && (
          <span className="ml-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-emerald-300">
            Current
          </span>
        )}
      </div>

      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-zinc-500">
        <span>{formatDateRange(entry.start_date, entry.end_date)}</span>
        <span>·</span>
        <span>{formatMonths(entry.duration_months)}</span>
        <span>·</span>
        <span>{entry.industry}</span>
        <span className="rounded bg-zinc-800 px-1.5 py-0.5">{entry.company_size}</span>
      </div>

      {description && (
        <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-zinc-300">
          {shown}
        </p>
      )}
      {truncated && (
        <button
          type="button"
          onClick={() => setExpanded(v => !v)}
          className="mt-1 inline-flex items-center gap-1 text-xs text-violet-400 hover:text-violet-300"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </li>
  );
};

interface Props {
  history: CareerEntry[];
}

export const CareerTimeline: React.FC<Props> = ({ history }) => {
  if (!history || history.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-500">
        No career history on file.
      </div>
    );
  }

  // Sort most-recent-first: current role first, then by start_date desc.
  const sorted = [...history].sort((a, b) => {
    if (a.is_current !== b.is_current) return a.is_current ? -1 : 1;
    return b.start_date.localeCompare(a.start_date);
  });

  return (
    <section aria-labelledby="career-timeline-heading">
      <h3 id="career-timeline-heading" className="mb-3 text-sm font-semibold text-zinc-300">
        Career History
      </h3>
      <ol className="relative">
        {sorted.map((entry, i) => (
          <TimelineEntry
            key={`${entry.company}-${entry.start_date}-${i}`}
            entry={entry}
            isLast={i === sorted.length - 1}
          />
        ))}
      </ol>
    </section>
  );
};
