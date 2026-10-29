import React from 'react';
import { ConnectionStatus, UserSession, ActiveScreen } from '../types/system';

interface TopBarProps {
  connectionStatus: ConnectionStatus;
  session: UserSession | null;
  activeScreen: ActiveScreen;
  onOpenMobileMenu: () => void;
  remainingBudget?: number;
}

export const TopBar: React.FC<TopBarProps> = ({
  connectionStatus,
  session,
  activeScreen,
  onOpenMobileMenu,
  remainingBudget = 5.0,
}) => {
  const getScreenTitle = (screen: ActiveScreen): { title: string; subtitle: string } => {
    switch (screen) {
      case 'dashboard':
        return { title: 'Dashboard', subtitle: 'Gateway Overview & Analytical Health' };
      case 'datasets':
        return { title: 'Dataset Selection', subtitle: 'Private Data Vault • Approved Fixtures' };
      case 'query':
        return { title: 'Query Builder', subtitle: 'Restricted Grammar • Bounded Sensitivity Δf = 1.0' };
      case 'results':
        return { title: 'Query Results', subtitle: 'Differentially Private Analytical Release' };
      case 'budget':
        return { title: 'Privacy Budget', subtitle: 'Shared ε-Ledger • Micro-Epsilon Precision' };
      case 'receipt':
        return { title: 'Privacy Receipt', subtitle: 'Verifiable Cryptographic Proof (Ed25519)' };
      case 'audit':
        return { title: 'Audit Logs', subtitle: 'Immutable SHA-256 Hash Chained Ledger' };
      case 'security':
        return { title: 'Security Events & Alerts', subtitle: 'Authoritative SIEM Audit Trail' };
      case 'users':
        return { title: 'User Management', subtitle: 'Zero-Trust RBAC & Account Lockout Control' };
      case 'settings':
        return { title: 'Settings & Diagnostics', subtitle: 'Gateway Configuration & Security Health' };
      case 'about':
        return { title: 'About SentinelVault', subtitle: 'Architecture & Track 4 Privacy Commitments' };
      case '404':
      default:
        return { title: 'Page Not Found', subtitle: 'The requested resource was not found' };
    }
  };

  const { title, subtitle } = getScreenTitle(activeScreen);

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md px-6 py-4 sticky top-0 z-30">
      <div className="flex items-center justify-between gap-4">
        {/* Left: Hamburger & Breadcrumb */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenMobileMenu}
            className="lg:hidden p-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-white"
            title="Open navigation"
          >
            ☰
          </button>
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight leading-snug">{title}</h2>
            <p className="text-xs text-slate-400 font-medium hidden sm:block">{subtitle}</p>
          </div>
        </div>

        {/* Right: Status Pills & Identity */}
        <div className="flex items-center gap-3">
          {session && (
            <div className="hidden md:flex items-center gap-2 px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-xs font-mono">
              <span className="text-slate-400">Budget:</span>
              <span className={`font-bold ${remainingBudget > 2.0 ? 'text-cyan-400' : 'text-amber-400'}`}>
                {remainingBudget.toFixed(2)} ε
              </span>
            </div>
          )}

          {/* Connection badge */}
          {connectionStatus === 'connected' ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="hidden sm:inline">Gateway</span> Online
            </span>
          ) : connectionStatus === 'connecting' ? (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950 text-amber-400 border border-amber-800">
              <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse"></span>
              Connecting...
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-950 text-rose-400 border border-rose-800">
              <span className="w-2 h-2 rounded-full bg-rose-500"></span>
              Offline
            </span>
          )}

          {/* Team Tag */}
          <span className="hidden lg:inline-block px-2.5 py-1 text-xs font-mono font-bold rounded bg-slate-800 text-cyan-300 border border-slate-700">
            Team UG 59
          </span>
        </div>
      </div>
    </header>
  );
};

