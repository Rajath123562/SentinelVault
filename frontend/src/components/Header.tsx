import React from 'react';
import { ConnectionStatus } from '../types/system';

interface HeaderProps {
  connectionStatus: ConnectionStatus;
  teamId?: string;
  phase?: string;
}

export const Header: React.FC<HeaderProps> = ({
  connectionStatus,
  teamId = 'UG 59',
  phase = 'Phase 1',
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

        <div className="flex items-center gap-3">
          <span className="px-2.5 py-1 text-xs font-mono rounded bg-slate-800 text-cyan-400 border border-slate-700">
            {phase}
          </span>
          {getStatusBadge()}
        </div>
      </div>
    </header>
  );
};

