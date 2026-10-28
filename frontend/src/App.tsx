import React, { useEffect, useState, useCallback } from 'react';
import { Header } from './components/Header';
import { StatusBanner } from './components/StatusBanner';
import { CapabilityMatrix } from './components/CapabilityMatrix';
import { ConnectionAlert } from './components/ConnectionAlert';
import { AuthView } from './components/AuthView';
import { AnalyticsDashboard } from './components/AnalyticsDashboard';
import { PrivacyReceiptViewer } from './components/PrivacyReceiptViewer';
import { AuditEvaluationView } from './components/AuditEvaluationView';
import { getSystemStatus, logoutUser, ApiError } from './services/api';
import { SystemStatusResponse, ConnectionStatus, UserSession, PrivacyReceipt } from './types/system';

export const App: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // MVP Session & Navigation state
  const [session, setSession] = useState<UserSession | null>(null);
  const [activeTab, setActiveTab] = useState<'analytics' | 'receipt' | 'audit' | 'architecture'>('analytics');
  const [currentReceipt, setCurrentReceipt] = useState<PrivacyReceipt | null>(null);

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

  const handleLoginSuccess = (newSession: UserSession) => {
    setSession(newSession);
    setActiveTab('analytics');
  };

  const handleLogout = async () => {
    if (session) {
      try {
        await logoutUser(session.token);
      } catch (err) {
        console.warn('Logout notification error', err);
      }
    }
    setSession(null);
    setCurrentReceipt(null);
  };

  const handleViewReceipt = (receipt: PrivacyReceipt) => {
    setCurrentReceipt(receipt);
    setActiveTab('receipt');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        connectionStatus={connectionStatus}
        teamId={status?.team_id}
        phase={status?.current_phase || 'MVP'}
        session={session}
        onLogout={handleLogout}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-8">
        {errorMessage && (
          <ConnectionAlert error={errorMessage} onRetry={fetchStatus} />
        )}

        {!session ? (
          <div className="space-y-8">
            <StatusBanner status={status} />
            <AuthView onLoginSuccess={handleLoginSuccess} />
            {status?.capabilities && status.capabilities.length > 0 && (
              <div className="mt-12 pt-8 border-t border-slate-900">
                <CapabilityMatrix capabilities={status.capabilities} />
              </div>
            )}
          </div>
        ) : (
          <div>
            {activeTab === 'analytics' && (
              <AnalyticsDashboard
                session={session}
                onViewReceipt={handleViewReceipt}
              />
            )}

            {activeTab === 'receipt' && (
              <PrivacyReceiptViewer
                initialReceipt={currentReceipt}
                token={session.token}
                onBackToDashboard={() => setActiveTab('analytics')}
              />
            )}

            {activeTab === 'audit' && (
              <AuditEvaluationView token={session.token} />
            )}

            {activeTab === 'architecture' && (
              <div className="space-y-6">
                <StatusBanner status={status} />
                {status?.capabilities && status.capabilities.length > 0 && (
                  <CapabilityMatrix capabilities={status.capabilities} />
                )}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="border-t border-slate-900 bg-slate-950 px-6 py-6 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>HOTFIX Privacy-by-Design Analytics Gateway • Team UG 59</span>
          <span>Fail-Closed Differential Privacy Architecture • MVP</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
