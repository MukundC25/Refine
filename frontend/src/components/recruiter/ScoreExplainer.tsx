import React from 'react';
import { ScoreBreakdown } from '../../lib/types';
import { ScoreBadge } from './ScoreBadge';
import { ScoreDimension } from './ScoreDimension';

interface DimensionConfig {
  key: keyof ScoreBreakdown;
  label: string;
  description: string;
  weight: number;
  icon: string;
  transform?: (v: number) => number;
  color: string; // Tailwind bg class used in the stacked bar
}

export const DIMENSION_CONFIG: DimensionConfig[] = [
  {
    key: 'rule_score',
    label: 'Rules Score',
    description: 'Years of experience, title match, skills overlap, industry background',
    weight: 0.20,
    icon: '⚙️',
    color: 'bg-zinc-400',
  },
  {
    key: 'embedding_similarity',
    label: 'Semantic Match',
    description: "How closely the candidate's full profile text aligns with the JD meaning",
    weight: 0.25,
    icon: '🧠',
    transform: (v: number) => v * 100,
    color: 'bg-violet-500',
  },
  {
    key: 'skills_score',
    label: 'Skills Trust',
    description: 'Trust-weighted skills match — endorsed + platform-assessed skills score higher',
    weight: 0.20,
    icon: '🛠',
    color: 'bg-blue-500',
  },
  {
    key: 'career_score',
    label: 'Career Trajectory',
    description: 'Progression toward AI/ML, product company ratio, domain convergence',
    weight: 0.15,
    icon: '📈',
    color: 'bg-emerald-500',
  },
  {
    key: 'behavioral_score',
    label: 'Platform Signals',
    description: 'Responsiveness, interview completion, GitHub activity, offer acceptance',
    weight: 0.20,
    icon: '📊',
    color: 'bg-amber-500',
  },
];

// Internal stacked bar — each segment proportional to (score × weight) / total
const WeightedFormulaBar: React.FC<{
  breakdown: ScoreBreakdown;
  finalScore: number;
}> = ({ breakdown, finalScore }) => {
  const total = finalScore > 0 ? finalScore : 1; // avoid divide-by-zero
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[10px] text-zinc-500">
        <span>Weighted contributions</span>
        <span className="font-mono">= {finalScore.toFixed(1)}</span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-zinc-800">
        {DIMENSION_CONFIG.map(dim => {
          const raw = breakdown[dim.key] ?? 0;
          const display = dim.transform ? dim.transform(raw) : raw;
          const contribution = display * dim.weight;
          const widthPct = (contribution / total) * 100;
          return (
            <div
              key={dim.key}
              className={`h-full transition-all duration-500 ${dim.color}`}
              style={{ width: `${Math.max(widthPct, 0)}%` }}
              title={`${dim.label}: ${contribution.toFixed(1)} pts (${display.toFixed(1)} × ${Math.round(dim.weight * 100)}%)`}
            />
          );
        })}
      </div>
      {/* Legend */}
      <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
        {DIMENSION_CONFIG.map(dim => (
          <span key={dim.key} className="flex items-center gap-1 text-[10px] text-zinc-500">
            <span className={`inline-block h-2 w-2 rounded-full ${dim.color}`} />
            {dim.label}
          </span>
        ))}
      </div>
    </div>
  );
};

interface Props {
  breakdown: ScoreBreakdown;
  reasoning: string;
  finalScore: number;
  honeypotFlags: string[];
}

export const ScoreExplainer: React.FC<Props> = ({
  breakdown,
  reasoning,
  finalScore,
  honeypotFlags,
}) => (
  <section aria-labelledby="score-explainer-heading" className="space-y-4">
    {/* Header */}
    <div className="flex items-center justify-between">
      <h3 id="score-explainer-heading" className="text-sm font-semibold text-zinc-300">
        Score Breakdown
      </h3>
      <div className="flex items-center gap-2">
        <span className="text-xs text-zinc-500">Final Score</span>
        <ScoreBadge score={finalScore} />
      </div>
    </div>

    {/* Stacked formula bar */}
    <WeightedFormulaBar breakdown={breakdown} finalScore={finalScore} />

    {/* Per-dimension rows */}
    <div className="space-y-2">
      {DIMENSION_CONFIG.map(dim => {
        const raw = breakdown[dim.key] ?? 0;
        const display = dim.transform ? dim.transform(raw) : raw;
        const weighted = display * dim.weight;
        return (
          <ScoreDimension
            key={dim.key}
            icon={dim.icon}
            label={dim.label}
            description={dim.description}
            score={display}
            weight={dim.weight}
            weightedContribution={weighted}
          />
        );
      })}
    </div>

    {/* Reasoning */}
    <div className="rounded-lg bg-zinc-800 p-4">
      <h4 className="mb-2 text-xs font-semibold text-zinc-400">AI Reasoning</h4>
      <p className="text-sm leading-relaxed text-zinc-200">
        {reasoning || 'No reasoning available for this candidate.'}
      </p>
    </div>

    {/* Honeypot flags — only when present */}
    {honeypotFlags.length > 0 && (
      <div className="rounded-lg border border-amber-700/40 bg-amber-950/30 p-3">
        <h4 className="mb-1 text-xs font-semibold text-amber-400">⚠ Anomaly Flags</h4>
        <ul className="space-y-0.5">
          {honeypotFlags.map((flag, i) => (
            <li key={i} className="text-xs text-amber-300">
              {flag}
            </li>
          ))}
        </ul>
      </div>
    )}
  </section>
);
