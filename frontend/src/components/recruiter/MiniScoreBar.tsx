import React from 'react';
import { ScoreBreakdown } from '../../lib/types';
import { DIMENSION_CONFIG } from './ScoreExplainer';

interface Props {
  breakdown: ScoreBreakdown;
  className?: string;
}

export const MiniScoreBar: React.FC<Props> = ({ breakdown, className }) => (
  <div
    className={`flex items-end gap-0.5 h-4 ${className ?? ''}`}
    title="Score breakdown — hover individual bars for details"
  >
    {DIMENSION_CONFIG.map(dim => {
      const raw = breakdown[dim.key] ?? 0;
      const score = dim.transform ? dim.transform(raw) : raw;
      return (
        <div
          key={dim.key}
          className={`w-3 rounded-sm ${dim.color}`}
          style={{ height: `${Math.max(score, 4)}%` }}
          title={`${dim.label}: ${score.toFixed(1)}`}
        />
      );
    })}
  </div>
);
