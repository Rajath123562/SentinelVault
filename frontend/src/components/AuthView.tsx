import React, { useState } from 'react';
import { UserSession } from '../types/system';
import { loginUser, ApiError } from '../services/api';

interface AuthViewProps {
  onLoginSuccess: (session: UserSession) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('analyst_user');
  const [password, setPassword] = useState('AnalystPass2026!');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lockoutWarning, setLockoutWarning] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setLockoutWarning(null);

    try {
      const session = await loginUser(username, password);
      onLoginSuccess(session);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.statusCode === 429 || err.message.toLowerCase().includes('locked')) {
          setLockoutWarning('Account is temporarily locked due to 5 consecutive failed login attempts.');
        } else {
          setError(err.message);
        }
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Login failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const setDemoCredentials = (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setError(null);
    setLockoutWarning(null);
  };

  return (
    <div className="w-full max-w-5xl mx-auto my-auto bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden grid grid-cols-1 md:grid-cols-2 backdrop-blur-md">
      {/* Left Column: Brand Hero & Cyber Mesh */}
      <div className="relative bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/60 p-8 md:p-12 flex flex-col justify-between border-b md:border-b-0 md:border-r border-slate-800 overflow-hidden">
        {/* Glow orb */}
        <div className="absolute top-1/4 left-1/4 w-72 h-72 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 right-0 w-80 h-80 bg-blue-600/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10">
          <div className="inline-flex p-3 rounded-2xl bg-cyan-950/80 border border-cyan-500/40 text-cyan-400 text-3xl mb-4 shadow-lg shadow-cyan-950/50">
            🛡️
          </div>
          <h1 className="text-3xl lg:text-4xl font-extrabold text-white tracking-tight">
            SentinelVault
          </h1>
          <p className="text-sm font-medium text-cyan-400 mt-2 tracking-wide">
            Analyze Data. Don't Expose It.
          </p>
          <p className="text-xs text-slate-400 mt-4 leading-relaxed max-w-sm">
            Zero-Trust Privacy-Preserving Analytics Gateway. Formal differential privacy, zero-knowledge queries, and cryptographic tamper-evident receipts.
          </p>
        </div>

        {/* Decorative Wave SVG */}
        <div className="relative z-10 mt-8 mb-4">
          <svg
            className="w-full h-32 opacity-70"
            viewBox="0 0 400 120"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M0 60 C 100 100, 200 20, 300 80 C 350 110, 380 90, 400 70"
              stroke="#06b6d4"
              strokeWidth="2"
              fill="none"
              strokeDasharray="4 2"
            />
            <path
              d="M0 80 C 120 40, 220 110, 320 50 C 360 30, 390 60, 400 65"
              stroke="#3b82f6"
              strokeWidth="1.5"
              fill="none"
            />
            <path
              d="M0 70 C 80 90, 180 50, 280 90 C 340 110, 370 85, 400 75"
              stroke="#0284c7"
              strokeWidth="1"
              fill="none"
              opacity="0.6"
            />
          </svg>
          <div className="flex items-center gap-4 text-[11px] text-slate-400 font-mono">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              DP Laplace Engine: Active
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400" />
              Ed25519 Verified
            </span>
          </div>
        </div>

        <div className="relative z-10 pt-4 border-t border-slate-800/80 text-[11px] text-slate-500 flex items-center justify-between">
          <span>HOTFIX UG 59 • Track 4</span>
          <span>MIT Hackathon 2026</span>
        </div>
      </div>

      {/* Right Column: Sign In Card */}
      <div className="p-8 md:p-12 flex flex-col justify-center bg-slate-900/60">
        <div className="mb-6">
          <div className="text-[11px] font-mono text-cyan-400 uppercase tracking-widest font-semibold mb-1">
            Gateway Authentication
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Welcome Back</h2>
          <p className="text-xs text-slate-400 mt-1">
            Sign in to your account with zero-trust credentials.
          </p>
        </div>

        {lockoutWarning && (
          <div className="mb-4 p-4 rounded-xl bg-rose-950/80 border border-rose-700 text-rose-200 text-xs space-y-1">
            <div className="font-semibold flex items-center gap-2 text-rose-300">
              <span>⛔</span> Account Lockout Active
            </div>
            <p>{lockoutWarning}</p>
          </div>
        )}

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Email / Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950/80 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono text-sm transition"
              placeholder="e.g. analyst_user"
              required
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
                Password
              </label>
            </div>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 pr-10 rounded-xl bg-slate-950/80 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 font-mono text-sm transition"
                placeholder="••••••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-xs"
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs pt-1">
            <label className="flex items-center gap-2 text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="rounded bg-slate-950 border-slate-700 text-cyan-500 focus:ring-0"
              />
              <span>Remember me</span>
            </label>
            <span className="text-cyan-400 text-xs cursor-pointer hover:underline">
              Forgot password?
            </span>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 font-semibold text-white transition disabled:opacity-50 text-sm shadow-lg shadow-cyan-950 flex items-center justify-center gap-2 mt-2"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Verifying credentials...</span>
              </>
            ) : (
              <span>Sign In to Gateway</span>
            )}
          </button>
        </form>

        {/* Quick fill demo credentials */}
        <div className="mt-6 pt-5 border-t border-slate-800">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Quick-Fill Role Credentials:
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <button
              type="button"
              onClick={() => setDemoCredentials('analyst_user', 'AnalystPass2026!')}
              className="py-1.5 px-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-[11px] font-mono text-cyan-300 border border-slate-700 text-center transition"
            >
              Analyst
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('steward_user', 'StewardPass2026!')}
              className="py-1.5 px-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-[11px] font-mono text-purple-300 border border-slate-700 text-center transition"
            >
              Steward
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('auditor_user', 'AuditorPass2026!')}
              className="py-1.5 px-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-[11px] font-mono text-amber-300 border border-slate-700 text-center transition"
            >
              Auditor
            </button>
            <button
              type="button"
              onClick={() => setDemoCredentials('admin_user', 'AdminPass2026!')}
              className="py-1.5 px-2 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 text-[11px] font-mono text-rose-300 border border-slate-700 text-center transition"
            >
              Admin
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
