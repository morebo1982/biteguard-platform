import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, getToken, setToken } from './api';

function response(status: number, body?: unknown) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: vi.fn().mockResolvedValue(body),
  } as unknown as Response;
}

describe('IAM API client', () => {
  beforeEach(() => {
    localStorage.clear();
    setToken(null);
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('adds the bearer token and JSON content type', async () => {
    setToken('access-token');
    vi.mocked(fetch).mockResolvedValue(response(200, { ok: true }));
    await expect(api('/users', { method: 'POST', body: '{}' })).resolves.toEqual({ ok: true });
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get('Authorization')).toBe('Bearer access-token');
    expect(headers.get('Content-Type')).toBe('application/json');
  });

  it('removes the session and dispatches the unauthorized event on 401', async () => {
    setToken('expired-token');
    const handler = vi.fn();
    window.addEventListener('bg:unauthorized', handler);
    vi.mocked(fetch).mockResolvedValue(response(401));
    await expect(api('/users')).rejects.toThrow('نشست شما منقضی شده است');
    expect(getToken()).toBeNull();
    expect(localStorage.getItem('bg_access_token')).toBeNull();
    expect(handler).toHaveBeenCalledTimes(1);
    window.removeEventListener('bg:unauthorized', handler);
  });

  it('returns a clear permission error on 403', async () => {
    vi.mocked(fetch).mockResolvedValue(response(403));
    await expect(api('/users')).rejects.toThrow('دسترسی لازم برای این عملیات را ندارید (403)');
  });

  it('uses the API detail message for other errors', async () => {
    vi.mocked(fetch).mockResolvedValue(response(422, { detail: 'داده نامعتبر است' }));
    await expect(api('/users')).rejects.toThrow('داده نامعتبر است');
  });

  it('reads the structured error envelope used by the FastAPI application', async () => {
    vi.mocked(fetch).mockResolvedValue(response(404, { error: { code: 'NOT_FOUND', message: 'کاربر پیدا نشد' } }));
    await expect(api('/users/missing')).rejects.toThrow('کاربر پیدا نشد');
  });

  it('handles no-content responses without attempting JSON parsing', async () => {
    vi.mocked(fetch).mockResolvedValue(response(204));
    await expect(api('/users/user-1/roles/role-1', { method: 'DELETE' })).resolves.toBeUndefined();
  });
});
