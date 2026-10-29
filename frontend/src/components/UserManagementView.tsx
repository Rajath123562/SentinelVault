import React, { useState, useEffect, useCallback } from 'react';
import { UserListItem, UserSession } from '../types/system';
import { getUsers, unlockUser, ApiError } from '../services/api';
import { AccessDeniedView } from './AccessDeniedView';

interface UserManagementViewProps {
  session: UserSession;
  onGoBack: () => void;
}

export const UserManagementView: React.FC<UserManagementViewProps> = ({ session, onGoBack }) => {
  const [users, setUsers] = useState<UserListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const isPrivileged = session.role === 'admin' || session.role === 'data_steward';

  const fetchUsers = useCallback(async () => {
    if (!isPrivileged) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getUsers(session.token);
      setUsers(data);
    } catch (err: unknown) {
      if (err instanceof ApiError && err.statusCode === 403) {
        setError('FORBIDDEN');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to fetch users');
      }
    } finally {
      setLoading(false);
    }
  }, [session.token, isPrivileged]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleUnlock = async (username: string) => {
    try {
      setError(null);
      const res = await unlockUser(session.token, username);
      setSuccessMessage(res.message);
      await fetchUsers();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unlock failed');
    }
  };

  if (!isPrivileged || error === 'FORBIDDEN') {
    return (
      <AccessDeniedView
        resourceName="the User Management Console"
        requiredPermission="user.manage (Admin or Data Steward)"
        onGoBack={onGoBack}
      />
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">👥</span>
            <h2 className="text-xl font-bold text-white tracking-tight">User & Role Management</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Authoritative identity ledger enforcing zero-trust roles and 5-attempt rate-limiting lockout state.
          </p>
        </div>

        <button
          onClick={fetchUsers}
          disabled={loading}
          className="py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs transition shadow-md shadow-cyan-950 disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : '🔄 Refresh Users'}
        </button>
      </div>

      {successMessage && (
        <div className="p-3.5 rounded-xl bg-emerald-950/70 border border-emerald-800 text-emerald-300 text-xs flex items-center gap-2">
          <span>✓</span>
          <span>{successMessage}</span>
        </div>
      )}

      {error && error !== 'FORBIDDEN' && (
        <div className="p-3.5 rounded-xl bg-rose-950/70 border border-rose-800 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Users Table matching Screen 10 */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left border-collapse">
            <thead className="bg-slate-950 text-slate-300 uppercase tracking-wider font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Username</th>
                <th className="py-3 px-4">User ID</th>
                <th className="py-3 px-4">Assigned Role</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Failures</th>
                <th className="py-3 px-4">MFA</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 font-mono">
              {users.map((u) => {
                const isLocked = u.status === 'LOCKED' || Boolean(u.locked_until);
                return (
                  <tr key={u.username} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 font-bold text-white">{u.username}</td>
                    <td className="py-3 px-4 text-slate-400">{u.user_id}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-slate-800 text-purple-300 border border-slate-700">
                        {u.role}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      {isLocked ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950 text-rose-400 border border-rose-800 animate-pulse">
                          LOCKED (5 FAILS)
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
                          ACTIVE
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-300">{u.failed_attempts} / 5</td>
                    <td className="py-3 px-4">
                      {u.mfa_enabled ? (
                        <span className="text-emerald-400 font-bold">✓ Enabled</span>
                      ) : (
                        <span className="text-slate-500">Disabled</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {isLocked ? (
                        <button
                          onClick={() => handleUnlock(u.username)}
                          className="py-1 px-3 rounded bg-amber-600 hover:bg-amber-500 text-white font-sans text-xs font-semibold transition"
                        >
                          🔓 Lift Lockout
                        </button>
                      ) : (
                        <span className="text-slate-600 text-xs font-sans">Normal</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

