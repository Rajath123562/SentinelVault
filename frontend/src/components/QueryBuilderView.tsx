import React, { useState, useEffect } from 'react';
import { DatasetMetadata, QueryPreviewResponse } from '../types/system';

interface QueryBuilderViewProps {
  datasets: DatasetMetadata[];
  selectedDatasetId: string;
  onSelectDatasetId: (id: string) => void;
  onRunQuery: (datasetId: string, field: string, value: string, epsilon: number) => Promise<void>;
  loadingRun: boolean;
  onPreviewQuery: (datasetId: string, field: string, value: string, epsilon: number) => Promise<QueryPreviewResponse | null>;
  preview: QueryPreviewResponse | null;
  error: string | null;
}

export const QueryBuilderView: React.FC<QueryBuilderViewProps> = ({
  datasets,
  selectedDatasetId,
  onSelectDatasetId,
  onRunQuery,
  loadingRun,
  onPreviewQuery,
  preview,
  error,
}) => {
  const currentDataset = datasets.find((d) => d.dataset_id === selectedDatasetId) || datasets[0];
  const fields = currentDataset?.approved_fields || currentDataset?.allowed_fields || {};
  const fieldKeys = Object.keys(fields);

  const [selectedField, setSelectedField] = useState<string>(fieldKeys[0] || 'diagnosis');
  const [selectedValue, setSelectedValue] = useState<string>(
    (fieldKeys[0] && fields[fieldKeys[0]]?.[0]) || 'Hypertension'
  );
  const [selectedEpsilon, setSelectedEpsilon] = useState<number>(0.5);
  const [groupBy, setGroupBy] = useState<string>('none');
  const [queryType, setQueryType] = useState<string>('COUNT');

  // Update selected field/value when dataset changes
  useEffect(() => {
    if (fieldKeys.length > 0 && !fieldKeys.includes(selectedField)) {
      const firstField = fieldKeys[0];
      setSelectedField(firstField);
      const firstVal = fields[firstField]?.[0] || '';
      setSelectedValue(firstVal);
    }
  }, [selectedDatasetId, fieldKeys, selectedField, fields]);

  // Handle field change
  const handleFieldChange = (newField: string) => {
    setSelectedField(newField);
    const availableVals = fields[newField] || [];
    setSelectedValue(availableVals[0] || '');
  };

  // Trigger preview on parameter adjustments
  useEffect(() => {
    if (selectedDatasetId && selectedField && selectedValue) {
      onPreviewQuery(selectedDatasetId, selectedField, selectedValue, selectedEpsilon);
    }
  }, [selectedDatasetId, selectedField, selectedValue, selectedEpsilon, onPreviewQuery]);

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    await onRunQuery(selectedDatasetId, selectedField, selectedValue, selectedEpsilon);
  };

  // Generate live SQL syntax string matching authoritative backend COUNT_DISTINCT execution
  const privacyUnit = currentDataset?.privacy_unit || (selectedDatasetId === 'health' ? 'patient_id' : 'customer_id');
  const tableName = selectedDatasetId === 'health' ? 'healthcare_vault' : 'financial_vault';
  const groupClause = groupBy !== 'none' ? `\nGROUP BY ${groupBy}` : '';
  const fallbackSql = `SELECT ${groupBy !== 'none' ? `${groupBy}, ` : ''}COUNT_DISTINCT(${privacyUnit}) AS noisy_count\nFROM ${tableName}\nWHERE ${selectedField} = '${selectedValue}'${groupClause};`;
  const generatedSql = preview?.logical_query ? `${preview.logical_query};` : fallbackSql;

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🔍</span>
            <h2 className="text-xl font-bold text-white tracking-tight">Build Your Query</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Construct an approved privacy-preserving statistical query. Raw rows never leave the secure boundary.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full text-xs font-mono bg-cyan-950 text-cyan-300 border border-cyan-700">
            Mechanism: Laplace (Δf = 1.0)
          </span>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-300 text-xs">
          <strong>Query Error:</strong> {error}
        </div>
      )}

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form: Query Parameters (7 cols) */}
        <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider border-b border-slate-800 pb-3 flex items-center gap-2">
            <span>⚙️</span> Query Specifications
          </h3>

          <form onSubmit={handleExecute} className="space-y-4 text-xs">
            {/* Dataset Selector */}
            <div>
              <label className="block text-slate-400 font-semibold mb-1.5">
                Target Dataset
              </label>
              <select
                value={selectedDatasetId}
                onChange={(e) => onSelectDatasetId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                {datasets.map((d) => (
                  <option key={d.dataset_id} value={d.dataset_id}>
                    {d.title || d.name || d.dataset_id} ({d.total_records} records)
                  </option>
                ))}
              </select>
            </div>

            {/* Query Type */}
            <div>
              <label className="block text-slate-400 font-semibold mb-1.5">
                Query Type
              </label>
              <select
                value={queryType}
                onChange={(e) => setQueryType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="COUNT">Aggregate (Count / Sum / Avg)</option>
              </select>
              <p className="text-[10px] text-slate-500 mt-1">
                Zero-trust policy restricts queries to approved aggregate operations. Arbitrary SQL is rejected.
              </p>
            </div>

            {/* Select Field */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-slate-400 font-semibold mb-1.5">
                  Select Field
                </label>
                <select
                  value={selectedField}
                  onChange={(e) => handleFieldChange(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                >
                  {fieldKeys.map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-400 font-semibold mb-1.5">
                  Filter Value
                </label>
                <select
                  value={selectedValue}
                  onChange={(e) => setSelectedValue(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
                >
                  {(fields[selectedField] || []).map((val) => (
                    <option key={val} value={val}>
                      {val}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Optional Group By */}
            <div>
              <label className="block text-slate-400 font-semibold mb-1.5">
                Group By (Optional)
              </label>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="none">None (Single Aggregate)</option>
                {fieldKeys
                  .filter((k) => k !== selectedField)
                  .map((k) => (
                    <option key={k} value={k}>
                      {k}
                    </option>
                  ))}
              </select>
            </div>

            {/* Privacy Budget Epsilon */}
            <div className="pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-slate-400 font-semibold">
                  Privacy Loss Parameter (Epsilon ε)
                </label>
                <span className="font-mono text-cyan-400 font-bold bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800">
                  ε = {selectedEpsilon.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0.10"
                max="1.00"
                step="0.05"
                value={selectedEpsilon}
                onChange={(e) => setSelectedEpsilon(parseFloat(e.target.value))}
                className="w-full accent-cyan-500 cursor-pointer"
              />
              <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
                <span>0.10 (High Privacy / More Noise)</span>
                <span>1.00 (High Accuracy / Less Noise)</span>
              </div>
            </div>
          </form>
        </div>

        {/* Right Column: Query Preview & Execution (5 cols) */}
        <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col justify-between space-y-4">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <span>💻</span> Query Preview
              </h3>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1">
                <span>✓</span> Query is valid
              </span>
            </div>

            {/* SQL Terminal Syntax Box */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-[11px] text-cyan-300 leading-relaxed shadow-inner overflow-x-auto">
              <div className="text-slate-500 select-none pb-1 mb-1 border-b border-slate-900 text-[10px]">
                -- Protected Sandbox Query
              </div>
              <pre className="whitespace-pre-wrap">{generatedSql}</pre>
            </div>

            {/* Verification Metadata */}
            <div className="mt-4 space-y-2.5 text-xs text-slate-400 bg-slate-950/50 p-3 rounded-lg border border-slate-800/80">
              <div className="flex justify-between">
                <span>Global Sensitivity (Δf):</span>
                <span className="font-mono text-white font-semibold">1.0</span>
              </div>
              <div className="flex justify-between">
                <span>Differential Noise Mechanism:</span>
                <span className="font-mono text-white font-semibold">Laplace(0, 1/ε)</span>
              </div>
              <div className="flex justify-between">
                <span>Estimated Privacy Cost:</span>
                <span className="font-mono text-amber-400 font-semibold">
                  {preview?.estimated_privacy_cost !== undefined
                    ? `${preview.estimated_privacy_cost.toFixed(2)} ε`
                    : `${selectedEpsilon.toFixed(2)} ε`}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Cache Reuse Detection:</span>
                <span className="font-mono text-emerald-400 font-semibold">
                  {preview?.is_cached_release_available ? 'Cache Hit (0.00 ε)' : 'Fresh Compute'}
                </span>
              </div>
            </div>
          </div>

          {/* Big Run Query Button */}
          <button
            onClick={handleExecute}
            disabled={loadingRun}
            className="w-full py-3.5 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 font-bold text-white text-sm transition shadow-lg shadow-cyan-950 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <span>{loadingRun ? 'Processing...' : '⚡ Run Query'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
