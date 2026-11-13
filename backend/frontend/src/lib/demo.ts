import type { CurrentUserProfile, User, Role, Permission, Audit } from './api';

const permissions: Permission[] = [
  'users.read','users.create','users.update','users.activate','users.deactivate',
  'users.roles.assign','roles.read','roles.create','roles.update',
  'roles.activate','roles.deactivate','roles.delete','roles.permissions.assign',
  'users.scopes.manage','audit.read',
].map((code, i) => ({
  id: `perm-${i + 1}`,
  code,
  name: code,
  module: code.split('.')[0],
  description: 'Demo permission',
}));

let users: User[] = [
  {
    id: 'demo-user-1',
    username: 'sara',
    display_name: 'سارا رضایی',
    email: 'sara@example.test',
    is_active: true,
    created_at: '2026-01-10T09:00:00Z',
  },
  {
    id: 'demo-user-2',
    username: 'ali',
    display_name: 'علی محمدی',
    email: 'ali@example.test',
    is_active: true,
    created_at: '2026-02-15T10:30:00Z',
  },
  {
    id: 'demo-user-3',
    username: 'niloofar',
    display_name: 'نیلوفر احمدی',
    email: 'niloofar@example.test',
    is_active: false,
    created_at: '2026-03-02T08:15:00Z',
  },
  {
    id: 'demo-user-68',
    username: 'testuser68',
    display_name: 'کاربر آزمایشی ۶۸',
    email: 'testuser68@example.test',
    is_active: true,
    created_at: '2026-11-12T08:00:00Z',
  },
  {
    id: 'demo-user-auditor',
    username: 'auditor',
    display_name: 'ممیز نمایشی',
    email: 'auditor@example.test',
    is_active: true,
    created_at: '2026-11-12T08:00:00Z',
  },
];

let roles: Role[] = [
  {
    id: 'demo-role-1',
    code: 'system_admin',
    name: 'مدیر سیستم',
    description: 'نقش نمایشی مدیر سیستم',
    is_active: true,
    is_system: true,
  },
  {
    id: 'demo-role-2',
    code: 'security_auditor',
    name: 'ممیز امنیت',
    description: 'مشاهده رویدادهای امنیتی',
    is_active: true,
    is_system: false,
  },
  {
    id: 'demo-role-3',
    code: 'operator',
    name: 'اپراتور',
    description: 'مدیریت کاربران',
    is_active: true,
    is_system: false,
  },
];

let rolePermissions: Record<string, string[]> = {
  'demo-role-1': permissions.map(p => p.id),
  'demo-role-2': [permissions[0].id, permissions[14].id],
  'demo-role-3': [],
};

let userRoles: Record<string, string[]> = {
  'demo-user-1': ['demo-role-3'],
  'demo-user-2': ['demo-role-2'],
  'demo-user-3': [],
  'demo-user-68': ['demo-role-3'],
  'demo-user-auditor': ['demo-role-2'],
};

let scopes: Array<{
  id: string;
  user_id: string;
  scope_type: string;
  scope_value: string;
}> = [
  {
    id: 'demo-scope-1',
    user_id: 'demo-user-1',
    scope_type: 'company',
    scope_value: 'company-demo',
  },
];

let audits: Audit[] = [
  {
    id: 'demo-audit-1',
    actor_user_id: 'demo-admin',
    action: 'auth.login',
    entity_type: 'authentication',
    entity_id: 'demo-admin',
    occurred_at: '2026-11-12T08:30:00Z',
    result: 'success',
    source: 'demo',
    ip_address: '127.0.0.1',
    context_data: { mode: 'demo' },
  },
  {
    id: 'demo-audit-2',
    actor_user_id: 'demo-user-1',
    action: 'user.updated',
    entity_type: 'user',
    entity_id: 'demo-user-1',
    occurred_at: '2026-11-11T12:00:00Z',
    result: 'success',
    source: 'demo',
    ip_address: '127.0.0.1',
    context_data: { mode: 'demo' },
  },
];

const accounts = [
  {
    username: 'demo',
    password: 'demo1234',
    token: 'biteguard-demo-admin-session',
    userId: 'demo-admin',
    displayName: 'مدیر نمایشی BiteGuard',
    email: 'demo@example.test',
    roleIds: ['demo-role-1'],
  },
  {
    username: 'operator',
    password: 'operator1234',
    token: 'biteguard-demo-operator-session',
    userId: 'demo-user-68',
    displayName: 'کاربر آزمایشی ۶۸',
    email: 'testuser68@example.test',
    roleIds: ['demo-role-3'],
  },
  {
    username: 'testuser68',
    password: 'operator1234',
    token: 'biteguard-demo-operator-session',
    userId: 'demo-user-68',
    displayName: 'کاربر آزمایشی ۶۸',
    email: 'testuser68@example.test',
    roleIds: ['demo-role-3'],
  },
  {
    username: 'auditor',
    password: 'auditor1234',
    token: 'biteguard-demo-auditor-session',
    userId: 'demo-user-auditor',
    displayName: 'ممیز نمایشی',
    email: 'auditor@example.test',
    roleIds: ['demo-role-2'],
  },
];

let activeToken: string | null = null;

function storedToken(): string | null {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('bg_access_token') ?? activeToken;
    }
  } catch {
    // Use in-memory session when storage is unavailable.
  }
  return activeToken;
}

function accountForToken(token: string | null) {
  return accounts.find(account => account.token === token) ?? null;
}

function currentAccount() {
  return accountForToken(storedToken());
}

function profileFor(account: NonNullable<ReturnType<typeof currentAccount>>): CurrentUserProfile {
  const assignedRoles = account.roleIds;
  const permissionIds = new Set(
    assignedRoles.flatMap(roleId => rolePermissions[roleId] ?? []),
  );

  return {
    id: account.userId,
    username: account.username === 'operator' ? 'testuser68' : account.username,
    display_name: account.displayName,
    email: account.email,
    is_active: true,
    roles: assignedRoles
      .map(roleId => roles.find(role => role.id === roleId)?.code)
      .filter((code): code is string => Boolean(code)),
    permissions: permissions
      .filter(permission => permissionIds.has(permission.id))
      .map(permission => permission.code),
  };
}

function requireAccount() {
  const account = currentAccount();
  if (!account) {
    throw new Error('نشست معتبر نیست؛ لطفاً دوباره وارد شوید. (401)');
  }
  return account;
}

function requirePermission(permission: string) {
  const account = requireAccount();
  const profile = profileFor(account);

  if (!profile.permissions.includes(permission)) {
    throw new Error(`دسترسی لازم برای این عملیات را ندارید: ${permission} (403)`);
  }

  return account;
}

function record(
  action: string,
  entity: string,
  id: string | null,
  actorId: string | null = currentAccount()?.userId ?? null,
) {
  audits.unshift({
    id: `demo-audit-${Date.now()}-${audits.length}`,
    actor_user_id: actorId,
    action,
    entity_type: entity,
    entity_id: id,
    occurred_at: new Date().toISOString(),
    result: 'success',
    source: 'demo',
    ip_address: '127.0.0.1',
    context_data: { mode: 'demo' },
  });
}

function bodyOf(init?: RequestInit): Record<string, unknown> {
  if (typeof init?.body !== 'string') return {};
  try {
    return JSON.parse(init.body) as Record<string, unknown>;
  } catch {
    return {};
  }
}

export async function demoApi<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase();
  const cleanPath = path.split('?')[0];
  const parts = cleanPath.split('/').filter(Boolean);
  const body = bodyOf(init);

  if (cleanPath === '/auth/login' && method === 'POST') {
    const account = accounts.find(
      item => item.username === body.username && item.password === body.password,
    );

    if (!account) {
      throw new Error('نام کاربری یا رمز عبور نمایشی صحیح نیست.');
    }

    activeToken = account.token;
    record('auth.login', 'authentication', account.userId, account.userId);

    return {
      access_token: account.token,
      token_type: 'bearer',
    } as T;
  }

  if (cleanPath === '/auth/me') {
    const account = requireAccount();
    return profileFor(account) as T;
  }

  if (cleanPath === '/auth/logout' && method === 'POST') {
    const account = requireAccount();
    record('auth.logout', 'authentication', account.userId, account.userId);
    activeToken = null;
    return undefined as T;
  }

  if (cleanPath === '/users' && method === 'GET') {
    requirePermission('users.read');
    return { items: users, total: users.length } as T;
  }

  if (cleanPath === '/users' && method === 'POST') {
    const account = requirePermission('users.create');
    const user: User = {
      id: `demo-user-${Date.now()}`,
      username: String(body.username ?? ''),
      display_name: String(body.display_name ?? ''),
      email: body.email ? String(body.email) : null,
      is_active: true,
      created_at: new Date().toISOString(),
    };
    users = [...users, user];
    record('user.created', 'user', user.id, account.userId);
    return user as T;
  }

  if (parts[0] === 'users' && parts[1]) {
    const user = users.find(u => u.id === parts[1]);
    if (!user) throw new Error('کاربر نمایشی پیدا نشد.');

    if (parts.length === 2 && method === 'PATCH') {
      const account = requirePermission('users.update');
      Object.assign(user, {
        display_name: body.display_name ?? user.display_name,
        email: body.email ?? user.email,
      });
      record('user.updated', 'user', user.id, account.userId);
      return user as T;
    }

    if (parts[2] === 'activate' && method === 'POST') {
      const account = requirePermission('users.activate');
      user.is_active = true;
      record('user.activate', 'user', user.id, account.userId);
      return user as T;
    }

    if (parts[2] === 'deactivate' && method === 'POST') {
      const account = requirePermission('users.deactivate');
      user.is_active = false;
      record('user.deactivate', 'user', user.id, account.userId);
      return user as T;
    }

    if (parts[2] === 'roles' && parts.length === 3 && method === 'GET') {
      requirePermission('users.roles.assign');
      return roles.filter(r => (userRoles[user.id] ?? []).includes(r.id)) as T;
    }

    if (parts[2] === 'roles' && method === 'POST') {
      const account = requirePermission('users.roles.assign');
      const roleId = String(body.role_id ?? '');
      if (!roles.some(role => role.id === roleId)) {
        throw new Error('نقش انتخاب‌شده پیدا نشد.');
      }
      userRoles[user.id] ??= [];
      if (!userRoles[user.id].includes(roleId)) userRoles[user.id].push(roleId);
      record('user.role.assigned', 'user', user.id, account.userId);
      return undefined as T;
    }

    if (parts[2] === 'roles' && parts[3] && method === 'DELETE') {
      const account = requirePermission('users.roles.assign');
      userRoles[user.id] = (userRoles[user.id] ?? []).filter(id => id !== parts[3]);
      record('user.role.revoked', 'user', user.id, account.userId);
      return undefined as T;
    }

    if (parts[2] === 'data-scopes' && parts.length === 3 && method === 'GET') {
      requirePermission('users.scopes.manage');
      return scopes.filter(s => s.user_id === user.id) as T;
    }

    if (parts[2] === 'data-scopes' && method === 'POST') {
      const account = requirePermission('users.scopes.manage');
      const item = {
        id: `demo-scope-${Date.now()}`,
        user_id: user.id,
        scope_type: String(body.scope_type ?? 'company'),
        scope_value: String(body.scope_value ?? ''),
      };
      scopes.push(item);
      record('data_scope.granted', 'data_scope', item.id, account.userId);
      return item as T;
    }

    if (parts[2] === 'data-scopes' && parts[3] && parts[4] && method === 'DELETE') {
      const account = requirePermission('users.scopes.manage');
      const scopeType = decodeURIComponent(parts[3]);
      const scopeValue = decodeURIComponent(parts[4]);
      scopes = scopes.filter(s =>
        !(s.user_id === user.id && s.scope_type === scopeType && s.scope_value === scopeValue)
      );
      record('data_scope.revoked', 'data_scope', user.id, account.userId);
      return undefined as T;
    }
  }

  if (cleanPath === '/roles' && method === 'GET') {
    requirePermission('roles.read');
    return { items: roles, total: roles.length } as T;
  }

  if (cleanPath === '/roles' && method === 'POST') {
    const account = requirePermission('roles.create');
    const role: Role = {
      id: `demo-role-${Date.now()}`,
      code: String(body.code ?? ''),
      name: String(body.name ?? ''),
      description: null,
      is_active: true,
      is_system: false,
    };
    roles.push(role);
    rolePermissions[role.id] = [];
    record('role.created', 'role', role.id, account.userId);
    return role as T;
  }

  if (parts[0] === 'roles' && parts[1]) {
    if (parts[2] === 'permissions' && parts.length === 3 && method === 'GET') {
      requirePermission('roles.read');
      const ids = rolePermissions[parts[1]] ?? [];
      return permissions.filter(p => ids.includes(p.id)) as T;
    }

    if (parts[2] === 'permissions' && method === 'POST') {
      const account = requirePermission('roles.permissions.assign');
      const id = String(body.permission_id ?? '');
      rolePermissions[parts[1]] ??= [];
      if (!rolePermissions[parts[1]].includes(id)) rolePermissions[parts[1]].push(id);
      record('role.permission.assigned', 'role', parts[1], account.userId);
      return undefined as T;
    }

    if (parts[2] === 'permissions' && parts[3] && method === 'DELETE') {
      const account = requirePermission('roles.permissions.assign');
      rolePermissions[parts[1]] = (rolePermissions[parts[1]] ?? []).filter(id => id !== parts[3]);
      record('role.permission.revoked', 'role', parts[1], account.userId);
      return undefined as T;
    }
  }

  if (cleanPath === '/permissions' && method === 'GET') {
    requirePermission('roles.read');
    return { items: permissions, total: permissions.length } as T;
  }

  if (cleanPath === '/audit-logs' && method === 'GET') {
    requirePermission('audit.read');
    return { items: audits, total: audits.length } as T;
  }

  throw new Error(`Demo API route not implemented: ${method} ${cleanPath}`);
}
