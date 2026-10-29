import React from 'react';
import { QueryRunResponse, PrivacyReceipt, ActiveScreen } from '../types/system';

interface QueryResultsViewProps {
  result: QueryRunResponse | null;
  onNavigate: (screen: ActiveScreen) => void;
  onViewReceipt: (receipt: PrivacyReceipt) => void;
  datasetName?: string;
  queryDescription?: string;
}

export const QueryResultsView: React.FC<QueryResultsViewProps> = ({
  result,
  onNavigate,
  onViewReceipt,
  datasetName = 'Healthcare Clinical Cohort',
  queryDescription = 'Count where condition matches',
}) => {
  if (!result) {
    return (
      <div className="max-w-4xl mx-auto bg-slate-900 border border-slate-800 rounded-xl p-10 text-center space-y-4 animate-in fade-in">
        <span className="text-4xl">📈</span>
        <h3 className="text-lg font-bold text-white">No Query Results to Display</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Execute a privacy-preserving query from the Query Builder to view differential privacy outputs and cryptographic release details.
        </p>
        <button
          onClick={() => onNavigate('query')}
          className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs transition shadow-md shadow-cyan-950"
        >
          Go to Query Builder →
        </button>
      </div>
    );
  }

  // Calculate theoretical 95% Laplace confidence interval bounds (± 2.99 / epsilon)
  const epsilon = result.epsilon_spent > 0 ? result.epsilon_spent : 0.5;
  const margin = Math.round((Math.log(20) / epsilon) * 10) / 10;
  const noisyVal = result.noisy_count;
  const lowerBound = Math.max(0, Math.round(noisyVal - margin));
  const upperBound = Math.round(noisyVal + margin);

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📈</span>
            <h2 className="text-xl font-bold text-white tracking-tight">Query Results</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Dataset: <span className="text-cyan-300 font-semibold">{datasetName}</span> • Query: <span className="text-slate-200 font-mono">{queryDescription}</span>. Differential privacy noise applied.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1.5 shadow-sm">
            <span>✓</span> Differential Privacy Applied
          </span>
          {result.is_cached && (
            <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
              Cached (0.00 ε)
            </span>
          )}
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Total Records Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
          <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            Total Records (Protected Estimate)
          </div>
          <div className="text-4xl font-extrabold text-white tracking-tight">
            {noisyVal.toLocaleString()}
          </div>
          <div className="mt-3 flex items-center gap-2 text-xs font-mono text-cyan-400">
            <span>± {margin}</span>
            <span className="text-slate-500">[{lowerBound.toLocaleString()} – {upperBound.toLocaleString()}] 95% CI</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Obtained via Laplace(0, { (1.0 / epsilon).toFixed(2) }) mechanism.
          </p>
        </div>

        {/* Privacy Budget Cost Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
          <div className="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">
            Privacy Budget Cost
          </div>
          <div className="text-4xl font-extrabold text-amber-400 tracking-tight">
            {result.epsilon_spent.toFixed(2)} ε
          </div>
          <div className="mt-3 text-xs text-slate-300 flex justify-between">
            <span>Remaining Budget:</span>
            <span className="font-mono text-white font-semibold">
              {result.remaining_budget.toFixed(2)} / 5.00 ε
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            Tracked in shared ACID budget ledger to prevent privacy reconstruction attacks.
          </p>
        </div>
      </div>

      {/* Breakdown Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
          Statistical Cohort Output
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border border-slate-800 rounded-lg overflow-hidden">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-mono">
              <tr>
                <th className="py-2.5 px-4">Partition / Dimension</th>
                <th className="py-2.5 px-4">Count (Noisy)</th>
                <th className="py-2.5 px-4">Confidence Interval (95%)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-200">
              <tr className="hover:bg-slate-800/40">
                <td className="py-3 px-4 font-semibold text-white">Matching Criteria Cohort</td>
                <td className="py-3 px-4 font-mono text-cyan-300 font-bold">{noisyVal.toLocaleString()}</td>
                <td className="py-3 px-4 font-mono text-slate-400">[{lowerBound} – {upperBound}]</td>
              </tr>
              <tr className="hover:bg-slate-800/40">
                <td className="py-3 px-4 font-semibold text-slate-400">Remaining Population Complement</td>
                <td className="py-3 px-4 font-mono text-slate-300">Protected</td>
                <td className="py-3 px-4 font-mono text-slate-500">[N/A — Not Requested]</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Protection Notice */}
        <div className="mt-4 flex items-center gap-2 text-xs text-slate-400 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
          <span>ℹ️</span>
          <span>
            Results are mathematically protected with differential privacy and cannot be linked back to individual respondents or account holders.
          </span>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex flex-wrap gap-3 pt-4 border-t border-slate-800">
          {result.receipt && (
            <button
              onClick={() => {
                onViewReceipt(result.receipt);
                onNavigate('receipt');
              }}
              className="px-4 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs transition shadow-md shadow-cyan-950 flex items-center gap-2"
            >
              <span>📜</span> View Privacy Receipt
            </button>
          )}

          <button
            onClick={() => onNavigate('audit')}
            className="px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 font-semibold text-slate-200 text-xs border border-slate-700 transition flex items-center gap-2"
          >
            <span>🛡️</span> View Audit Log
          </button>

          <button
            onClick={() => onNavigate('query')}
            className="px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 font-semibold text-slate-200 text-xs border border-slate-700 transition"
          >
            ← Back to Query Builder
          </button>
        </div>
      </div>
    </div>
  );
};
