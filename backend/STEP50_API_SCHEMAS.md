# Step 50 — API Schemas

## Scope
- Added Pydantic v2 request/response schemas for User, Role, and Permission.
- Added paginated list response contracts and IAM assignment request contracts.
- Enabled ORM attribute loading for read schemas (`from_attributes=True`).
- Rejected unknown request fields, constrained lengths, stripped surrounding whitespace,
  and applied basic email format validation without adding a new dependency.

## Boundaries
- No API routes/endpoints, authentication, authorization enforcement, database changes,
  Alembic migrations, or transaction behavior were changed.
- Update schemas are partial; callers can distinguish omitted fields from explicit null
  using `model_fields_set`.

## Validation
Run from the backend directory:

```powershell
.\\.venv\\Scripts\\python.exe -m pytest -q
```
