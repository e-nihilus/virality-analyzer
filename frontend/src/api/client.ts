const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

/**
 * Auth token provider — will be set by AureaSuite's ClerkProvider
 * when this module runs embedded. For standalone dev, remains null.
 */
let authTokenProvider: (() => Promise<string | null>) | null = null;

export function setAuthTokenProvider(provider: () => Promise<string | null>) {
  authTokenProvider = provider;
}

export function buildUrl(path: string): string {
  return `${BASE_URL}${path}`;
}

export function getAuthHeaders(): Record<string, string> {
  // Synchronous version for FormData uploads where we can't await.
  // The token will be set via the provider for apiFetch calls.
  return {};
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers: Record<string, string> = {
    "Accept": "application/json",
    ...(init?.headers as Record<string, string>),
  };

  // Inject auth token if provider is configured (AureaSuite integration)
  if (authTokenProvider) {
    const token = await authTokenProvider();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const res = await fetch(buildUrl(path), {
    ...init,
    headers,
  });

  if (!res.ok) {
    throw new ApiError(res.status, `${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<T>;
}
