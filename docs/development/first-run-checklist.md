# First-run checklist

- [ ] Install Python 3.11+.
- [ ] Install Node.js 20+ and npm.
- [ ] Install backend dependencies and run `pytest`.
- [ ] Start backend and check `/api/v1/health/live`.
- [ ] Install frontend dependencies and run `npm run build`.
- [ ] Start frontend and test backend readiness button.
- [ ] Verify no credentials or real customer/patient data are in Git.
- [ ] Verify database connectivity only against a development/test instance.

## Step 45 baseline validation

- [ ] Copy `.env.example` to `.env` and configure local-only database settings.
- [ ] Confirm `.env`, virtual environments, dependency folders, caches, and build output are not included in shared source archives.
- [ ] Run `ruff check app tests` and `pytest -q` from `backend`.
- [ ] Run `npm ci`, `npm run lint`, `npm run typecheck`, and `npm run build` from `frontend`.
- [ ] Confirm each API response includes `X-Correlation-ID`; verify a supplied correlation ID is preserved.
- [ ] For production configuration, keep `DATABASE_TRUST_SERVER_CERTIFICATE=false`.
- [ ] Treat this scaffold as development-only until authentication, authorization, data scoping, and audit controls are implemented.
