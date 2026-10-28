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
    username: data.user_id,
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
  return data;
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
  return data;
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

export async function getBudgetStatus(token: string, datasetId: string): Promise<BudgetStatusResponse> {
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

