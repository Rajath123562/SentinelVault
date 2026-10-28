import { SystemStatusResponse, ReadinessResponse } from '../types/system';

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
 * Executes a fetch request with timeout protection.
 */
async function fetchWithTimeout(url: string, timeoutMs: number = REQUEST_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
      },
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

  // Type and structure validation
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

