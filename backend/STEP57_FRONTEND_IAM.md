# Step 57 — Frontend IAM (integration and test pass)

## Implemented
- React + TypeScript + Vite frontend, Persian-first RTL layout.
- Login/logout with JWT access-token handling.
- Login state now updates immediately after a successful login (previously the login component navigated but the parent authentication state remained false).
- User list, search, create, edit, activate/deactivate.
- Role creation and role-permission assignment/removal.
- User role assignment.
- Data Scope grant/revoke for global/company/department/owner.
- Read-only audit log view.
- API client sends bearer tokens, handles 401/403/204, parses FastAPI validation errors and the application's structured `{error: {message}}` envelope.
- Frontend tests added for login, error handling, user flows, role-permission assignment, Data Scope, audit display, unauthorized-session redirect, and API client behavior.

## API contracts
Base URL: `/api/v1` (override with `VITE_API_BASE_URL`).
- Authentication: `/auth/login`, `/auth/logout`
- IAM: `/users`, `/roles`, `/permissions`
- User roles: `/users/{id}/roles`
- Data Scope: `/users/{id}/data-scopes`
- Audit: `/audit-logs`

The audit endpoint returns a paginated object with `items`, `total`, `offset`, and `limit`; the frontend reads `items`. It requires permission code `audit.read`.

## Run locally (Windows PowerShell)
From this directory:
```powershell
npm ci
node .\node_modules\typescript\bin\tsc --noEmit
node .\node_modules\vite\bin\vite.js build
node .\node_modules\vitest\vitest.mjs run
```
The direct Node commands avoid npm's shell parsing issue when the project path contains `&` (for example `B&B Studio`).
Start the backend from the repository root:
```powershell
uvicorn app.main:app --reload
```
Start the frontend:
```powershell
node .\node_modules\vite\bin\vite.js --host 0.0.0.0
```
Optional frontend API URL: create `.env` beside `package.json`:
```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## Verification status
- Backend automated tests: **56 passed** in the provided environment.
- Python compile check: passed.
- Frontend: **16 tests added**, but not executed in this environment because `npm ci` could not download a package (`ENOTCACHED` in offline mode; online install timed out). Run the commands above locally before accepting this step.
- The previous uploaded `dist/` build is not regenerated from these changes; do not deploy that stale build.

## Remaining validation before Step 57 can be closed
- Run frontend `tsc`, Vite build, and all Vitest tests locally.
- Verify the frontend against a running API and a real test database with accounts/permissions provisioned.
- Verify browser-level keyboard navigation, screen-reader labels, RTL/LTR behavior, and responsive layouts.
- The UI currently supports role creation and permission assignment/removal, but does not yet provide a complete CRUD screen for the permission catalog or a full role-membership review/removal workflow.
- For production, assess replacing localStorage token storage with a backend-for-frontend or secure HttpOnly cookie approach; the backend remains the authorization authority.
