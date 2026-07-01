import React from 'react';
import { AlertTriangle, Sparkles } from 'lucide-react';

interface Props {
  reasoning: string;
  flags: string[];
}

export const ReasoningCard: React.FC<Props> = ({ reasoning, flags }) => (
  <section aria-labelledby="reasoning-heading" className="space-y-3">
    <h3 id="reasoning-heading" className="text-sm font-semibold text-zinc-300">
      Why this candidate
    </h3>

    <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 p-4">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-violet-300">
        <Sparkles size={12} />
        Ranking summary
      </div>
      <p className="whitespace-pre-line text-sm leading-relaxed text-zinc-200">
        {reasoning || 'No reasoning available for this candidate.'}
      </p>
    </div>

    {flags && flags.length > 0 && (
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4">
        <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-300">
          <AlertTriangle size={12} />
          Anomaly flags ({flags.length})
        </div>
        <ul className="space-y-1">
          {flags.map((flag, i) => (
            <li key={i} className="text-xs text-amber-200/90">
              · {flag}
            </li>
          ))}
        </ul>
      </div>
    )}
  </section>
);
