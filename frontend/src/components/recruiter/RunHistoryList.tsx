import React, { useEffect, useState } from 'react';
import { RankingResult } from '../../lib/types';
import { Clock } from 'lucide-react';
import Button from '../ui/Button';

const STORAGE_KEY = 'refine_run_history';
const MAX_HISTORY = 10;

export interface RunHistorySummary {
  run_id: string;
  timestamp: string;
  elapsed_seconds: number;
  jd_snippet: string;
  top1_candidate: string;
  top1_score: number;
  result: RankingResult;
}

export function saveRunToHistory(jdText: string, result: RankingResult): void {
  const top1 = result.ranked_candidates[0];
  const entry: RunHistorySummary = {
    run_id: result.run_id,
    timestamp: new Date().toISOString(),
    elapsed_seconds: result.elapsed_seconds,
    jd_snippet: jdText.slice(0, 60),
    top1_candidate: top1?.candidate_id ?? '—',
    top1_score: top1?.final_score ?? 0,
    result,
  };
  try {
    const existing: RunHistorySummary[] = JSON.parse(
      localStorage.getItem(STORAGE_KEY) ?? '[]',
    );
    const updated = [entry, ...existing.filter(e => e.run_id !== entry.run_id)].slice(
      0,
      MAX_HISTORY,
    );
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {
    // localStorage unavailable — silently skip
  }
}

export function loadRunHistory(): RunHistorySummary[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]');
  } catch {
    return [];
  }
}

interface Props {
  onLoad: (result: RankingResult) => void;
  currentRunId: string | null;
}

export const RunHistoryList: React.FC<Props> = ({ onLoad, currentRunId }) => {
  const [history, setHistory] = useState<RunHistorySummary[]>([]);

  useEffect(() => {
    setHistory(loadRunHistory());
  }, [currentRunId]);

  if (history.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
        Recent Runs
      </h3>
      <ul className="space-y-1.5">
        {history.map(entry => (
          <li
            key={entry.run_id}
            className="flex items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <Clock size={11} />
                <span>{new Date(entry.timestamp).toLocaleString()}</span>
                <span className="text-zinc-600">·</span>
                <span className="font-mono">{entry.elapsed_seconds.toFixed(1)}s</span>
              </div>
              <p className="mt-0.5 truncate text-sm text-zinc-300">
                {entry.jd_snippet}
                {entry.jd_snippet.length >= 60 ? '…' : ''}
              </p>
              <p className="text-[11px] text-zinc-500">
                Top: {entry.top1_candidate} ({entry.top1_score.toFixed(1)})
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onLoad(entry.result)}
              disabled={entry.run_id === currentRunId}
            >
              {entry.run_id === currentRunId ? 'Active' : 'Load'}
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
};
