# BiteGuard Step 48 — Persistence Repositories

This step adds a repository layer for the existing IAM and audit persistence models.

## Added modules

- `app.infrastructure.persistence.repositories.UserRepository`
- `app.infrastructure.persistence.repositories.RoleRepository`
- `app.infrastructure.persistence.repositories.PermissionRepository`
- `app.infrastructure.persistence.repositories.AuditLogRepository`

## Usage

Repositories receive an existing SQLAlchemy `Session`. They call `flush()` when needed
so generated values and database constraints are visible within the current transaction.
They intentionally do **not** call `commit()` or `rollback()`: transaction ownership stays
with the application/service boundary.

```python
with SessionLocal() as session:
    try:
        users = UserRepository(session)
        user = users.add(User(username="operator", display_name="Operator"))
        session.commit()
    except Exception:
        session.rollback()
        raise
```

Updates accept only explicitly allowed fields. Pagination uses `offset >= 0` and
`1 <= limit <= 500`. Assignment methods are idempotent: assigning an existing role or
permission returns `False`; a new assignment returns `True`. Missing entities raise
`ValueError`.

Audit logs expose append and query operations only; no update/delete methods are provided.

## Validation

Automated tests: **17 passed** in the build environment.

No database migration is included in Step 48. The existing SQL Server schema and
Alembic revision remain unchanged.
