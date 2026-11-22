# Changelog

Notable repository and product-documentation changes are recorded here. This log
does not imply that planned application features have been implemented.

## Unreleased

- P1-12: project file attachments. Allowed types PDF, PNG, JPEG and WebP, decided from the
  file's own bytes (extension must agree); 10 MiB per file and 100 files per project are
  development defaults pending DEC-023. Metadata: kind, document date, ownership text,
  detected type, size, SHA-256, uploader and time. Bytes are stored privately under
  random keys and leave only through an authenticated, authorized download (attachment,
  nosniff, no-store); nothing is served publicly. The built-in scanner rejects the EICAR
  test signature and PDFs with active content markers into quarantine; it is not an
  antivirus, so outside development a clean verdict is not granted and files stay
  pending (fail closed) until a real scanner is chosen under DEC-023. Quarantined or
  pending files are never downloadable. Owner, architect, structural and MEP engineers
  upload; owner and architect delete (bytes removed, metadata kept for audit); other
  roles read and download; archived projects are read-only. Raw-body upload (no multipart
  dependency), migration 0012, Persian UI, API tests (SQLite/PostgreSQL), mocked-UI and
  full-stack tests. No feature status changed.
- P1-11: environmental and technical conditions in thirteen categories (climate, solar
  exposure, prevailing wind, rainfall, design temperature and comfort, natural hazards,
  seismicity, water / electricity / gas / sewer / telecom availability, energy constraints
  and efficiency requirements). Each record keeps the user's values plus source type,
  title or reference, the location the data applies to, a Jalali or Gregorian date and an
  explicit "source verified" statement. Status is derived: no values = unknown, values
  without a complete verified source, location and date = needs inquiry, otherwise
  verified. Entered values only; never defaulted, never produced by AI. Owner, architect,
  structural and MEP engineers edit; other roles read; archived read-only; activity
  events, migration 0011, Persian UI, API tests (SQLite/PostgreSQL), mocked-UI and
  full-stack tests. No feature status changed.
- P1-10: client requirements in three versioned sections. Program: unit and floor counts,
  target area or range, and rooms / named spaces (bedrooms, kitchen, reception, living,
  bathrooms, storage, laundry, special spaces, parking, yard, terrace, balcony, roof
  garden, green space) with counts and area targets or ranges. Preferences: accessibility,
  privacy and public/private separation, style, quality and material level, budget with
  currency and priorities, mandatory / preferred / unacceptable constraints, expansion and
  change of use, each independent and reported as not provided when omitted. References:
  examples with label, explanation, kind and optional http(s) link (uploaded image files
  wait for FILE-001/DEC-023). Inverted ranges, budget without currency and bad links are
  rejected with per-field reasons. Owner and architect edit, others read, archived
  read-only, activity events, migration 0010, Persian UI, API tests (SQLite/PostgreSQL),
  mocked-UI and full-stack tests. No feature status changed.
- P1-09: zoning / building-control inputs in nine categories (land use/zone, coverage,
  density and floor area, floors and height, setbacks, parking/access, daylight and
  openings, stairs/elevator/ramp/exit, local constraints). Each record carries a source
  (type, title or reference, Jalali or Gregorian date) and an explicit "source verified"
  statement; status is derived: no values = unknown, values without a complete verified
  source = needs inquiry, otherwise verified. Values are user-entered only and never
  asserted as law or produced by AI. Owner and architect edit, other roles read, archived
  read-only, activity events, migration 0009, Persian UI, API tests (SQLite/PostgreSQL),
  mocked-UI and full-stack tests. No feature status changed.
- P1-08: site / land data in five versioned sections (parcel, access and orientation,
  terrain, surroundings, soil): rectangle sides or polygon vertices with computed area
  (shoelace; self-intersecting or degenerate boundaries rejected), survey references and
  points, and an explicit declared-vs-computed area report (match within a 1% development
  default, otherwise discrepancy). Neighbors, shared walls, barriers, trees, wells,
  channels, existing utilities and easements are distinct fields; empty lists mean
  "none"; omitted soil values are reported as `not_provided`, never defaulted. Owner and
  architect edit, other roles read, archived read-only, activity events, migration 0008,
  Persian UI, API tests (SQLite/PostgreSQL), mocked-UI and full-stack tests. Numbers are
  user-entered; nothing asserts surveying or legal validity. No feature status changed.
- P1-07: staged project intake (identity, location with coordinates, people, land-status
  notes): partial saves, per-field error reasons, optimistic version locking, owner-only
  edit with member read access, archived read-only, activity events, migration 0007, and
  the Persian form UI. Covered by API tests (SQLite/PostgreSQL), mocked-UI tests, and the
  unmocked full-stack run. Legal fields record user statements only; no validation of
  legal validity. No feature status changed.
- P1-06: CI job `Full stack` runs the real FastAPI service on migrated PostgreSQL 17 and the
  real Next.js server with three unmocked browser workflows (sign-up, project
  create/edit/archive/restore, invitation with single-use link, member role, hidden
  project 404, sign-out, lockout). It found and led to a fix of a sign-out redirect
  bug. README API start command corrected (`--group dev --app-dir apps/api`).
- P1-05: Persian RTL web pages for sign-up, sign-in, password-reset request/confirm,
  project list/create/detail (edit, archive/restore, members, activity), organization
  members and invitations, and invitation acceptance; `/api` is proxied to the API.
  Browser tests (mocked API, axe A/AA, 320px overflow) pass on Ubuntu and Windows
  runners. No feature status changed.
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
