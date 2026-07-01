import React from 'react';
import { ScoreBreakdown } from '../../lib/types';

// Pure SVG radar chart — no chart library dependency.
// 5 axes drawn from a shared centre with concentric grid pentagons at
// 25/50/75/100. The candidate polygon is filled to make relative
// strengths and weaknesses obvious at a glance.

interface Props {
  breakdown: ScoreBreakdown;
  size?: number;
}

const AXES = [
  { key: 'rule_score', label: 'Rules' },
  { key: 'embedding_similarity', label: 'Semantic' },
  { key: 'skills_score', label: 'Skills' },
  { key: 'career_score', label: 'Career' },
  { key: 'behavioral_score', label: 'Signals' },
] as const;

function polarToXY(cx: number, cy: number, radius: number, angle: number): [number, number] {
  return [cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)];
}

export const ScoreRadarChart: React.FC<Props> = ({ breakdown, size = 320 }) => {
  const cx = size / 2;
  const cy = size / 2;
  const maxRadius = size * 0.36;
  // Start at top (-π/2), then step clockwise by 2π/5
  const angles = AXES.map((_, i) => -Math.PI / 2 + (i * 2 * Math.PI) / 5);

  // Normalise every dimension into [0,100] before drawing.
  // embedding_similarity comes back in [0,1] so it needs a ×100 lift.
  const values: number[] = AXES.map(a => {
    const raw = breakdown[a.key as keyof ScoreBreakdown] ?? 0;
    const val = a.key === 'embedding_similarity' ? raw * 100 : raw;
    return Math.max(0, Math.min(100, val));
  });

  // Grid pentagons at 25/50/75/100 percent of maxRadius
  const gridLevels = [0.25, 0.5, 0.75, 1.0];
  const gridPolygons = gridLevels.map(level => {
    return angles
      .map(a => polarToXY(cx, cy, maxRadius * level, a).join(','))
      .join(' ');
  });

  // Candidate polygon points
  const candidatePoints = angles
    .map((a, i) => polarToXY(cx, cy, maxRadius * (values[i] / 100), a).join(','))
    .join(' ');

  // Axis line + label positions
  const axisEnds = angles.map(a => polarToXY(cx, cy, maxRadius, a));
  const labelPositions = angles.map(a => polarToXY(cx, cy, maxRadius * 1.15, a));

  return (
    <div className="flex flex-col items-center">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        role="img"
        aria-label="Score breakdown radar chart"
        className="max-w-full"
      >
        {/* Grid rings */}
        {gridPolygons.map((points, i) => (
          <polygon
            key={`grid-${i}`}
            points={points}
            fill="none"
            stroke="rgb(63 63 70)" // zinc-700
            strokeWidth={i === gridLevels.length - 1 ? 1.2 : 0.6}
            strokeDasharray={i === gridLevels.length - 1 ? undefined : '2 3'}
          />
        ))}

        {/* Axis lines */}
        {axisEnds.map(([x, y], i) => (
          <line
            key={`axis-${i}`}
            x1={cx} y1={cy} x2={x} y2={y}
            stroke="rgb(63 63 70)"
            strokeWidth={0.6}
          />
        ))}

        {/* Candidate polygon */}
        <polygon
          points={candidatePoints}
          fill="rgb(139 92 246 / 0.25)"      // violet-500 / 25%
          stroke="rgb(139 92 246)"
          strokeWidth={2}
          strokeLinejoin="round"
        />

        {/* Value dots */}
        {angles.map((a, i) => {
          const [x, y] = polarToXY(cx, cy, maxRadius * (values[i] / 100), a);
          return (
            <circle
              key={`dot-${i}`}
              cx={x} cy={y} r={3.5}
              fill="rgb(167 139 250)"          // violet-400
              stroke="rgb(24 24 27)"
              strokeWidth={1.2}
            />
          );
        })}

        {/* Labels */}
        {labelPositions.map(([x, y], i) => {
          const anchor =
            Math.abs(x - cx) < 4 ? 'middle' : x < cx ? 'end' : 'start';
          return (
            <g key={`label-${i}`}>
              <text
                x={x}
                y={y - 4}
                textAnchor={anchor}
                className="fill-zinc-300 text-[11px] font-medium"
              >
                {AXES[i].label}
              </text>
              <text
                x={x}
                y={y + 10}
                textAnchor={anchor}
                className="fill-violet-400 text-[10px] font-mono"
              >
                {values[i].toFixed(1)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
