/**
 * API utilities for HeyAmin web app.
 *
 * API URL Resolution Strategy
 * ===========================
 *
 * SAME-ORIGIN MODE (Production Target):
 * - Web and API served from same origin via reverse proxy
 * - API accessible at path like "/api" (same origin, no CORS issues)
 * - Cookies work with SameSite=Lax (no cross-site complexity)
 * - Client calls: "/api/health", "/api/auth/me", etc.
 *
 * CROSS-ORIGIN MODE (Local Development):
 * - Web at localhost:3000, API at localhost:8000
 * - Requires CORS configuration
 * - Uses NEXT_PUBLIC_API_BASE_URL to specify full API URL
 *
 * Environment Variables:
 * - NEXT_PUBLIC_API_BASE_URL: Full API URL for cross-origin (e.g., http://localhost:8000)
 * - NEXT_PUBLIC_API_PREFIX: Same-origin API path prefix (default: "/api")
 * - API_INTERNAL_BASE_URL: Server-side API URL for Docker SSR (e.g., http://api:8000)
 *
 * Resolution Priority:
 * 1. If NEXT_PUBLIC_API_BASE_URL is set → use it (cross-origin mode)
 * 2. Else use NEXT_PUBLIC_API_PREFIX → same-origin mode ("/api")
 *
 * Docker Notes:
 * - SSR runs inside container, needs API_INTERNAL_BASE_URL (http://api:8000)
 * - Browser runs on host, needs NEXT_PUBLIC_API_BASE_URL (http://localhost:8000)
 */

export interface HealthResponse {
  status: string;
}

/**
 * Default API prefix for same-origin mode.
 * In production, API will be mounted at this path behind a reverse proxy.
 */
const DEFAULT_API_PREFIX = '/api';

/**
 * Check if code is running on the server.
 */
export function isServer(): boolean {
  return typeof window === 'undefined';
}

/**
 * Get the API prefix for same-origin mode.
 * Used when NEXT_PUBLIC_API_BASE_URL is not set.
 */
export function getApiPrefix(): string {
  return process.env.NEXT_PUBLIC_API_PREFIX || DEFAULT_API_PREFIX;
}

/**
 * Check if we're in same-origin mode.
 * Same-origin mode: API at /api path (no full URL specified)
 * Cross-origin mode: API at different origin (full URL specified)
 */
export function isSameOriginMode(): boolean {
  // Cross-origin if NEXT_PUBLIC_API_BASE_URL is explicitly set
  return !process.env.NEXT_PUBLIC_API_BASE_URL;
}

/**
 * Get the API base URL for CLIENT-SIDE (browser) requests ONLY.
 *
 * Resolution:
 * 1. If NEXT_PUBLIC_API_BASE_URL set → use it (cross-origin mode, e.g., http://localhost:8000)
 * 2. Else use NEXT_PUBLIC_API_PREFIX → same-origin mode (e.g., "/api")
 *
 * Same-origin mode works when:
 * - Running behind Caddy proxy (https://localhost)
 * - NEXT_PUBLIC_API_BASE_URL is NOT set
 * - Client calls relative URLs like /api/health
 *
 * NEVER call this from server-side code.
 */
export function getClientApiBaseUrl(): string {
  // NEXT_PUBLIC_* vars are inlined at build time for client bundles
  const explicitUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (explicitUrl) {
    // Cross-origin mode: full URL specified
    return explicitUrl;
  }
  // Same-origin mode: use prefix (works with Caddy proxy at https://localhost)
  // Client calls /api/* which reverse proxy routes to API service
  return getApiPrefix();
}

/**
 * Get the API base URL for SERVER-SIDE requests ONLY.
 *
 * Resolution:
 * 1. API_INTERNAL_BASE_URL → for Docker SSR (http://api:8000)
 * 2. NEXT_PUBLIC_API_BASE_URL → for local dev outside Docker
 * 3. Fallback to localhost:8000
 *
 * NEVER call this from client-side code.
 */
export function getServerApiBaseUrl(): string {
  // API_INTERNAL_BASE_URL is NOT prefixed with NEXT_PUBLIC_
  // so it's only available on the server (not exposed to browser bundle)
  return (
    process.env.API_INTERNAL_BASE_URL ||
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    'http://localhost:8000'
  );
}

/**
 * Get the appropriate API base URL based on execution context.
 */
export function getApiBaseUrl(): string {
  return isServer() ? getServerApiBaseUrl() : getClientApiBaseUrl();
}

/**
 * Resolve an endpoint against the configured API base URL.
 *
 * This keeps `/api/...` routes working in both modes:
 * - same-origin mode: baseUrl is `/api`, so `/api/v1/foo` stays `/api/v1/foo`
 * - cross-origin mode: baseUrl is `https://host`, so `/api/v1/foo` becomes
 *   `https://host/api/v1/foo`
 */
export function resolveApiUrl(
  endpoint: string,
  mode?: 'client' | 'server'
): string {
  const resolvedMode = mode || (isServer() ? 'server' : 'client');
  const baseUrl =
    resolvedMode === 'server' ? getServerApiBaseUrl() : getClientApiBaseUrl();
  const normalizedBaseUrl = baseUrl.replace(/\/$/, '');
  const normalizedEndpoint = endpoint.startsWith('/')
    ? endpoint
    : `/${endpoint}`;

  if (
    normalizedBaseUrl.endsWith('/api') &&
    normalizedEndpoint.startsWith('/api/')
  ) {
    return `${normalizedBaseUrl}${normalizedEndpoint.slice(4)}`;
  }

  return `${normalizedBaseUrl}${normalizedEndpoint}`;
}

/**
 * Get API configuration info for debugging/verification.
 */
export function getApiConfig(): {
  mode: 'same-origin' | 'cross-origin';
  clientUrl: string;
  serverUrl: string;
  prefix: string;
  envVars: {
    NEXT_PUBLIC_API_BASE_URL: string | undefined;
    NEXT_PUBLIC_API_PREFIX: string | undefined;
    API_INTERNAL_BASE_URL: string | undefined;
  };
} {
  return {
    mode: isSameOriginMode() ? 'same-origin' : 'cross-origin',
    clientUrl: getClientApiBaseUrl(),
    serverUrl: getServerApiBaseUrl(),
    prefix: getApiPrefix(),
    envVars: {
      NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
      NEXT_PUBLIC_API_PREFIX: process.env.NEXT_PUBLIC_API_PREFIX,
      API_INTERNAL_BASE_URL: process.env.API_INTERNAL_BASE_URL,
    },
  };
}

/**
 * Fetch health status from the API.
 *
 * @param mode - 'client' for browser requests, 'server' for server-side requests
 * @returns Health response or throws an error
 */
export async function fetchHealth(
  mode: 'client' | 'server' = 'client'
): Promise<HealthResponse> {
  const baseUrl =
    mode === 'server' ? getServerApiBaseUrl() : getClientApiBaseUrl();
  const url = `${baseUrl}/health`;

  const response = await fetch(url, {
    cache: 'no-store', // Always fetch fresh data
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Generic API fetch wrapper with proper URL handling.
 *
 * @param endpoint - API endpoint (e.g., '/health', '/users')
 * @param options - Fetch options
 * @param mode - 'client' or 'server' (auto-detected if not specified)
 */
export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {},
  mode?: 'client' | 'server'
): Promise<T> {
  const url = resolveApiUrl(endpoint, mode);

  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}
