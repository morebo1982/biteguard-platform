# Step 51 — IAM API

## Scope
- REST API v1 endpoints for users, roles, and permissions.
- User lifecycle and user-role assignment endpoints.
- Role lifecycle, deletion, and role-permission assignment endpoints.
- Permission catalogue CRUD endpoints with optional module filtering.
- Pydantic request/response contracts from Step 50 and paginated list metadata.
- Application exceptions mapped to HTTP 404, 409, and 422 responses.
- Request-scoped SQLAlchemy sessions; commit on success, rollback on failure, close always.

## API base
`/api/v1`

## Important routes
- `/users`, `/users/{user_id}`, `/users/{user_id}/activate`, `/users/{user_id}/deactivate`, `/users/{user_id}/roles`
- `/roles`, `/roles/{role_id}`, `/roles/{role_id}/activate`, `/roles/{role_id}/deactivate`, `/roles/{role_id}/permissions`
- `/permissions`, `/permissions/{permission_id}`

## Explicit exclusions
- Authentication and token issuance are not implemented (planned Step 52).
- Authorization enforcement and data scope are not implemented (planned Steps 53–54).
- Audit event integration is not implemented (planned Step 55).
- No database schema or migration changes.
- Production database integration/UAT is not claimed by the SQLite API tests.

## Transaction ownership
The API database dependency owns the request transaction. Application services and repositories continue to flush but do not commit or rollback.
