
import { useEffect, useState, type FormEvent } from 'react';
import {
  Navigate,
  NavLink,
  Route,
  Routes,
  useNavigate,
} from 'react-router-dom';

import {
  api,
  getToken,
  setToken,
  type User,
  type CurrentUserProfile,
  type Role,
  type Permission,
  type Audit,
} from './lib/api';

/* -------------------------------------------------------
   Helpers
------------------------------------------------------- */

type ListResponse<T> = {
  items?: T[];
  data?: T[];
};

function toList<T>(value: unknown): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  if (value && typeof value === 'object') {
    const result = value as ListResponse<T>;

    if (Array.isArray(result.items)) {
      return result.items;
    }

    if (Array.isArray(result.data)) {
      return result.data;
    }
  }

  return [];
}

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : 'خطای پیش‌بینی‌نشده رخ داد.';
}

/* -------------------------------------------------------
   Login
------------------------------------------------------- */

function Login({ onLogin }: { onLogin: (profile: CurrentUserProfile) => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await api<{
        access_token: string;
        token_type: string;
        expires_at?: string;
        user_id?: string;
        username?: string;
      }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });

      if (!result.access_token) {
        throw new Error('توکن ورود از سرور دریافت نشد.');
      }

      setToken(result.access_token);
      const profile = await api<CurrentUserProfile>('/auth/me');
      onLogin(profile);
      navigate('/users', { replace: true });
    } catch (error) {
      setToken(null);
      setError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login">
      <form className="panel" onSubmit={submit}>
        <div className="brand">
          B<span>G</span>
        </div>

        <h1>ورود به بایت گارد</h1>

        {import.meta.env.MODE === 'demo' && (
          <div className="demo-notice" role="note">
            <strong>{'\u0646\u0633\u062e\u0647 \u0646\u0645\u0627\u06cc\u0634\u06cc'}</strong>
            <p>{'\u0627\u06cc\u0646 \u0646\u0633\u062e\u0647 \u0628\u0647 Backend \u0648\u0642\u0639\u06cc \u0645\u062a\u0635\u0644 \u0646\u06cc\u0633\u062a\u061b \u062a\u0645\u0627\u0645 \u0627\u0637\u0644\u0627\u0639\u0627\u062a \u0646\u0645\u0627\u06cc\u0634\u06cc \u0647\u0633\u062a\u0646\u062f.'}</p>
            <p>{'\u0646\u0627\u0645 \u06a9\u0627\u0631\u0628\u0631\u06cc'}: <code>demo</code></p>
            <p>{'\u06af\u0630\u0631\u0648\u0627\u0698\u0647'}: <code>demo1234</code></p>
          </div>
        )}

        <label>
          نام کاربری
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>

        <label>
          گذرواژه
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={loading}>
          {loading ? 'در حال ورود...' : 'ورود امن'}
        </button>
      </form>
    </main>
  );
}

/* -------------------------------------------------------
   Users
------------------------------------------------------- */

function Users({ profile }: { profile: CurrentUserProfile | null }) {
  const canCreate = hasPermission(profile, 'users.create');
  const canUpdate = hasPermission(profile, 'users.update');
  const canActivate = hasPermission(profile, 'users.activate');
  const canDeactivate = hasPermission(profile, 'users.deactivate');
  const canAssignRoles = hasPermission(profile, 'users.roles.assign');
  const [rows, setRows] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [userRoles, setUserRoles] = useState<Role[]>([]);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const [query, setQuery] = useState('');
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError('');

    try {
      const [usersResponse, rolesResponse] = await Promise.all([
        api<unknown>('/users?limit=500'),
        api<unknown>('/roles?limit=500'),
      ]);

      setRows(toList<User>(usersResponse));
      setRoles(toList<Role>(rolesResponse));
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError('');

    try {
      await api('/users', {
        method: 'POST',
        body: JSON.stringify({
          username,
          display_name: displayName,
          email: email || null,
        }),
      });

      setUsername('');
      setDisplayName('');
      setEmail('');

      await load();
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function toggle(user: User) {
    setError('');

    try {
      const action = user.is_active ? 'deactivate' : 'activate';

      await api(`/users/${user.id}/${action}`, {
        method: 'POST',
      });

      await load();
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function edit(user: User) {
    const display_name = window.prompt(
      'نام نمایشی جدید',
      user.display_name,
    );

    if (display_name === null) return;

    const newEmail = window.prompt(
      'ایمیل جدید',
      user.email || '',
    );

    if (newEmail === null) return;

    setError('');

    try {
      await api(`/users/${user.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          display_name,
          email: newEmail || null,
        }),
      });

      await load();
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function showUserRoles(user: User) {
    setError('');
    setSelectedUser(user);
    setUserRoles([]);

    try {
      const response = await api<unknown>(
        `/users/${user.id}/roles`,
      );

      setUserRoles(toList<Role>(response));
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function assignRole(roleId: string) {
    if (!selectedUser || !roleId) return;

    setError('');

    try {
      await api(`/users/${selectedUser.id}/roles`, {
        method: 'POST',
        body: JSON.stringify({ role_id: roleId }),
      });

      await showUserRoles(selectedUser);
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function removeRole(roleId: string) {
    if (!selectedUser) return;

    setError('');

    try {
      await api(
        `/users/${selectedUser.id}/roles/${roleId}`,
        { method: 'DELETE' },
      );

      await showUserRoles(selectedUser);
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  const filteredRows = rows.filter((user) =>
    [
      user.username,
      user.display_name,
      user.email || '',
    ]
      .join(' ')
      .toLowerCase()
      .includes(query.toLowerCase()),
  );

  return (
    <>
      <h1>مدیریت کاربران</h1>

      {canCreate && (
<form className="panel inline" onSubmit={create}>
        <input
          aria-label="نام کاربری جدید"
          placeholder="نام کاربری"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          required
        />

        <input
          aria-label="نام نمایشی"
          placeholder="نام و نام خانوادگی"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          required
        />

        <input
          aria-label="ایمیل"
          placeholder="ایمیل (اختیاری)"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />

        <button type="submit">افزودن کاربر</button>
      </form>
)}

      <input
        className="search"
        placeholder="جستجو در کاربران..."
        aria-label="جستجو در کاربران"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />

      {error && <p className="error" role="alert">{error}</p>}

      {loading && <p>در حال دریافت اطلاعات...</p>}

      <div className="panel tablewrap">
        <table>
          <thead>
            <tr>
              <th>کاربر</th>
              <th>نام نمایشی</th>
              <th>ایمیل</th>
              <th>وضعیت</th>
              <th>نقش‌ها</th>
              <th>عملیات</th>
            </tr>
          </thead>

          <tbody>
            {filteredRows.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>{user.display_name}</td>
                <td>{user.email || '—'}</td>

                <td>
                  <span className={user.is_active ? 'good' : 'muted'}>
                    {user.is_active ? 'فعال' : 'غیرفعال'}
                  </span>
                </td>

                <td>
                  { canAssignRoles && (
<button
                    type="button"
                    className="small secondary"
                    onClick={() => void showUserRoles(user)}
                  >
                    مدیریت نقش‌ها
                  </button>
)}
                </td>

                <td>
                  { canUpdate && (
<button
                    type="button"
                    className="small secondary"
                    onClick={() => void edit(user)}
                  >
                    ویرایش
                  </button>
)}

                  {' '}

                  { (user.is_active ? canDeactivate : canActivate) && (
<button
                    type="button"
                    className="small secondary"
                    onClick={() => void toggle(user)}
                  >
                    {user.is_active ? 'غیرفعال‌سازی' : 'فعال‌سازی'}
                  </button>
)}
                </td>
              </tr>
            ))}

            {filteredRows.length === 0 && (
              <tr>
                <td colSpan={6}>کاربری یافت نشد.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selectedUser && (
        <section className="panel">
          <div className="inline">
            <h2>
              نقش‌های کاربر: {selectedUser.username}
            </h2>

            <button
              type="button"
              className="small secondary"
              onClick={() => {
                setSelectedUser(null);
                setUserRoles([]);
              }}
            >
              بستن
            </button>
          </div>

          {canAssignRoles && (
<label>
            افزودن نقش
            <select
              value=""
              onChange={(event) => void assignRole(event.target.value)}
            >
              <option value="">انتخاب نقش...</option>

              {roles
                .filter(
                  (role) =>
                    !userRoles.some((item) => item.id === role.id),
                )
                .map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))}
            </select>
          </label>
)}

          <ul>
            {userRoles.map((role) => (
              <li key={role.id}>
                {role.name} ({role.code})

                { canAssignRoles && (
<button
                  type="button"
                  className="small danger"
                  onClick={() => void removeRole(role.id)}
                >
                  حذف نقش
                </button>
)}
              </li>
            ))}

            {userRoles.length === 0 && (
              <li>برای این کاربر نقشی ثبت نشده است.</li>
            )}
          </ul>
        </section>
      )}
    </>
  );
}

/* -------------------------------------------------------
   Roles and Permissions
------------------------------------------------------- */

function Roles({ profile }: { profile: CurrentUserProfile | null }) {
  const canCreate = hasPermission(profile, 'roles.create');
  const canAssignPermissions = hasPermission(profile, 'roles.permissions.assign');
  const [rows, setRows] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [assigned, setAssigned] = useState<Permission[]>([]);

  const [selected, setSelected] = useState('');
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  async function load() {
    setError('');

    try {
      const [rolesResponse, permissionsResponse] = await Promise.all([
        api<unknown>('/roles?limit=500'),
        api<unknown>('/permissions?limit=500'),
      ]);

      setRows(toList<Role>(rolesResponse));
      setPermissions(toList<Permission>(permissionsResponse));
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function loadAssigned(roleId: string) {
    if (!roleId) {
      setAssigned([]);
      return;
    }

    try {
      const response = await api<unknown>(
        `/roles/${roleId}/permissions`,
      );

      setAssigned(toList<Permission>(response));
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    void loadAssigned(selected);
  }, [selected]);

  async function create(event: FormEvent) {
    event.preventDefault();
    setError('');

    try {
      await api('/roles', {
        method: 'POST',
        body: JSON.stringify({ code, name }),
      });

      setCode('');
      setName('');

      await load();
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function changePermission(
    permissionId: string,
    add: boolean,
  ) {
    if (!selected) return;

    setError('');

    try {
      const path = add
        ? `/roles/${selected}/permissions`
        : `/roles/${selected}/permissions/${permissionId}`;

      await api(path, {
        method: add ? 'POST' : 'DELETE',
        ...(add
          ? {
              body: JSON.stringify({
                permission_id: permissionId,
              }),
            }
          : {}),
      });

      await loadAssigned(selected);
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  return (
    <>
      <h1>نقش‌ها و مجوزها</h1>

      {canCreate && (
<form className="panel inline" onSubmit={create}>
        <input
          placeholder="کد نقش"
          aria-label="کد نقش"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          required
        />

        <input
          placeholder="عنوان نقش"
          aria-label="عنوان نقش"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />

        <button type="submit">ایجاد نقش</button>
      </form>
)}

      {error && <p className="error" role="alert">{error}</p>}

      <div className="two">
        <section className="panel">
          <h2>نقش‌های تعریف‌شده</h2>

          {rows.map((role) => (
            <button
              type="button"
              key={role.id}
              className={`role ${selected === role.id ? 'active' : ''}`}
              onClick={() => setSelected(role.id)}
            >
              {role.name}
              <small>{role.code}</small>
            </button>
          ))}
        </section>

        <section className="panel">
          <h2>مجوزهای نقش انتخاب‌شده</h2>

          {!selected ? (
            <p>یک نقش را انتخاب کنید.</p>
          ) : (
            permissions.map((permission) => {
              const hasPermission = assigned.some(
                (item) => item.id === permission.id,
              );

              return (
                <label className="check" key={permission.id}>
                  <input
                    type="checkbox"
                    disabled={!canAssignPermissions}
                    checked={hasPermission}
                    onChange={() =>
                      void changePermission(
                        permission.id,
                        !hasPermission,
                      )
                    }
                  />

                  <span>
                    {permission.name}
                    <small>
                      {permission.code} · {permission.module}
                    </small>
                  </span>
                </label>
              );
            })
          )}
        </section>
      </div>
    </>
  );
}

/* -------------------------------------------------------
   Data Scopes
------------------------------------------------------- */

type DataScope = {
  id: string;
  user_id?: string;
  scope_type: string;
  scope_value: string;
};

function Scopes() {
  const [users, setUsers] = useState<User[]>([]);
  const [userId, setUserId] = useState('');
  const [items, setItems] = useState<DataScope[]>([]);

  const [scopeType, setScopeType] = useState('company');
  const [scopeValue, setScopeValue] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    void api<unknown>('/users?limit=500')
      .then((response) => setUsers(toList<User>(response)))
      .catch((error) => setError(errorMessage(error)));
  }, []);

  async function load(userId: string) {
    setUserId(userId);
    setItems([]);
    setError('');

    if (!userId) return;

    try {
      const response = await api<unknown>(
        `/users/${userId}/data-scopes`,
      );

      setItems(toList<DataScope>(response));
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function grant(event: FormEvent) {
    event.preventDefault();

    if (!userId) return;

    setError('');

    try {
      await api(`/users/${userId}/data-scopes`, {
        method: 'POST',
        body: JSON.stringify({
          scope_type: scopeType,
          scope_value: scopeValue,
        }),
      });

      setScopeValue('');
      await load(userId);
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  async function revoke(scope: DataScope) {
    if (!userId) return;

    setError('');

    try {
      await api(
        `/users/${userId}/data-scopes/${encodeURIComponent(scope.scope_type)}/${encodeURIComponent(scope.scope_value)}`,
        { method: 'DELETE' },
      );

      await load(userId);
    } catch (error) {
      setError(errorMessage(error));
    }
  }

  return (
    <>
      <h1>محدوده دسترسی داده‌ها</h1>

      <section className="panel">
        <label>
          انتخاب کاربر

          <select
            value={userId}
            onChange={(event) => void load(event.target.value)}
          >
            <option value="">انتخاب کنید</option>

            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.display_name} ({user.username})
              </option>
            ))}
          </select>
        </label>

        {userId && (
          <>
            <form className="inline" onSubmit={grant}>
              <select
                aria-label="نوع محدوده"
                value={scopeType}
                onChange={(event) => setScopeType(event.target.value)}
              >
                <option value="global">Global</option>
                <option value="company">Company</option>
                <option value="department">Department</option>
                <option value="owner">Owner</option>
              </select>

              <input
                placeholder="مقدار محدوده"
                value={scopeValue}
                onChange={(event) => setScopeValue(event.target.value)}
                required
              />

              <button type="submit">اعطای محدوده</button>
            </form>

            <ul className="scope-list">
              {items.map((scope) => (
                <li key={scope.id}>
                  {scope.scope_type}: {scope.scope_value}

                  <button
                    type="button"
                    className="small danger"
                    onClick={() => void revoke(scope)}
                  >
                    لغو
                  </button>
                </li>
              ))}

              {items.length === 0 && (
                <li>محدوده‌ای برای این کاربر ثبت نشده است.</li>
              )}
            </ul>
          </>
        )}
      </section>

      {error && <p className="error" role="alert">{error}</p>}
    </>
  );
}

/* -------------------------------------------------------
   Audit Logs
------------------------------------------------------- */

function Audits() {
  const [items, setItems] = useState<Audit[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function load() {
    setError('');
    setLoading(true);

    try {
      const response = await api<unknown>('/audit-logs?limit=100');
      setItems(toList<Audit>(response));
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <>
      <h1>گزارش رویدادها (Audit)</h1>

      <button type="button" onClick={() => void load()}>
        تازه‌سازی
      </button>

      {loading && <p>در حال دریافت اطلاعات...</p>}

      {error && <p className="error" role="alert">{error}</p>}

      <div className="panel tablewrap">
        <table>
          <thead>
            <tr>
              <th>زمان</th>
              <th>کاربر</th>
              <th>رویداد</th>
              <th>موجودیت</th>
              <th>نتیجه</th>
              <th>IP</th>
            </tr>
          </thead>

          <tbody>
            {items.map((audit) => (
              <tr key={audit.id}>
                <td>
                  {new Date(audit.occurred_at).toLocaleString()}
                </td>

                <td>{audit.actor_user_id || 'سیستم'}</td>
                <td>{audit.action}</td>

                <td>
                  {audit.entity_type} / {audit.entity_id || '—'}
                </td>

                <td>{audit.result}</td>
                <td>{audit.ip_address || '—'}</td>
              </tr>
            ))}

            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={6}>رویدادی برای نمایش وجود ندارد.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

/* -------------------------------------------------------
   Main App
------------------------------------------------------- */


function hasPermission(
  profile: CurrentUserProfile | null,
  permission: string,
): boolean {
  return Array.isArray(profile?.permissions) &&
    profile.permissions.includes(permission);
}

function NoAccess() {
  return (
    <section className="panel">
      <h1>403</h1>
      <p>شما مجوز دسترسی به این بخش را ندارید.</p>
    </section>
  );
}

type SessionStatus =
  | 'checking'
  | 'authenticated'
  | 'anonymous';

export default function App() {
  const [session, setSession] = useState<SessionStatus>(
    getToken() ? 'checking' : 'anonymous',
  );
  const [profile, setProfile] = useState<CurrentUserProfile | null>(null);

  const navigate = useNavigate();

  useEffect(() => {
    let active = true;

    function unauthorized() {
      if (active) {
        setProfile(null);
        setSession('anonymous');
      }
    }

    window.addEventListener('bg:unauthorized', unauthorized);

    async function validateSession() {
      if (!getToken()) {
        if (active) {
          setSession('anonymous');
        }
        return;
      }

      try {
        const currentProfile = await api<CurrentUserProfile>('/auth/me');

        if (active) {
          setProfile(currentProfile);
          setSession('authenticated');
        }
      } catch {
        if (active) {
          setToken(null);
          setProfile(null);
          setSession('anonymous');
        }
      }
    }

    void validateSession();

    return () => {
      active = false;
      window.removeEventListener(
        'bg:unauthorized',
        unauthorized,
      );
    };
  }, []);

  async function logout() {
    try {
      if (getToken()) {
        await api('/auth/logout', {
          method: 'POST',
        });
      }
    } catch {
      // Local session is cleared even if logout request fails.
    } finally {
      setToken(null);
      setProfile(null);
      setSession('anonymous');
      navigate('/login', { replace: true });
    }
  }

  if (session === 'checking') {
    return (
      <main className="login">
        <section className="panel">
          <p>در حال بررسی نشست کاربری...</p>
        </section>
      </main>
    );
  }

  if (session === 'anonymous') {
    return (
      <Routes>
        <Route
          path="/login"
          element={
            <Login
              onLogin={(currentProfile) => {
                setProfile(currentProfile);
                setSession('authenticated');
              }}
            />
          }
        />

        <Route
          path="*"
          element={<Navigate to="/login" replace />}
        />
      </Routes>
    );
  }

  return (
    <div className="layout">
      <aside>
        <div className="brand">
          B<span>G</span>
        </div>

        <p className="muted">BiteGuard Platform</p>

        <nav>
          {hasPermission(profile, 'users.read') && (
            <NavLink to="/users">کاربران</NavLink>
          )}
          {hasPermission(profile, 'roles.read') && (
            <NavLink to="/roles">نقش‌ها و مجوزها</NavLink>
          )}
          {hasPermission(profile, 'users.scopes.manage') && (
            <NavLink to="/scopes">Data Scope</NavLink>
          )}
          {hasPermission(profile, 'audit.read') && (
            <NavLink to="/audits">گزارش‌های ممیزی</NavLink>
          )}
        </nav>

        <button
          type="button"
          className="logout"
          onClick={() => void logout()}
        >
          خروج امن
        </button>
      </aside>

      <main className="content">
        <header>
          <span>مدیریت هویت و دسترسی</span>
          {import.meta.env.MODE === 'demo' ? (
            <span className="demo-status">{'\u0646\u0633\u062e\u0647 \u0646\u0645\u0627\u06cc\u0634\u06cc \u2014 \u0628\u062f\u0648\u0646 Backend'}</span>
          ) : (
            <span className="status">اتصال API</span>
          )}
        </header>

        <Routes>
          <Route
            path="/users"
            element={hasPermission(profile, 'users.read') ? <Users profile={profile} /> : <NoAccess />}
          />
          <Route
            path="/roles"
            element={hasPermission(profile, 'roles.read') ? <Roles profile={profile} /> : <NoAccess />}
          />
          <Route
            path="/scopes"
            element={hasPermission(profile, 'users.scopes.manage') ? <Scopes /> : <NoAccess />}
          />
          <Route
            path="/audits"
            element={hasPermission(profile, 'audit.read') ? <Audits /> : <NoAccess />}
          />
          <Route
            path="*"
            element={
              <Navigate
                to={
                  hasPermission(profile, 'users.read') ? '/users' :
                  hasPermission(profile, 'roles.read') ? '/roles' :
                  hasPermission(profile, 'users.scopes.manage') ? '/scopes' :
                  hasPermission(profile, 'audit.read') ? '/audits' : '/forbidden'
                }
                replace
              />
            }
          />
          <Route path="/forbidden" element={<NoAccess />} />
        </Routes>
      </main>
    </div>
  );
}
