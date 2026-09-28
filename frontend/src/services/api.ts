/**
 * Resilient API client with automatic offline/timeout detection and mock data fallback.
 */

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL as string) || 'http://localhost:8000';

export interface ApiResponse<T> {
  data: T;
  isMock: boolean;
  error?: string;
}

export async function fetchWithFallback<T>(
  endpoint: string,
  options: RequestInit = {},
  mockFallback: () => T,
  timeoutMs: number = 3000
): Promise<ApiResponse<T>> {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = endpoint.startsWith('http') ? endpoint : `${BACKEND_URL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    clearTimeout(id);

    if (!response.ok) {
      throw new Error(`Server returned HTTP ${response.status}: ${response.statusText}`);
    }

    const contentType = response.headers.get('content-type');
    let data: any;
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    return {
      data: data as T,
      isMock: false,
    };
  } catch (err: any) {
    clearTimeout(id);
    // Graceful fallback to mock data on offline or connection failure
    return {
      data: mockFallback(),
      isMock: true,
      error: err.name === 'AbortError' ? 'Backend request timed out' : err.message,
    };
  }
}
