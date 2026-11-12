import { demoApi } from './demo';

const BASE = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
).replace(/\/+$/, '');

export type Page<T> = {
  items: T[];
  page?: { total: number };
  total?: number;
};

export type User = {
  id: string;
  username: string;
  display_name: string;
  email: string | null;
  is_active: boolean;
  created_at: string;
};

export type CurrentUserProfile = {
  id: string;
  username: string;
  display_name: string;
  email: string | null;
  is_active: boolean;
  roles: string[];
  permissions: string[];
};

export type Role = {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_active: boolean;
  is_system: boolean;
};

export type Permission = {
  id: string;
  code: string;
  name: string;
  module: string;
  description: string | null;
};

export type Audit = {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  occurred_at: string;
  result: string;
  source: string;
  ip_address: string | null;
  context_data: Record<string, unknown> | null;
};

function readStoredToken(): string | null {
  try {
    return typeof localStorage !== 'undefined'
      ? localStorage.getItem('bg_access_token')
      : null;
  } catch {
    return null;
  }
}

let token: string | null = readStoredToken();

export function setToken(value: string | null): void {
  token = value;

  try {
    if (typeof localStorage !== 'undefined') {
      if (value) {
        localStorage.setItem('bg_access_token', value);
      } else {
        localStorage.removeItem('bg_access_token');
      }
    }
  } catch {
    // Keep the in-memory token if browser storage is unavailable.
  }
}

export function getToken(): string | null {
  return token;
}

function extractErrorMessage(body: unknown, status: number): string {
  const fallback = `خطای سرور (${status})`;

  if (!body || typeof body !== 'object') {
    return fallback;
  }

  const data = body as Record<string, unknown>;
  const error = data.error;

  const candidate =
    data.detail ??
    (typeof error === 'object' && error !== null
      ? (error as Record<string, unknown>).message
      : undefined) ??
    data.message;

  if (typeof candidate === 'string') {
    return candidate;
  }

  if (Array.isArray(candidate)) {
    return candidate
      .map((item: unknown) => {
        if (typeof item === 'string') {
          return item;
        }

        if (
          typeof item === 'object' &&
          item !== null &&
          'msg' in item
        ) {
          return String((item as { msg: unknown }).msg);
        }

        return String(item);
      })
      .join('، ');
  }

  return fallback;
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  if (import.meta.env.MODE === 'demo') {
    return demoApi<T>(path, init);
  }
  const headers = new Headers(init.headers);

  headers.set('Accept', 'application/json');

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Do not set JSON Content-Type for FormData.
  if (
    typeof init.body === 'string' &&
    !headers.has('Content-Type')
  ) {
    headers.set('Content-Type', 'application/json');
  }

  let response: Response;

  try {
    response = await fetch(`${BASE}${path}`, {
      ...init,
      headers,
    });
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw error;
    }

    throw new Error(
      'ارتباط با سرور برقرار نشد. اتصال شبکه و آدرس API را بررسی کنید.',
    );
  }

  // Unauthorized: clear session and notify the application.
  if (response.status === 401) {
    setToken(null);

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new Event('bg:unauthorized'));
    }

    throw new Error(
      'نشست شما منقضی شده است؛ دوباره وارد شوید.',
    );
  }

  // Forbidden.
  if (response.status === 403) {
    throw new Error(
      'دسترسی لازم برای این عملیات را ندارید (403).',
    );
  }

  // No Content.
  if (response.status === 204) {
    return undefined as T;
  }

  // Read JSON response.
  let body: unknown = null;

  try {
    body = await response.json();
  } catch {
    body = null;
  }

  // Handle HTTP errors.
  if (!response.ok) {
    throw new Error(
      extractErrorMessage(body, response.status),
    );
  }

  // Successful response without a JSON body.
  if (body === null) {
    return undefined as T;
  }

  return body as T;
}
