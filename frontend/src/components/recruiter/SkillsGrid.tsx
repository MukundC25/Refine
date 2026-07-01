import React from 'react';
import { Proficiency, SkillEntry } from '../../lib/types';
import { CheckCircle2 } from 'lucide-react';

const PROFICIENCY_STYLE: Record<Proficiency, string> = {
  beginner: 'bg-zinc-800 border-zinc-700 text-zinc-300',
  intermediate: 'bg-blue-900/40 border-blue-700/60 text-blue-200',
  advanced: 'bg-violet-900/40 border-violet-700/60 text-violet-200',
  expert: 'bg-emerald-900/40 border-emerald-600/60 text-emerald-200',
};

const PROFICIENCY_ORDER: Record<Proficiency, number> = {
  expert: 0, advanced: 1, intermediate: 2, beginner: 3,
};

interface Props {
  skills: SkillEntry[];
  assessmentScores: Record<string, number>;
}

const SkillPill: React.FC<{ skill: SkillEntry; assessment?: number }> = ({ skill, assessment }) => {
  const durationLabel =
    skill.duration_months && skill.duration_months > 0
      ? `${skill.duration_months} mo`
      : null;

  const tooltip = [
    `${skill.name}`,
    `Proficiency: ${skill.proficiency}`,
    skill.endorsements > 0 ? `${skill.endorsements} endorsements` : null,
    durationLabel ? `Used for ${durationLabel}` : null,
    assessment !== undefined ? `Assessment score: ${assessment.toFixed(0)}/100` : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <span
      title={tooltip}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${PROFICIENCY_STYLE[skill.proficiency]}`}
    >
      <span>{skill.name}</span>

      {assessment !== undefined && (
        <span
          className="flex items-center gap-0.5 rounded bg-emerald-500/20 px-1 py-0.5 text-[10px] font-mono text-emerald-300"
          title={`Platform-verified assessment score ${assessment.toFixed(0)}/100`}
        >
          <CheckCircle2 size={10} />
          {assessment.toFixed(0)}
        </span>
      )}

      {skill.endorsements > 0 && (
        <span className="rounded bg-zinc-900/50 px-1 py-0.5 text-[10px] font-mono text-zinc-400">
          {skill.endorsements}★
        </span>
      )}
    </span>
  );
};

export const SkillsGrid: React.FC<Props> = ({ skills, assessmentScores }) => {
  if (!skills || skills.length === 0) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-sm text-zinc-500">
        No skills listed.
      </div>
    );
  }

  // Sort by proficiency (expert → beginner), then by endorsements desc.
  const sorted = [...skills].sort((a, b) => {
    const p = PROFICIENCY_ORDER[a.proficiency] - PROFICIENCY_ORDER[b.proficiency];
    if (p !== 0) return p;
    return b.endorsements - a.endorsements;
  });

  return (
    <section aria-labelledby="skills-heading">
      <h3 id="skills-heading" className="mb-3 text-sm font-semibold text-zinc-300">
        Skills
        <span className="ml-2 text-xs text-zinc-500">({skills.length} listed)</span>
      </h3>
      <div className="flex flex-wrap gap-2">
        {sorted.map(skill => (
          <SkillPill
            key={skill.name}
            skill={skill}
            assessment={assessmentScores?.[skill.name]}
          />
        ))}
      </div>
    </section>
  );
};
