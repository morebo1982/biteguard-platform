# Step 45 — Infrastructure stabilization baseline

## Scope

Stabilize the existing starter project without introducing business modules or changing the approved technology stack.

## Changes included

- Use a project-root `.env` path so backend configuration does not depend on the shell working directory.
- Set SQL Server certificate trust to a secure default (`false`) and reject `true` when `APP_ENV=production`.
- Add tests for Windows Authentication configuration and production TLS configuration.
- Verify and preserve `X-Correlation-ID`, and log successful request status and duration.
- Add the missing ESLint flat configuration and run frontend lint/typecheck in CI.
- Use `npm ci` in CI and add npm caching.
- Exclude `.env`, virtual environments, dependency folders, caches, generated files, and accidental zero-byte artifacts from the delivery archive.

## Validation performed in this environment

- Backend tests: **7 passed**.
- Frontend ESLint: **passed** using the dependencies included in the source archive.
- Frontend TypeScript typecheck: **passed**.
- Frontend Vite production build: **not verified here** because the uploaded `node_modules` contained platform-specific Rollup dependencies for Windows and lacked the Linux native package. Run `npm ci` on the development machine to install dependencies for that platform, then run `npm run build`.
- Ruff: **not run here** because Ruff was unavailable and this environment could not download packages. The CI workflow runs `ruff check app tests`.
- Live SQL Server connection: **not tested here**; the existing automated tests do not replace an integration check against the configured development database.

## Acceptance criteria

- [x] Backend unit tests pass in the review environment.
- [x] Correlation ID behavior is covered by tests.
- [x] Production configuration rejects trusting an unverified SQL Server certificate.
- [x] Frontend lint and typecheck pass in the review environment.
- [x] Delivery archive contains no local `.env` or dependency/build directories.
- [ ] Developer runs the full frontend build on the target Windows machine.
- [ ] Developer runs Ruff and verifies live SQL Server connectivity locally.

## Known limitations

This is still a development scaffold. Authentication, authorization, data scope, audit persistence, database migrations, domain models, and business modules are not implemented. Do not deploy it to production.
