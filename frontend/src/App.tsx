import React, { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { StatusBanner } from './components/StatusBanner';
import { CapabilityMatrix } from './components/CapabilityMatrix';
import { ConnectionAlert } from './components/ConnectionAlert';
import { getSystemStatus, ApiError } from './services/api';
import { SystemStatusResponse, ConnectionStatus } from './types/system';

export const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setConnectionStatus('connecting');
    setErrorMessage(null);
    try {
      const data = await getSystemStatus();
      setStatus(data);
      setConnectionStatus('connected');
    } catch (err: unknown) {
      setConnectionStatus('error');
      if (err instanceof ApiError) {
        setErrorMessage(err.message);
      } else if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Failed to connect to backend server');
      }
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        connectionStatus={connectionStatus}
        teamId={status?.team_id}
        phase={status?.current_phase}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {errorMessage && (
          <ConnectionAlert error={errorMessage} onRetry={fetchStatus} />
        )}

        <StatusBanner status={status} />

        {status?.capabilities && status.capabilities.length > 0 && (
          <CapabilityMatrix capabilities={status.capabilities} />
        )}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-6 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>HOTFIX Privacy-by-Design Analytics Gateway • Team UG 59</span>
          <span>Fail-Closed Security Architecture • Phase 1 Foundation</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
