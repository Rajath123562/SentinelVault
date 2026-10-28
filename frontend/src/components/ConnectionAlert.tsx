import React from 'react';

interface ConnectionAlertProps {
  error: string;
  onRetry: () => void;
}

export const ConnectionAlert: React.FC<ConnectionAlertProps> = ({ error, onRetry }) => {
  return (
    <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-5 mb-8 backdrop-blur" role="alert">
      <div className="flex items-start gap-4">
        <div className="text-2xl mt-0.5">⚠️</div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-rose-300">Backend Communication Unavailable</h3>
          <p className="text-xs text-rose-200 mt-1 leading-relaxed">
            {error || 'Unable to establish HTTP connection with the HOTFIX FastAPI backend gateway.'}
          </p>
          <div className="mt-3 flex items-center gap-3">
            <button
              onClick={onRetry}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-900/60 text-rose-200 hover:bg-rose-900 border border-rose-700 transition"
            >
              Retry Connection
            </button>
            <span className="text-xs text-slate-400">
              Ensure FastAPI backend is running on <code className="text-cyan-400 font-mono">http://127.0.0.1:8000</code>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
