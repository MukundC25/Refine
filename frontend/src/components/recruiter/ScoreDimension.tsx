import React from 'react';

interface Props {
  icon: string;
  label: string;
  description: string;
  score: number;              // 0–100
  weight: number;             // 0.0–1.0
  weightedContribution: number;
}

export const ScoreDimension: React.FC<Props> = ({
  icon,
  label,
  description,
  score,
  weight,
  weightedContribution,
}) => {
  const barColor =
    score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-3">
      <span className="w-6 text-center text-base">{icon}</span>
      <div className="flex-1">
        <div className="mb-1 flex items-center justify-between">
          <span
            className="cursor-help text-xs font-medium text-zinc-300"
            title={description}
          >
            {label}
          </span>
          <div className="flex items-center gap-2">
            <span className="text-xs text-zinc-500">×{Math.round(weight * 100)}%</span>
            <span className="font-mono text-xs text-zinc-400">
              = {weightedContribution.toFixed(1)}
            </span>
            <span className="w-10 text-right font-mono text-xs font-semibold text-zinc-200">
              {score.toFixed(1)}
            </span>
          </div>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-zinc-700">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${Math.min(Math.max(score, 0), 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
};
