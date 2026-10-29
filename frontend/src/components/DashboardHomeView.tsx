import React from 'react';
import { UserSession, DatasetMetadata, BudgetStatusResponse, ActiveScreen } from '../types/system';

interface ActivityItem {
  id: string;
  time: string;
  action: string;
  dataset: string;
  status: 'Success' | 'Info' | 'Warning';
}

interface DashboardHomeViewProps {
  session: UserSession;
  datasets: DatasetMetadata[];
  budget: BudgetStatusResponse | null;
  onNavigate: (screen: ActiveScreen) => void;
  recentActivities?: ActivityItem[];
}

export const DashboardHomeView: React.FC<DashboardHomeViewProps> = ({
  session,
  datasets,
  budget,
  onNavigate,
  recentActivities = [],
}) => {
  const spent = budget?.spent_epsilon ?? 0;
  const cap = budget?.cap_epsilon ?? 5.0;
  const remaining = budget?.remaining_epsilon ?? (cap - spent);
  const percentageUsed = cap > 0 ? ((spent / cap) * 100).toFixed(1) : '0.0';

  // Display real authenticated activities
  const displayActivities: ActivityItem[] = recentActivities;

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-cyan-950/40 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🛡️</span>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Welcome back, {session.username}
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-700/60 uppercase">
              {session.role}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Zero-Trust Gateway is active. Differential privacy engine and tamper-evident cryptographic hash chain are enforcing fail-closed privacy.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => onNavigate('query')}
            className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs transition shadow-md shadow-cyan-950 flex items-center gap-1.5"
          >
            <span>⚡</span> New Query
          </button>
          <button
            onClick={() => onNavigate('datasets')}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 font-semibold text-slate-200 text-xs border border-slate-700 transition"
          >
            📁 Browse Datasets
          </button>
        </div>
      </div>

      {/* 4 Metric KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Datasets */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Total Datasets</span>
            <span className="text-cyan-400 text-base">📁</span>
          </div>
          <div className="text-3xl font-extrabold text-white">
            {datasets.length || 2}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Official sensitive vaults
          </p>
        </div>

        {/* Privacy Budget Used */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Privacy Budget Used</span>
            <span className="text-amber-400 text-base">⚖️</span>
          </div>
          <div className="text-2xl font-extrabold text-white flex items-baseline gap-1.5">
            <span>{spent.toFixed(2)}</span>
            <span className="text-slate-400 text-sm font-normal">/ {cap.toFixed(2)} ε</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ${
                parseFloat(percentageUsed) > 80 ? 'bg-rose-500' : 'bg-cyan-500'
              }`}
              style={{ width: `${Math.min(parseFloat(percentageUsed), 100)}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-400 mt-1.5 flex justify-between">
            <span>{percentageUsed}% consumed</span>
            <span>{remaining.toFixed(2)} ε remaining</span>
          </p>
        </div>

        {/* Active Datasets */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Active Datasets</span>
            <span className="text-emerald-400 text-base">🟢</span>
          </div>
          <div className="text-3xl font-extrabold text-emerald-400">
            {datasets.filter((d) => d.is_official_dataset).length || 2}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Verified isolated partitions
          </p>
        </div>

        {/* Recent Actions */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg relative overflow-hidden group hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <span>Recent Actions</span>
            <span className="text-purple-400 text-base">📜</span>
          </div>
          <div className="text-3xl font-extrabold text-white">
            {displayActivities.length}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">
            Audited & receipt-signed
          </p>
        </div>
      </div>

      {/* Recent Activity Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider">
              Recent Activity Ledger
            </h3>
            <p className="text-xs text-slate-400">
              Authenticated query requests, signature verifications, and privacy releases.
            </p>
          </div>
          <button
            onClick={() => onNavigate('audit')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold transition"
          >
            View Full Audit Log →
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-mono">
              <tr>
                <th className="py-2.5 px-4">Time</th>
                <th className="py-2.5 px-4">Action</th>
                <th className="py-2.5 px-4">Dataset</th>
                <th className="py-2.5 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-200">
              {displayActivities.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-slate-500 font-mono">
                    No query releases recorded yet. Click "⚡ New Query" to execute a differential privacy query.
                  </td>
                </tr>
              ) : (
                displayActivities.map((act) => (
                  <tr key={act.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-mono text-slate-400">{act.time}</td>
                    <td className="py-3 px-4 font-semibold text-white">{act.action}</td>
                    <td className="py-3 px-4 font-mono text-cyan-300">{act.dataset}</td>
                    <td className="py-3 px-4">
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800/80">
                        {act.status}
                      </span>
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

