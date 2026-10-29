import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from '../src/App';
import { SystemStatusResponse } from '../src/types/system';

const mockSuccessStatus: SystemStatusResponse = {
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
      status: 'IMPLEMENTED',
      phase: 'Phase 2',
      description: 'Credential verification and temporary lockout.',
    },
    {
      id: 'CAP-06-DP-ENGINE',
      name: 'Differential Privacy Engine',
      status: 'IMPLEMENTED',
      phase: 'Phase 3',
      description: 'Verified DP noise mechanisms conforming to official Track 4 specification.',
    },
  ],
};

describe('SentinelVault Frontend App Integration Tests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('1. Application renders successfully and displays product title and team', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSuccessStatus),
      } as Response)
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getAllByText(/SentinelVault/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Team UG 59/i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText(/Gateway Authentication/i)).toBeInTheDocument();
    });
  });

  it('2. Shows public About & Trust Pillars screen when toggled', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockSuccessStatus),
      } as Response)
    );

    render(<App />);

    const aboutToggle = await screen.findByText(/About & Trust Pillars/i);
    aboutToggle.click();

    await waitFor(() => {
      expect(screen.getAllByText(/Analyze Data. Don't Expose It./i).length).toBeGreaterThanOrEqual(1);
      expect(screen.getByText('Privacy Preserving')).toBeInTheDocument();
      expect(screen.getByText('Secure & Compliant')).toBeInTheDocument();
      expect(screen.getByText('Audit Ready')).toBeInTheDocument();
    });
  });

  it('3. Unavailable backend produces visible connection error alert', async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.reject(new Error('Connection refused: Gateway offline'))
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Backend Communication Unavailable/i)).toBeInTheDocument();
      expect(screen.getByText(/Connection refused: Gateway offline/i)).toBeInTheDocument();
    });
  });
});
