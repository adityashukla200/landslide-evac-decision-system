/**
 * Officer Authentication Service with JWT handling and refresh flow.
 */

import { AuthTokenResponse, OfficerProfile } from '../types';
import { BACKEND_URL, setTokenProvider } from './api';

const AUTH_BASE = BACKEND_URL ? `${BACKEND_URL}/api/v1/auth` : '/api/v1/auth';

let inMemoryAccessToken: string | null = null;
let tokenExpiresAt: number = 0;

setTokenProvider(() => inMemoryAccessToken);

export const authService = {
  getAccessToken(): string | null {
    return inMemoryAccessToken;
  },

  setAccessToken(token: string | null, expiresInSec: number = 1800) {
    inMemoryAccessToken = token;
    if (token) {
      tokenExpiresAt = Date.now() + (expiresInSec - 30) * 1000; // 30s buffer
      // Store flag in sessionStorage so page reload triggers refresh
      sessionStorage.setItem('ews_has_session', 'true');
    } else {
      tokenExpiresAt = 0;
      sessionStorage.removeItem('ews_has_session');
    }
  },

  isTokenExpired(): boolean {
    if (!inMemoryAccessToken) return true;
    return Date.now() >= tokenExpiresAt;
  },

  async login(username: string, password: string): Promise<AuthTokenResponse> {
    try {
      const res = await fetch(`${AUTH_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include', // sends and receives cookies
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Authentication failed.' }));
        throw new Error(err.detail || 'Login failed.');
      }

      const data: AuthTokenResponse = await res.json();
      this.setAccessToken(data.access_token, data.expires_in);
      return data;
    } catch (err: any) {
      // If error is network unreachable ("Failed to fetch"):
      if (!err.message || err.message === 'Failed to fetch' || err.message.includes('fetch') || err.message.includes('NetworkError')) {
        const u = username.toLowerCase().trim();
        const p = password.trim();

        const demoAccounts = [
          {
            id: 'OFF_002',
            name: 'Maj. Vikram Negi',
            role: 'officer' as const,
            district: 'Uttarkashi',
            email: 'ndrf.uttarkashi@gov.in',
            phone: '+919412000002',
            demoPass: 'NDRF#Rescue2026',
          },
          {
            id: 'OFF_001',
            name: 'Dr. Rajesh Sharma',
            role: 'admin' as const,
            district: 'Uttarkashi',
            email: 'ddmo.uttarkashi@uk.gov.in',
            phone: '+919412000001',
            demoPass: 'Uttarkashi@2026',
          },
          {
            id: 'OFF_003',
            name: 'Pooja Rawat',
            role: 'officer' as const,
            district: 'Bhatwari Block',
            email: 'bdo.bhatwari@uk.gov.in',
            phone: '+919412000003',
            demoPass: 'Bhatwari@2026',
          },
        ];

        const match = demoAccounts.find(
          (acc) => (acc.email.toLowerCase() === u || acc.phone === u) && acc.demoPass === p
        );

        if (match) {
          const fallbackResponse: AuthTokenResponse = {
            access_token: `demo_jwt_token_${Date.now()}`,
            refresh_token: `demo_refresh_token_${Date.now()}`,
            token_type: 'bearer',
            expires_in: 3600,
            officer: {
              id: match.id,
              name: match.name,
              role: match.role,
              district: match.district,
              email: match.email,
              phone: match.phone,
            },
          };
          this.setAccessToken(fallbackResponse.access_token, fallbackResponse.expires_in);
          sessionStorage.setItem('ews_offline_officer', JSON.stringify(fallbackResponse.officer));
          return fallbackResponse;
        }

        throw new Error('Backend server is offline. Please select a Quick Demo Account to authenticate.');
      }

      throw err;
    }
  },

  async refreshToken(): Promise<AuthTokenResponse | null> {
    try {
      const res = await fetch(`${AUTH_BASE}/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });

      if (!res.ok) {
        this.setAccessToken(null);
        return null;
      }

      const data: AuthTokenResponse = await res.json();
      this.setAccessToken(data.access_token, data.expires_in);
      return data;
    } catch {
      this.setAccessToken(null);
      return null;
    }
  },

  async logout(): Promise<void> {
    sessionStorage.removeItem('ews_offline_officer');
    try {
      await fetch(`${AUTH_BASE}/logout`, {
        method: 'POST',
        credentials: 'include',
      });
    } catch {
      // Ignore network errors on logout
    } finally {
      this.setAccessToken(null);
    }
  },

  async getMe(): Promise<OfficerProfile | null> {
    const offlineSaved = sessionStorage.getItem('ews_offline_officer');
    if (offlineSaved) {
      try {
        return JSON.parse(offlineSaved);
      } catch {
        // continue
      }
    }

    const token = await this.getValidToken();
    if (!token) return null;

    try {
      const res = await fetch(`${AUTH_BASE}/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        credentials: 'include',
      });

      if (!res.ok) return null;
      return await res.json();
    } catch {
      return null;
    }
  },

  async getValidToken(): Promise<string | null> {
    if (inMemoryAccessToken && !this.isTokenExpired()) {
      return inMemoryAccessToken;
    }
    // Attempt silent refresh if session was active
    if (sessionStorage.getItem('ews_has_session') === 'true') {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        return refreshed.access_token;
      }
    }
    return null;
  },
};
