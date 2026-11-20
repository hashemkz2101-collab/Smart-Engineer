# Changelog

Notable repository and product-documentation changes are recorded here. This log
does not imply that planned application features have been implemented.

## Unreleased

- P1-04: projects (create, list, read, update, archive, restore), project members with
  last-owner protection, and an ordered activity log written with each change;
  `/api/v1/projects` endpoints, migration 0006. Backend only; no feature status changed.
- P1-03: role/permission matrix, project and organization authorization, organization
  members and invitations (hashed single-use tokens), member role change and removal,
  `/api/v1/orgs` endpoints, migration 0005. Backend only; no feature status changed.
- P1-02: authentication backend (scrypt passwords, hashed cookie sessions, CSRF and
  Origin checks, lockout, password change and reset, migration 0004) with HTTP
  endpoints under `/api/v1/auth`. Tests run on SQLite and PostgreSQL; no frontend
  and no real email delivery yet. No feature status changed.
- P1-01: added users, organizations, memberships, projects and project_members
  tables (migration 0003), the SQLite foreign-key pragma, schema tests, the Phase 1
  plan, and owner-delegated Phase 1 decision records. CI passed on all jobs
  (PR #8). No feature status changed.
- Renamed the master product specification to `SMART_ENGINEER_MASTER_SPEC.md`
  without changing its contents.
- Added the phase roadmap, initial phase-status register, open-decision register,
  feature registry, architecture overview, and documentation maintenance policy.
- Added per-feature acceptance criteria, individual-requirement traceability,
  explicit AI/role/collaboration phase mapping, and the six-state output
  lifecycle policy.
- Recorded dependency rationale, additional open decisions, and an accurate
  repository-status overview in README.md.
- Added the minimal P0-03 FastAPI application shell with `/health`, generated
  OpenAPI/docs endpoints, and standard-library tests; HTTPX and Uvicorn are
  scoped to the API development dependency group.
- Added the P0-04 Persian-first Next.js frontend shell with responsive RTL
  layout, system-aware persisted light/dark themes, safe error/404 pages, and
  Node built-in HTTP smoke tests.
- The user approved the initial frontend's visual appearance, and P0-04 was
  marked complete. Browser-based responsive, interaction, keyboard/screen-reader
  accessibility checks and Windows testing remain outstanding; Phase 0 remains
  in progress.
- Added P0-05 CI configuration (`.github/workflows/ci.yml`) running the API
  tests and the web typecheck, production build, and smoke tests on Ubuntu and
  Windows runners, plus `apps/web/scripts/run-smoke.mjs` (`test:ci`) so the
  smoke tests can start and stop the production server themselves. The first
  GitHub Actions run (PR #1, 2026-11-15) passed all four jobs on Ubuntu and
  Windows runners; this is not a manual Windows install on a developer machine.
- Added P0-06 API foundation: validated environment settings and
  `.env.example`, JSON logging with `X-Correlation-ID`, a safe error envelope
  (no stack traces or echoed input in responses), a `create_app` factory, and a
  versioned `/api/v1/health` route beside `/health`. 21 tests were added; CI
  (PR #3, 2026-11-15) passed API and web jobs on Ubuntu and Windows runners.
- Added P0-07 database foundation: validated `SMART_ENGINEER_DATABASE_URL`,
  SQLAlchemy base and the `feature_flags` and `background_jobs` tables, an
  Alembic baseline migration with downgrade, exact-pinned `sqlalchemy`,
  `alembic`, and `psycopg[binary]`, and a PostgreSQL 17 CI job. CI (PR #4,
  2026-11-16) passed on Ubuntu and Windows runners and on PostgreSQL. The
  library choices are provisional; DEC-029 and DEC-009 remain open.
- Added P0-08: migration `0002` (versioned job input and result), feature-flag
  and job-lifecycle services with tests, ruff and ESLint in CI, and Playwright
  browser tests (responsive, RTL, keyboard, theme, axe accessibility) on Ubuntu
  and Windows runners. Fixed a WCAG 2.5.3 label mismatch on the brand link
  (removed its `aria-label`; no visual change). CI (PR #5, 2026-11-16) passed
  all seven jobs. New dev dependencies are provisional; DEC-029 remains open.
- Added P0-09 closure readiness review (`docs/PHASE_0_CLOSURE.md`) with
  evidence-versus-criteria tables, open owner decisions, Windows validation
  steps, and a blank sign-off record; corrected a stale README paragraph. Phase
  0 is not closed and no feature status changed.
- Added `scripts/windows-validate.ps1` (Windows PowerShell 5.1 compatible) that
  runs Phase 0 Windows validation steps 2-9 and writes a report; verified once on
  a `windows-latest` runner (all steps passed). It does not replace the manual
  install (step 1) or the owner's run on their own machine.
- `scripts/windows-validate.ps1` now stops with a clear message on PowerShell
  older than 5.1 and no longer depends on `$PSScriptRoot`; re-verified on a
  `windows-latest` runner from the repository root and from the `scripts` folder.
- Phase 0 is in progress; registered product feature statuses remain unchanged.
