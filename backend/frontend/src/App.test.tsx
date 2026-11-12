
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import App from './App';
import { api, getToken, setToken } from './lib/api';

vi.mock('./lib/api', () => ({
  api: vi.fn(),
  getToken: vi.fn(),
  setToken: vi.fn(),
}));

const apiMock = vi.mocked(api);
const tokenMock = vi.mocked(getToken);
const setTokenMock = vi.mocked(setToken);

const user = {
  id: 'user-1',
  username: 'sara',
  display_name: 'سارا رضایی',
  email: 'sara@example.com',
  is_active: true,
  created_at: '2026-01-01T10:00:00Z',
};

const role = {
  id: 'role-1',
  code: 'admin',
  name: 'مدیر سیستم',
  description: null,
  is_active: true,
  is_system: false,
};

const permission = {
  id: 'permission-1',
  code: 'users.read',
  name: 'مشاهده کاربران',
  module: 'identity',
  description: null,
};

const audit = {
  id: 'audit-1',
  actor_user_id: 'user-1',
  action: 'user.created',
  entity_type: 'user',
  entity_id: 'user-1',
  occurred_at: '2026-01-01T10:00:00Z',
  result: 'success',
  source: 'api',
  ip_address: '127.0.0.1',
  context_data: null,
};

function renderApp(
  path = '/users',
  permissions = [
    'users.read',
    'users.create',
    'users.update',
    'users.activate',
    'users.deactivate',
    'users.roles.assign',
    'roles.read',
    'roles.create',
    'roles.update',
    'roles.activate',
    'roles.deactivate',
    'roles.delete',
    'roles.permissions.assign',
    'users.scopes.manage',
    'audit.read',
  ],
) {
  const originalImplementation = apiMock.getMockImplementation();

  apiMock.mockImplementation(async (requestPath, init) => {
    if (requestPath === '/auth/me') {
      return {
        id: user.id,
        username: user.username,
        display_name: user.display_name,
        email: user.email,
        is_active: true,
        roles: ['system_admin'],
        permissions,
      } as never;
    }

    return originalImplementation
      ? originalImplementation(requestPath, init)
      : ({} as never);
  });

  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('BiteGuard IAM frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    tokenMock.mockReturnValue('test-token');
    apiMock.mockReset();
  });

  it('redirects unauthenticated visitors to login', () => {
    tokenMock.mockReturnValue(null);

    renderApp('/users');

    expect(
      screen.getByRole('heading', {
        name: 'ورود به بایت گارد',
      }),
    ).toBeInTheDocument();
  });

  it('hides user creation when users.create is missing', async () => {
    const { container } = renderApp('/users', ['users.read']);

    await screen.findByRole('heading', { level: 1 });

    expect(
      container.querySelector('form.panel.inline'),
    ).not.toBeInTheDocument();
  });

  it('logs in, stores the access token and opens the users page', async () => {
    tokenMock.mockReturnValue(null);

    apiMock.mockResolvedValueOnce({
      access_token: 'new-token',
    } as never);

    renderApp('/login');

    fireEvent.change(
      screen.getByLabelText('نام کاربری'),
      {
        target: { value: 'sara' },
      },
    );

    fireEvent.change(
      screen.getByLabelText('گذرواژه'),
      {
        target: { value: 'secret' },
      },
    );

    fireEvent.click(
      screen.getByRole('button', {
        name: 'ورود امن',
      }),
    );

    expect(
      await screen.findByRole('heading', {
        name: 'مدیریت کاربران',
      }),
    ).toBeInTheDocument();

    expect(setTokenMock).toHaveBeenCalledWith('new-token');

    expect(apiMock).toHaveBeenCalledWith(
      '/auth/login',
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });

  it('shows login errors without exposing the protected area', async () => {
    tokenMock.mockReturnValue(null);

    apiMock.mockRejectedValueOnce(
      new Error('اعتبار ورود نامعتبر است'),
    );

    renderApp('/login');

    fireEvent.change(
      screen.getByLabelText('نام کاربری'),
      {
        target: { value: 'bad' },
      },
    );

    fireEvent.change(
      screen.getByLabelText('گذرواژه'),
      {
        target: { value: 'bad' },
      },
    );

    fireEvent.click(
      screen.getByRole('button', {
        name: 'ورود امن',
      }),
    );

    expect(
      await screen.findByRole('alert'),
    ).toHaveTextContent('اعتبار ورود نامعتبر است');
  });

  it('loads users and roles and filters the user list', async () => {
    apiMock.mockImplementation(async (path) => {
      if (path.startsWith('/users?')) {
        return { items: [user] } as never;
      }

      if (path.startsWith('/roles?')) {
        return { items: [role] } as never;
      }

      return {} as never;
    });

    renderApp();

    expect(
      await screen.findByText('sara'),
    ).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText('جستجو در کاربران...'),
      {
        target: { value: 'nobody' },
      },
    );

    expect(screen.queryByText('sara')).not.toBeInTheDocument();
  });

  it('creates a user and refreshes the user list', async () => {
    apiMock.mockImplementation(async (path, init) => {
      if (path.startsWith('/users?')) {
        return { items: [user] } as never;
      }

      if (path.startsWith('/roles?')) {
        return { items: [] } as never;
      }

      if (path === '/users' && init?.method === 'POST') {
        return user as never;
      }

      return {} as never;
    });

    renderApp();

    await screen.findByText('sara');

    fireEvent.change(
      screen.getByLabelText('نام کاربری جدید'),
      {
        target: { value: 'newuser' },
      },
    );

    fireEvent.change(
      screen.getByLabelText('نام نمایشی'),
      {
        target: { value: 'کاربر جدید' },
      },
    );

    fireEvent.click(
      screen.getByRole('button', {
        name: 'افزودن کاربر',
      }),
    );

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith(
        '/users',
        expect.objectContaining({
          method: 'POST',
        }),
      );
    });
  });

  it('toggles a user active state through the API', async () => {
    apiMock.mockImplementation(async (path) => {
      if (path.startsWith('/users?')) {
        return { items: [user] } as never;
      }

      if (path.startsWith('/roles?')) {
        return { items: [] } as never;
      }

      return user as never;
    });

    renderApp();

    await screen.findByText('sara');

    fireEvent.click(
      screen.getByRole('button', {
        name: 'غیرفعال‌سازی',
      }),
    );

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith(
        '/users/user-1/deactivate',
        { method: 'POST' },
      );
    });
  });

  it('loads roles and permissions and assigns a permission', async () => {
    apiMock.mockImplementation(async (path) => {
      if (path.startsWith('/roles?')) {
        return { items: [role] } as never;
      }

      if (path.startsWith('/permissions?')) {
        return { items: [permission] } as never;
      }

      if (path === '/roles/role-1/permissions') {
        return [] as never;
      }

      return {} as never;
    });

    renderApp('/roles');

    fireEvent.click(
      await screen.findByRole('button', {
        name: /مدیر سیستم/,
      }),
    );

    const checkbox = await screen.findByRole('checkbox', {
      name: /مشاهده کاربران/,
    });

    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith(
        '/roles/role-1/permissions',
        expect.objectContaining({
          method: 'POST',
        }),
      );
    });
  });

  it('grants a data scope to a selected user', async () => {
    apiMock.mockImplementation(async (path) => {
      if (path.startsWith('/users?')) {
        return { items: [user] } as never;
      }

      if (path === '/users/user-1/data-scopes') {
        return [] as never;
      }

      return {} as never;
    });

    renderApp('/scopes');

    fireEvent.change(
      await screen.findByLabelText('انتخاب کاربر'),
      {
        target: { value: 'user-1' },
      },
    );

    fireEvent.change(
      screen.getByPlaceholderText('مقدار محدوده'),
      {
        target: { value: 'company-1' },
      },
    );

    fireEvent.click(
      screen.getByRole('button', {
        name: 'اعطای محدوده',
      }),
    );

    await waitFor(() => {
      expect(apiMock).toHaveBeenCalledWith(
        '/users/user-1/data-scopes',
        expect.objectContaining({
          method: 'POST',
        }),
      );
    });
  });

  it('displays audit records returned by the API', async () => {
    apiMock.mockImplementation(async (path) => {
      if (path === '/auth/me') {
        return {
          id: user.id,
          username: user.username,
          display_name: user.display_name,
          email: user.email,
          is_active: user.is_active,
        } as never;
      }

      if (path.startsWith('/audit-logs')) {
        return {
          items: [audit],
          total: 1,
          offset: 0,
          limit: 100,
        } as never;
      }

      return {} as never;
    });

    renderApp('/audits');

    expect(
      await screen.findByText('user.created'),
    ).toBeInTheDocument();

    expect(
      screen.getByText('127.0.0.1'),
    ).toBeInTheDocument();
  });

  it('clears the session and redirects to login after an unauthorized event', async () => {
    apiMock.mockImplementation(async (path) => {
      if (path.startsWith('/users?')) {
        return { items: [user] } as never;
      }

      if (path.startsWith('/roles?')) {
        return { items: [] } as never;
      }

      return {} as never;
    });

    renderApp();

    await screen.findByText('sara');

    act(() => {
      window.dispatchEvent(
        new Event('bg:unauthorized'),
      );
    });

    expect(
      await screen.findByRole('heading', {
        name: 'ورود به بایت گارد',
      }),
    ).toBeInTheDocument();
  });
});
