import React from 'react';
import { SystemStatusResponse } from '../types/system';

interface StatusBannerProps {
  status: SystemStatusResponse | null;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({ status }) => {
  return (
    <section className="mb-8">
      {/* Primary Fail-Closed Mission Status Banner */}
      <div className="rounded-xl border border-amber-500/40 bg-amber-950/20 p-5 backdrop-blur">
        <div className="flex items-start gap-4">
          <div className="text-2xl mt-0.5">🔒</div>
          <div className="flex-1">
            <h2 className="text-base font-semibold text-amber-300">
              Foundation ready — privacy releases disabled until the required privacy controls are implemented and configured.
            </h2>
            <p className="text-sm text-slate-300 mt-1 leading-relaxed">
              {status?.release_disabled_reason ||
                'Phase 1 establishes verified software architecture, configuration boundaries, and API contracts. No analytical release path is open until Phase 3 differential privacy mechanisms and official accounting are validated.'}
            </p>
          </div>
        </div>
      </div>

      {/* Grid of Key Diagnostic Indicators */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Application Process</div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-emerald-400">
              {status ? status.application_health : 'OFFLINE'}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
              Initialized
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-1">FastAPI process alive & validated</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Configuration</div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-emerald-400">
              {status?.configuration_valid ? 'VALIDATED' : 'UNKNOWN'}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              app.yaml
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-1">Environment & schema checks passed</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Privacy Release Gate</div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-rose-400">
              {status?.privacy_releases_enabled ? 'ENABLED' : 'DISABLED'}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
              Fail Closed
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-1">Strictly blocked until Phase 3 DP engine</div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4">
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">Accounting Spec</div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-amber-400">
              {status ? status.official_spec_status : 'NOT CONFIGURED'}
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
              spec.yaml
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-1">Awaiting official Track 4 specification</div>
        </div>
      </div>
    </section>
  );
};

