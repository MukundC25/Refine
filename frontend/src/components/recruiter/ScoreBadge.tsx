import React from 'react';

export const ScoreBadge: React.FC<{ score: number }> = ({ score }) => {
  const color = score >= 80
    ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
    : score >= 60
    ? "bg-amber-500/20 text-amber-300 border-amber-500/30"
    : "bg-red-500/20 text-red-300 border-red-500/30";

  return (
    <span className={`px-2 py-1 rounded-full border text-xs font-mono font-semibold ${color}`}>
      {score.toFixed(1)}
    </span>
  );
};
