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
