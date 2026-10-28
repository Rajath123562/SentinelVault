import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../src/App';
import { SystemStatusResponse } from '../src/types/system';

const mockSuccessStatus: SystemStatusResponse = {
  project_name: 'HOTFIX Privacy-by-Design Analytics Gateway',
  project_code: 'HOTFIX',
  team_id: 'UG 59',
  current_phase: 'Phase 1',
  application_health: 'HEALTHY',
  configuration_valid: true,
  privacy_releases_enabled: false,
  release_disabled_reason: 'Phase 1 foundation: Differential privacy engine and official accounting specification not yet configured',
  official_spec_status: 'NOT_CONFIGURED',
  official_harness_status: 'NOT_INTEGRATED',
  server_time: '2026-10-28T10:00:00Z',
  capabilities: [
    {
      id: 'CAP-01-FOUNDATION',
      name: 'Application Foundation & Lifecycle',
      status: 'IMPLEMENTED',
      phase: 'Phase 1',
      description: 'FastAPI application structure, routing, schemas, and lifecycle management.',
    },
    {
      id: 'CAP-03-AUTH-RBAC',
      name: 'Authentication & Role-Based Access Control',
      status: 'PLANNED',
      phase: 'Phase 2',
      description: 'Credential verification and temporary lockout.',
    },
    {
      id: 'CAP-06-DP-ENGINE',
      name: 'Differential Privacy Engine',
      status: 'PLANNED',
      phase: 'Phase 3',
      description: 'Verified DP noise mechanisms conforming to official Track 4 specification.',
    },
  ],
};

describe('HOTFIX Phase 1 Frontend Acceptance Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('1. Application renders successfully and displays title', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSuccessStatus),
      } as Response)
    );

    render(<App />);

    expect(screen.getAllByText(/HOTFIX/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Team UG 59/i).length).toBeGreaterThanOrEqual(1);
  });

  it('2. Successful API response displays actual system status', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSuccessStatus),
      } as Response)
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Backend Connected')).toBeInTheDocument();
      expect(screen.getByText('HEALTHY')).toBeInTheDocument();
      expect(screen.getByText('VALIDATED')).toBeInTheDocument();
    });
  });

  it('3. Unavailable backend produces understandable connection error', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.reject(new Error('Failed to fetch'))
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Communication Unavailable/i)).toBeInTheDocument();
      expect(screen.getByText('Backend Offline')).toBeInTheDocument();
    });
  });

  it('4. Invalid response payload is handled safely', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ unexpected: 'garbage_data' }),
      } as Response)
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Communication Unavailable/i)).toBeInTheDocument();
    });
  });

  it('5. Privacy releases disabled by backend are never displayed as enabled', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSuccessStatus),
      } as Response)
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Fail Closed')).toBeInTheDocument();
      expect(screen.getByText('DISABLED')).toBeInTheDocument();
      expect(screen.queryByText(/Releases Operational/i)).not.toBeInTheDocument();
    });
  });

  it('6. Unavailable future functionality is not presented as implemented', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSuccessStatus),
      } as Response)
    );

    render(<App />);

    await waitFor(() => {
      const plannedBadges = screen.getAllByText(/PLANNED/i);
      expect(plannedBadges.length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('Authentication & Role-Based Access Control')).toBeInTheDocument();
      expect(screen.getByRole('cell', { name: 'Differential Privacy Engine' })).toBeInTheDocument();
    });
  });
});
