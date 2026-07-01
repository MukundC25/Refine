import React, { useRef, useState } from 'react';
import { Upload, File as FileIcon, X } from 'lucide-react';
import { RankingResult } from '../../lib/types';
import Button from '../ui/Button';
import TextArea from '../ui/TextArea';
import { WeightsTuner, DEFAULT_WEIGHTS } from './WeightsTuner';
import { RunHistoryList, saveRunToHistory } from './RunHistoryList';
import {
  runRankingPipeline,
  runRankingPipelineWithFile,
  rerankPipeline,
} from '../../lib/utils';

type PanelState = 'idle' | 'running' | 'complete' | 'reranking' | 'error';
type InputTab = 'text' | 'file';

const MAX_JD_CHARS = 50_000;
const ALLOWED_EXTENSIONS = ['.docx', '.pdf'];

interface CompletionStats {
  elapsed_seconds: number;
  total_candidates_processed: number;
  honeypots_excluded: number;
}

// Stage labels shown while the backend is processing
const STAGE_LABELS = [
  'Stage 1: Rule-based pre-screening candidates…',
  'Stage 2: Semantic re-ranking top results…',
  'Stage 3: Behavioural signal boost…',
];

interface Props {
  onResultReady: (result: RankingResult) => void;
  currentRunId: string | null;
}

export const JDInputPanel: React.FC<Props> = ({ onResultReady, currentRunId }) => {
  const [panelState, setPanelState] = useState<PanelState>('idle');
  const [tab, setTab] = useState<InputTab>('text');
  const [jdText, setJdText] = useState('');
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [stats, setStats] = useState<CompletionStats | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({ ...DEFAULT_WEIGHTS });
  const [stageIdx, setStageIdx] = useState(0);
  const stageTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cancelledRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canRun = tab === 'text'
    ? jdText.trim().length > 0 && jdText.length <= MAX_JD_CHARS
    : jdFile !== null;

  function startStageCycler() {
    setStageIdx(0);
    stageTimerRef.current = setInterval(() => {
      setStageIdx(i => (i + 1) % STAGE_LABELS.length);
    }, 2500);
  }

  function stopStageCycler() {
    if (stageTimerRef.current) {
      clearInterval(stageTimerRef.current);
      stageTimerRef.current = null;
    }
  }

  async function handleRun() {
    cancelledRef.current = false;
    setPanelState('running');
    setErrorMsg(null);
    startStageCycler();

    try {
      const result = tab === 'file' && jdFile
        ? await runRankingPipelineWithFile(jdFile)
        : await runRankingPipeline(jdText);

      if (cancelledRef.current) return;

      setStats({
        elapsed_seconds: result.elapsed_seconds,
        total_candidates_processed: result.total_candidates_processed,
        honeypots_excluded: result.honeypots_excluded,
      });
      saveRunToHistory(tab === 'text' ? jdText : (jdFile?.name ?? ''), result);
      setPanelState('complete');
      onResultReady(result);
    } catch (err: unknown) {
      if (!cancelledRef.current) {
        setErrorMsg(err instanceof Error ? err.message : 'Ranking failed');
        setPanelState('error');
      }
    } finally {
      stopStageCycler();
    }
  }

  function handleCancel() {
    cancelledRef.current = true;
    stopStageCycler();
    setPanelState('idle');
  }

  async function handleRerank() {
    setPanelState('reranking');
    setErrorMsg(null);
    try {
      const result = await rerankPipeline(
        tab === 'text' ? jdText : null,
        weights,
      );
      setStats({
        elapsed_seconds: result.elapsed_seconds,
        total_candidates_processed: result.total_candidates_processed,
        honeypots_excluded: result.honeypots_excluded,
      });
      saveRunToHistory(tab === 'text' ? jdText : (jdFile?.name ?? ''), result);
      setPanelState('complete');
      onResultReady(result);
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Re-rank failed');
      setPanelState('complete'); // stay on complete so user can try again
    }
  }

  function handleWeightChange(key: string, value: number) {
    setWeights(prev => ({ ...prev, [key]: value }));
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0] ?? null;
    if (!file) return;
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFileError('Only .docx and .pdf files are accepted.');
      setJdFile(null);
      return;
    }
    setFileError(null);
    setJdFile(file);
  }

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setFileError('Only .docx and .pdf files are accepted.');
      return;
    }
    setFileError(null);
    setJdFile(file);
  }

  function resetToIdle() {
    setPanelState('idle');
    setErrorMsg(null);
    setStats(null);
  }

  return (
    <div className="space-y-4">
      {/* Card */}
      <div className="bg-neutral-800/50 border border-zinc-800 p-6 rounded-xl backdrop-blur-sm space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-white">
            {panelState === 'idle' || panelState === 'error' ? 'New Ranking Run' : 'Ranking Run'}
          </h2>
          {(panelState === 'complete') && (
            <Button variant="outline" size="sm" onClick={resetToIdle}>
              New Run
            </Button>
          )}
        </div>

        {/* ── Idle / Error: JD input ─────────────────────────────────────── */}
        {(panelState === 'idle' || panelState === 'error') && (
          <div className="space-y-4">
            {/* Tab switcher */}
            <div className="flex gap-1 p-1 bg-zinc-900 rounded-lg w-fit">
              {(['text', 'file'] as InputTab[]).map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    tab === t
                      ? 'bg-zinc-700 text-white'
                      : 'text-zinc-400 hover:text-white'
                  }`}
                >
                  {t === 'text' ? 'Paste Text' : 'Upload File'}
                </button>
              ))}
            </div>

            {/* Text tab */}
            {tab === 'text' && (
              <div className="space-y-1.5">
                <TextArea
                  value={jdText}
                  onChange={e => setJdText(e.target.value)}
                  placeholder="Paste the full job description here…"
                  rows={8}
                  className="font-mono text-sm resize-y"
                />
                <div className="flex items-center gap-2 text-xs text-zinc-500">
                  <span>{jdText.length.toLocaleString()} chars</span>
                  {jdText.length > MAX_JD_CHARS && (
                    <span className="text-red-400">⚠ Too long (max 50,000)</span>
                  )}
                </div>
              </div>
            )}

            {/* File tab */}
            {tab === 'file' && (
              <div
                className={`flex flex-col items-center justify-center w-full border-2 border-dashed rounded-xl p-8 transition-all cursor-pointer ${
                  jdFile
                    ? 'border-primary-500/50 bg-white/5'
                    : 'border-white/10 hover:border-primary-400/50 hover:bg-white/5'
                } ${fileError ? 'border-red-500/50 bg-red-500/5' : ''}`}
                onDragOver={e => e.preventDefault()}
                onDrop={handleFileDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".docx,.pdf"
                  className="hidden"
                  onChange={handleFileSelect}
                />

                {jdFile ? (
                  <div className="flex items-center justify-between w-full">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-lg bg-neutral-800 border border-white/10">
                        <FileIcon className="h-5 w-5 text-primary-400" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-white">{jdFile.name}</p>
                        <p className="text-xs text-zinc-400">
                          {(jdFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="text-zinc-400 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors"
                      onClick={e => {
                        e.stopPropagation();
                        setJdFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = '';
                      }}
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="p-4 rounded-full bg-white/5 mb-4">
                      <Upload className="h-7 w-7 text-zinc-400" />
                    </div>
                    <p className="text-sm text-zinc-300 font-medium">
                      Drag & drop or{' '}
                      <span className="text-primary-400 hover:underline">browse</span>
                    </p>
                    <p className="mt-1 text-xs text-zinc-500">.docx or .pdf only</p>
                  </>
                )}
              </div>
            )}

            {fileError && (
              <p className="text-sm text-red-400">{fileError}</p>
            )}

            {panelState === 'error' && errorMsg && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm">
                {errorMsg}
              </div>
            )}

            <div className="flex justify-end">
              <Button onClick={handleRun} disabled={!canRun} glow>
                Run Ranking
              </Button>
            </div>
          </div>
        )}

        {/* ── Running ────────────────────────────────────────────────────── */}
        {panelState === 'running' && (
          <div className="flex flex-col items-center gap-5 py-6">
            <div className="w-10 h-10 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin" />
            <p className="text-sm text-zinc-400 animate-pulse text-center">
              {STAGE_LABELS[stageIdx]}
            </p>
            <Button variant="outline" size="sm" onClick={handleCancel}>
              Cancel
            </Button>
          </div>
        )}

        {/* ── Complete ───────────────────────────────────────────────────── */}
        {(panelState === 'complete' || panelState === 'reranking') && stats && (
          <div className="space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Elapsed', value: `${stats.elapsed_seconds.toFixed(1)}s` },
                { label: 'Candidates', value: stats.total_candidates_processed.toLocaleString() },
                { label: 'Honeypots excluded', value: stats.honeypots_excluded.toLocaleString() },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="rounded-lg border border-zinc-800 bg-zinc-900 p-3 text-center"
                >
                  <div className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</div>
                  <div className="mt-1 font-mono text-base font-semibold text-white">{value}</div>
                </div>
              ))}
            </div>

            {errorMsg && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm">
                {errorMsg}
              </div>
            )}

            {/* WeightsTuner */}
            <WeightsTuner
              weights={weights}
              onChange={handleWeightChange}
              onRerank={handleRerank}
              isReranking={panelState === 'reranking'}
            />
          </div>
        )}
      </div>

      {/* Run history (outside the card) */}
      <RunHistoryList onLoad={onResultReady} currentRunId={currentRunId} />
    </div>
  );
};
