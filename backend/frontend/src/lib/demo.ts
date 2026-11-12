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

const profile: CurrentUserProfile = {
  id: 'demo-admin',
  username: 'demo',
  display_name: 'مدیر نمایشی BiteGuard',
  email: 'demo@example.test',
  is_active: true,
  roles: ['system_admin'],
  permissions: permissions.map(p => p.code),
};

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
  'demo-role-3': [permissions[0].id, permissions[1].id],
};

let userRoles: Record<string, string[]> = {
  'demo-user-1': ['demo-role-3'],
  'demo-user-2': ['demo-role-2'],
  'demo-user-3': [],
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

function record(action: string, entity: string, id: string | null) {
  audits.unshift({
    id: `demo-audit-${Date.now()}`,
    actor_user_id: profile.id,
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
    if (body.username !== 'demo' || body.password !== 'demo1234') {
      throw new Error('اطلاعات ورود نمایشی صحیح نیست.');
    }
    record('auth.login', 'authentication', profile.id);
    return {
      access_token: 'biteguard-demo-session',
      token_type: 'bearer',
    } as T;
  }

  if (cleanPath === '/auth/me') return profile as T;

  if (cleanPath === '/auth/logout' && method === 'POST') {
    record('auth.logout', 'authentication', profile.id);
    return undefined as T;
  }

  if (cleanPath.startsWith('/users') && parts.length === 1 && method === 'GET') {
    return { items: users, total: users.length } as T;
  }

  if (cleanPath === '/users' && method === 'POST') {
    const user: User = {
      id: `demo-user-${Date.now()}`,
      username: String(body.username ?? ''),
      display_name: String(body.display_name ?? ''),
      email: body.email ? String(body.email) : null,
      is_active: true,
      created_at: new Date().toISOString(),
    };
    users = [...users, user];
    record('user.created', 'user', user.id);
    return user as T;
  }

  if (parts[0] === 'users' && parts[1]) {
    const user = users.find(u => u.id === parts[1]);
    if (!user) throw new Error('کاربر نمایشی پیدا نشد.');

    if (parts.length === 2 && method === 'PATCH') {
      Object.assign(user, {
        display_name: body.display_name ?? user.display_name,
        email: body.email ?? user.email,
      });
      record('user.updated', 'user', user.id);
      return user as T;
    }

    if (parts[2] === 'activate' || parts[2] === 'deactivate') {
      user.is_active = parts[2] === 'activate';
      record(`user.${parts[2]}`, 'user', user.id);
      return user as T;
    }

    if (parts[2] === 'roles' && parts.length === 3 && method === 'GET') {
      return roles.filter(r => (userRoles[user.id] ?? []).includes(r.id)) as T;
    }

    if (parts[2] === 'roles' && method === 'POST') {
      const roleId = String(body.role_id ?? '');
      userRoles[user.id] ??= [];
      if (!userRoles[user.id].includes(roleId)) userRoles[user.id].push(roleId);
      record('user.role.assigned', 'user', user.id);
      return undefined as T;
    }

    if (parts[2] === 'roles' && parts[3] && method === 'DELETE') {
      userRoles[user.id] = (userRoles[user.id] ?? []).filter(id => id !== parts[3]);
      record('user.role.revoked', 'user', user.id);
      return undefined as T;
    }

    if (parts[2] === 'data-scopes' && parts.length === 3 && method === 'GET') {
      return scopes.filter(s => s.user_id === user.id) as T;
    }

    if (parts[2] === 'data-scopes' && method === 'POST') {
      const item = {
        id: `demo-scope-${Date.now()}`,
        user_id: user.id,
        scope_type: String(body.scope_type ?? 'company'),
        scope_value: String(body.scope_value ?? ''),
      };
      scopes.push(item);
      record('data_scope.granted', 'data_scope', item.id);
      return item as T;
    }

    if (parts[2] === 'data-scopes' && parts[3] && parts[4] && method === 'DELETE') {
      const scopeType = decodeURIComponent(parts[3]);
      const scopeValue = decodeURIComponent(parts[4]);
      scopes = scopes.filter(s =>
        !(s.user_id === user.id && s.scope_type === scopeType && s.scope_value === scopeValue)
      );
      record('data_scope.revoked', 'data_scope', user.id);
      return undefined as T;
    }
  }

  if (cleanPath.startsWith('/roles') && parts.length === 1 && method === 'GET') {
    return { items: roles, total: roles.length } as T;
  }

  if (cleanPath === '/roles' && method === 'POST') {
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
    record('role.created', 'role', role.id);
    return role as T;
  }

  if (parts[0] === 'roles' && parts[1]) {
    if (parts[2] === 'permissions' && parts.length === 3 && method === 'GET') {
      const ids = rolePermissions[parts[1]] ?? [];
      return permissions.filter(p => ids.includes(p.id)) as T;
    }

    if (parts[2] === 'permissions' && method === 'POST') {
      const id = String(body.permission_id ?? '');
      rolePermissions[parts[1]] ??= [];
      if (!rolePermissions[parts[1]].includes(id)) rolePermissions[parts[1]].push(id);
      record('role.permission.assigned', 'role', parts[1]);
      return undefined as T;
    }

    if (parts[2] === 'permissions' && parts[3] && method === 'DELETE') {
      rolePermissions[parts[1]] = (rolePermissions[parts[1]] ?? []).filter(id => id !== parts[3]);
      record('role.permission.revoked', 'role', parts[1]);
      return undefined as T;
    }
  }

  if (cleanPath.startsWith('/permissions')) {
    return { items: permissions, total: permissions.length } as T;
  }

  if (cleanPath.startsWith('/audit-logs')) {
    return { items: audits, total: audits.length } as T;
  }

  throw new Error(`Demo API route not implemented: ${method} ${cleanPath}`);
}
