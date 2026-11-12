# BiteGuard Platform — Development Bootstrap

Development baseline for the Comprehensive Company Management Software and Smart Bite Guard Ecosystem. This package excludes local secrets, virtual environments, dependency folders, and generated build output.

## Included
- FastAPI backend with health endpoints, settings, SQLAlchemy SQL Server URL configuration, request correlation IDs and tests.
- React + TypeScript + Vite frontend with Persian/English direction starter and API readiness check.
- SQLAlchemy foundational identity/audit schema with Alembic migration support.
- Environment examples, Git hygiene files, development notes and CI workflow.

## Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- SQL Server 2025 or compatible instance for database integration
- ODBC Driver 18 for SQL Server for `mssql+pyodbc`

## Backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
uvicorn app.main:app --reload
```
Check `http://127.0.0.1:8000/api/v1/health/live` and `/docs`.

Run tests and lint:

```bash
cd backend
python -m pytest -q
python -m ruff check app tests
```

## Database migrations

Configure the root `.env` first, then run from `backend`:

```powershell
python -m alembic current
python -m alembic upgrade head
```

Review and back up the target database before applying a migration. Do not run against production without explicit approval.

## Frontend
```bash
cd frontend
npm install
npm run dev
```
Set `VITE_API_BASE_URL` in `frontend/.env.local` if the API is elsewhere. The default is `http://127.0.0.1:8000`.

## SQL Server (optional for bootstrap)
Copy root `.env.example` to a root-level local `.env` and provide development-only settings. The delivered package intentionally does not include `.env`. Never commit `.env` or production credentials. The backend starts without database configuration; readiness reports `not_configured`. When configured, readiness performs a read-only `SELECT 1` check.

## Limitations
- Business modules and API authentication/authorization are not implemented yet. The first migration creates only foundational identity catalogue and audit tables.
- Authentication and authorization are not implemented.
- Health endpoints are starter endpoints and must be appropriately restricted before deployment.
- SQL Server connectivity has not been verified against your actual host/driver.
- Production configuration rejects `DATABASE_TRUST_SERVER_CERTIFICATE=true`; configure valid SQL Server certificate validation before production use.
- CI runs backend lint/tests and frontend lint/typecheck/build. CI is not production deployment automation. Production changes still require approval.
