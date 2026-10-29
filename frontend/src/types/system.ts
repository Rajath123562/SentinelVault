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

export interface SecurityEvent {
  event_id: string;
  event_type: string;
  outcome: string;
  actor?: string;
  resource?: string;
  action?: string;
  source_ip?: string;
  details?: string;
  timestamp: string;
}

export type UserRole = 'analyst' | 'data_steward' | 'auditor' | 'admin';

export interface UserSession {
  username: string;
  role: UserRole;
  token: string;
  expires_at: string;
}

export interface DatasetMetadata {
  dataset_id: string;
  title?: string;
  name?: string;
  description: string;
  total_records: number;
  privacy_unit: string;
  version?: string;
  sensitive_fields_protected?: string[];
  approved_fields?: Record<string, string[]>;
  allowed_fields?: Record<string, string[]>;
  allowed_operators?: string[];
  is_official_dataset: boolean;
}

export interface QueryPreviewResponse {
  is_valid: boolean;
  dataset_id: string;
  field: string;
  operator: string;
  value: any;
  epsilon: number;
  query_fingerprint: string;
  estimated_privacy_cost?: number;
  current_remaining_budget?: number;
  is_budget_sufficient?: boolean;
  is_cached_release_available?: boolean;
  policy_status?: string;
  policy_check?: string;
  global_sensitivity?: number;
  privacy_unit?: string;
  epsilon_requested?: number;
  message?: string;
  logical_query?: string;
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

export interface BudgetRecentRelease {
  release_id: string;
  query_description: string;
  epsilon_spent: number;
  cumulative_epsilon: number;
  timestamp: string;
}

export interface BudgetStatusResponse {
  dataset_id: string;
  cap_epsilon: number;
  spent_epsilon: number;
  remaining_epsilon: number;
  accounting_notice: string;
  updated_at: string;
  recent_releases?: BudgetRecentRelease[];
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

export interface UserListItem {
  username: string;
  user_id: string;
  role: string;
  status: string;
  failed_attempts: number;
  locked_until?: string | null;
  created_at: string;
  mfa_enabled: boolean;
}

export interface SecurityAlert {
  alert_id: string;
  rule_id?: string;
  title?: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | string;
  status?: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'FALSE_POSITIVE' | string;
  actor?: string | null;
  resource?: string | null;
  details?: string | null;
  evidence?: Record<string, any>;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
  resolution_notes?: string | null;
  created_at?: string;
  updated_at?: string;
  timestamp?: string;
  event_type?: string;
  outcome?: string;
  source_ip?: string | null;
}

export interface ReceiptVerificationCheck {
  name: string;
  passed: boolean;
  details: string;
}

export interface ReceiptVerificationResponse {
  receipt_id: string;
  is_valid: boolean;
  status: 'VERIFIED' | 'TAMPERED' | 'REVOKED' | 'INVALID';
  verified_at: string;
  checks: Record<string, ReceiptVerificationCheck>;
  receipt_summary: Record<string, any>;
  error?: string;
}

export interface AuditEntryItem {
  entry_id: string;
  timestamp: string;
  event_type: string;
  dataset_id: string;
  user_id: string;
  query_fingerprint: string;
  epsilon_spent: number;
  entry_hash: string;
  previous_entry_hash: string;
  status: string;
}

export interface AuditEntriesResponse {
  total: number;
  limit: number;
  offset: number;
  entries: AuditEntryItem[];
  ledger_valid: boolean;
}

export interface IncidentStatusResponse {
  current_state: 'NORMAL' | 'RESTRICTED' | 'RELEASES_DISABLED';
  trigger_source: string;
  reason: string;
  updated_by: string;
  updated_at: string;
  releases_allowed: boolean;
  max_permitted_epsilon: number | null;
  status_badge: string;
}

export type ActiveScreen = 
  | 'dashboard'
  | 'datasets'
  | 'query'
  | 'results'
  | 'budget'
  | 'receipt'
  | 'audit'
  | 'security'
  | 'users'
  | 'settings'
  | 'about'
  | 'denied'
  | '404';


