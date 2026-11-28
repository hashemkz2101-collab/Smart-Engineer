# Changelog

Notable repository and product-documentation changes are recorded here. This log
does not imply that planned application features have been implemented.

## Unreleased

- 2026-11-27, Phase 3 (ARCH-004): units, snap and undo/redo for the design model. Edits accept
  `unit` (m/cm/mm, exact Decimal conversion to metres) and an optional grid `snap` (nearest
  multiple, ties away from zero, only touched geometry); a per-project history (migration
  0020, 200 snapshots) backs `POST .../design/undo`, `.../redo` and `GET .../design/history`;
  undo then redo returns the exact prior/subsequent model data as new versions. Panel gained
  unit/snap selectors, undo/redo buttons and a history list. Tests are run by CI.

- 2026-11-27, Phase 3 (ARCH-003): editable base design model. A chosen layout alternative can
  be imported as a persisted, versioned model with stable element IDs (spaces, walls, doors,
  windows, openings) that is edited by explicit operations (add, move, resize, rotate,
  delete, lock, unlock, set) applied atomically. Locked elements reject edits with an
  explicit reason; invalid values are rejected, not clamped. New permission
  `project.design.edit` (owner, architect). Migration 0019, `GET /projects/{id}/design`,
  `POST .../design/import-layout`, `POST .../design/edit`, a project-page panel and tests.
  No overlap/closure checks, snapping, undo, versions or exports yet. See docs/PHASE_3_PLAN.md.
- 2026-11-26, Phase 3 (ARCH-002): conceptual layout alternatives. From the buildable
  envelope and the space schedule the API produces, persisted and versioned, either at
  least two distinct alternatives (axis-aligned space blocks per floor, with the criteria
  applied, assumptions, what was not evaluated and limitations) or a specific infeasibility
  result. Unplaceable spaces are reported with a reason; results go stale when the parcel,
  setbacks, coverage or schedule change. Migration 0018, `GET /projects/{id}/layouts`,
  `POST .../layouts/generate`, a project-page panel with an SVG view, and tests. Not a plan,
  not a rule check, not an approved design. See docs/PHASE_3_PLAN.md.
- 2026-11-26, Phase 3 started by explicit owner authorization (ARCH-001 first slice). The
  saved physical program now produces a persisted, versioned space schedule: one entry per
  counted space with stable IDs, the given target/range areas, net-area lower/upper totals and
  flags for everything unmet (missing count or area, target outside its range, program larger
  or smaller than the stated target area, counts not multiplied by units). A schedule built
  from an older program is shown as stale. Migration 0017, endpoints `GET
  /projects/{id}/space-schedule` and `POST .../space-schedule/generate`, a project-page panel
  and tests. No layout, geometry or rule check is claimed. See docs/PHASE_3_PLAN.md.
- P1-24: reference examples can link to an uploaded file (REQ-003). A reference item may carry
  `file_id`; the API accepts only a live, non-quarantined file of the same project (a file of
  another project is reported exactly like a missing one) and returns each linked file's name
  and whether it is still available. If the file is later deleted the reference keeps its label
  and explanation and is shown as "file deleted". The form offers a "no file" choice, so files
  stay optional.

- 2026-11-25, Phase 1 stabilization: all five versioned document services now use
  database-atomic compare-and-swap writes, including duplicate first-save conflicts;
  failed writes do not add activity. Comparing two old file versions now uses the
  actual latest undeleted version of their series for latest/stale-basis flags.
- Phase 2 (GEOM-001–004): independent Shapely 2.2.0 local-plane engine, explicit
  m/cm/mm conversion, validated parcel metrics and source-versioned, per-edge
  setback clearance envelopes; missing/unverified/expired sources remain unknown.
  The parcel form now includes an accessible SVG drawing/editing sheet with
  numeric, pointer and keyboard editing, unit switching, grid/snap and read-only
  mode. No geographic projection, automated legal compliance, design generation,
  or construction approval is claimed. See docs/PHASE_2_PLAN.md for evidence.
- Development: disposable migrated-database preview launcher, new targeted
  regression/reference/API tests and a new geometry full-stack browser scenario.
  Earlier tests are not rerun at the owner's request. Chromium installation was
  blocked by the CDN's regional HTTP 403; browser evidence is tracked explicitly.
- P1-18: the project intake panel applies the saved response at once, so text typed while
  the step list reloads after a save is no longer discarded by the late refetch (the form
  is keyed by version). Regression test with a delayed refetch. No feature status changed.
- P1-21: real malware scanning (SEC-002, DEC-023). Uploads are streamed to a ClamAV daemon on
  the owner's server (TCP or Unix socket, settings `SMART_ENGINEER_CLAMAV_*`). A clean verdict
  makes the file downloadable even in production; a detection quarantines it with the
  signature name; if the scanner cannot answer the file stays pending (fail closed) and
  `manage.py rescan-files` finishes it later. The built-in EICAR/PDF/Office checks still run
  first. Setup steps are in the README.
- P1-23: Codespaces trial environment. `.devcontainer` installs the pinned Python/Node and the
  locked dependencies; `scripts/dev/up.sh` starts a throwaway PostgreSQL, MySQL or SQLite
  database, applies migrations, seeds demo accounts (`manage.py seed-demo`, refuses non-local
  databases and production) and runs the API on 0.0.0.0:8000 and the web app on 0.0.0.0:3000.
  Ports are forwarded privately. See docs/CODESPACES.md.

- P1-20: file versions (FILE-002). An upload can be a new version of an existing file; earlier
  versions and their bytes are kept with uploader and time. A version can be restored (as a
  new version, nothing is overwritten) and two versions compared by recorded facts (identical
  content, size change, type change). Owner and quantity surveyor can mark the version that
  takeoff/estimate work is based on; the list warns when a newer version exists. Migration
  0016; new permission `project.files.set_basis`. Content-level comparison is FILE-003.

- P1-17: invitation emails. Creating an organization or project invitation now also emails
  the invited address (Persian text naming the inviter, the organization or project, the
  role and a 7-day accept link). Nothing is sent when the invitation is refused. The
  one-time link is still returned to the inviter, and the response says whether email is
  configured (`email_sent`), so the page tells the inviter whether to share the link by
  hand. Without SMTP configuration (development, tests) messages stay in memory. No
  feature status changed.
- Registry: FILE-002 (versions, Phase 1), FILE-003 (extraction, Phase 3) and FILE-004 (cross-file
  reconciliation, Phase 5) added as NOT STARTED per the owner's file decisions.
- P1-19: file formats and upload safety (DEC-023, owner-approved 2026-11-24). Uploads now
  accept DXF, DWG, IFC, XLSX, XLS, CSV, DOCX and DOC besides PDF and images, with the type
  decided from the file bytes. Macro-enabled files (DOCM/XLSM, legacy macro documents) and
  OOXML archives with path traversal, too many entries or huge expansion are refused;
  Office files with embedded objects, ActiveX or external template/workbook links are
  quarantined. Size limits are per type (25 MiB documents, 50 MiB CAD/BIM). Migration 0015
  widens the stored-type check. Extraction, cross-file comparison and file versioning are
  not implemented yet; see docs/FILE_REQUIREMENTS_GAP_ANALYSIS.md.

- P1-16: email authentication (DEC-010). Real email delivery over SMTP (any provider,
  STARTTLS/SSL/none, sent from a background thread so timing does not reveal accounts;
  failures are logged without address or token). Registration sends a confirmation link
  when verification is required, login stays refused until it is used (24 hours, single
  use, one click on the confirmation page so mail scanners cannot burn the token), and
  "send again" is neutral and rate-limited to once a minute. Password-reset emails are
  now delivered too. Production refuses to start without SMTP host, sender and public
  URL; development and tests keep messages in memory. Persian pages: confirm email,
  resend from login and registration. DEC-010 answer recorded: Zibal for subscription
  payment in Phase 10 (merchant code is a server secret, nothing built yet). Organization
  and project invitations are still shared as links, not emailed. No feature status changed.
- P1-15: hardening. The API adds `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, `Cross-Origin-Resource-Policy`, `Permissions-Policy` to every
  response, plus `Cache-Control: no-store` and a deny-all CSP on `/api/*`, and HSTS only in
  production; headers a route sets itself (file downloads) are kept. The web app sends
  nosniff, frame denial, a referrer policy, a permissions policy and a CSP limited to
  `frame-ancestors`, `base-uri`, `form-action` and `object-src`; script sources stay open
  because Next.js inline scripts would need per-request nonces (not done). HSTS for the
  web site belongs to the TLS terminator. CORS stays unconfigured on purpose: the browser
  uses one origin through the `/api` proxy and state changes are guarded by the origin check
  and CSRF token. A new CI job scans tracked files for well-known credential shapes
  (`scripts/check-secrets.mjs`, fixtures opt out with `secret-scan:allow`); it is a guard
  against accidents, not a full scanner. No feature status changed.
- P1-14: project invitations (FLOW-001 refinement). A project owner can invite someone who is
  not yet in the organization by email, with one bounded project role. Accepting the
  one-time link (7 days, only the account with that email) makes the person a plain
  organization member and grants exactly that project role; before acceptance they have
  no access, and revoked, expired, used, wrong-account or archived-project links all look
  the same (invalid). Invitation creation, revocation and acceptance are recorded in the
  project activity with actor, target, role and time. Existing organization members are
  still added directly. Organization-level invitations no longer revoke project
  invitations for the same email. Migration 0014 (project_id and project_role on
  invitations), Persian UI on the project page and the accept page, API tests
  (SQLite/PostgreSQL), mocked-UI and full-stack tests. No feature status changed.
- P1-13: system administration (ADMIN-001). Active system administrators can list and
  search users, deactivate or reactivate accounts (deactivation revokes the user's
  sessions at once), grant or revoke the system-admin flag, list projects (metadata only:
  name, type, status, organization, member count; no project content) and add, re-role or
  remove project members. Project access never crosses organizations: the user must
  already belong to the project's organization, a project keeps at least one owner, and
  archived projects stay read-only. Admins cannot change their own account state here and
  the platform keeps at least one active admin. Every action writes an append-only
  `admin_audit_events` row in the same transaction (project access changes also appear in
  the project's own activity, marked as made by a platform admin). Everyone else gets 404
  from `/admin/*`. The first administrator can only be created from the command line
  (`python -m smart_engineer_api.manage grant-admin EMAIL`, audited). Migration 0013,
  Persian `/admin` UI (users, projects and access, audit), API tests (SQLite/PostgreSQL),
  mocked-UI and full-stack tests. No feature status changed.
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
