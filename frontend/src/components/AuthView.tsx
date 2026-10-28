import React, { useState } from 'react';
import { UserSession } from '../types/system';
import { loginUser, ApiError } from '../services/api';

interface AuthViewProps {
  onLoginSuccess: (session: UserSession) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('analyst_user');
  const [password, setPassword] = useState('AnalystPass2026!');
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
    <div className="max-w-md mx-auto my-12 bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl">
      <div className="text-center mb-6">
        <div className="inline-flex p-3 rounded-2xl bg-cyan-950/60 border border-cyan-800 text-3xl mb-3">
          🔐
        </div>
        <h2 className="text-2xl font-bold text-white">Gateway Authentication</h2>
        <p className="text-xs text-slate-400 mt-1">
          Zero-trust authenticated entry with 5-attempt rate-limit lockout
        </p>
      </div>

      {lockoutWarning && (
        <div className="mb-4 p-4 rounded-lg bg-rose-950/80 border border-rose-700 text-rose-200 text-sm">
          <div className="font-semibold flex items-center gap-2">
            <span>⛔</span> Temporary Lockout Active
          </div>
          <p className="text-xs mt-1 text-rose-300">{lockoutWarning}</p>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-red-950/60 border border-red-800 text-red-300 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleLogin} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
            Username
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 focus:outline-none focus:border-cyan-500 font-mono text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 focus:outline-none focus:border-cyan-500 font-mono text-sm"
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white transition disabled:opacity-50 text-sm shadow-lg shadow-cyan-950"
        >
          {loading ? 'Authenticating...' : 'Sign In to Gateway'}
        </button>
      </form>

      <div className="mt-6 pt-6 border-t border-slate-800">
        <p className="text-xs text-slate-400 mb-2 font-medium">Quick-fill Demo Credentials:</p>
        <div className="grid grid-cols-3 gap-2">
          <button
            type="button"
            onClick={() => setDemoCredentials('analyst_user', 'AnalystPass2026!')}
            className="py-1.5 px-2 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-cyan-300 border border-slate-700 text-center"
          >
            Analyst
          </button>
          <button
            type="button"
            onClick={() => setDemoCredentials('steward_user', 'StewardPass2026!')}
            className="py-1.5 px-2 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-purple-300 border border-slate-700 text-center"
          >
            Steward
          </button>
          <button
            type="button"
            onClick={() => setDemoCredentials('auditor_user', 'AuditorPass2026!')}
            className="py-1.5 px-2 rounded bg-slate-800 hover:bg-slate-700 text-xs font-mono text-amber-300 border border-slate-700 text-center"
          >
            Auditor
          </button>
        </div>
      </div>
    </div>
  );
};
