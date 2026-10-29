import React, { useState } from 'react';
import { DatasetMetadata } from '../types/system';

interface DatasetSelectionViewProps {
  datasets: DatasetMetadata[];
  selectedDatasetId: string;
  onSelectDataset: (datasetId: string) => void;
  onProceedToQuery: () => void;
}

export const DatasetSelectionView: React.FC<DatasetSelectionViewProps> = ({
  datasets,
  selectedDatasetId,
  onSelectDataset,
  onProceedToQuery,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredDatasets = datasets.filter((ds) => {
    const term = searchTerm.toLowerCase();
    const title = (ds.title || ds.name || ds.dataset_id).toLowerCase();
    const desc = (ds.description || '').toLowerCase();
    return title.includes(term) || desc.includes(term);
  });

  const handleSelect = (id: string) => {
    onSelectDataset(id);
    onProceedToQuery();
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">📁</span>
            <h2 className="text-xl font-bold text-white tracking-tight">Select Dataset</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Choose a dataset to analyze. All underlying records remain protected inside the zero-trust data vault.
          </p>
        </div>

        {/* Search input */}
        <div className="relative w-full sm:w-72">
          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 text-xs">
            🔍
          </span>
          <input
            type="text"
            placeholder="Search datasets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
          />
        </div>
      </div>

      {/* Dataset Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filteredDatasets.map((ds) => {
          const isSelected = ds.dataset_id === selectedDatasetId;
          const title = ds.title || ds.name || ds.dataset_id;
          const fields = ds.approved_fields || ds.allowed_fields || {};
          const fieldKeys = Object.keys(fields);

          return (
            <div
              key={ds.dataset_id}
              className={`bg-slate-900 border rounded-xl p-6 shadow-lg transition-all flex flex-col justify-between ${
                isSelected
                  ? 'border-cyan-500 ring-1 ring-cyan-500/50 shadow-cyan-950/50'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-cyan-950 border border-cyan-800 flex items-center justify-center text-xl">
                      {ds.dataset_id.includes('health') ? '🏥' : '🏦'}
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white leading-snug">{title}</h3>
                      <span className="text-[10px] text-cyan-400 font-mono">
                        {ds.dataset_id} • v{ds.version || '1.0'}
                      </span>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-700">
                      ACTIVE
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-400 line-clamp-2 mb-4">
                  {ds.description}
                </p>

                {/* Metadata Badges */}
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-300 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 mb-4">
                  <div>
                    <span className="text-slate-500 block text-[10px]">TOTAL RECORDS</span>
                    <span className="font-semibold text-white">{ds.total_records.toLocaleString()}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">PRIVACY UNIT</span>
                    <span className="font-semibold text-cyan-400 truncate block">{ds.privacy_unit}</span>
                  </div>
                </div>

                {/* Approved Fields Tags */}
                <div className="mb-4">
                  <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
                    Protected Query Fields
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {fieldKeys.map((k) => (
                      <span
                        key={k}
                        className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800/80 text-slate-300 border border-slate-700/60"
                      >
                        {k}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={() => handleSelect(ds.dataset_id)}
                className={`w-full py-2.5 px-4 rounded-lg font-semibold text-xs transition flex items-center justify-center gap-2 ${
                  isSelected
                    ? 'bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-950'
                    : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700'
                }`}
              >
                <span>{isSelected ? 'Proceed to Query' : 'Select Dataset'}</span>
                <span>→</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

