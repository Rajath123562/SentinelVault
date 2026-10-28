import React from 'react';
import { ConnectionStatus, UserSession } from '../types/system';

interface HeaderProps {
  connectionStatus: ConnectionStatus;
  teamId?: string;
  phase?: string;
  session?: UserSession | null;
  onLogout?: () => void;
  activeTab?: 'analytics' | 'receipt' | 'audit' | 'architecture';
  onSelectTab?: (tab: 'analytics' | 'receipt' | 'audit' | 'architecture') => void;
}

export const Header: React.FC<HeaderProps> = ({
  connectionStatus,
  teamId = 'UG 59',
  phase = 'Phase 1',
  session,
  onLogout,
  activeTab = 'analytics',
  onSelectTab,
}) => {
  const getStatusBadge = () => {
    switch (connectionStatus) {
      case 'connected':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            Backend Connected
          </span>
        );
      case 'connecting':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            Connecting...
          </span>
        );
      case 'disconnected':
      case 'error':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-950 text-rose-400 border border-rose-800">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
            Backend Offline
          </span>
        );
    }
  };

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 py-4">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-2xl">🛡️</span>
            <h1 className="text-xl font-bold tracking-tight text-white">
              HOTFIX <span className="text-slate-400 font-normal">| Privacy-by-Design Analytics Gateway</span>
            </h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Track: Privacy by Design — Unlock Data Without Exposing It • Team {teamId}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {session && (
            <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
              <span className="text-slate-400">User:</span>
              <span className="font-mono text-cyan-300 font-semibold">{session.username}</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-mono font-bold bg-slate-800 text-purple-300">
                {session.role}
              </span>
              {onLogout && (
                <button
                  onClick={onLogout}
                  className="ml-2 text-slate-400 hover:text-rose-400 transition"
                  title="Sign out"
                >
                  🚪
                </button>
              )}
            </div>
          )}

          <span className="px-2.5 py-1 text-xs font-mono rounded bg-slate-800 text-cyan-400 border border-slate-700">
            {phase}
          </span>
          {getStatusBadge()}
        </div>
      </div>

      {/* Navigation tabs when authenticated */}
      {session && onSelectTab && (
        <div className="max-w-6xl mx-auto mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap gap-2">
          <button
            onClick={() => onSelectTab('analytics')}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold transition border ${
              activeTab === 'analytics'
                ? 'bg-cyan-950 border-cyan-500 text-cyan-300'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            📊 Analytics Dashboard
          </button>

          <button
            onClick={() => onSelectTab('receipt')}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold transition border ${
              activeTab === 'receipt'
                ? 'bg-cyan-950 border-cyan-500 text-cyan-300'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            📜 Privacy Receipts
          </button>

          <button
            onClick={() => onSelectTab('audit')}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold transition border ${
              activeTab === 'audit'
                ? 'bg-cyan-950 border-cyan-500 text-cyan-300'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            🛡️ Cryptographic Audit & Utility
          </button>

          <button
            onClick={() => onSelectTab('architecture')}
            className={`py-1.5 px-3 rounded-lg text-xs font-semibold transition border ${
              activeTab === 'architecture'
                ? 'bg-cyan-950 border-cyan-500 text-cyan-300'
                : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
          >
            ⚙️ System Architecture
          </button>
        </div>
      )}
    </header>
  );
};


