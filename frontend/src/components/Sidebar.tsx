import React from 'react';
import { ActiveScreen, UserSession } from '../types/system';

interface SidebarProps {
  activeScreen: ActiveScreen;
  onNavigate: (screen: ActiveScreen) => void;
  session: UserSession | null;
  onLogout: () => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeScreen,
  onNavigate,
  session,
  onLogout,
  isOpenMobile,
  onCloseMobile,
}) => {
  const isPrivileged = session?.role === 'admin' || session?.role === 'data_steward';

  const navItems: { id: ActiveScreen; label: string; icon: string; adminOnly?: boolean }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'datasets', label: 'Select Dataset', icon: '📁' },
    { id: 'query', label: 'Query Builder', icon: '🔍' },
    { id: 'results', label: 'Query Results', icon: '📈' },
    { id: 'budget', label: 'Privacy Budget', icon: '⚖️' },
    { id: 'receipt', label: 'Privacy Receipts', icon: '📜' },
    { id: 'audit', label: 'Audit Logs', icon: '🛡️' },
    { id: 'security', label: 'Security Events', icon: '🚨' },
    { id: 'users', label: 'User Management', icon: '👥', adminOnly: true },
    { id: 'settings', label: 'Settings', icon: '⚙️' },
    { id: 'about', label: 'About & Security', icon: 'ℹ️' },
  ];

  const handleItemClick = (screen: ActiveScreen) => {
    onNavigate(screen);
    onCloseMobile();
  };

  return (
    <>
      {/* Mobile backdrop */}
      {isOpenMobile && (
        <div
          className="fixed inset-0 bg-black/70 z-40 lg:hidden backdrop-blur-sm"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`fixed lg:static top-0 bottom-0 left-0 z-50 w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between transition-transform duration-300 ease-in-out ${
          isOpenMobile ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div>
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center text-xl shadow-md shadow-cyan-950">
                🛡️
              </div>
              <div>
                <h1 className="text-base font-extrabold text-white tracking-tight">SentinelVault</h1>
                <p className="text-[10px] text-cyan-400 font-semibold tracking-wide uppercase">
                  Analyze Data. Don't Expose It.
                </p>
              </div>
            </div>
            {/* Close button on mobile */}
            <button
              onClick={onCloseMobile}
              className="lg:hidden text-slate-400 hover:text-white p-1 rounded-lg"
              title="Close menu"
            >
              ✕
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1">
            {navItems.map((item) => {
              const isActive = activeScreen === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleItemClick(item.id)}
                  className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-lg text-xs font-semibold transition group ${
                    isActive
                      ? 'bg-cyan-950/90 text-cyan-300 border border-cyan-500/40 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-base">{item.icon}</span>
                    <span>{item.label}</span>
                  </div>
                  {item.adminOnly && (
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-mono font-bold uppercase tracking-wider ${
                        isPrivileged ? 'bg-purple-950 text-purple-300 border border-purple-800' : 'bg-slate-800 text-slate-500'
                      }`}
                    >
                      Admin
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User Session & Sign Out Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/70">
          {session ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 overflow-hidden">
                  <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-cyan-400">
                    {session.username.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="truncate">
                    <p className="text-xs font-bold text-white truncate">{session.username}</p>
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 inline-block uppercase">
                      {session.role}
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-slate-800 hover:bg-rose-950/80 hover:text-rose-300 text-slate-300 text-xs font-semibold border border-slate-700 transition"
              >
                <span>🚪</span>
                <span>Sign Out</span>
              </button>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-xs text-slate-400 mb-2">Zero-Trust Gateway</p>
              <button
                onClick={() => onNavigate('dashboard')}
                className="w-full py-2 px-3 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition"
              >
                Sign In
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};

