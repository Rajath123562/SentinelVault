import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../src/App';
import {
  SystemStatusResponse,
  DatasetMetadata,
  BudgetStatusResponse,
  QueryRunResponse,
  AuditVerificationResponse,
  EvaluationStatusResponse,
} from '../src/types/system';

const mockSystemStatus: SystemStatusResponse = {
  project_name: 'SentinelVault — Zero-Trust Privacy-Preserving Analytics Gateway',
  project_code: 'HOTFIX',
  team_id: 'UG 59',
  current_phase: 'MVP',
  application_health: 'HEALTHY',
  configuration_valid: true,
  privacy_releases_enabled: true,
  release_disabled_reason: '',
  official_spec_status: 'ALIGNED',
  official_harness_status: 'INTEGRATED',
  server_time: '2026-10-28T10:00:00Z',
  capabilities: [],
};

const mockDatasets: DatasetMetadata[] = [
  {
    dataset_id: 'health',
    title: 'Hospital Clinical Cohort (Synthetic)',
    description: '500 de-identified patient records',
    total_records: 500,
    privacy_unit: 'patient_id',
    version: '1.0.0',
    is_official_dataset: true,
    approved_fields: {
      diagnosis: ['Hypertension', 'Diabetes Type 2', 'Asthma'],
      department: ['Cardiology', 'Endocrinology'],
    },
    allowed_fields: {
      diagnosis: ['Hypertension', 'Diabetes Type 2', 'Asthma'],
      department: ['Cardiology', 'Endocrinology'],
    },
  },
];

const mockBudget: BudgetStatusResponse = {
  dataset_id: 'health',
  cap_epsilon: 5.0,
  spent_epsilon: 0.5,
  remaining_epsilon: 4.5,
  accounting_notice: 'ACID shared ledger budget',
  updated_at: '2026-10-28T10:00:00Z',
};

const mockQueryRunResult: QueryRunResponse = {
  release_id: 'rel-health-12345678',
  dataset_id: 'health',
  noisy_count: 104,
  epsilon_spent: 0.5,
  cumulative_epsilon: 0.5,
  remaining_budget: 4.5,
  is_cached: false,
  policy_check_status: 'APPROVED',
  receipt: {
    receipt_id: 'rcpt-health-12345678',
    release_id: 'rel-health-12345678',
    user_id: 'analyst_user',
    dataset_id: 'health',
    dataset_version: '1.0.0',
    query_fingerprint: 'sha256:fp12345',
    query_description: 'diagnosis = Hypertension',
    mechanism: 'Laplace(0, 2.0)',
    epsilon_spent: 0.5,
    cumulative_epsilon: 0.5,
    remaining_budget: 4.5,
    policy_check_status: 'APPROVED',
    audit_entry_hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b',
    signature: '3f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a3f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a',
    timestamp: '2026-10-28T10:00:00Z',
  },
};

const mockAuditVerification: AuditVerificationResponse = {
  valid: true,
  total_entries: 3,
  verified_entries: 3,
  tamper_detected: false,
  error_message: null,
  broken_at_entry: null,
  algorithm: 'SHA-256 Hash Chain',
  notice: 'Chain verified successfully',
};

const mockEvaluationStatus: EvaluationStatusResponse = {
  demonstration_benchmark_status: 'BENCHMARK_COMPLETE',
  official_accounting_spec_status: 'ALIGNED',
  official_empirical_risk_evaluation_status: 'EVALUATED',
  notice: 'Utility evaluation complete',
  benchmark_report: {
    benchmark_timestamp: '2026-10-28T10:00:00Z',
    dataset_evaluated: 'health',
    mechanism: 'Laplace',
    trials_per_setting: 10,
    epsilons_tested: [0.1, 0.5, 1.0],
    overall_summary_by_epsilon: {
      '0.1': { avg_mae: 9.8, avg_rmse: 12.1, avg_rel_error_pct: 12.4, theoretical_stddev: 14.14 },
      '0.5': { avg_mae: 2.1, avg_rmse: 2.7, avg_rel_error_pct: 2.6, theoretical_stddev: 2.82 },
      '1.0': { avg_mae: 1.0, avg_rmse: 1.4, avg_rel_error_pct: 1.2, theoretical_stddev: 1.41 },
    },
    conclusions: ['Error scales inversely with epsilon conforming to theory'],
  },
};

const setupFetchMock = () => {
  return vi.fn().mockImplementation((url: RequestInfo | URL) => {
    const urlStr = url.toString();

    if (urlStr.includes('/api/system/status')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSystemStatus) } as Response);
    }
    if (urlStr.includes('/api/auth/login')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          username: 'analyst_user',
          role: 'analyst',
          token: 'mock-analyst-jwt-token-2026',
          expires_at: '2026-10-29T10:00:00Z',
        }),
      } as Response);
    }
    if (urlStr.includes('/api/datasets')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockDatasets) } as Response);
    }
    if (urlStr.includes('/api/budget/')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockBudget) } as Response);
    }
    if (urlStr.includes('/api/queries/preview')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          is_valid: true,
          dataset_id: 'health',
          query_fingerprint: 'sha256:fp12345',
          privacy_unit: 'patient_id',
          global_sensitivity: 1.0,
          epsilon_requested: 0.5,
          policy_check: 'APPROVED',
          policy_status: 'APPROVED',
          message: 'Sensitivity strictly bounded',
        }),
      } as Response);
    }
    if (urlStr.includes('/api/queries/run')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockQueryRunResult) } as Response);
    }
    if (urlStr.includes('/api/audit/verify')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAuditVerification) } as Response);
    }
    if (urlStr.includes('/api/evaluation/status')) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(mockEvaluationStatus) } as Response);
    }
    if (urlStr.includes('/api/security/events')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([
          {
            event_id: 'evt-1',
            event_type: 'AUTH_SUCCESS',
            outcome: 'SUCCESS',
            actor: 'analyst_user',
            source_ip: '127.0.0.1',
            details: 'Login successful',
            timestamp: '2026-10-28T10:00:00Z',
          },
        ]),
      } as Response);
    }
    if (urlStr.includes('/api/security/alerts')) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      } as Response);
    }
    if (urlStr.includes('/api/users')) {
      return Promise.resolve({
        ok: false,
        status: 403,
        json: () => Promise.resolve({ detail: 'Access denied: requires user.manage permission' }),
      } as Response);
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
  });
};

describe('SentinelVault 16-Screen Enterprise Workflow Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('1. User signs in with analyst credentials and enters Screen 2: Dashboard (Home)', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    expect(screen.getByText('Gateway Authentication')).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Sign In to Gateway/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Welcome back, analyst_user/i)).toBeInTheDocument();
      expect(screen.getByText('Total Datasets')).toBeInTheDocument();
      expect(screen.getByText('Privacy Budget Used')).toBeInTheDocument();
      expect(screen.getByText('Recent Activity Ledger')).toBeInTheDocument();
    });
  });

  it('2. Analyst navigates to Screen 4: Query Builder and executes a differential privacy release', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /Sign In to Gateway/i }));

    await waitFor(() => {
      expect(screen.getByText(/Welcome back, analyst_user/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /New Query/i }));

    await waitFor(() => {
      expect(screen.getByText('Build Your Query')).toBeInTheDocument();
      expect(screen.getByText(/Query Preview/i)).toBeInTheDocument();
      expect(screen.getByText(/Query is valid/i)).toBeInTheDocument();
    });

    const runBtn = screen.getByRole('button', { name: /Run Query/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getAllByText('Query Results').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Differential Privacy Applied/i)).toBeInTheDocument();
      expect(screen.getAllByText('104').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/View Privacy Receipt/i)).toBeInTheDocument();
    });
  });

  it('3. Analyst inspects Screen 7: Privacy Receipt and verifies Ed25519 signature', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /Sign In to Gateway/i }));
    await waitFor(() => expect(screen.getByText(/Welcome back, analyst_user/i)).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /New Query/i }));
    await waitFor(() => expect(screen.getByText('Build Your Query')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: /Run Query/i }));

    await waitFor(() => expect(screen.getAllByText('Query Results').length).toBeGreaterThanOrEqual(1));

    fireEvent.click(screen.getByRole('button', { name: /View Privacy Receipt/i }));

    await waitFor(() => {
      expect(screen.getAllByText(/Privacy Receipt/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/rcpt-health-12345678/i)).toBeInTheDocument();
      expect(screen.getByText(/Verified Release/i)).toBeInTheDocument();
      expect(screen.getByText(/Verify Signature/i)).toBeInTheDocument();
      expect(screen.getByText(/Download Receipt/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Verify Signature/i }));
    await waitFor(() => {
      expect(screen.getByText(/Ed25519 Gateway Signature Verified/i)).toBeInTheDocument();
    });
  });

  it('4. Analyst navigates to Screen 6: Privacy Budget and inspects circular meter', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /Sign In to Gateway/i }));
    await waitFor(() => expect(screen.getByText(/Welcome back, analyst_user/i)).toBeInTheDocument());

    // In sidebar, click Privacy Budget button
    const budgetBtn = screen.getAllByRole('button', { name: /Privacy Budget/i })[0];
    fireEvent.click(budgetBtn);

    await waitFor(() => {
      expect(screen.getByText('Privacy Budget Tracker')).toBeInTheDocument();
      expect(screen.getByText(/Total Allocated Cap/i)).toBeInTheDocument();
      expect(screen.getByText(/Recent Privacy Expenditure Ledger/i)).toBeInTheDocument();
    });
  });

  it('5. Analyst navigates to Screen 8: Audit Logs and verifies SHA-256 hash chain', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /Sign In to Gateway/i }));
    await waitFor(() => expect(screen.getByText(/Welcome back, analyst_user/i)).toBeInTheDocument());

    const auditBtn = screen.getAllByRole('button', { name: /Audit Logs/i })[0];
    fireEvent.click(auditBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Audit Logs/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/SHA-256 HASH CHAIN INTEGRITY VERIFIED/i)).toBeInTheDocument();
      expect(screen.getByText(/0 Broken Links/i)).toBeInTheDocument();
    });
  });

  it('6. Ordinary analyst can navigate to Settings & Diagnostics (Screen 14)', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /Sign In to Gateway/i }));
    await waitFor(() => expect(screen.getByText(/Welcome back, analyst_user/i)).toBeInTheDocument());

    const settingsBtn = screen.getByText('Settings');
    fireEvent.click(settingsBtn);

    await waitFor(() => {
      expect(screen.getAllByText(/Settings/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Identity Profile')).toBeInTheDocument();
      expect(screen.getAllByText('analyst_user').length).toBeGreaterThanOrEqual(1);
    });
  });
});
