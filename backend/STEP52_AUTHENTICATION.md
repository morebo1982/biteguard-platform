# Step 52 — Authentication

## Delivered
- Password credentials are stored separately from user profiles using salted scrypt hashes.
- JWT access tokens (HS256) expire after a configurable short lifetime (default 15 minutes).
- `/api/v1/auth/login`, `/api/v1/auth/me`, and `/api/v1/auth/logout` are available.
- Logout revocation is persisted in SQL Server (`revoked_tokens`) and checked on authenticated requests.
- All IAM management endpoints now require a valid Bearer access token. Permission-level authorization is Step 53.
- Failed login attempts are throttled by username and client IP (default 5 attempts / 15 minutes).
- Interactive password provisioning utility: `python -m scripts.set_user_password`.

## Required configuration
Add to the project-root `.env` (generate a random secret of at least 32 characters):

```dotenv
AUTH_JWT_SECRET_KEY=replace-with-a-random-secret-at-least-32-characters
AUTH_JWT_ALGORITHM=HS256
AUTH_ACCESS_TOKEN_MINUTES=15
AUTH_FAILED_ATTEMPTS=5
AUTH_LOCKOUT_MINUTES=15
```

Use a unique secret in each environment and keep `.env` out of source control. Production startup rejects a missing/short JWT secret.

## Database migration
This step adds `user_credentials` and `revoked_tokens`. After taking a verified backup and reviewing the migration, apply it explicitly:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Run the command from the backend directory if Alembic is installed in the active virtual environment. Do not apply it to production without the approved change process.

## First password setup
After migration, provision an existing active user interactively:

```powershell
.\.venv\Scripts\python.exe -m scripts.set_user_password
```

Run from the backend directory; it uses the project `.env` and does not echo the password.

## Security notes / limitations
- The login throttle is process-local. Before multi-worker or multi-instance production deployment, move it to a shared Redis/API gateway limiter.
- Access tokens are short-lived; logout revokes the presented token in SQL Server. Password reset does not yet revoke all previously issued tokens; add a per-user token version/revocation policy before enabling self-service password changes.
- Step 53 adds role/permission enforcement. Until then any authenticated account can call IAM endpoints; restrict network access and do not expose them publicly.
- HTTPS is mandatory outside local development. Never commit secrets or send passwords in logs.
