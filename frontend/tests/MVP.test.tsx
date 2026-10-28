import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import App from '../src/App';
import { 
  SystemStatusResponse, 
  DatasetMetadata, 
  BudgetStatusResponse, 
  QueryRunResponse,
  AuditVerificationResponse,
  EvaluationStatusResponse 
} from '../src/types/system';

const mockSystemStatus: SystemStatusResponse = {
  project_name: 'HOTFIX Privacy-by-Design Analytics Gateway',
  project_code: 'HOTFIX',
  team_id: 'UG 59',
  current_phase: 'MVP',
  application_health: 'HEALTHY',
  configuration_valid: true,
  privacy_releases_enabled: true,
  release_disabled_reason: 'MVP: Differential privacy engine and micro-epsilon ledger active.',
  official_spec_status: 'DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED',
  official_harness_status: 'OFFICIAL EMPIRICAL RISK EVALUATION NOT CONFIGURED',
  server_time: '2026-10-28T12:00:00Z',
  capabilities: [
    {
      id: 'CAP-01-FOUNDATION',
      name: 'Application Foundation',
      status: 'IMPLEMENTED',
      phase: 'Phase 1',
      description: 'Core application structure and configuration.',
    },
    {
      id: 'CAP-03-AUTH-RBAC',
      name: 'Authentication & Lockout',
      status: 'IMPLEMENTED',
      phase: 'MVP',
      description: 'PBKDF2 authentication with 5-attempt lockout.',
    },
    {
      id: 'CAP-06-DP-ENGINE',
      name: 'Differential Privacy Engine',
      status: 'IMPLEMENTED',
      phase: 'MVP',
      description: 'IBM diffprivlib Laplace mechanism.',
    },
  ],
};

const mockDatasets: DatasetMetadata[] = [
  {
    dataset_id: 'health',
    name: 'Synthetic Health Records',
    description: 'De-identified clinical encounter and demographic attributes.',
    total_records: 500,
    privacy_unit: 'patient_id',
    sensitive_fields_protected: ['patient_id', 'ssn', 'medical_record_number'],
    allowed_fields: {
      diagnosis_category: ['cardiovascular', 'respiratory', 'neurology'],
      admission_type: ['emergency', 'elective', 'urgent'],
    },
    allowed_operators: ['equals'],
    is_official_dataset: false,
  },
  {
    dataset_id: 'financial',
    name: 'Synthetic Financial Transactions',
    description: 'Transaction records and risk assessments.',
    total_records: 500,
    privacy_unit: 'customer_id',
    sensitive_fields_protected: ['customer_id', 'account_number', 'pan'],
    allowed_fields: {
      transaction_type: ['wire', 'ach', 'pos'],
      risk_band: ['low', 'medium', 'high'],
    },
    allowed_operators: ['equals'],
    is_official_dataset: false,
  },
];

const mockBudget: BudgetStatusResponse = {
  dataset_id: 'health',
  cap_epsilon: 5.0,
  spent_epsilon: 0.5,
  remaining_epsilon: 4.5,
  accounting_notice: 'Integer micro-epsilon ledger',
  updated_at: '2026-10-28T12:00:00Z',
};

const mockQueryRunResult: QueryRunResponse = {
  release_id: 'rel-health-12345678',
  dataset_id: 'health',
  noisy_count: 104,
  epsilon_spent: 0.5,
  cumulative_epsilon: 0.5,
  remaining_budget: 4.5,
  is_cached: false,
  policy_check_status: 'POLICY_CHECK_PASSED',
  receipt: {
    receipt_id: 'rcpt-health-12345678',
    release_id: 'rel-health-12345678',
    user_id: 'analyst_user',
    dataset_id: 'health',
    dataset_version: 'v1.0-synthetic-demo',
    query_fingerprint: 'sha256:fp12345',
    query_description: "COUNT DISTINCT patient_id WHERE diagnosis_category = 'cardiovascular'",
    mechanism: 'Laplace Mechanism (IBM diffprivlib with bounded CSPRNG)',
    epsilon_spent: 0.5,
    cumulative_epsilon: 0.5,
    remaining_budget: 4.5,
    policy_check_status: 'POLICY_CHECK_PASSED',
    audit_entry_hash: '3f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a',
    signature: 'MEUCIQDxSampleEd25519SignatureBase64StringForTestingReceiptVerification==',
    timestamp: '2026-10-28T12:00:01Z',
  },
};

const mockAuditVerification: AuditVerificationResponse = {
  valid: true,
  total_entries: 5,
  verified_entries: 5,
  tamper_detected: false,
  error_message: null,
  broken_at_entry: null,
  algorithm: 'SHA-256 + Ed25519',
  notice: 'Tamper-evident verification of cryptographic hash chain and digital signatures',
};

const mockEvaluationStatus: EvaluationStatusResponse = {
  demonstration_benchmark_status: 'AVAILABLE',
  official_accounting_spec_status: 'DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED',
  official_empirical_risk_evaluation_status: 'OFFICIAL EMPIRICAL RISK EVALUATION NOT CONFIGURED',
  notice: 'Official Track 4 competition specification and attack harnesses not yet integrated.',
  benchmark_report: {
    benchmark_timestamp: '2026-10-28T12:00:00Z',
    dataset_evaluated: 'health',
    mechanism: 'Laplace Mechanism',
    trials_per_setting: 50,
    epsilons_tested: [0.1, 0.2, 0.5, 1.0],
    overall_summary_by_epsilon: {
      '0.1': { avg_mae: 9.47, avg_rmse: 13.22, avg_rel_error_pct: 8.71, theoretical_stddev: 14.14 },
      '0.5': { avg_mae: 1.90, avg_rmse: 2.81, avg_rel_error_pct: 1.73, theoretical_stddev: 2.83 },
      '1.0': { avg_mae: 0.92, avg_rmse: 1.41, avg_rel_error_pct: 0.83, theoretical_stddev: 1.41 },
    },
    conclusions: ['Noise decreases inversely proportional to epsilon.'],
  },
};

describe('HOTFIX MVP Frontend User Journeys', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  const setupFetchMock = () => {
    return vi.fn().mockImplementation((url: string, _options?: RequestInit) => {
      const urlStr = String(url);
      if (urlStr.includes('/api/system/status')) {
        return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSystemStatus) } as Response);
      }
      if (urlStr.includes('/api/auth/login')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            token: 'test-analyst-token-xyz',
            user_id: 'analyst_user',
            role: 'analyst',
            expires_at: '2026-10-29T12:00:00Z',
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
            policy_check: 'POLICY_CHECK_PASSED',
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
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) } as Response);
    });
  };

  it('1. User signs in with analyst credentials and enters Analytics Dashboard', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    // Check login form appears
    expect(screen.getByText('Gateway Authentication')).toBeInTheDocument();

    // Click Sign In
    const submitBtn = screen.getByRole('button', { name: /Sign In to Gateway/i });
    fireEvent.click(submitBtn);

    // Verify Analytics Dashboard is shown
    await waitFor(() => {
      expect(screen.getByText('Differential Privacy Query Specification')).toBeInTheDocument();
      expect(screen.getByText(/Shared Privacy Budget/i)).toBeInTheDocument();
      expect(screen.getByText('analyst_user')).toBeInTheDocument();
    });
  });

  it('2. Analyst executes a differential privacy query and inspects the release', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    // Login first
    const submitBtn = screen.getByRole('button', { name: /Sign In to Gateway/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('Differential Privacy Query Specification')).toBeInTheDocument();
      expect(screen.getByText('cardiovascular')).toBeInTheDocument();
    });

    // Run query
    const runBtn = screen.getByRole('button', { name: /Execute Differential Privacy Release/i });
    fireEvent.click(runBtn);

    // Verify release details appear
    await waitFor(() => {
      expect(screen.getByText(/Differential Privacy Release Committed/i)).toBeInTheDocument();
      expect(screen.getByText('104')).toBeInTheDocument(); // Noisy count
      expect(screen.getByText(/View Cryptographic Privacy Receipt/i)).toBeInTheDocument();
    });
  });

  it('3. User navigates to Privacy Receipt and sees Ed25519 signature', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    // Login
    fireEvent.click(screen.getByRole('button', { name: /Sign In to Gateway/i }));
    await waitFor(() => {
      expect(screen.getByText('Differential Privacy Query Specification')).toBeInTheDocument();
      expect(screen.getByText('cardiovascular')).toBeInTheDocument();
    });

    // Run query
    fireEvent.click(screen.getByRole('button', { name: /Execute Differential Privacy Release/i }));
    await waitFor(() => {
      expect(screen.getByText(/View Cryptographic Privacy Receipt/i)).toBeInTheDocument();
    });

    // Click View Receipt
    fireEvent.click(screen.getByText(/View Cryptographic Privacy Receipt/i));

    // Verify Receipt View
    await waitFor(() => {
      expect(screen.getByText('Cryptographic Privacy Receipt')).toBeInTheDocument();
      expect(screen.getByText('rcpt-health-12345678')).toBeInTheDocument();
      expect(screen.getByText(/Ed25519 Digital Signature/i)).toBeInTheDocument();
      expect(screen.getByText(/3f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a/i)).toBeInTheDocument();
    });
  });

  it('4. User navigates to Audit & Evaluation tab and sees integrity & benchmark report', async () => {
    globalThis.fetch = setupFetchMock();
    render(<App />);

    // Login
    fireEvent.click(screen.getByRole('button', { name: /Sign In to Gateway/i }));
    await waitFor(() => {
      expect(screen.getByText('Differential Privacy Query Specification')).toBeInTheDocument();
      expect(screen.getByText('cardiovascular')).toBeInTheDocument();
    });

    // Click Audit & Utility tab
    const auditTabBtn = screen.getByRole('button', { name: /Cryptographic Audit & Utility/i });
    fireEvent.click(auditTabBtn);

    // Verify Audit Verification & Utility Table
    await waitFor(() => {
      expect(screen.getByText(/Cryptographic Audit Chain Verification/i)).toBeInTheDocument();
      expect(screen.getByText('AUDIT CHAIN INTEGRITY VERIFIED')).toBeInTheDocument();
      expect(screen.getByText('Empirical Privacy-Utility Trade-off Benchmark')).toBeInTheDocument();
      expect(screen.getByText('DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED')).toBeInTheDocument();
    });
  });
});
