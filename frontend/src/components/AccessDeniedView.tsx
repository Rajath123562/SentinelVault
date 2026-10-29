import React from 'react';

interface AccessDeniedViewProps {
  resourceName?: string;
  requiredPermission?: string;
  onGoBack: () => void;
}

export const AccessDeniedView: React.FC<AccessDeniedViewProps> = ({
  resourceName = 'this restricted resource',
  requiredPermission = 'Privileged Administrative Access',
  onGoBack,
}) => {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 max-w-lg w-full text-center space-y-6 shadow-2xl">
        <div className="w-20 h-20 rounded-2xl bg-rose-950/70 border border-rose-800 flex items-center justify-center text-4xl mx-auto shadow-lg shadow-rose-950">
          🛡️
        </div>

        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Access Denied</h2>
          <p className="text-xs text-rose-400 font-mono font-semibold uppercase mt-1">
            Zero-Trust Policy Violation Intercepted
          </p>
          <p className="text-xs text-slate-400 mt-3 leading-relaxed">
            You do not have permission to access {resourceName}.
          </p>
          <div className="mt-4 p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-400">
            Required Permission: <span className="text-amber-400 font-semibold">{requiredPermission}</span>
          </div>
        </div>

        <button
          onClick={onGoBack}
          className="py-2.5 px-6 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs transition shadow-md shadow-cyan-950"
        >
          ← Go Back to Dashboard
        </button>
      </div>
    </div>
  );
};

