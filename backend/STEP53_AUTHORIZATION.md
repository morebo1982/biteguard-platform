# Step 53 — Authorization & Permission Enforcement

## Scope
- Added `require_permission(code)` FastAPI dependency.
- IAM endpoints require explicit permission codes; authentication alone is no longer sufficient.
- Permission resolution joins `users -> user_roles -> active roles -> role_permissions -> permissions`.
- Disabled roles do not grant permissions.
- Denied requests return HTTP 403 with `PERMISSION_DENIED` and record an `authorization.denied` AuditLog entry (independent transaction when the application session factory is available).
- Added API coverage for denied access and persisted denial audit.

## IAM permission catalogue

| Permission code | Endpoint capability |
|---|---|
| `users.create` | Create users |
| `users.read` | Read/list users and their roles |
| `users.update` | Update users |
| `users.activate` | Activate users |
| `users.deactivate` | Deactivate users |
| `users.roles.assign` | Assign/remove user roles |
| `roles.create` | Create roles |
| `roles.read` | Read/list roles and their permissions |
| `roles.update` | Update roles |
| `roles.activate` | Activate roles |
| `roles.deactivate` | Deactivate roles |
| `roles.delete` | Delete roles |
| `roles.permissions.assign` | Assign/remove permissions on roles |
| `permissions.create` | Create permissions |
| `permissions.read` | Read/list permissions |
| `permissions.update` | Update permissions |
| `permissions.delete` | Delete permissions |

## Operational note
Existing users without an assigned active role and matching permissions will receive 403 on IAM endpoints. Provision the permission catalogue and assign only the required permissions to an authorized administrative role through a controlled bootstrap/administrative process before enabling IAM administration. Do not grant all permissions to ordinary users.

## Database and migration
No schema or migration changes were introduced in Step 53.

## Verification
- `python -m pytest -q`: 42 passed.
- `python -m compileall -q app tests`: expected to pass in the build environment.
- SQL Server integration testing remains a deployment validation task.
