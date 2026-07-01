import React from 'react';
import { RedrobSignals } from '../../lib/types';

interface Props {
  signals: RedrobSignals;
}

interface Card {
  label: string;
  value: string;
  highlight: boolean;
  neutral?: boolean;   // for -1 sentinels: "No history", "Not linked"
}

function buildCards(sig: RedrobSignals): Card[] {
  const verified = [
    sig.verified_email && 'Email',
    sig.verified_phone && 'Phone',
    sig.linkedin_connected && 'LinkedIn',
  ].filter(Boolean) as string[];

  return [
    {
      label: 'Open to Work',
      value: sig.open_to_work_flag ? 'Yes ✓' : 'No',
      highlight: sig.open_to_work_flag,
    },
    {
      label: 'Response Rate',
      value: `${(sig.recruiter_response_rate * 100).toFixed(0)}%`,
      highlight: sig.recruiter_response_rate > 0.7,
    },
    {
      label: 'Avg Response Time',
      value: `${sig.avg_response_time_hours.toFixed(0)}h`,
      highlight: sig.avg_response_time_hours < 24,
    },
    {
      label: 'Interview Completion',
      value: `${(sig.interview_completion_rate * 100).toFixed(0)}%`,
      highlight: sig.interview_completion_rate > 0.8,
    },
    {
      label: 'Offer Acceptance',
      value: sig.offer_acceptance_rate === -1
        ? 'No history'
        : `${(sig.offer_acceptance_rate * 100).toFixed(0)}%`,
      highlight: sig.offer_acceptance_rate > 0.7,
      neutral: sig.offer_acceptance_rate === -1,
    },
    {
      label: 'Notice Period',
      value: `${sig.notice_period_days} days`,
      highlight: sig.notice_period_days <= 30,
    },
    {
      label: 'GitHub Score',
      value: sig.github_activity_score === -1
        ? 'Not linked'
        : `${sig.github_activity_score.toFixed(0)}/100`,
      highlight: sig.github_activity_score > 50,
      neutral: sig.github_activity_score === -1,
    },
    {
      label: 'Saved by Recruiters',
      value: `${sig.saved_by_recruiters_30d} (30d)`,
      highlight: sig.saved_by_recruiters_30d > 3,
    },
    {
      label: 'Profile Complete',
      value: `${sig.profile_completeness_score.toFixed(0)}%`,
      highlight: sig.profile_completeness_score > 80,
    },
    {
      label: 'Verified',
      value: verified.length > 0 ? verified.join(', ') : 'None',
      highlight: sig.verified_email && sig.verified_phone,
    },
  ];
}

const SignalCard: React.FC<{ card: Card }> = ({ card }) => {
  const highlightClass = card.highlight
    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-100'
    : card.neutral
      ? 'border-zinc-700 bg-zinc-900 text-zinc-500'
      : 'border-zinc-800 bg-zinc-900 text-zinc-400';

  const valueClass = card.highlight
    ? 'text-emerald-200'
    : card.neutral
      ? 'text-zinc-500'
      : 'text-zinc-200';

  return (
    <div className={`rounded-lg border p-3 ${highlightClass}`}>
      <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
        {card.label}
      </div>
      <div className={`mt-1 font-mono text-sm ${valueClass}`}>{card.value}</div>
    </div>
  );
};

export const SignalsPanel: React.FC<Props> = ({ signals }) => {
  const cards = buildCards(signals);
  return (
    <section aria-labelledby="signals-heading">
      <h3 id="signals-heading" className="mb-3 text-sm font-semibold text-zinc-300">
        Redrob Platform Signals
      </h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {cards.map(card => (
          <SignalCard key={card.label} card={card} />
        ))}
      </div>
    </section>
  );
};
