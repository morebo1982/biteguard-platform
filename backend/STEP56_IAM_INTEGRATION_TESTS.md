# Step 56 — IAM Integration Tests

## Scope

This step adds end-to-end API coverage for the integrated identity and access-management flow:

- Password-based login, JWT issuance, `/auth/me`, and logout/revocation.
- Permission assignment through the existing role/permission catalogue.
- Protected IAM API calls with a valid bearer token.
- Denial of an operation after its permission is removed, including verification that the business operation did not occur and the denial is audited.
- Data-scope grant, idempotent re-grant, revoke, and corresponding audit events.
- Rejection of unauthenticated IAM API requests.

The tests use an isolated in-memory SQLite database and do not connect to or modify SQL Server.

## Audit correction

The data-scope grant endpoint now emits `user.data_scope_granted` only when a new grant is actually created. Repeating an existing grant remains idempotent and does not create a duplicate audit event. Revoke events continue to be recorded only when a grant is removed.

## Validation

```text
55 passed
```

`python -m compileall -q app tests migrations` completed successfully.

## Database and deployment

- No Alembic migration was added.
- No database schema change is required for this step.
- Run the tests in the project's virtual environment before accepting the ZIP.
- These tests validate application/API integration against SQLite; SQL Server-specific integration and production load/security testing remain separate validation activities.
