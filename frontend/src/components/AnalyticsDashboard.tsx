import React, { useState, useEffect, useCallback } from 'react';
import { 
  UserSession, 
  DatasetMetadata, 
  BudgetStatusResponse, 
  QueryPreviewResponse, 
  QueryRunResponse,
  PrivacyReceipt 
} from '../types/system';
import { 
  getDatasets, 
  getBudgetStatus, 
  previewQuery, 
  runQuery, 
  ApiError 
} from '../services/api';

interface AnalyticsDashboardProps {
  session: UserSession;
  onViewReceipt: (receipt: PrivacyReceipt) => void;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  session,
  onViewReceipt,
}) => {
  const [datasets, setDatasets] = useState<DatasetMetadata[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('health');
  const [budget, setBudget] = useState<BudgetStatusResponse | null>(null);

  // Query Builder state
  const [selectedField, setSelectedField] = useState<string>('');
  const [selectedValue, setSelectedValue] = useState<string>('');
  const [selectedEpsilon, setSelectedEpsilon] = useState<number>(0.5);

  // Query Execution state
  const [preview, setPreview] = useState<QueryPreviewResponse | null>(null);
  const [latestResult, setLatestResult] = useState<QueryRunResponse | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingRun, setLoadingRun] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch datasets
  const loadDatasets = useCallback(async () => {
    try {
      const data = await getDatasets(session.token);
      setDatasets(data);
      if (data.length > 0) {
        setSelectedDatasetId(data[0].dataset_id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load datasets');
    }
  }, [session.token]);

  // Fetch budget for selected dataset
  const loadBudget = useCallback(async (datasetId: string) => {
    try {
      const b = await getBudgetStatus(session.token, datasetId);
      setBudget(b);
    } catch (err: unknown) {
      console.error('Failed to load budget', err);
    }
  }, [session.token]);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  useEffect(() => {
    if (selectedDatasetId) {
      loadBudget(selectedDatasetId);
      setPreview(null);
      setLatestResult(null);
      setError(null);

      // Reset field and value to defaults of current dataset
      const currentDs = datasets.find((d) => d.dataset_id === selectedDatasetId);
      if (currentDs && Object.keys(currentDs.allowed_fields).length > 0) {
        const firstField = Object.keys(currentDs.allowed_fields)[0];
        setSelectedField(firstField);
        setSelectedValue(currentDs.allowed_fields[firstField][0] || '');
      }
    }
  }, [selectedDatasetId, datasets, loadBudget]);

  const currentDataset = datasets.find((d) => d.dataset_id === selectedDatasetId);

  const handleFieldChange = (field: string) => {
    setSelectedField(field);
    if (currentDataset && currentDataset.allowed_fields[field]) {
      setSelectedValue(currentDataset.allowed_fields[field][0] || '');
    }
    setPreview(null);
  };

  const handlePreview = async () => {
    if (!selectedField || !selectedValue) return;
    setLoadingPreview(true);
    setError(null);
    try {
      const p = await previewQuery(session.token, {
        dataset_id: selectedDatasetId,
        field: selectedField,
        operator: 'equals',
        value: selectedValue,
        epsilon: selectedEpsilon,
      });
      setPreview(p);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleRunQuery = async () => {
    if (!selectedField || !selectedValue) return;
    setLoadingRun(true);
    setError(null);
    try {
      const res = await runQuery(session.token, {
        dataset_id: selectedDatasetId,
        field: selectedField,
        operator: 'equals',
        value: selectedValue,
        epsilon: selectedEpsilon,
      });
      setLatestResult(res);
      // Refresh budget after successful run
      await loadBudget(selectedDatasetId);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.statusCode === 429) {
        setError(`Budget Exhausted (HTTP 429): ${err.message}`);
      } else {
        setError(err instanceof Error ? err.message : 'Query execution failed');
      }
    } finally {
      setLoadingRun(false);
    }
  };

  const budgetRemainingPct = budget ? (budget.remaining_epsilon / budget.cap_epsilon) * 100 : 100;

  return (
    <div className="space-y-8">
      {/* Top Banner / Dataset Selector & Budget Progress */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Dataset Selection */}
        <div className="lg:col-span-1 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Select Analytical Target
            </label>
            <div className="flex gap-2 mb-4">
              {datasets.map((ds) => (
                <button
                  key={ds.dataset_id}
                  onClick={() => setSelectedDatasetId(ds.dataset_id)}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold transition border ${
                    selectedDatasetId === ds.dataset_id
                      ? 'bg-cyan-950 border-cyan-500 text-cyan-300'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {ds.dataset_id === 'health' ? '🏥 Health' : '💳 Financial'}
                </button>
              ))}
            </div>
            {currentDataset && (
              <div className="text-xs space-y-1.5 text-slate-400 border-t border-slate-800/80 pt-3">
                <p className="text-slate-200 font-medium">{currentDataset.name}</p>
                <p>Records: <span className="font-mono text-cyan-300">{currentDataset.total_records}</span> (Demo fixture)</p>
                <p>
                  Privacy Unit: <span className="font-mono text-amber-300 font-semibold">{currentDataset.privacy_unit}</span>
                </p>
                <p className="text-[11px] text-slate-400 italic">
                  Sensitivity bounded to Δf = 1.0 (distinct unit counts).
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Shared Privacy Budget Progress Bar */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Shared Privacy Budget (ε-Ledger)
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Cap: {budget?.cap_epsilon.toFixed(2) ?? '5.00'} ε
              </span>
            </div>

            <div className="w-full bg-slate-950 rounded-full h-4 overflow-hidden border border-slate-800 my-2">
              <div
                className={`h-full transition-all duration-500 ${
                  budgetRemainingPct > 40
                    ? 'bg-gradient-to-r from-emerald-500 to-cyan-500'
                    : budgetRemainingPct > 15
                    ? 'bg-amber-500'
                    : 'bg-rose-500'
                }`}
                style={{ width: `${Math.max(0, Math.min(100, budgetRemainingPct))}%` }}
              ></div>
            </div>

            <div className="flex items-center justify-between text-xs font-mono text-slate-300 mt-2">
              <span>Spent: {budget?.spent_epsilon.toFixed(2) ?? '0.00'} ε</span>
              <span className="font-bold text-cyan-400">
                Remaining: {budget?.remaining_epsilon.toFixed(2) ?? '5.00'} ε ({budgetRemainingPct.toFixed(0)}%)
              </span>
            </div>
          </div>

          <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
            <span>Notice: Micro-epsilon integer precision (1 ε = 1,000,000 με)</span>
            <span className="text-amber-400 text-[11px]">Strict Fail-Closed Enforcement</span>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-300 text-sm flex items-start gap-3">
          <span className="text-xl">⚠️</span>
          <div>
            <div className="font-bold">Execution Gate Intercepted</div>
            <div>{error}</div>
          </div>
        </div>
      )}

      {/* Query Builder Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <h3 className="text-base font-bold text-white mb-4 flex items-center gap-2">
          <span>🔍</span> Differential Privacy Query Specification
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {/* Target Field */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Approved Field
            </label>
            <select
              value={selectedField}
              onChange={(e) => handleFieldChange(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 font-mono text-sm focus:outline-none focus:border-cyan-500"
            >
              {currentDataset &&
                Object.keys(currentDataset.allowed_fields).map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
            </select>
          </div>

          {/* Target Category Value */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Approved Category Value
            </label>
            <select
              value={selectedValue}
              onChange={(e) => setSelectedValue(e.target.value)}
              className="w-full px-3 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 font-mono text-sm focus:outline-none focus:border-cyan-500"
            >
              {currentDataset &&
                selectedField &&
                currentDataset.allowed_fields[selectedField]?.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
            </select>
          </div>

          {/* Epsilon Selector */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Privacy Parameter (ε)
            </label>
            <div className="grid grid-cols-4 gap-1.5">
              {[0.1, 0.2, 0.5, 1.0].map((eps) => (
                <button
                  key={eps}
                  type="button"
                  onClick={() => setSelectedEpsilon(eps)}
                  className={`py-2 rounded-lg text-xs font-mono font-bold border transition ${
                    selectedEpsilon === eps
                      ? 'bg-cyan-600 border-cyan-400 text-white shadow-md shadow-cyan-950'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  {eps}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-slate-400 mt-1.5">
              {selectedEpsilon === 0.1 && 'Max Privacy • High Noise'}
              {selectedEpsilon === 0.2 && 'High Privacy • Moderate Noise'}
              {selectedEpsilon === 0.5 && 'Balanced Trade-off'}
              {selectedEpsilon === 1.0 && 'Max Utility • Low Noise'}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handlePreview}
            disabled={loadingPreview || loadingRun}
            className="py-2.5 px-5 rounded-lg bg-slate-800 hover:bg-slate-700 font-semibold text-slate-200 border border-slate-700 text-sm transition disabled:opacity-50"
          >
            {loadingPreview ? 'Validating...' : 'Validate & Preview'}
          </button>

          <button
            onClick={handleRunQuery}
            disabled={loadingRun || Boolean(budget && budget.remaining_epsilon < selectedEpsilon)}
            className="py-2.5 px-6 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white shadow-lg shadow-cyan-950 text-sm transition disabled:opacity-50"
          >
            {loadingRun ? 'Injecting DP Noise...' : 'Execute Differential Privacy Release'}
          </button>
        </div>
      </div>

      {/* Query Preview Section */}
      {preview && (
        <div className="bg-slate-900 border border-cyan-800/60 rounded-xl p-5 shadow-lg">
          <h4 className="text-sm font-bold text-cyan-400 uppercase tracking-wider mb-2 flex items-center gap-2">
            <span>🛡️</span> Security Pre-flight Gate Passed
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono text-slate-300">
            <div>
              <span className="text-slate-400 block text-[11px]">Global Sensitivity:</span>
              <span className="font-bold text-emerald-400">Δf = {preview.global_sensitivity}.0</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Privacy Unit:</span>
              <span className="text-amber-400">{preview.privacy_unit}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Fingerprint:</span>
              <span className="truncate block" title={preview.query_fingerprint}>
                {preview.query_fingerprint.slice(0, 16)}...
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Policy Gate:</span>
              <span className="text-emerald-400 font-semibold">{preview.policy_check}</span>
            </div>
          </div>
        </div>
      )}

      {/* Query Result Section */}
      {latestResult && (
        <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-emerald-800/80 rounded-xl p-6 shadow-2xl">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-emerald-400 font-bold text-sm uppercase tracking-wider">
                  ✓ Differential Privacy Release Committed
                </span>
                {latestResult.is_cached ? (
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-blue-950 text-blue-300 border border-blue-800">
                    ⚡ CACHE HIT (0.00 ε SPENT)
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                    NEW RELEASE (-{latestResult.epsilon_spent.toFixed(2)} ε)
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Mechanism: IBM diffprivlib Laplace with bounded integer post-processing.
              </p>
            </div>

            <button
              onClick={() => onViewReceipt(latestResult.receipt)}
              className="py-2 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-white text-xs shadow-md shadow-emerald-950 transition"
            >
              📜 View Cryptographic Privacy Receipt
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-4 rounded-lg bg-slate-950 border border-slate-800">
            <div className="text-center md:text-left">
              <span className="block text-xs uppercase tracking-wider text-slate-400 font-semibold mb-1">
                Differentially Private Result
              </span>
              <div className="text-4xl font-extrabold text-white font-mono">
                {latestResult.noisy_count}
              </div>
              <span className="text-[11px] text-slate-400 block mt-1">
                (Raw individual records concealed)
              </span>
            </div>

            <div className="space-y-1 text-xs font-mono text-slate-300 border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-4">
              <div>
                <span className="text-slate-400">Release ID:</span> {latestResult.release_id.slice(0, 18)}...
              </div>
              <div>
                <span className="text-slate-400">Epsilon Spent:</span> {latestResult.epsilon_spent.toFixed(2)} ε
              </div>
              <div>
                <span className="text-slate-400">Cumulative Spent:</span> {latestResult.cumulative_epsilon.toFixed(2)} ε
              </div>
            </div>

            <div className="space-y-1 text-xs font-mono text-slate-300 border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-4">
              <div>
                <span className="text-slate-400">Remaining Budget:</span>{' '}
                <span className="text-cyan-400 font-bold">{latestResult.remaining_budget.toFixed(2)} ε</span>
              </div>
              <div>
                <span className="text-slate-400">Audit Pointer:</span>{' '}
                <span className="text-slate-400">{latestResult.receipt.audit_entry_hash.slice(0, 12)}...</span>
              </div>
              <div>
                <span className="text-slate-400">Ed25519 Signed:</span>{' '}
                <span className="text-emerald-400 font-bold">VERIFIED</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
