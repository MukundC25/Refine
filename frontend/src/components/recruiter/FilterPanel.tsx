import React from 'react';
import { CandidateFilters, RankedCandidate } from '../../lib/types';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface FilterPanelProps {
  filters: CandidateFilters;
  onChange: (filters: CandidateFilters) => void;
  candidates: RankedCandidate[];
}

export const FilterPanel: React.FC<FilterPanelProps> = ({ filters, onChange, candidates }) => {
  // Extract unique top skills for the filter options
  const allSkills = Array.from(
    new Set(candidates.flatMap(c => c.profile_snapshot.top_skills))
  ).sort();

  const handleSkillToggle = (skill: string) => {
    const newSkills = filters.skills.includes(skill)
      ? filters.skills.filter(s => s !== skill)
      : [...filters.skills, skill];
    onChange({ ...filters, skills: newSkills });
  };

  const handleModeToggle = (mode: string) => {
    const newModes = filters.workMode.includes(mode)
      ? filters.workMode.filter(m => m !== mode)
      : [...filters.workMode, mode];
    onChange({ ...filters, workMode: newModes });
  };

  return (
    <Card className="w-64 shrink-0 bg-neutral-900 border-zinc-800" variant="glass">
      <CardHeader className="p-4 border-b border-zinc-800">
        <CardTitle className="text-lg">Filters</CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-6">
        
        {/* Search */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Search</label>
          <input
            type="search"
            className="w-full bg-zinc-800 border border-zinc-700 rounded p-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-primary-500"
            placeholder="Name, role, company..."
            value={filters.searchQuery}
            onChange={(e) => onChange({ ...filters, searchQuery: e.target.value })}
          />
        </div>

        {/* Min Score */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            <label>Min Score</label>
            <span className="text-primary-400">{filters.minScore}</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            className="w-full accent-primary-500"
            value={filters.minScore}
            onChange={(e) => onChange({ ...filters, minScore: parseInt(e.target.value) })}
          />
        </div>

        {/* Years of Experience */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            <label>Experience (YoE)</label>
            <span className="text-primary-400">{filters.minYoe} - {filters.maxYoe === 20 ? '20+' : filters.maxYoe}</span>
          </div>
          <div className="flex gap-2 items-center">
            <input
              type="number"
              min="0"
              max="20"
              className="w-16 bg-zinc-800 border border-zinc-700 rounded p-1 text-sm text-center text-white"
              value={filters.minYoe}
              onChange={(e) => onChange({ ...filters, minYoe: parseInt(e.target.value) || 0 })}
            />
            <span className="text-zinc-500">to</span>
            <input
              type="number"
              min="0"
              max="20"
              className="w-16 bg-zinc-800 border border-zinc-700 rounded p-1 text-sm text-center text-white"
              value={filters.maxYoe}
              onChange={(e) => onChange({ ...filters, maxYoe: parseInt(e.target.value) || 20 })}
            />
          </div>
        </div>

        {/* Work Mode */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Work Mode</label>
          <div className="flex flex-wrap gap-2">
            {['Remote', 'Hybrid', 'Onsite', 'Flexible'].map(mode => (
              <button
                key={mode}
                className={`px-2 py-1 rounded text-xs transition-colors ${
                  filters.workMode.includes(mode) 
                    ? 'bg-primary-500/20 text-primary-300 border border-primary-500/50' 
                    : 'bg-zinc-800 text-zinc-400 border border-zinc-700 hover:bg-zinc-700'
                }`}
                onClick={() => handleModeToggle(mode)}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        {/* Notice Period */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Notice Period (Days)</label>
          <select 
            className="w-full bg-zinc-800 border border-zinc-700 rounded p-2 text-sm text-white"
            value={filters.maxNoticeDays}
            onChange={(e) => onChange({ ...filters, maxNoticeDays: parseInt(e.target.value) })}
          >
            <option value={999}>Any</option>
            <option value={30}>30 Days or less</option>
            <option value={60}>60 Days or less</option>
            <option value={90}>90 Days or less</option>
          </select>
        </div>

        {/* Top Skills */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Skills</label>
          <div className="max-h-48 overflow-y-auto space-y-1 pr-2 custom-scrollbar">
            {allSkills.slice(0, 50).map(skill => (
              <label key={skill} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  className="accent-primary-500"
                  checked={filters.skills.includes(skill)}
                  onChange={() => handleSkillToggle(skill)}
                />
                <span className="text-sm text-zinc-300 group-hover:text-white truncate" title={skill}>
                  {skill}
                </span>
              </label>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
