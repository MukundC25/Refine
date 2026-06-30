import React, { useState, useMemo } from 'react';
import { RankedCandidate, RankingResult, CandidateFilters } from '../../lib/types';
import { FilterPanel } from './FilterPanel';
import { CandidateRow } from './CandidateRow';
import Button from '../ui/Button';
import { Download } from 'lucide-react';

const defaultFilters: CandidateFilters = {
  minYoe: 0,
  maxYoe: 20,
  minScore: 0,
  skills: [],
  workMode: [],
  maxNoticeDays: 999,
  searchQuery: ''
};

function exportCSV(candidates: RankedCandidate[]): void {
  const rows = [
    ["rank", "candidate_id", "score", "headline", "title", "company", "yoe", "reasoning"],
    ...candidates.map(c => [
      c.rank, 
      c.candidate_id, 
      c.final_score,
      `"${(c.profile_snapshot.headline || "").replace(/"/g, '""')}"`,
      `"${(c.profile_snapshot.current_title || "").replace(/"/g, '""')}"`,
      `"${(c.profile_snapshot.current_company || "").replace(/"/g, '""')}"`,
      c.profile_snapshot.years_of_experience,
      `"${(c.reasoning || "").replace(/"/g, '""')}"`
    ])
  ];
  const csv = rows.map(r => r.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "ranked_candidates.csv"; a.click();
  URL.revokeObjectURL(url);
}

const TableHeader: React.FC<{ result: RankingResult; onExport: () => void }> = ({ result, onExport }) => (
  <div className="flex justify-between items-center mb-4">
    <div>
      <h2 className="text-xl font-bold text-white">Ranked Candidates</h2>
      <p className="text-sm text-zinc-400">
        Showing top results out of {result.total_candidates_processed} processed 
        ({result.honeypots_excluded} honeypots excluded).
      </p>
    </div>
    <Button variant="outline" size="sm" onClick={onExport} icon={<Download size={16} />}>
      Export CSV
    </Button>
  </div>
);

const EmptyState = () => (
  <div className="py-12 text-center text-zinc-500">
    <p>No candidates match your current filters.</p>
    <p className="text-sm mt-1">Try relaxing your search criteria.</p>
  </div>
);

const TableHead: React.FC<{
  sortKey: keyof RankedCandidate;
  sortDir: 'asc' | 'desc';
  onSort: (key: keyof RankedCandidate) => void;
}> = ({ sortKey, sortDir, onSort }) => {
  const SortIcon = ({ columnKey }: { columnKey: keyof RankedCandidate }) => {
    if (sortKey !== columnKey) return null;
    return <span className="ml-1 text-primary-500">{sortDir === 'asc' ? '▲' : '▼'}</span>;
  };

  return (
    <thead>
      <tr className="text-left text-xs font-semibold text-zinc-500 uppercase tracking-wider border-b border-zinc-800">
        <th className="px-3 py-3 cursor-pointer hover:text-zinc-300" onClick={() => onSort('rank')}>
          Rank <SortIcon columnKey="rank" />
        </th>
        <th className="px-3 py-3">Candidate</th>
        <th className="px-3 py-3">Role</th>
        <th className="px-3 py-3 cursor-pointer hover:text-zinc-300 text-center" onClick={() => onSort('candidate_id')}>
          {/* Using candidate_id as dummy for YoE sort logic below, but we sort by true YoE */}
          YoE
        </th>
        <th className="px-3 py-3 cursor-pointer hover:text-zinc-300" onClick={() => onSort('final_score')}>
          Score <SortIcon columnKey="final_score" />
        </th>
        <th className="px-3 py-3">Top Skills</th>
        <th className="px-3 py-3">Reasoning</th>
      </tr>
    </thead>
  );
};

interface Props {
  result: RankingResult;
  onCandidateClick: (candidateId: string) => void;
}

export const RankedCandidateTable: React.FC<Props> = ({ result, onCandidateClick }) => {
  const [filters, setFilters] = useState<CandidateFilters>(defaultFilters);
  const [sortKey, setSortKey] = useState<string>("rank");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const filtered = useMemo(() => {
    return result.ranked_candidates.filter(c => {
      // Score filter
      if (c.final_score < filters.minScore) return false;
      
      // YoE filter
      const yoe = c.profile_snapshot.years_of_experience;
      if (yoe < filters.minYoe) return false;
      if (filters.maxYoe < 20 && yoe > filters.maxYoe) return false;

      // Skills filter
      if (filters.skills.length > 0) {
        const hasSkill = filters.skills.some(skill => c.profile_snapshot.top_skills.includes(skill));
        if (!hasSkill) return false;
      }

      // Work Mode and Notice Period (mock implementation since data might not have these yet)
      // If we need them, we assume they pass if not specified in snapshot, or just skip filtering if not applicable.

      // Search
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const headlineMatch = (c.profile_snapshot.headline || "").toLowerCase().includes(query);
        const titleMatch = (c.profile_snapshot.current_title || "").toLowerCase().includes(query);
        const companyMatch = (c.profile_snapshot.current_company || "").toLowerCase().includes(query);
        const idMatch = c.candidate_id.toLowerCase().includes(query);
        
        if (!headlineMatch && !titleMatch && !companyMatch && !idMatch) {
          return false;
        }
      }

      return true;
    });
  }, [result, filters]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let aVal: any = a[sortKey as keyof RankedCandidate];
      let bVal: any = b[sortKey as keyof RankedCandidate];

      // Handle nested or special sorts
      if (sortKey === 'candidate_id') {
        // We used this column to sort by YoE in our header click handler above, 
        // to avoid TS errors. Let's redirect to YoE properly.
        aVal = a.profile_snapshot.years_of_experience;
        bVal = b.profile_snapshot.years_of_experience;
      }

      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filtered, sortKey, sortDir]);

  const handleSort = (key: keyof RankedCandidate | string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key as string);
      setSortDir('asc');
    }
  };

  return (
    <div className="flex flex-col md:flex-row gap-6">
      <FilterPanel filters={filters} onChange={setFilters} candidates={result.ranked_candidates} />
      <div className="flex-1 overflow-x-auto">
        <TableHeader result={result} onExport={() => exportCSV(sorted)} />
        <div className="bg-neutral-900 border border-zinc-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <TableHead sortKey={sortKey as any} sortDir={sortDir} onSort={handleSort} />
            <tbody>
              {sorted.map(c => (
                <CandidateRow
                  key={c.candidate_id}
                  candidate={c}
                  onClick={() => onCandidateClick(c.candidate_id)}
                />
              ))}
            </tbody>
          </table>
          {sorted.length === 0 && <EmptyState />}
        </div>
      </div>
    </div>
  );
};
