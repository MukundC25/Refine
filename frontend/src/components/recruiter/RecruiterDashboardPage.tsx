import React, { useState, useEffect } from 'react';
import { RankedCandidateTable } from './RankedCandidateTable';
import { CandidateProfile } from './CandidateProfile';
import { JDInputPanel } from './JDInputPanel';
import { RankingResult } from '../../lib/types';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import Button from '../ui/Button';
import LoginModal from '../auth/LoginModal';
import ProfileModal from '../auth/ProfileModal';
import { User } from '../../lib/types';

export const RecruiterDashboardPage: React.FC = () => {
  const [result, setResult] = useState<RankingResult | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('refine_token');
    if (token) fetchUser(token);
  }, []);

  const fetchUser = async (token: string) => {
    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setUser(await res.json());
      } else {
        localStorage.removeItem('refine_token');
      }
    } catch {
      localStorage.removeItem('refine_token');
    }
  };

  const handleLoginSuccess = (token: string) => {
    localStorage.setItem('refine_token', token);
    fetchUser(token);
    setLoginModalOpen(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('refine_token');
    setUser(null);
    setResult(null);
  };

  const handleResultReady = (r: RankingResult) => {
    setResult(r);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleStart = () => {
    if (!user) {
      setLoginModalOpen(true);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-neutral-900 text-neutral-silver">
      <Header
        mode="landing"
        onLogoClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        onStart={handleStart}
        user={user}
        onLoginClick={() => setLoginModalOpen(true)}
        onLogout={handleLogout}
        onProfileClick={() => setProfileModalOpen(true)}
      />

      <main className="flex-1 px-4 py-8 pt-24 max-w-[1400px] mx-auto w-full">
        {/* Hero-style header for the ranking system */}
        <div className="mb-8">
          <h1 className="text-3xl font-display font-bold text-white">
            Intelligent Candidate Ranking
          </h1>
          <p className="text-zinc-400 mt-2 max-w-2xl">
            Upload a job description and rank 100,000+ candidates using a hybrid AI pipeline —
            rule-based pre-screening, semantic matching, career trajectory analysis, and
            behavioural signal scoring.
          </p>
        </div>

        {!user ? (
          <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-900/40 py-24 text-center">
            <p className="text-zinc-400 mb-4">Sign in to run the ranking pipeline.</p>
            <Button glow onClick={() => setLoginModalOpen(true)}>
              Get Started
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-[380px,1fr] gap-8 items-start">
            <div className="xl:sticky xl:top-24">
              <JDInputPanel
                onResultReady={handleResultReady}
                currentRunId={result?.run_id ?? null}
              />
            </div>
            <div>
              {result ? (
                <div className="space-y-3">
                  <div className="flex justify-end">
                    <Button variant="outline" size="sm" onClick={() => setResult(null)}>
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
                    Paste or upload a JD and run the pipeline to see ranked candidates here.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <Footer onLogoClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} />

      <CandidateProfile
        candidateId={selectedCandidateId}
        isOpen={selectedCandidateId !== null}
        onClose={() => setSelectedCandidateId(null)}
      />

      <LoginModal
        isOpen={loginModalOpen}
        onClose={() => setLoginModalOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />

      {user && (
        <ProfileModal
          isOpen={profileModalOpen}
          onClose={() => setProfileModalOpen(false)}
          user={user}
          onUpdate={setUser}
        />
      )}
    </div>
  );
};
