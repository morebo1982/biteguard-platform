# Step 49 — Application Services

## Scope
- Added `UserService`, `RoleService`, and `PermissionService`.
- Added transport-neutral application exceptions for not-found, conflict, and invalid operations.
- Services coordinate the Step 48 repositories and enforce lifecycle, duplicate-key, and assignment rules.
- System roles cannot be deactivated or deleted through `RoleService`.
- Inactive users cannot receive role assignments; inactive roles cannot be assigned to users or receive permissions.

## Transaction boundary
Services call repository methods that flush changes but **do not commit or roll back**. The caller owns the transaction boundary. This allows an API request or background job to atomically combine several service operations.

## Explicitly out of scope
- HTTP endpoints and request/response schemas
- Authentication, password handling, sessions, and token issuance
- Permission enforcement on API routes and data-scope filtering
- Database schema changes and Alembic migrations
- SQL Server integration tests (the included service tests use in-memory SQLite)

## Verification
Run from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
