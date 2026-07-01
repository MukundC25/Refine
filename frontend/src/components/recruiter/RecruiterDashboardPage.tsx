import React, { useState } from 'react';
import { RankedCandidateTable } from './RankedCandidateTable';
import { CandidateProfile } from './CandidateProfile';
import { RankingResult } from '../../lib/types';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import Button from '../ui/Button';
import { runRankingPipeline } from '../../lib/utils';
import { dummyResult } from '../../lib/mockData';

export const RecruiterDashboardPage: React.FC = () => {
  const [result, setResult] = useState<RankingResult | null>(null);
  const [jdText, setJdText] = useState("");
  const [isRanking, setIsRanking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunPipeline = async () => {
    if (!jdText.trim()) {
      setError("Please enter a Job Description.");
      return;
    }

    setIsRanking(true);
    setError(null);

    try {
      // Call the live backend endpoint
      const liveResult = await runRankingPipeline(jdText, 100);
      setResult(liveResult);
    } catch (err: any) {
      console.warn("Backend ranking failed. Falling back to dummy data.", err);
      // If the backend fails (e.g. no server running, token invalid, or Gemini API limits),
      // we gracefully fallback to our isolated dummy dataset for the demo.
      setResult(dummyResult);
      setError(`Backend API Error: ${err.message}. Using fallback demo data.`);
    } finally {
      setIsRanking(false);
    }
  };

  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  const handleCandidateClick = (id: string) => setSelectedCandidateId(id);
  const closeDeepDive = () => setSelectedCandidateId(null);

  return (
    <div className="flex flex-col min-h-screen bg-neutral-900 text-neutral-silver">
      <Header 
        mode="app" 
        onLogoClick={() => window.location.href = '/'}
        onStart={() => window.location.href = '/'}
      />
      
      <main className="flex-1 px-4 py-8 pt-24 max-w-[1400px] mx-auto w-full">
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white">Recruiter Dashboard</h1>
          <p className="text-zinc-400 mt-2">Run the ranking pipeline and evaluate candidates for your open positions.</p>
        </div>

        {/* Input Form */}
        {!result && (
          <div className="bg-neutral-800/50 border border-zinc-800 p-6 rounded-xl mb-8 backdrop-blur-sm">
            <h2 className="text-lg font-bold text-white mb-4">New Ranking Run</h2>
            <div className="flex flex-col gap-4">
              <textarea 
                className="w-full h-32 p-3 bg-neutral-900 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-colors"
                placeholder="Paste the Job Description here (min 20 characters)..."
                value={jdText}
                onChange={(e) => setJdText(e.target.value)}
                disabled={isRanking}
              />
              
              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-md text-sm">
                  {error}
                </div>
              )}

              <div className="flex justify-end">
                <Button 
                  onClick={handleRunPipeline} 
                  disabled={isRanking || jdText.length < 20}
                  glow
                >
                  {isRanking ? "Running Pipeline..." : "Run Ranking Pipeline"}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Loading Spinner */}
        {isRanking && !result && (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin mb-4"></div>
            <p className="text-zinc-400 animate-pulse">Running AI candidate evaluation pipeline (this may take a minute)...</p>
          </div>
        )}

        {/* Results Table */}
        {result && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              {error && (
                <div className="flex-1 mr-4 p-3 bg-warning-500/10 border border-warning-500/20 text-warning-400 rounded-md text-sm">
                  {error}
                </div>
              )}
              <Button variant="outline" size="sm" onClick={() => { setResult(null); setError(null); }}>
                Start New Run
              </Button>
            </div>
            
            <RankedCandidateTable result={result} onCandidateClick={handleCandidateClick} />
          </div>
        )}
      </main>

      <Footer onLogoClick={() => window.location.href = '/'} />

      <CandidateProfile
        candidateId={selectedCandidateId}
        isOpen={selectedCandidateId !== null}
        onClose={closeDeepDive}
      />
    </div>
  );
};
