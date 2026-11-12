# Step 46 — Foundational data models and database migrations

## Scope

This step establishes the persistence foundation without enabling login or authorization APIs.

- SQLAlchemy 2 declarative `Base` and UTC timestamp mixin.
- Initial identity catalogue: `users`, `roles`, `permissions`, `user_roles`, and `role_permissions`.
- Append-oriented `audit_logs` table with result validation and query indexes.
- Alembic migration environment that obtains the SQL Server URL from application settings.
- SQLite-backed schema tests that do not require a live SQL Server.
- Frontend npm scripts invoke package entry points through Node directly to avoid Windows `.cmd` shim parsing problems in paths containing `&`.

## Migration commands

Run from `backend` after installing `pip install -e ".[dev]"`:

```powershell
python -m alembic current
python -m alembic upgrade head
```

The database must be configured in the root `.env` before running migrations. A migration changes the database schema; review the target database and back it up before applying it. Do not run the migration against production without explicit approval.

To generate a future migration after changing models:

```powershell
python -m alembic revision --autogenerate -m "describe schema change"
```

Review generated SQL and migration code before applying it. Autogeneration does not replace review.

## Model boundaries

These tables are foundational schema only. This step does not implement authentication, password storage, permission enforcement, data scopes, or audit-write middleware. Those remain separate security implementation tasks. `audit_logs` must be treated as sensitive operational data; avoid storing secrets or unnecessary personal data in `context_data`.

## Validation

- Schema metadata and SQLite create-table tests run without SQL Server.
- SQL Server migration execution must be validated in the developer environment before the step is considered fully verified.
