import { 
  SystemStatusResponse, 
  ReadinessResponse,
  DatasetMetadata,
  QueryPreviewResponse,
  QueryRunResponse,
  BudgetStatusResponse,
  AuditVerificationResponse,
  EvaluationStatusResponse,
  PrivacyReceipt,
  UserSession
} from '../types/system';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';
const REQUEST_TIMEOUT_MS = 6000;

export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public isTimeout: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Executes a fetch request with timeout protection and auth header support.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const headers = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    };

    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers,
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error: unknown) {
    clearTimeout(timeoutId);
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError('Request timed out while contacting backend gateway', undefined, true);
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error: failed to establish connection with backend'
    );
  }
}

/**
 * Retrieves the comprehensive system status from the backend.
 */
export async function getSystemStatus(): Promise<SystemStatusResponse> {
  const url = `${API_BASE_URL}/api/system/status`;
  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new ApiError(
      `Backend returned error status HTTP ${response.status}`,
      response.status
    );
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new ApiError('Invalid response: Backend payload is not valid JSON');
  }

  const typed = data as SystemStatusResponse;
  if (!typed.project_name || typeof typed.privacy_releases_enabled !== 'boolean' || !Array.isArray(typed.capabilities)) {
    throw new ApiError('Invalid schema: Missing required fields in backend status payload');
  }

  return typed;
}

/**
 * Retrieves the readiness probe from the backend.
 */
export async function getReadiness(): Promise<ReadinessResponse> {
  const url = `${API_BASE_URL}/ready`;
  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new ApiError(`Readiness probe failed with status HTTP ${response.status}`, response.status);
  }

  return (await response.json()) as ReadinessResponse;
}

// -------------------------------------------------------------
// MVP AUTHENTICATION & SESSION
// -------------------------------------------------------------

export async function loginUser(username: string, password: string): Promise<UserSession> {
  const url = `${API_BASE_URL}/api/auth/login`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Login failed', response.status);
  }

  return {
    username: data.username || data.user_id,
    role: data.role,
    token: data.token,
    expires_at: data.expires_at,
  };
}

export async function logoutUser(token: string): Promise<void> {
  const url = `${API_BASE_URL}/api/auth/logout`;
  await fetchWithTimeout(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getMe(token: string): Promise<UserSession> {
  const url = `${API_BASE_URL}/api/me`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Session invalid or expired', response.status);
  }

  return {
    username: data.username || data.user_id,
    role: data.role,
    token: token,
    expires_at: data.expires_at || new Date(Date.now() + 86400000).toISOString(),
  };
}

// -------------------------------------------------------------
// MVP DATASETS & QUERIES
// -------------------------------------------------------------

export async function getDatasets(token: string): Promise<DatasetMetadata[]> {
  const url = `${API_BASE_URL}/api/datasets`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch datasets', response.status);
  }
  const rawList: Record<string, any>[] = Array.isArray(data) ? data : [];
  return rawList.map((d) => {
    const fields = d.approved_fields || d.allowed_fields || {};
    const title = d.title || d.name || d.dataset_id || 'Dataset';
    return {
      dataset_id: d.dataset_id,
      title,
      name: title,
      description: d.description || '',
      total_records: typeof d.total_records === 'number' ? d.total_records : 0,
      privacy_unit: d.privacy_unit || 'record_id',
      version: d.version || '1.0.0',
      approved_fields: fields,
      allowed_fields: fields,
      is_official_dataset: Boolean(d.is_official_dataset),
      sensitive_fields_protected: d.sensitive_fields_protected || [],
      allowed_operators: d.allowed_operators || ['equals'],
    };
  });
}

export async function previewQuery(
  token: string,
  payload: { dataset_id: string; field: string; operator: string; value: string; epsilon: number }
): Promise<QueryPreviewResponse> {
  const url = `${API_BASE_URL}/api/queries/preview`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Query preview rejected', response.status);
  }
  return {
    is_valid: true,
    dataset_id: data.dataset_id || payload.dataset_id,
    field: data.field || payload.field,
    operator: data.operator || payload.operator,
    value: data.value ?? payload.value,
    epsilon: data.epsilon ?? payload.epsilon,
    query_fingerprint: data.query_fingerprint || '',
    estimated_privacy_cost: data.estimated_privacy_cost ?? payload.epsilon,
    current_remaining_budget: data.current_remaining_budget,
    is_budget_sufficient: data.is_budget_sufficient ?? true,
    is_cached_release_available: Boolean(data.is_cached_release_available),
    policy_status: data.policy_status || 'APPROVED',
    policy_check: data.policy_status || 'PASSED',
    global_sensitivity: 1.0,
    privacy_unit: payload.dataset_id === 'health' ? 'patient_id' : 'account_id',
    epsilon_requested: data.epsilon ?? payload.epsilon,
    message: data.message || 'Query parameters validated against dataset policy',
  };
}

export async function runQuery(
  token: string,
  payload: {
    dataset_id: string;
    field: string;
    operator: string;
    value: string;
    epsilon: number;
    idempotency_key?: string;
  }
): Promise<QueryRunResponse> {
  const url = `${API_BASE_URL}/api/queries/run`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Differential privacy query rejected', response.status);
  }
  return data;
}

export async function getBudgetStatus(paramA: string, paramB: string): Promise<BudgetStatusResponse> {
  // Support both (datasetId, token) and (token, datasetId) cleanly
  let datasetId = 'health';
  let token = '';

  const knownDatasets = ['health', 'financial', 'education'];
  if (knownDatasets.includes(paramA.toLowerCase())) {
    datasetId = paramA;
    token = paramB;
  } else if (knownDatasets.includes(paramB.toLowerCase())) {
    datasetId = paramB;
    token = paramA;
  } else {
    // Default fallback: paramA is datasetId, paramB is token
    datasetId = paramA;
    token = paramB;
  }

  const url = `${API_BASE_URL}/api/budget/${datasetId}`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch budget status', response.status);
  }
  return data;
}

export async function getReceipt(token: string, receiptId: string): Promise<PrivacyReceipt> {
  const url = `${API_BASE_URL}/api/receipts/${receiptId}`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch receipt', response.status);
  }
  return data;
}

export async function verifyAuditLedger(token: string): Promise<AuditVerificationResponse> {
  const url = `${API_BASE_URL}/api/audit/verify`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Audit verification failed', response.status);
  }
  return data;
}

export async function getEvaluationStatus(token: string): Promise<EvaluationStatusResponse> {
  const url = `${API_BASE_URL}/api/evaluation/status`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Evaluation status query failed', response.status);
  }
  return data;
}

export async function getSecurityEvents(token: string, limit = 50): Promise<import('../types/system').SecurityEvent[]> {
  const url = `${API_BASE_URL}/api/security/events?limit=${limit}`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch security events', response.status);
  }
  return data;
}

export async function getSecurityAlerts(token: string, limit = 50): Promise<import('../types/system').SecurityAlert[]> {
  const url = `${API_BASE_URL}/api/security/alerts?limit=${limit}`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch security alerts', response.status);
  }
  return data;
}

export async function getUsers(token: string): Promise<import('../types/system').UserListItem[]> {
  const url = `${API_BASE_URL}/api/users`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to fetch user list', response.status);
  }
  return data;
}

export async function unlockUser(token: string, username: string): Promise<{ unlocked: boolean; message: string }> {
  const url = `${API_BASE_URL}/api/users/${username}/unlock`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to unlock user account', response.status);
  }
  return data;
}

// -------------------------------------------------------------
// PHASE 6: RECEIPT CRYPTOGRAPHIC VERIFICATION & AUDIT RETRIEVAL
// -------------------------------------------------------------

export async function verifyReceipt(token: string, receiptId: string): Promise<import('../types/system').ReceiptVerificationResponse> {
  const url = `${API_BASE_URL}/api/receipts/${receiptId}/verify`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Cryptographic receipt verification request failed', response.status);
  }
  return data;
}

export async function getAuditEntries(
  token: string,
  params?: { limit?: number; offset?: number; dataset_id?: string; search?: string }
): Promise<import('../types/system').AuditEntriesResponse> {
  const q = new URLSearchParams();
  if (params?.limit) q.set('limit', String(params.limit));
  if (params?.offset) q.set('offset', String(params.offset));
  if (params?.dataset_id) q.set('dataset_id', params.dataset_id);
  if (params?.search) q.set('search', params.search);

  const qs = q.toString() ? `?${q.toString()}` : '';
  const url = `${API_BASE_URL}/api/audit/entries${qs}`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to retrieve audit ledger entries', response.status);
  }
  return data;
}

// -------------------------------------------------------------
// PHASE 6: INCIDENT RESPONSE & SECURITY MONITORING
// -------------------------------------------------------------

export async function getIncidentStatus(token: string): Promise<import('../types/system').IncidentStatusResponse> {
  const url = `${API_BASE_URL}/api/incident/status`;
  const response = await fetchWithTimeout(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to retrieve gateway incident status', response.status);
  }
  return data;
}

export async function transitionIncidentState(
  token: string,
  newState: string,
  reason: string
): Promise<import('../types/system').IncidentStatusResponse> {
  const url = `${API_BASE_URL}/api/incident/transition`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ new_state: newState, reason }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to transition incident state', response.status);
  }
  return data;
}

export async function acknowledgeAlert(token: string, alertId: string): Promise<any> {
  const url = `${API_BASE_URL}/api/security/alerts/${alertId}/acknowledge`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to acknowledge alert', response.status);
  }
  return data;
}

export async function resolveAlert(
  token: string,
  alertId: string,
  resolutionNotes: string,
  status: 'RESOLVED' | 'FALSE_POSITIVE' = 'RESOLVED'
): Promise<any> {
  const url = `${API_BASE_URL}/api/security/alerts/${alertId}/resolve`;
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ resolution_notes: resolutionNotes, status }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiError(data.detail || 'Failed to resolve alert', response.status);
  }
  return data;
}


