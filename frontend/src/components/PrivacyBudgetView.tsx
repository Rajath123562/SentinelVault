import React, { useState, useEffect } from 'react';
import { BudgetStatusResponse, DatasetMetadata } from '../types/system';
import { getBudgetStatus } from '../services/api';

export interface UsageRecord {
  id: string;
  time: string;
  query: string;
  cost: number;
}

interface PrivacyBudgetViewProps {
  token: string;
  datasets: DatasetMetadata[];
  selectedDatasetId: string;
  onSelectDatasetId: (id: string) => void;
  budget: BudgetStatusResponse | null;
  recentUsage?: UsageRecord[];
}

export const PrivacyBudgetView: React.FC<PrivacyBudgetViewProps> = ({
  token,
  datasets,
  selectedDatasetId,
  onSelectDatasetId,
  budget,
  recentUsage = [],
}) => {
  const [localBudget, setLocalBudget] = useState<BudgetStatusResponse | null>(budget);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLocalBudget(budget);
  }, [budget]);

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const data = await getBudgetStatus(selectedDatasetId, token);
      setLocalBudget(data);
    } catch (err) {
      console.error('Failed to refresh budget', err);
    } finally {
      setLoading(false);
    }
  };

  const spent = localBudget?.spent_epsilon ?? 0;
  const cap = localBudget?.cap_epsilon ?? 5.0;
  const remaining = localBudget?.remaining_epsilon ?? Math.max(0, cap - spent);
  const percentageUsed = cap > 0 ? (spent / cap) * 100 : 0;
  const percentageRemaining = 100 - percentageUsed;

  // SVG circular ring calculations
  const radius = 70;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentageUsed / 100) * circumference;

  // Reconcile recent usage strictly from authoritative backend releases
  const serverReleases: UsageRecord[] = (localBudget?.recent_releases || []).map((r) => {
    const d = new Date(r.timestamp);
    const timeStr = isNaN(d.getTime()) ? r.timestamp : d.toLocaleTimeString();
    return {
      id: r.release_id,
      time: timeStr,
      query: r.query_description,
      cost: r.epsilon_spent,
    };
  });

  const displayUsage: UsageRecord[] = serverReleases.length > 0
    ? serverReleases
    : recentUsage.filter((u) => u.cost > 0);

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚖️</span>
            <h2 className="text-xl font-bold text-white tracking-tight">Privacy Budget Tracker</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Track cumulative epsilon (ε) expenditure. Enforces global fail-closed privacy limits to prevent composition attacks.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedDatasetId}
            onChange={(e) => onSelectDatasetId(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
          >
            {datasets.map((d) => (
              <option key={d.dataset_id} value={d.dataset_id}>
                {d.title || d.name || d.dataset_id}
              </option>
            ))}
          </select>

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
          >
            {loading ? '...' : '🔄 Refresh'}
          </button>
        </div>
      </div>

      {/* Circular Ring Gauge & Metrics */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-xl">
        <div className="flex flex-col md:flex-row items-center justify-around gap-8">
          {/* SVG Circular Meter */}
          <div className="relative flex items-center justify-center">
            <svg className="w-52 h-52 -rotate-90 transform">
              {/* Background Track */}
              <circle
                cx="104"
                cy="104"
                r={radius}
                className="text-slate-800"
                strokeWidth="14"
                stroke="currentColor"
                fill="transparent"
              />
              {/* Progress Ring */}
              <circle
                cx="104"
                cy="104"
                r={radius}
                className={percentageUsed > 80 ? 'text-rose-500' : 'text-cyan-500'}
                strokeWidth="14"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                stroke="currentColor"
                fill="transparent"
                style={{ transition: 'stroke-dashoffset 0.8s ease' }}
              />
            </svg>

            {/* Inner Content */}
            <div className="absolute flex flex-col items-center justify-center text-center">
              <span className="text-2xl font-extrabold text-white tracking-tight">
                {spent.toFixed(2)} / {cap.toFixed(2)}
              </span>
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-widest mt-0.5">
                used (ε)
              </span>
            </div>
          </div>

          {/* Legend and Stats */}
          <div className="space-y-4 w-full max-w-sm">
            {/* Used */}
            <div className="flex items-center justify-between p-3.5 bg-slate-950/60 rounded-xl border border-slate-800">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-cyan-500" />
                <span className="text-xs font-semibold text-white">Used Budget</span>
              </div>
              <span className="text-xs font-mono font-bold text-cyan-400">
                {spent.toFixed(2)} ε ({percentageUsed.toFixed(1)}%)
              </span>
            </div>

            {/* Remaining */}
            <div className="flex items-center justify-between p-3.5 bg-slate-950/60 rounded-xl border border-slate-800">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-slate-600" />
                <span className="text-xs font-semibold text-white">Remaining Budget</span>
              </div>
              <span className="text-xs font-mono font-bold text-slate-300">
                {remaining.toFixed(2)} ε ({percentageRemaining.toFixed(1)}%)
              </span>
            </div>

            {/* Total */}
            <div className="flex items-center justify-between p-3.5 bg-slate-950/60 rounded-xl border border-slate-800">
              <div className="flex items-center gap-3">
                <span className="w-3 h-3 rounded-full bg-purple-500" />
                <span className="text-xs font-semibold text-white">Total Allocated Cap</span>
              </div>
              <span className="text-xs font-mono font-bold text-purple-300">
                {cap.toFixed(2)} ε
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Usage Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 border-b border-slate-800 pb-3">
          Recent Privacy Expenditure Ledger
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-mono">
              <tr>
                <th className="py-2.5 px-4">Time</th>
                <th className="py-2.5 px-4">Query Operation</th>
                <th className="py-2.5 px-4">Cost (ε)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-200">
              {displayUsage.length === 0 ? (
                <tr>
                  <td colSpan={3} className="py-6 text-center text-slate-500 font-mono">
                    No query releases executed yet for {selectedDatasetId}. Full budget allocation ({cap.toFixed(2)} ε) is available.
                  </td>
                </tr>
              ) : (
                displayUsage.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4 font-mono text-slate-400">{u.time}</td>
                    <td className="py-3 px-4 font-semibold text-white">{u.query}</td>
                    <td className="py-3 px-4 font-mono text-amber-400 font-bold">
                      {u.cost.toFixed(2)} ε
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

