import React, { useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { useCandidateDetail } from '../../lib/hooks';
import { ProfileHeader } from './ProfileHeader';
import { ScoreRadarChart } from './ScoreRadarChart';
import { ReasoningCard } from './ReasoningCard';
import { CareerTimeline } from './CareerTimeline';
import { SkillsGrid } from './SkillsGrid';
import { SignalsPanel } from './SignalsPanel';
import { EducationList } from './EducationList';

interface Props {
  candidateId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

const ProfileSkeleton: React.FC = () => (
  <div className="h-full overflow-y-auto">
    <div className="border-b border-zinc-800 px-6 py-5">
      <div className="h-3 w-20 animate-pulse rounded bg-zinc-800" />
      <div className="mt-3 h-6 w-2/3 animate-pulse rounded bg-zinc-800" />
      <div className="mt-2 h-4 w-1/2 animate-pulse rounded bg-zinc-800" />
    </div>
    <div className="space-y-4 p-6">
      <div className="h-64 animate-pulse rounded-lg bg-zinc-800/50" />
      <div className="h-24 animate-pulse rounded-lg bg-zinc-800/50" />
      <div className="h-40 animate-pulse rounded-lg bg-zinc-800/50" />
    </div>
  </div>
);

const ErrorState: React.FC<{ message: string; onClose: () => void }> = ({ message, onClose }) => (
  <div className="flex h-full flex-col">
    <div className="flex items-center justify-between border-b border-zinc-800 px-6 py-4">
      <h2 className="text-lg font-semibold text-white">Candidate detail</h2>
      <button
        type="button"
        onClick={onClose}
        className="rounded-full p-1.5 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-white"
        aria-label="Close"
      >
        ×
      </button>
    </div>
    <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
      <AlertCircle size={32} className="text-red-400" />
      <p className="text-sm text-zinc-300">Unable to load candidate detail.</p>
      <p className="max-w-sm text-xs text-zinc-500">{message}</p>
    </div>
  </div>
);

export const CandidateProfile: React.FC<Props> = ({ candidateId, isOpen, onClose }) => {
  const { data, isLoading, error } = useCandidateDetail(isOpen ? candidateId : null);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose]);

  // Prevent body scroll while the drawer is open
  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [isOpen]);

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        aria-hidden={!isOpen}
        className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity duration-200 ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
      />

      {/* Drawer */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Candidate detail"
        className={`fixed inset-y-0 right-0 z-50 flex w-full transform flex-col border-l border-zinc-800 bg-zinc-900 shadow-2xl transition-transform duration-300 ease-out md:w-[52%] md:min-w-[560px] ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {isLoading && <ProfileSkeleton />}
        {error && !isLoading && <ErrorState message={error} onClose={onClose} />}
        {data && !isLoading && !error && (
          <div className="flex h-full flex-col overflow-hidden">
            <ProfileHeader
              candidate={data.candidate}
              rank={data.rank}
              finalScore={data.final_score}
              onClose={onClose}
            />
            <div className="flex-1 space-y-6 overflow-y-auto p-6">
              <ScoreRadarChart breakdown={data.score_breakdown} />
              <ReasoningCard reasoning={data.reasoning} flags={data.honeypot_flags} />
              <CareerTimeline history={data.candidate.career_history} />
              <SkillsGrid
                skills={data.candidate.skills}
                assessmentScores={data.candidate.redrob_signals.skill_assessment_scores}
              />
              <SignalsPanel signals={data.candidate.redrob_signals} />
              <EducationList education={data.candidate.education} />
            </div>
          </div>
        )}
      </aside>
    </>
  );
};
