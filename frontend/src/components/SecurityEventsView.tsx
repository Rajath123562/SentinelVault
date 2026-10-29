import React, { useState, useEffect, useCallback } from 'react';
import { SecurityEvent, SecurityAlert } from '../types/system';
import { getSecurityEvents, getSecurityAlerts, acknowledgeAlert, resolveAlert, ApiError } from '../services/api';
import { AccessDeniedView } from './AccessDeniedView';

interface SecurityEventsViewProps {
  token: string;
  onGoBack?: () => void;
}

export const SecurityEventsView: React.FC<SecurityEventsViewProps> = ({ token, onGoBack }) => {
  const [activeTab, setActiveTab] = useState<'events' | 'alerts'>('events');
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [alerts, setAlerts] = useState<SecurityAlert[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [filterType, setFilterType] = useState<string>('ALL');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    setForbidden(false);
    try {
      if (activeTab === 'events') {
        const data = await getSecurityEvents(token, 100);
        setEvents(data);
      } else {
        const data = await getSecurityAlerts(token, 100);
        setAlerts(data);
      }
    } catch (err: unknown) {
      if (err instanceof ApiError && err.statusCode === 403) {
        setForbidden(true);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to fetch security ledger');
      }
    } finally {
      setLoading(false);
    }
  }, [token, activeTab]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (forbidden) {
    return (
      <AccessDeniedView
        resourceName="the Security Events & Alerts Ledger"
        requiredPermission="security.events.read (Auditor or Data Steward)"
        onGoBack={onGoBack || (() => {})}
      />
    );
  }

  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleAcknowledge = async (alertId: string) => {
    setActionLoading(alertId);
    try {
      await acknowledgeAlert(token, alertId);
      await fetchData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to acknowledge alert');
    } finally {
      setActionLoading(null);
    }
  };

  const handleResolve = async (alertId: string) => {
    const notes = prompt('Enter resolution notes / rationale (required, min 10 chars):');
    if (!notes || notes.trim().length < 10) {
      if (notes !== null) {
        alert('Resolution notes must be at least 10 characters.');
      }
      return;
    }
    setActionLoading(alertId);
    try {
      await resolveAlert(token, alertId, notes.trim());
      await fetchData();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to resolve alert');
    } finally {
      setActionLoading(null);
    }
  };

  const getAlertStatusBadge = (status?: string) => {
    switch (status?.toUpperCase()) {
      case 'OPEN':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
            OPEN
          </span>
        );
      case 'ACKNOWLEDGED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">
            ACKNOWLEDGED
          </span>
        );
      case 'RESOLVED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
            RESOLVED
          </span>
        );
      case 'FALSE_POSITIVE':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
            FALSE POSITIVE
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
            {status || 'OPEN'}
          </span>
        );
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'HIGH':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
            High
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-300 border border-amber-800">
            Medium
          </span>
        );
      case 'LOW':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-950 text-blue-300 border border-blue-800">
            Low
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
            {severity}
          </span>
        );
    }
  };

  const getOutcomeBadge = (outcome: string) => {
    switch (outcome?.toUpperCase()) {
      case 'SUCCESS':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
            Success
          </span>
        );
      case 'FAILURE':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-950 text-amber-400 border border-amber-800">
            Failure
          </span>
        );
      case 'DENIED':
      case 'BLOCKED':
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
            Blocked
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300">
            {outcome}
          </span>
        );
    }
  };

  const filteredEvents = filterType === 'ALL'
    ? events
    : events.filter((e) => e.event_type === filterType);

  const uniqueTypes = Array.from(new Set(events.map((e) => e.event_type)));

  return (
    <div className="space-y-6 max-w-6xl mx-auto animate-in fade-in duration-200">
      {/* Header Matching Screen 9 */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">🚨</span>
            <h2 className="text-xl font-bold text-white tracking-tight">Security Events & Alerts</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Monitor suspicious activity, rate limit breaches, policy violations, and gateway alerts.
          </p>
        </div>

        <button
          onClick={fetchData}
          disabled={loading}
          className="py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs shadow-md shadow-cyan-950 transition disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : '🔄 Refresh Data'}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/70 border border-rose-800 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {/* Tabs matching Screen 9: Events vs Alerts */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-6">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('events')}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition ${
                activeTab === 'events'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/60'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              📊 Events ({events.length})
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`px-4 py-2 rounded-lg text-xs font-semibold transition ${
                activeTab === 'alerts'
                  ? 'bg-rose-950 text-rose-300 border border-rose-700/60'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              🚨 Alerts ({alerts.length})
            </button>
          </div>

          {activeTab === 'events' && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">Filter Event:</span>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-slate-950 border border-slate-700 rounded px-2.5 py-1 text-slate-200 text-xs focus:outline-none focus:border-cyan-500 font-mono"
              >
                <option value="ALL">ALL ({events.length})</option>
                {uniqueTypes.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Tab 1: SIEM Events Table */}
        {activeTab === 'events' && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border border-slate-800 rounded-lg overflow-hidden">
              <thead className="bg-slate-950 text-slate-300 uppercase tracking-wider font-mono">
                <tr>
                  <th className="py-2.5 px-3">Timestamp (UTC)</th>
                  <th className="py-2.5 px-3">Event Type</th>
                  <th className="py-2.5 px-3">Outcome</th>
                  <th className="py-2.5 px-3">Actor</th>
                  <th className="py-2.5 px-3">IP Address</th>
                  <th className="py-2.5 px-3">Details / Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300 bg-slate-900">
                {filteredEvents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-500">
                      {loading ? 'Loading events from gateway...' : 'No security events recorded matching filter.'}
                    </td>
                  </tr>
                ) : (
                  filteredEvents.map((evt) => (
                    <tr key={evt.event_id} className="hover:bg-slate-800/50">
                      <td className="py-2.5 px-3 text-[11px] text-slate-400">
                        {new Date(evt.timestamp).toLocaleString()}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-cyan-300 font-mono">
                        {evt.event_type}
                      </td>
                      <td className="py-2.5 px-3">{getOutcomeBadge(evt.outcome)}</td>
                      <td className="py-2.5 px-3 text-purple-300">{evt.actor || 'anonymous'}</td>
                      <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                        {evt.source_ip || 'unknown'}
                      </td>
                      <td className="py-2.5 px-3 text-slate-300 max-w-xs truncate" title={evt.details || ''}>
                        {evt.details || '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 2: Security Alerts Table (Screen 9) */}
        {activeTab === 'alerts' && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left border border-slate-800 rounded-lg overflow-hidden">
              <thead className="bg-slate-950 text-slate-300 uppercase tracking-wider font-mono">
                <tr>
                  <th className="py-2.5 px-4">Time</th>
                  <th className="py-2.5 px-4">Alert Title & Rule</th>
                  <th className="py-2.5 px-4">Severity</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Target / Actor</th>
                  <th className="py-2.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300 bg-slate-900">
                {alerts.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-500">
                      {loading ? 'Loading alerts...' : 'No high-risk security alerts detected. Gateway is operating nominally.'}
                    </td>
                  </tr>
                ) : (
                  alerts.map((al) => {
                    const timeStr = al.created_at || al.timestamp;
                    const dateObj = timeStr ? new Date(timeStr) : new Date();
                    return (
                      <tr key={al.alert_id} className="hover:bg-slate-800/50">
                        <td className="py-2.5 px-4 text-slate-400 text-[11px]">
                          {dateObj.toLocaleTimeString()}
                        </td>
                        <td className="py-2.5 px-4 font-semibold text-white">
                          <div>{al.title || (al.event_type ? al.event_type.replace(/_/g, ' ') : 'Security Detection Alert')}</div>
                          <div className="text-[10px] text-cyan-400 font-normal">{al.rule_id || al.alert_id}</div>
                        </td>
                        <td className="py-2.5 px-4">{getSeverityBadge(al.severity)}</td>
                        <td className="py-2.5 px-4">
                          {getAlertStatusBadge(al.status)}
                        </td>
                        <td className="py-2.5 px-4 text-slate-400">
                          <div className="text-purple-300">{al.actor || 'System'}</div>
                          <div className="text-[10px] text-slate-500">{al.resource || al.source_ip || 'gateway'}</div>
                        </td>
                        <td className="py-2.5 px-4 text-right space-x-1.5 whitespace-nowrap">
                          {al.status === 'OPEN' && (
                            <button
                              onClick={() => handleAcknowledge(al.alert_id)}
                              disabled={actionLoading === al.alert_id}
                              className="px-2 py-1 rounded bg-amber-950/80 hover:bg-amber-900 border border-amber-800 text-amber-300 text-[10px] font-semibold transition"
                            >
                              {actionLoading === al.alert_id ? '...' : 'Acknowledge'}
                            </button>
                          )}
                          {al.status !== 'RESOLVED' && al.status !== 'FALSE_POSITIVE' && (
                            <button
                              onClick={() => handleResolve(al.alert_id)}
                              disabled={actionLoading === al.alert_id}
                              className="px-2 py-1 rounded bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800 text-emerald-300 text-[10px] font-semibold transition"
                            >
                              Resolve
                            </button>
                          )}
                          {(al.status === 'RESOLVED' || al.status === 'FALSE_POSITIVE') && (
                            <span className="text-[10px] text-slate-500 italic">Closed</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
