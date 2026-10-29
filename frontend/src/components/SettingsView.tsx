import React, { useState } from 'react';
import { UserSession, SystemStatusResponse } from '../types/system';

interface SettingsViewProps {
  session: UserSession;
  status: SystemStatusResponse | null;
  onLogout?: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ session, status, onLogout }) => {
  const [activeTab, setActiveTab] = useState<'profile' | 'security' | 'system'>('profile');

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <h2 className="text-xl font-bold text-white tracking-tight">Settings & Diagnostics</h2>
        <p className="text-xs text-slate-400 mt-1">
          Identity management, session credentials, and cryptographic release status.
        </p>

        {/* Tab Selector matching Screen 14 */}
        <div className="flex gap-2 border-b border-slate-800 mt-6 pt-2">
          {(['profile', 'security', 'system'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-3 px-4 text-xs font-semibold capitalize border-b-2 transition ${
                activeTab === tab
                  ? 'border-cyan-400 text-cyan-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              {tab === 'system' ? 'System Diagnostics' : tab}
            </button>
          ))}
        </div>
      </div>

      {/* Tab 1: Profile */}
      {activeTab === 'profile' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Identity Profile</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Authenticated Username</span>
              <span className="text-white font-bold text-sm">{session.username}</span>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Assigned Security Role</span>
              <span className="text-cyan-400 font-bold uppercase">{session.role}</span>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Session Expiration</span>
              <span className="text-slate-300">{new Date(session.expires_at).toLocaleString()}</span>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Bearer Token Hash</span>
              <span className="text-slate-400 select-all">{session.token.slice(0, 16)}...</span>
            </div>
          </div>
          {onLogout && (
            <div className="pt-3 flex justify-end border-t border-slate-800">
              <button
                onClick={onLogout}
                className="px-4 py-2 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-semibold transition"
              >
                Terminate Active Session
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Security */}
      {activeTab === 'security' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Security Controls & MFA</h3>
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-bold text-white">Multi-Factor Authentication (TOTP RFC 6238)</h4>
                <p className="text-slate-400 text-[11px]">Time-based one-time password verification for privileged logins.</p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-slate-800 text-slate-300">
                STANDARD SEEDED
              </span>
            </div>
            <div className="flex items-center justify-between border-t border-slate-800/80 pt-3">
              <div>
                <h4 className="font-bold text-white">5-Attempt Lockout Protection</h4>
                <p className="text-slate-400 text-[11px]">Accounts automatically lock for 15 minutes after 5 consecutive bad attempts.</p>
              </div>
              <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                ACTIVE
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: System Diagnostics */}
      {activeTab === 'system' && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Gateway Configuration & Diagnostics</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Project Name</span>
              <span className="text-white font-bold">{status?.project_name || 'SentinelVault'}</span>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Team Identity</span>
              <span className="text-cyan-400 font-bold">{status?.team_id || 'UG 59'}</span>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Fail-Closed Gates</span>
              <span className="text-emerald-400 font-bold">ENFORCED (Strict Mode)</span>
            </div>
            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 block text-[11px] mb-1">Accounting Arithmetic</span>
              <span className="text-amber-400 font-bold">Integer Micro-Epsilon (SQLite)</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

