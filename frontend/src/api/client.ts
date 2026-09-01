/**
 * Typed HTTP client for the SUS backend API.
 *
 * Centralizes fetch logic, error handling, and base URL configuration.
 * All API communication goes through this client — components never call
 * fetch() directly.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiError {
  status: number;
  message: string;
  detail?: unknown;
}

export interface ApiResponse<T> {
  data: T;
  ok: boolean;
  error?: ApiError;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const url = `${API_BASE_URL}${path}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> ?? {}),
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let detail: unknown;
      try {
        detail = await response.json();
      } catch {
        detail = await response.text();
      }

      return {
        data: null as unknown as T,
        ok: false,
        error: {
          status: response.status,
          message: `HTTP ${response.status}: ${response.statusText}`,
          detail,
        },
      };
    }

    const data: T = await response.json();
    return { data, ok: true };
  } catch (err) {
    // Network error, DNS failure, CORS, etc.
    const message =
      err instanceof Error ? err.message : 'Network error: unable to reach the server';

    return {
      data: null as unknown as T,
      ok: false,
      error: {
        status: 0,
        message,
      },
    };
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export const apiClient = {
  get<T>(path: string): Promise<ApiResponse<T>> {
    return request<T>(path, { method: 'GET' });
  },

  post<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
    return request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },

  patch<T>(path: string, body?: unknown): Promise<ApiResponse<T>> {
    return request<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
    });
  },
};

export { API_BASE_URL };
