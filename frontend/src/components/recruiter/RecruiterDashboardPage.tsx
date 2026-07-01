import React, { useState } from 'react';
import { RankedCandidateTable } from './RankedCandidateTable';
import { CandidateProfile } from './CandidateProfile';
import { JDInputPanel } from './JDInputPanel';
import { RankingResult } from '../../lib/types';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import Button from '../ui/Button';

export const RecruiterDashboardPage: React.FC = () => {
  const [result, setResult] = useState<RankingResult | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  const handleResultReady = (r: RankingResult) => {
    setResult(r);
    // Scroll up to the table after a ranking/re-rank completes
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="flex flex-col min-h-screen bg-neutral-900 text-neutral-silver">
      <Header
        mode="app"
        onLogoClick={() => (window.location.href = '/')}
        onStart={() => (window.location.href = '/')}
      />

      <main className="flex-1 px-4 py-8 pt-24 max-w-[1400px] mx-auto w-full">
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white">
            Recruiter Dashboard
          </h1>
          <p className="text-zinc-400 mt-2">
            Run the ranking pipeline and evaluate candidates for your open positions.
          </p>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[380px,1fr] gap-8 items-start">
          {/* Left: JD input + weights + history */}
          <div className="xl:sticky xl:top-24">
            <JDInputPanel
              onResultReady={handleResultReady}
              currentRunId={result?.run_id ?? null}
            />
          </div>

          {/* Right: results table or empty state */}
          <div>
            {result ? (
              <div className="space-y-3">
                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setResult(null)}
                  >
                    Clear Results
                  </Button>
                </div>
                <RankedCandidateTable
                  result={result}
                  onCandidateClick={setSelectedCandidateId}
                />
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-900/40 py-24 text-center">
                <p className="text-zinc-500 text-sm">
                  Run a ranking to see candidates here.
                </p>
              </div>
            )}
          </div>
        </div>
      </main>

      <Footer onLogoClick={() => (window.location.href = '/')} />

      <CandidateProfile
        candidateId={selectedCandidateId}
        isOpen={selectedCandidateId !== null}
        onClose={() => setSelectedCandidateId(null)}
      />
    </div>
  );
};
