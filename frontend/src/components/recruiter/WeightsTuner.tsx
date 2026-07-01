import React from 'react';
import Button from '../ui/Button';

export const DEFAULT_WEIGHTS: Record<string, number> = {
  rule_score: 0.20,
  embedding_similarity: 0.25,
  skills_trust: 0.20,
  career_trajectory: 0.15,
  behavioral: 0.20,
};

const WEIGHT_LABELS: Record<string, string> = {
  rule_score: 'Rules (YoE, Title, Skills)',
  embedding_similarity: 'Semantic Match',
  skills_trust: 'Skills Trust',
  career_trajectory: 'Career Trajectory',
  behavioral: 'Platform Signals',
};

function sumWeights(weights: Record<string, number>): number {
  return Object.values(weights).reduce((a, b) => a + b, 0);
}

interface Props {
  weights: Record<string, number>;
  onChange: (key: string, value: number) => void;
  onRerank: () => void;
  isReranking: boolean;
}

export const WeightsTuner: React.FC<Props> = ({ weights, onChange, onRerank, isReranking }) => {
  const total = sumWeights(weights);
  const invalid = Math.abs(total - 1) > 0.01;

  return (
    <div className="bg-neutral-800/50 border border-zinc-800 rounded-xl p-5 space-y-4">
      <h3 className="text-sm font-semibold text-zinc-300">Adjust Ranking Weights</h3>

      <div className="space-y-3">
        {Object.entries(WEIGHT_LABELS).map(([key, label]) => (
          <div key={key} className="flex items-center gap-3">
            <span className="text-xs text-zinc-400 w-44 shrink-0">{label}</span>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={Math.round((weights[key] ?? 0) * 100)}
              onChange={e => onChange(key, Number(e.target.value) / 100)}
              className="flex-1 accent-violet-500"
            />
            <span className="text-xs font-mono text-zinc-300 w-8 text-right">
              {Math.round((weights[key] ?? 0) * 100)}%
            </span>
          </div>
        ))}
      </div>

      <div className={`text-xs font-mono ${invalid ? 'text-red-400' : 'text-emerald-400'}`}>
        Total: {Math.round(total * 100)}%{' '}
        {invalid ? '⚠ must sum to 100%' : '✓'}
      </div>

      <Button
        onClick={onRerank}
        disabled={invalid || isReranking}
        isLoading={isReranking}
        size="sm"
        variant="outline"
      >
        {isReranking ? 'Re-ranking…' : 'Re-Rank with New Weights'}
      </Button>
    </div>
  );
};
