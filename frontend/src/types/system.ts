/**
 * Type definitions matching the backend HOTFIX API contracts.
 */

export interface CapabilityStatus {
  id: string;
  name: string;
  status: 'IMPLEMENTED' | 'PLANNED' | 'BLOCKED' | 'NOT_CONFIGURED';
  phase: string;
  description: string;
}

export interface SystemStatusResponse {
  project_name: string;
  project_code: string;
  team_id: string;
  current_phase: string;
  application_health: string;
  configuration_valid: boolean;
  privacy_releases_enabled: boolean;
  release_disabled_reason: string;
  official_spec_status: string;
  official_harness_status: string;
  server_time: string;
  capabilities: CapabilityStatus[];
}

export interface ReadinessResponse {
  status: string;
  phase: string;
  application_initialized: boolean;
  configuration_valid: boolean;
  privacy_release_ready: boolean;
  privacy_engine_implemented: boolean;
  official_spec_status: string;
  evaluation_harness_status: string;
  release_disabled_reason: string;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface UserSession {
  username: string;
  role: 'analyst' | 'data_steward' | 'auditor';
  token: string;
  expires_at: string;
}

export interface DatasetMetadata {
  dataset_id: string;
  name: string;
  description: string;
  total_records: number;
  privacy_unit: string;
  sensitive_fields_protected: string[];
  allowed_fields: Record<string, string[]>;
  allowed_operators: string[];
  is_official_dataset: boolean;
}

export interface QueryPreviewResponse {
  is_valid: boolean;
  dataset_id: string;
  query_fingerprint: string;
  privacy_unit: string;
  global_sensitivity: number;
  epsilon_requested: number;
  policy_check: string;
  message: string;
}

export interface PrivacyReceipt {
  receipt_id: string;
  release_id: string;
  user_id: string;
  dataset_id: string;
  dataset_version: string;
  query_fingerprint: string;
  query_description: string;
  mechanism: string;
  epsilon_spent: number;
  cumulative_epsilon: number;
  remaining_budget: number;
  policy_check_status: string;
  audit_entry_hash: string;
  signature: string;
  timestamp: string;
}

export interface QueryRunResponse {
  release_id: string;
  dataset_id: string;
  noisy_count: number;
  epsilon_spent: number;
  cumulative_epsilon: number;
  remaining_budget: number;
  is_cached: boolean;
  policy_check_status: string;
  receipt: PrivacyReceipt;
}

export interface BudgetStatusResponse {
  dataset_id: string;
  cap_epsilon: number;
  spent_epsilon: number;
  remaining_epsilon: number;
  accounting_notice: string;
  updated_at: string;
}

export interface AuditVerificationResponse {
  valid: boolean;
  total_entries: number;
  verified_entries: number;
  tamper_detected: boolean;
  error_message?: string | null;
  broken_at_entry?: number | null;
  algorithm: string;
  notice: string;
}

export interface EvaluationStatusResponse {
  demonstration_benchmark_status: string;
  official_accounting_spec_status: string;
  official_empirical_risk_evaluation_status: string;
  notice: string;
  benchmark_report?: {
    benchmark_timestamp: string;
    dataset_evaluated: string;
    mechanism: string;
    trials_per_setting: number;
    epsilons_tested: number[];
    overall_summary_by_epsilon: Record<string, {
      avg_mae: number;
      avg_rmse: number;
      avg_rel_error_pct: number;
      theoretical_stddev: number;
    }>;
    conclusions: string[];
  } | null;
}

