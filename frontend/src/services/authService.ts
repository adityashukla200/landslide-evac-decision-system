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
