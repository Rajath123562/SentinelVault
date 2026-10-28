import React from 'react';
import { CapabilityStatus } from '../types/system';

interface CapabilityMatrixProps {
  capabilities: CapabilityStatus[];
}

export const CapabilityMatrix: React.FC<CapabilityMatrixProps> = ({ capabilities }) => {
  const getStatusBadge = (status: CapabilityStatus['status']) => {
    switch (status) {
      case 'IMPLEMENTED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
            ✓ IMPLEMENTED
          </span>
        );
      case 'PLANNED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            ⏳ PLANNED
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-rose-950 text-rose-400 border border-rose-800">
            ⛔ BLOCKED
          </span>
        );
      case 'NOT_CONFIGURED':
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
            ⚠️ NOT CONFIGURED
          </span>
        );
    }
  };

  return (
    <section className="mt-8">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-semibold text-white">Product Capabilities & Phase Traceability</h3>
          <p className="text-xs text-slate-400">
            Transparently distinguishes implemented Phase 1 deliverables from planned future modules.
          </p>
        </div>
        <div className="text-xs text-slate-400 font-mono">
          Total Capabilities: {capabilities.length}
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900/40">
        <table className="w-full text-left text-sm text-slate-300">
          <thead className="bg-slate-950/80 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium">Capability ID</th>
              <th scope="col" className="px-4 py-3 font-medium">Capability Name</th>
              <th scope="col" className="px-4 py-3 font-medium">Target Phase</th>
              <th scope="col" className="px-4 py-3 font-medium">Status</th>
              <th scope="col" className="px-4 py-3 font-medium">Scope Description</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {capabilities.map((cap) => (
              <tr key={cap.id} className="hover:bg-slate-800/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-cyan-400 whitespace-nowrap">
                  {cap.id}
                </td>
                <td className="px-4 py-3 font-medium text-white whitespace-nowrap">
                  {cap.name}
                </td>
                <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                    {cap.phase}
                  </span>
                </td>
                <td className="px-4 py-3 whitespace-nowrap">
                  {getStatusBadge(cap.status)}
                </td>
                <td className="px-4 py-3 text-xs text-slate-400 max-w-md">
                  {cap.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
};

