import React, { useEffect, useState, useCallback } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { AuthView } from './components/AuthView';
import { DashboardHomeView } from './components/DashboardHomeView';
import { DatasetSelectionView } from './components/DatasetSelectionView';
import { QueryBuilderView } from './components/QueryBuilderView';
import { QueryResultsView } from './components/QueryResultsView';
import { PrivacyBudgetView, UsageRecord } from './components/PrivacyBudgetView';
import { PrivacyReceiptViewer } from './components/PrivacyReceiptViewer';
import { AuditEvaluationView } from './components/AuditEvaluationView';
import { SecurityEventsView } from './components/SecurityEventsView';
import { UserManagementView } from './components/UserManagementView';
import { SettingsView } from './components/SettingsView';
import { AboutView } from './components/AboutView';
import { AccessDeniedView } from './components/AccessDeniedView';
import { NotFoundView } from './components/NotFoundView';
import { LoadingModal } from './components/LoadingModal';
import { ConnectionAlert } from './components/ConnectionAlert';

import {
  getSystemStatus,
  getDatasets,
  getBudgetStatus,
  previewQuery,
  runQuery,
  logoutUser,
  getIncidentStatus,
  getMe,
  ApiError,
} from './services/api';
import {
  SystemStatusResponse,
  ConnectionStatus,
  UserSession,
  DatasetMetadata,
  BudgetStatusResponse,
  QueryPreviewResponse,
  QueryRunResponse,
  PrivacyReceipt,
  ActiveScreen,
  IncidentStatusResponse,
} from './types/system';

const DEFAULT_DATASETS: DatasetMetadata[] = [
  {
    dataset_id: 'health',
    title: 'Hospital Clinical Cohort (Synthetic)',
    name: 'Hospital Clinical Cohort (Synthetic)',
    version: '1.0.0',
    is_official_dataset: true,
    privacy_unit: 'patient_id',
    description: '500 de-identified patient diagnosis records with strict differential privacy protection.',
    approved_fields: {
      diagnosis: ['Hypertension', 'Diabetes Type 2', 'Asthma', 'Healthy'],
      department: ['Cardiology', 'Endocrinology', 'Pulmonology', 'General Medicine'],
    },
    allowed_fields: {
      diagnosis: ['Hypertension', 'Diabetes Type 2', 'Asthma', 'Healthy'],
      department: ['Cardiology', 'Endocrinology', 'Pulmonology', 'General Medicine'],
    },
    total_records: 500,
  },
  {
    dataset_id: 'financial',
    title: 'Retail Banking Suspicious Activity Transactions',
    name: 'Retail Banking Suspicious Activity Transactions',
    version: '1.0.0',
    is_official_dataset: true,
    privacy_unit: 'account_id',
    description: '450 transaction audit records for anti-money laundering privacy-preserving analysis.',
    approved_fields: {
      transaction_type: ['Wire Transfer', 'Cash Deposit', 'ATM Withdrawal', 'Online Purchase'],
      risk_category: ['High', 'Medium', 'Low'],
    },
    allowed_fields: {
      transaction_type: ['Wire Transfer', 'Cash Deposit', 'ATM Withdrawal', 'Online Purchase'],
      risk_category: ['High', 'Medium', 'Low'],
    },
    total_records: 450,
  },
];

export const App: React.FC = () => {
  // System Connection & Health
  const [status, setStatus] = useState<SystemStatusResponse | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [connectionError, setConnectionError] = useState<string | null>(null);

  // Authentication & Session
  const [session, setSession] = useState<UserSession | null>(null);

  // Navigation state (16 screens)
  const [activeScreen, setActiveScreen] = useState<ActiveScreen>('dashboard');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Analytical Data & Workflow state
  const [datasets, setDatasets] = useState<DatasetMetadata[]>(DEFAULT_DATASETS);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('health');
  const [budget, setBudget] = useState<BudgetStatusResponse | null>(null);
  const [preview, setPreview] = useState<QueryPreviewResponse | null>(null);
  const [latestResult, setLatestResult] = useState<QueryRunResponse | null>(null);
  const [currentReceipt, setCurrentReceipt] = useState<PrivacyReceipt | null>(null);
  const [usageHistory, setUsageHistory] = useState<UsageRecord[]>([]);
  const [incidentStatus, setIncidentStatus] = useState<IncidentStatusResponse | null>(null);

  // Async Execution States
  const [loadingRun, setLoadingRun] = useState(false);
  const [queryError, setQueryError] = useState<string | null>(null);

  // Fetch gateway status
  const fetchStatus = useCallback(async () => {
    setConnectionStatus('connecting');
    setConnectionError(null);
    try {
      const data = await getSystemStatus();
      setStatus(data);
      setConnectionStatus('connected');
    } catch (err: unknown) {
      setConnectionStatus('error');
      setConnectionError(err instanceof Error ? err.message : 'Failed to connect to backend gateway');
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Load datasets & budget whenever session or selected dataset changes
  const loadWorkspace = useCallback(async () => {
    if (!session) return;
    try {
      const dsList = await getDatasets(session.token);
      if (Array.isArray(dsList) && dsList.length > 0) {
        setDatasets(dsList);
      }
    } catch (err) {
      console.warn('Dataset load fallback used', err);
    }

    try {
      const bData = await getBudgetStatus(selectedDatasetId, session.token);
      setBudget(bData);
    } catch (err) {
      console.warn('Budget load notice', err);
    }

    try {
      const inc = await getIncidentStatus(session.token);
      setIncidentStatus(inc);
    } catch (err) {
      console.warn('Incident status notice', err);
    }
  }, [session, selectedDatasetId]);

  useEffect(() => {
    loadWorkspace();
  }, [loadWorkspace]);

  // Zero-Trust Session Restoration on browser refresh
  useEffect(() => {
    const saved = sessionStorage.getItem('sentinelvault_session');
    if (saved) {
      try {
        const parsed: UserSession = JSON.parse(saved);
        if (parsed?.token) {
          getMe(parsed.token)
            .then((validSession) => {
              setSession(validSession);
            })
            .catch(() => {
              sessionStorage.removeItem('sentinelvault_session');
            });
        }
      } catch {
        sessionStorage.removeItem('sentinelvault_session');
      }
    }
  }, []);

  // Auth Handlers
  const handleLoginSuccess = (newSession: UserSession) => {
    sessionStorage.setItem('sentinelvault_session', JSON.stringify(newSession));
    setSession(newSession);
    setActiveScreen('dashboard');
  };

  const handleLogout = async () => {
    sessionStorage.removeItem('sentinelvault_session');
    if (session) {
      try {
        await logoutUser(session.token);
      } catch (err) {
        console.warn('Logout notification error', err);
      }
    }
    setSession(null);
    setPreview(null);
    setLatestResult(null);
    setCurrentReceipt(null);
    setActiveScreen('dashboard');
  };

  // Query Execution Handlers
  const handlePreviewQuery = useCallback(
    async (dsId: string, field: string, value: string, epsilon: number) => {
      if (!session) return null;
      try {
        const res = await previewQuery(session.token, {
          dataset_id: dsId,
          field,
          operator: 'equals',
          value,
          epsilon,
        });
        setPreview(res);
        return res;
      } catch (err) {
        return null;
      }
    },
    [session]
  );

  const handleRunQuery = async (dsId: string, field: string, value: string, epsilon: number) => {
    if (!session) return;
    setLoadingRun(true);
    setQueryError(null);
    try {
      const runRes = await runQuery(session.token, {
        dataset_id: dsId,
        field,
        operator: 'equals',
        value,
        epsilon,
      });

      setLatestResult(runRes);
      if (runRes.receipt) {
        setCurrentReceipt(runRes.receipt);
      }

      // Record in authoritative local session usage history
      const newUsageItem: UsageRecord = {
        id: runRes.release_id || `REL-${Date.now()}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        query: `${dsId.toUpperCase()} - COUNT_DISTINCT (${field} = '${value}')`,
        cost: runRes.epsilon_spent,
      };
      setUsageHistory((prev) => [newUsageItem, ...prev]);

      // Refresh budget
      const updatedBudget = await getBudgetStatus(dsId, session.token);
      setBudget(updatedBudget);

      // Transition to Screen 5: Query Results
      setActiveScreen('results');
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setQueryError(err.message);
      } else if (err instanceof Error) {
        setQueryError(err.message);
      } else {
        setQueryError('Differential privacy release rejected by gateway policy');
      }
    } finally {
      setLoadingRun(false);
    }
  };

  // Public / Anonymous Login View (Screen 1 & Screen 15)
  if (!session) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
        {/* Simple Anonymous Navigation */}
        <header className="border-b border-slate-900 bg-slate-950/80 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-800 flex items-center justify-center text-lg">
              🛡️
            </div>
            <div>
              <span className="font-extrabold text-white text-sm tracking-tight">SentinelVault</span>
              <span className="hidden sm:inline text-xs text-slate-500 ml-2">HOTFIX Team UG 59</span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs">
            <button
              onClick={() => setActiveScreen(activeScreen === 'about' ? 'dashboard' : 'about')}
              className="text-cyan-400 hover:text-cyan-300 font-semibold transition"
            >
              {activeScreen === 'about' ? '← Back to Login' : 'About & Trust Pillars'}
            </button>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono bg-slate-900 border border-slate-800 text-slate-300">
              Track 4 • Privacy by Design
            </span>
          </div>
        </header>

        <main className="flex-1 max-w-5xl w-full mx-auto px-6 py-8 flex flex-col justify-center">
          {connectionError && (
            <div className="mb-6">
              <ConnectionAlert error={connectionError} onRetry={fetchStatus} />
            </div>
          )}

          {activeScreen === 'about' ? (
            <AboutView />
          ) : (
            <AuthView onLoginSuccess={handleLoginSuccess} />
          )}
        </main>

        <footer className="border-t border-slate-900 bg-slate-950 px-6 py-4 text-center text-xs text-slate-500 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>SentinelVault • Zero-Trust Privacy-Preserving Analytics Gateway</span>
          <span>Analyze Data. Don't Expose It.</span>
        </footer>
      </div>
    );
  }

  // Authenticated 16-Screen Enterprise Layout (Screen 2 - 16)
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex font-sans antialiased selection:bg-cyan-500 selection:text-white">
      {/* Screen 12: Loading Modal */}
      <LoadingModal
        isOpen={loadingRun}
        message="Processing your query..."
        subMessage="Applying differential privacy noise and checking privacy budget. This may take a few seconds."
      />

      {/* Desktop & Mobile Sidebar Drawer */}
      <Sidebar
        activeScreen={activeScreen}
        onNavigate={(screen) => setActiveScreen(screen)}
        session={session}
        onLogout={handleLogout}
        isOpenMobile={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        <TopBar
          connectionStatus={connectionStatus}
          session={session}
          activeScreen={activeScreen}
          onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
          remainingBudget={budget?.remaining_epsilon ?? 5.0}
        />

        {/* Phase 6 Incident Response Status Banners */}
        {incidentStatus?.current_state === 'RELEASES_DISABLED' && (
          <div className="bg-rose-950/90 border-b border-rose-800 text-rose-200 px-4 sm:px-8 py-2.5 text-xs font-mono flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-base">🚨</span>
              <span className="font-bold">FAIL-CLOSED GATE ACTIVE:</span>
              <span>All differential privacy query releases are temporarily suspended. ({incidentStatus.reason})</span>
            </div>
            <span className="px-2.5 py-1 rounded bg-rose-900 border border-rose-700 font-bold text-[10px] shrink-0">
              RELEASES DISABLED
            </span>
          </div>
        )}
        {incidentStatus?.current_state === 'RESTRICTED' && (
          <div className="bg-amber-950/90 border-b border-amber-800 text-amber-200 px-4 sm:px-8 py-2.5 text-xs font-mono flex items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <span className="text-base">⚠️</span>
              <span className="font-bold">RESTRICTED MODE:</span>
              <span>Privacy budget releases are capped at ε ≤ 0.50 due to elevated monitoring. ({incidentStatus.reason})</span>
            </div>
            <span className="px-2.5 py-1 rounded bg-amber-900 border border-amber-700 font-bold text-[10px] shrink-0">
              RESTRICTED
            </span>
          </div>
        )}

        <main className="flex-1 px-4 sm:px-8 py-6 max-w-7xl w-full mx-auto">
          {/* Screen 2: Dashboard (Home) */}
          {activeScreen === 'dashboard' && (
            <DashboardHomeView
              session={session}
              datasets={datasets}
              budget={budget}
              onNavigate={(s) => setActiveScreen(s)}
            />
          )}

          {/* Screen 3: Dataset Selection */}
          {activeScreen === 'datasets' && (
            <DatasetSelectionView
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              onSelectDataset={(id) => setSelectedDatasetId(id)}
              onProceedToQuery={() => setActiveScreen('query')}
            />
          )}

          {/* Screen 4: Query Builder */}
          {activeScreen === 'query' && (
            <QueryBuilderView
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              onSelectDatasetId={(id) => setSelectedDatasetId(id)}
              onRunQuery={handleRunQuery}
              loadingRun={loadingRun}
              onPreviewQuery={handlePreviewQuery}
              preview={preview}
              error={queryError}
            />
          )}

          {/* Screen 5: Query Results */}
          {activeScreen === 'results' && (
            <QueryResultsView
              result={latestResult}
              onNavigate={(s) => setActiveScreen(s)}
              onViewReceipt={(receipt) => {
                setCurrentReceipt(receipt);
                setActiveScreen('receipt');
              }}
            />
          )}

          {/* Screen 6: Privacy Budget */}
          {activeScreen === 'budget' && (
            <PrivacyBudgetView
              token={session.token}
              datasets={datasets}
              selectedDatasetId={selectedDatasetId}
              onSelectDatasetId={(id) => setSelectedDatasetId(id)}
              budget={budget}
              recentUsage={usageHistory}
            />
          )}

          {/* Screen 7: Privacy Receipt */}
          {activeScreen === 'receipt' && (
            <PrivacyReceiptViewer
              initialReceipt={currentReceipt}
              token={session.token}
              onBackToDashboard={() => setActiveScreen('dashboard')}
            />
          )}

          {/* Screen 8: Audit Logs */}
          {activeScreen === 'audit' && (
            <AuditEvaluationView token={session.token} />
          )}

          {/* Screen 9: Security Events & Alerts */}
          {activeScreen === 'security' && (
            <SecurityEventsView
              token={session.token}
              onGoBack={() => setActiveScreen('dashboard')}
            />
          )}

          {/* Screen 10: User Management (Role-Gated Admin Screen) */}
          {activeScreen === 'users' && (
            <UserManagementView
              session={session}
              onGoBack={() => setActiveScreen('dashboard')}
            />
          )}

          {/* Screen 13: Access Denied */}
          {activeScreen === 'denied' && (
            <AccessDeniedView
              resourceName="the Restricted Resource"
              requiredPermission="Privileged Role Authorization"
              onGoBack={() => setActiveScreen('dashboard')}
            />
          )}

          {/* Screen 16: Not Found */}
          {activeScreen === '404' && (
            <NotFoundView onGoHome={() => setActiveScreen('dashboard')} />
          )}

          {/* Screen 14: Settings & Diagnostics */}
          {activeScreen === 'settings' && (
            <SettingsView
              session={session}
              status={status}
              onLogout={handleLogout}
            />
          )}

          {/* Screen 15: About / Info */}
          {activeScreen === 'about' && (
            <AboutView />
          )}
        </main>

        {/* Screen 11: Responsive Mobile Bottom Navigation Bar */}
        <div className="lg:hidden border-t border-slate-800 bg-slate-900/95 backdrop-blur-md px-3 py-2 flex items-center justify-around sticky bottom-0 z-20 text-xs">
          <button
            onClick={() => setActiveScreen('dashboard')}
            className={`flex flex-col items-center gap-1 ${
              activeScreen === 'dashboard' ? 'text-cyan-400 font-bold' : 'text-slate-400'
            }`}
          >
            <span>📊</span>
            <span className="text-[10px]">Home</span>
          </button>
          <button
            onClick={() => setActiveScreen('datasets')}
            className={`flex flex-col items-center gap-1 ${
              activeScreen === 'datasets' ? 'text-cyan-400 font-bold' : 'text-slate-400'
            }`}
          >
            <span>📁</span>
            <span className="text-[10px]">Datasets</span>
          </button>
          <button
            onClick={() => setActiveScreen('query')}
            className={`flex flex-col items-center gap-1 ${
              activeScreen === 'query' ? 'text-cyan-400 font-bold' : 'text-slate-400'
            }`}
          >
            <span>⚡</span>
            <span className="text-[10px]">Query</span>
          </button>
          <button
            onClick={() => setActiveScreen('budget')}
            className={`flex flex-col items-center gap-1 ${
              activeScreen === 'budget' ? 'text-cyan-400 font-bold' : 'text-slate-400'
            }`}
          >
            <span>⚖️</span>
            <span className="text-[10px]">Budget</span>
          </button>
          <button
            onClick={() => setIsMobileMenuOpen(true)}
            className="flex flex-col items-center gap-1 text-slate-400"
          >
            <span>☰</span>
            <span className="text-[10px]">More</span>
          </button>
        </div>

        {/* Desktop Sticky Footer */}
        <footer className="hidden lg:flex border-t border-slate-900 bg-slate-950/70 px-6 py-3 text-xs text-slate-500 items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>SentinelVault • Fail-Closed Differential Privacy Gateway • Team UG 59</span>
          </div>
          <span className="font-mono text-[11px] text-slate-600">
            SHA-256 Hash Chain • Ed25519 Signatures • ISO/IEC 27701
          </span>
        </footer>
      </div>
    </div>
  );
};

export default App;
