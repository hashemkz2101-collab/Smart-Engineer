# Smart Engineer implementation roadmap

This roadmap is a planning transcription of Sections 1–22 of
[`../SMART_ENGINEER_MASTER_SPEC.md`](../SMART_ENGINEER_MASTER_SPEC.md), not a
claim that any application feature exists. The master specification is the
product-scope source of truth. No phase may be skipped or started before the
preceding phase's exit criteria pass, unless the product owner explicitly
authorizes a change and records it.

All phase dependencies below are gates in addition to the feature-level
dependencies in [`FEATURE_REGISTRY.md`](FEATURE_REGISTRY.md). Phase 0 is in
progress; later phases remain **NOT STARTED**. See
[`PHASE_STATUS.md`](PHASE_STATUS.md).

## Phase 0 — Infrastructure and development standards

**Features**

- Inspect the existing starter and resolve installation, build, and test
  problems; standardize project structure, configuration, and environments.
- Establish baseline domain/data models and database migration management.
- Establish logging, explicit error handling, automated tests, and CI.
- Record architecture decisions and developer setup/run instructions.

**Dependencies:** None. This is the prerequisite gate for Phase 1.

**Acceptance criteria (specification):** Repeatable installation on Windows;
backend tests pass; frontend production build succeeds; setup and run
documentation is complete.

**Feature IDs and acceptance:** OPS-001–OPS-004, ARCH-PLAT-001/002,
SEC-001/003, CORE-001–004, AI-003, TEST-001,
RELEASE-001, GOV-001, DATA-001, and SEC-005. Each feature's test is linked in
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md).

**Unresolved assignment:** AI-004 is not assigned to Phase 0; its
implementation phase remains unresolved under DEC-032.

### P0-03 implementation evidence — partial Phase 0 progress

- Added the minimal `apps/api/smart_engineer_api` FastAPI application with
  `GET /health`, default `/openapi.json`, `/docs`, and `/redoc` routes.
- Added `unittest` coverage for the exact health response, OpenAPI metadata
  and health operation, and interactive docs response.
- Local Linux/Codespaces install, tests, and endpoint checks are recorded for
  this work. The server binds to `127.0.0.1`; no database or external service is
  used.
- This is partial evidence for the broader Phase 0/OPS-001/OPS-003/TEST-001
  criteria, not completion of those criteria or of Phase 0. Windows execution
  remains untested under DEC-031.

### P0-04 — completed implementation; validation limitations remain

- Added the minimal Next.js App Router shell at `apps/web`: Persian RTL home,
  accessible header/navigation, local-storage theme toggle with system
  preference, generic error and not-found pages, and responsive system-font
  styling.
- Verified the pinned web dependencies with frozen install, strict TypeScript
  check, and production build on Linux. Four Node built-in smoke tests passed
  against the running local production server, covering the home shell,
  accessibility markers, and not-found route.
- The user reviewed and approved the initial UI appearance. The implementation
  and automated checks for this task are complete; no Feature ID or feature
  status is changed by this task completion.
- The server was bound to `127.0.0.1`; there is no frontend API, database,
  authentication, persistence, or product-feature integration. Browser-based
  responsive-layout, theme-interaction, keyboard, and screen-reader/accessibility
  checks were not performed. User visual approval does not constitute those
  tests. Windows execution also remains untested under DEC-031.
- P0-04 completion does not mark OPS-001, TEST-001, or Phase 0 complete; the
  broader Phase 0 acceptance criteria and quality gates remain outstanding.

### P0-05 — CI added; first run passed (2026-11-15)

- Added `.github/workflows/ci.yml`: on push to `main` and on pull requests, an
  `api` job (locked `uv sync`, `unittest` discovery) and a `web` job (frozen
  `pnpm install`, typecheck, production build, smoke tests), each on
  `ubuntu-latest` and `windows-latest`, using the pinned Node.js, pnpm, uv, and
  Python versions.
- Added `apps/web/scripts/run-smoke.mjs` and the `test:ci` script so smoke tests
  start the built production server, wait for readiness, run, and always stop it.
- Evidence: GitHub Actions run 43765451923 on pull request #1 (merged as
  `6af957c`) passed all four jobs: API tests and web typecheck/build/smoke on
  both `ubuntu-latest` and `windows-latest`, with no failed steps. This is
  automated-runner evidence only: it is partial evidence toward OPS-001,
  OPS-003, and TEST-001, and it is not a manual install on a developer's Windows
  machine. DEC-031 stays open until the owner accepts the Windows-verification
  method. No Feature ID status is changed. GitHub Actions use as the CI service
  is pending the owner's DEC-029 approval.
- Observed during review: `CLAUDE.md` referenced by master spec Section 20 is
  absent from the repository. (`.env.example` was added in P0-06.)

### P0-06 — API foundation; CI passed (2026-11-15)

- Added to `apps/api/smart_engineer_api`: validated environment settings
  (`config.py`, `.env.example`); JSON logging with a correlation-ID context
  (`logging_config.py`); a pure-ASGI correlation-ID and access-log middleware
  that never logs query strings (`middleware.py`); one safe error envelope for
  unhandled, HTTP, and validation errors with no exception text, stack trace, or
  echoed input in responses (`errors.py`); a `create_app` factory; and a
  versioned `/api/v1` router next to the unversioned `/health` probe
  (`routes.py`). No new dependencies; `uv.lock` is unchanged.
- Tests: 21 new `unittest` tests (settings, correlation IDs, access log,
  unhandled/404/405/422 envelopes, JSON formatter, logging idempotency, v1
  routes) plus the 3 existing tests. CI run 43766075454 (PR #3) passed all four
  jobs on Ubuntu and Windows runners; the Ubuntu API job reported 24 tests, OK.
- Mapping: partial progress on OPS-003 (a forced error is logged with a
  correlation ID and returns a safe response), SEC-003 (safe errors), SEC-005
  (no secrets in settings or `.env.example`), and ARCH-PLAT-001 (a versioned
  route exists). Not done: audit logs, a metrics/tracing/error-monitoring
  service, API-version policy, domain module boundaries, migrations, jobs, and
  feature flags. No Feature ID status is changed.
- Open question for the owner: keeping both `/health` (unversioned) and
  `/api/v1/health` is a proposal, not an approved API-versioning policy.

### P0-09 — closure readiness review; owner sign-off pending (2026-11-16)

- Added [`PHASE_0_CLOSURE.md`](PHASE_0_CLOSURE.md): the four roadmap acceptance
  criteria and the Phase 0 feature IDs measured against evidence, open owner
  decisions, a step-by-step Windows validation procedure with a results table,
  and a blank sign-off record. Verdicts: backend tests and frontend build are met
  (CI, Ubuntu and Windows runners); Windows installation is partial (runner
  evidence only; the README's own Windows steps have not been run anywhere);
  documentation is mostly met.
- Corrected a stale README paragraph that still said the repository had no
  database integration or migrations.
- `CLAUDE.md` was deliberately not created: DOCUMENTATION_POLICY says to record
  its absence rather than invent instructions. The owner is asked to supply it.
- Phase 0 is **not** closed. It needs the owner's Windows run, decisions on
  DEC-009/029/031, and a completed sign-off record; Phase 1 must not start
  before that (master spec §20, rule 11). No Feature ID status is changed.

### P0-08 — quality gates and job/flag foundation; CI passed (2026-11-16)

- Backend: migration `0002` adds `input_version` and `result` to
  `background_jobs`, closing a gap against the ARCH-PLAT-002 criterion (versioned
  input, output/error, start/end time). Added `feature_flags.py` (unknown flags
  are off; keys validated) and `jobs.py` (explicit state machine
  queued→running→succeeded/failed/cancelled, failed→queued retry, terminal
  states enforced, error text truncated, attempts counted). 18 new tests,
  including a data-preserving 0001→0002→0001 round trip, run on SQLite and on
  PostgreSQL 17.
- Lint: `ruff check` (rules E, F, I, B, UP) on the API and ESLint
  (`eslint-config-next`, core-web-vitals + TypeScript) on the web app, both
  enforced in CI. One react-hooks rule is disabled on a single line in
  `theme-toggle.tsx` with a written reason (the theme is set before hydration and
  can only be read from the DOM after mount).
- Browser tests (Playwright, Chromium; desktop and Pixel 7 viewport projects):
  47 tests passed on Ubuntu and Windows runners, 3 skipped by design (the
  Tab-order tests run on desktop only). They cover RTL/lang, landmarks, no
  horizontal overflow at 320/375/768/1024/1440px in light and dark, 24×24px
  target size, skip link, focus order and visible focus ring, theme toggle with
  Enter/Space, storage persistence and unavailable storage, the 404 page, and
  axe-core WCAG 2.0/2.1/2.2 A/AA scans of the home and 404 pages in both themes.
- Finding: the first axe run failed on `label-content-name-mismatch` (WCAG
  2.5.3, serious): the brand link's `aria-label` did not contain its visible text.
  The `aria-label` was removed so the name comes from the visible text; this is a
  non-visual change, but it is a change to a component whose appearance the
  owner approved in P0-04.
- Limits: automated checks find only part of the accessibility problems. No
  manual screen-reader, real-device, Firefox/Safari, text-zoom, or performance
  testing was done, and no Persian-PDF suite exists yet. A Windows runner is not
  the owner's own Windows machine. CI run 43814012419 (PR #5): all seven jobs
  passed; the PostgreSQL job ran 61 API tests, OK, none skipped.
- Mapping: partial progress on TEST-001, ARCH-PLAT-002, and OPS-003. Not done:
  versioned-API contract tests beyond `/api/v1/health`, domain-boundary import
  checks, performance and regression suites, authorization/isolation tests, a
  real job runner/queue (DEC-029), and the P0-09 closing validation. No Feature
  ID status is changed. New dev dependencies are provisional (see
  OPEN_DECISIONS).

### P0-07 — database foundation; CI passed (2026-11-16)

- Added `SMART_ENGINEER_DATABASE_URL` (validated; PostgreSQL required in
  production, SQLite accepted otherwise for tests; the value is never echoed or
  logged), SQLAlchemy declarative base with constraint naming conventions, and
  two operational tables only: `feature_flags` and `background_jobs`
  (status check constraint, JSON payload). Alembic is configured in
  `apps/api/alembic.ini` and `apps/api/migrations`, with baseline revision
  `0001` and working downgrade. No identity, project, or product tables exist;
  they belong to later phases. The `/health` endpoint still does not touch the
  database.
- Tests: 19 new tests. They cover upgrade, downgrade and re-upgrade, a drift
  check (migrated schema equals the models), model round trips, and database
  enforcement of the status check and primary key. They run on SQLite in every
  API job; a dedicated Ubuntu job runs them against PostgreSQL 17. CI run
  43806424484 (PR #4) passed all five jobs: the PostgreSQL job ran 43 tests, OK,
  with none skipped; the other API jobs ran 43 with the 6 PostgreSQL tests
  skipped by design.
- Mapping: partial progress on OPS-002 (migration strategy and an applied,
  reversible baseline) and DATA-001. Not done: the domain model, a
  development-database workflow decision (DEC-009), backup and restore,
  migration rollout policy, and any product schema. No Feature ID status is
  changed. The library choices are provisional (see OPEN_DECISIONS, DEC-029 and
  DEC-009).
- First CI attempt failed because of a bug in a new test (an ID read before the
  session flushed it); it was fixed in the test and no application code changed.

## Phase 1 — Product core and project management

**Features**

- Initial account registration/login and roles; profile and project membership
  foundations.
- Create, edit, list, and archive projects; project dashboard and activity
  history.
- Staged parcel/site and client-requirement forms with validation, draft saving,
  and later completion.
- Record project identity, type, location, purpose, ownership/legal-status
  information without claiming automated legal validation, team, and members.
- Capture parcel geometry/survey and declared/computed area, orientation,
  access, terrain, surroundings, obstacles, existing infrastructure, and
  available soil/geotechnical data.
- Capture zoning/building-control inputs and their source references; represent
  unverified or unavailable rules as unknown / requiring inquiry, never an AI
  guess.
- Capture client program, room counts/areas, accessibility, privacy, style,
  quality, budget, priorities, constraints, future expansion, and reference
  images; capture sourced climate, hazards, seismic, utility, and energy data.
- Securely upload and manage project photos, documents, and other attachments
  with type, date, and ownership metadata.

**Dependencies:** Phase 0 acceptance. Backend authorization and project/tenant
scoping are required before project data is exposed.

**Acceptance criteria (specification):** A user can manage a project from
creation through completion of its initial inputs; backend access controls are
tested.

**Feature IDs and acceptance:** IAM-001/002, ROLE-001, ADMIN-001, PRJ-001/002, INP-001/002,
SITE-001/002, RULE-DATA-001, REQ-001/002/003, ENV-001, FILE-001, SEC-002, FLOW-001,
AI-001/002/003. See the corresponding acceptance criteria in
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). AI-002 is limited to
file types/provider behavior approved under DEC-023/027.

## Phase 2 — Site and reliable geometry engine

**Features**

- Support rectangular, polygonal, and irregular parcels; boundaries, lengths,
  area, perimeter, orientation, and access fronts.
- Explicit units, coordinate systems, and conversions; distinguish declared
  area from computed area and report discrepancies.
- Apply registered setbacks to calculate the buildable envelope; do not infer
  setbacks or regulations that have not been sourced and recorded.
- Test invalid and boundary geometries against numerical reference cases.
- Display and edit a parcel on a 2D canvas.

**Dependencies:** Phase 1 acceptance; parcel/site data and explicit unit and
coordinate conventions must be available.

**Acceptance criteria (specification):** Geometry results match reference
examples and numerical tests.

**Feature IDs and acceptance:** GEOM-001/002/003/004. See
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). Setback acceptance
is gated by DEC-013/030; parcel geometry calculations do not depend on
environmental/climate data.

## Phase 3 — First architecture engine

**Features**

- Create a physical program and room/space list; produce multiple conceptual
  layout alternatives with explainable criteria, placement, privacy,
  orientation, and limitations.
- Represent spaces, walls, doors, windows/openings, dimensions, and multiple
  floors; copy/repeat typical floors and represent vertical connections.
- Interactively move, resize, rotate, add, remove, and edit elements; lock
  elements/dimensions; provide snap/grid, dimensions, and metre/centimetre/
  millimetre display.
- Provide undo/redo, change history, design versioning, comparison of two or
  more versions, and comments attached to a space or element.
- Check closed space geometry, unintended overlap, access, invalid geometry,
  and area totals versus building area. Apply minimum dimensions only where
  verified rule inputs are available; distinguish preliminary checks from the
  formal, versioned rule-engine findings in Phase 4.
- Provide supported preliminary checks for daylight/natural ventilation,
  privacy/views, access and egress, parking, vehicle circulation, stairs,
  elevators, and ramps; surface constraints and unsupported checks.
- Generate scaled conceptual 2D plans, dimensions, room names/areas, door and
  window schedules, optional furniture plans, and supported-stage elevations
  and sections.
- Generate PDF and image outputs; label conceptual status and limitations.
  DXF/DWG is conditional on implementation and compatibility validation; 3D/IFC
  belongs to the BIM phase.

**Dependencies:** Phase 2 acceptance; requires a valid parcel/buildable-area
representation and the Phase 1 requirements.

**Acceptance criteria (specification):** Designs can be edited, saved,
compared, and reproduced; all limitations are transparent.

**Feature IDs and acceptance:** ARCH-001–ARCH-009, ROLE-009/011, BIM-001, DOC-001, FLOW-004,
AI-003/005. See [`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md).
AI-005 remains a proposal-generating aid only; DEC-032 governs rollout of
AI-assisted design.

## Phase 4 — Regulations and architectural validation

**Features**

- Ingest official, versioned national and local regulations and project-specific
  requirements with source, clause, interpretation, applicability, publication
  and effective dates.
- Implement a deterministic, testable rule engine with traceable inputs and
  results.
- Classify findings as compliant, non-compliant, data-needed, or
  human-review-needed; show the supporting clause beside each finding.
- Support documented checks for daylight, access, stairs, parking, dimensions,
  and other explicitly supported architectural rules.
- Provide expert-admin review/approval of regulatory content. Deactivate
  obsolete versions only with a recorded reason and date.
- Record the exact rule/version applied to every design version. Never transfer
  a language-model-generated clause or value into the rule engine without a
  verified source and review.

**Dependencies:** Phase 3 acceptance; Phase 1 documented regulatory inputs and
Phase 2 geometry; authoritative sources and jurisdictions must be identified
before rules can be represented as active requirements.

**Acceptance criteria (specification):** Every result traces to a regulation
and version; missing data is not replaced by a guess.

**Feature IDs and acceptance:** RULE-001/002/003, ROLE-006/010, ADMIN-002,
ARCH-010, AI-003/006. See
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). AI explanations may
only quote an active source-linked finding; otherwise they must say no
verified source is available.

## Phase 5 — 3D and BIM

**Features**

- Derive the 3D model from the shared, versioned base building model; support
  floors, elevations/heights, and materials.
- Implement controlled IFC import/export, property/identifier mapping, and
  preservation checks.
- Report incomplete, inconsistent, unclassified, or unmapped model elements and
  perform model-quality checks before export.
- Connect drawings, schedules, quantities, and reports to a specific model
  version; keep the model the single source of geometry and element properties.

**Dependencies:** Phase 3 acceptance and the versioned domain model; Phase 4
regulation references are included where applicable. IFC scope and formats
remain subject to open decisions.

**Acceptance criteria (specification):** Exchanged models are checked for loss
of important identifiers and properties.

**Feature IDs and acceptance:** BIM-002/003/004/005, AI-003/007. See
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). AI extraction of
drawings/BIM is limited to formats and versions approved under DEC-004/023/027.

## Phase 6 — Structural engineering

**Features**

- Record structural system, materials/mechanical properties, assumptions, grid,
  and floor elevations; preliminarily locate columns, beams, shear walls, and
  other supported elements.
- Define gravity/lateral transfer, dead/live/wind/seismic loads, and
  combinations under the active supported code.
- Analyze stability and supported displacements, drift, forces, and design
  ratios; design reinforced-concrete and steel members only within the
  validated solver scope.
- Perform preliminary foundation design only when adequate geotechnical data is
  available.
- Detect architecture/structure inconsistency, floating columns, disconnected
  beams, unclear load paths, irregularities, insufficient soil/loading data,
  solver warnings, and non-convergence.
- Report assumptions, sources, solver version, errors, checks, and calculations;
  support structural-engineer review, approval, or revision request.
- Invalidate/stale structural results when geometry, materials, or loading
  changes. Do not present default dimensions/reinforcement as a final design.

**Dependencies:** Phase 5 shared model (or an explicitly approved compatible
model interface), adequate project/soil inputs, selected licensed solver and
supported code, and regulatory/code decisions. Professional output is gated on
benchmarking, independent validation, and qualified review.

**Acceptance criteria (specification):** Benchmarks, independent validation,
and specialist approval have been completed for the declared scope.

**Feature IDs and acceptance:** STR-001–STR-007, ROLE-002/007, ADMIN-003,
AI-003. See
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). Solver, code,
licensing, validation scope, and authorized professional sign-off are gated by
DEC-002/005/007/014/028.

## Phase 7 — MEP and coordination

**Features**

- Mechanical: cold/hot water, wastewater/vent, rainwater/drainage,
  heating/cooling/ventilation; preliminary equipment and capacity selection;
  duct/pipe/riser routes; supported slope/diameter calculations, insulation,
  specifications, drawings, riser diagrams, and equipment schedules.
- Electrical/low voltage: lighting/receptacle loads, panels/circuits, cable and
  conduit routes, grounding/protection, emergency lighting/exit signs, fire
  alarm/safety systems, network/telephone/camera/access control, supported load
  schedules and drawings.
- Coordinate routes with structural/architectural elements and other services;
  manage shafts/risers and maintenance access.
- Record clashes, locations, and severity; support resolution and re-review.

**Dependencies:** Phase 5 shared BIM/model geometry and Phase 6 structure for
cross-discipline coordination; selected, licensed, validated engineering
methods and specialist review.

**Acceptance criteria (specification):** Reference examples and the specialist
approval workflow succeed.

**Feature IDs and acceptance:** MEP-001–MEP-005, ROLE-003/013, ADMIN-005,
AI-003. See
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). Supported system
scope, methods, licenses, and professional approval are gated by
DEC-005/020/028.

## Phase 8 — Quantity takeoff and estimating

**Features**

- Derive length, area, volume, count, and weight from the model; group by floor,
  space, system, and operation.
- Apply configurable measurement rules, coefficients, opening deductions, and
  applicable measurement instructions; trace quantities to source elements.
- Allow manual quantity corrections only with a reason and user audit record;
  report raw, adjusted, and final quantities.
- Import annual official price books and disciplines with source file/hash,
  publisher, year, receipt date, code, description, unit, price, chapter, and
  decomposition/source data when available.
- Map quantities to price items; retain market prices separately from official
  schedules; record region, coefficients, contract conditions, assumptions,
  and source/date; compare editions and flag unmapped/obsolete items.
- Produce base official-schedule estimates and, when adequate sourced data is
  available, current-market estimates; distinguish materials, labor, machinery,
  transport, and ancillary costs when supported.
- Save estimate versions; compare changes; provide low/mid/high scenarios,
  price/quantity sensitivity, uncertainty range, and explicit exclusions.

**Dependencies:** Phase 5 versioned model; Phase 7 outputs where applicable;
approved measurement rules, official price-book sources, market-price sources,
and licensing decisions.

**Acceptance criteria (specification):** Quantities and costs are traceable and
compared with a manual reference takeoff.

**Feature IDs and acceptance:** QTY-001/002, EST-001/002/003, ROLE-004/012,
ADMIN-004, AI-003/008.
See [`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). Official/market
sources and licensing remain gated by DEC-006/021.

## Phase 9 — Professional documents and approval workflow

**Features**

- Produce a complete project record: project/site summary, client needs, design
  bases/assumptions, regulation sources/versions, plans/elevations/sections,
  space/door/window/material schedules, compliance findings, approved
  structural/MEP reports, clash status, sourced takeoff/estimate, version and
  approval history, warnings, and unresolved-review items.
- Produce Persian RTL and English PDFs with permitted embedded fonts, contents,
  page numbers, project/version titles, drawing scale/units, and draft,
  conceptual, reviewed, or approved status watermarks.
- Provide separate drawing/report exports, secure access-controlled expiring
  download links, and complete ZIP packages.
- Support collaboration: project invitations/roles, assigned tasks/owners/due
  dates, comments on issued documents/drawings (design-space/element comments
  begin in Phase 3), stage/approver status, and
  timestamped decisions with explanations.
- Implement the proposed workflow: site information → requirements →
  architecture options → client approval → regulation checks → structure/MEP →
  coordination → takeoff/estimate → final check → document issuance.
- Block final issuance while critical checks remain open; maintain audit trails
  and lock issued versions while managing revisions.
- Support in-app notifications and email/SMS only when services are connected;
  provide project activity reporting.

**Dependencies:** Phases 1–8 as applicable to the contents of the project
package; role/approval policy, status vocabulary, document generation, secure
storage/download, and audit history must be defined.

**Acceptance criteria (specification):** A sample project is traceable from
initial input through the final project package.

**Feature IDs and acceptance:** DOC-002/003/004, ROLE-005, FLOW-002/003/005/006,
AI-003/009. See [`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md).
Professional approval/signature authority and any required provider integration
remain gated by DEC-007/008/010/028.

## Phase 10 — Commercialization and public release

**Features**

- Organizations/teams and commercial plans (free, professional, organizational,
  usage-credit), with limits for projects, file volume, exports, and AI usage.
- Secure account confirmation as needed, recovery, session management,
  subscription administration, consumption reporting, trial/discount options
  when required.
- Integrate an Iranian payment provider only after provider selection and
  contract review; support invoices, renewal, cancellation, and payment history.
- Manage secrets securely; never put API/payment secrets in frontend code or a
  public repository.
- Monitor service health, errors, and job queues; provide scheduled backups and
  tested recovery.
- Perform load, security, and penetration tests; document deployment, incident
  response, and support operations.

**Dependencies:** Prior phase gates for the commercialized feature scope;
decisions on provider, contracts, hosting/resources, pricing, data policy, and
operational support.

**Acceptance criteria (specification):** Security, recovery, load, and support
processes are documented and tested.

**Feature IDs and acceptance:** BILL-001/002/003, AI-010, ROLE-008, ADMIN-006/007,
FLOW-007, SEC-004. See [`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md).
Provider, contract, pricing, service limit, recovery, and support decisions are
gated by DEC-009–012, 015–017, 021, 024, and 027/032.

## AI rollout status

The master specification defines AI capabilities but does not assign their
rollout to numbered phases. The roadmap therefore places capabilities only
where they depend on the corresponding project data/workflow and records
provider/format-dependent work as decision-gated: intake assistance (Phase 1,
AI-001); PDF/image extraction (Phase 1, AI-002, subject to DEC-023/027);
conceptual design suggestions (Phase 3, AI-005); rule explanations (Phase 4,
AI-006); drawing/BIM extraction (Phase 5, AI-007, subject to DEC-004/023/027);
takeoff mapping suggestions (Phase 8, AI-008); report generation and
role-specific assistance (Phase 9, AI-009); usage/cost attribution (Phase 10,
AI-010). AI safeguards (AI-003) apply in every phase that enables an AI
capability. The AI Gateway implementation phase remains **UNRESOLVED (DEC-032)**;
its technology is a proposal, not an approved decision.

These placements are planning dependencies, not authorization to start any
phase or to use AI for authoritative engineering/regulatory decisions.
All AI application features depend on AI-004. Until DEC-032 resolves the
gateway boundary and phase, the non-AI scope of a phase may proceed only after
its gate, while its AI subfeatures remain blocked.

## Role, collaboration, and notification rollout

- Phase 1 establishes role identities, project-scoped permission enforcement,
  owner/client intake access, architect input review, and invitations
  (ROLE-001, FLOW-001).
- Phase 3 adds architect design permissions (ROLE-009), client option
  view/comment permissions (ROLE-011), and drawing/model
  comments (FLOW-004); structural, MEP, and
  estimator permissions are introduced with their modules in Phases 6, 7, and
  8 (ROLE-002/003/004).
- Regulation and price-book publishing permissions are split with their
  respective resources (ROLE-006/ADMIN-002 in Phase 4; ROLE-012/ADMIN-004 in
  Phase 8); architect rule-review permission is ROLE-010 (Phase 4);
  structural and MEP engine administration is split with those modules
  (ROLE-007/ADMIN-003 in Phase 6; ROLE-013/ADMIN-005 in Phase 7).
- Phase 9 adds role-specific approvals/document access (ROLE-005), task
  assignment and due dates (FLOW-005), issued-document comments (FLOW-006),
  stage workflow (FLOW-002), and in-app notifications (FLOW-003). Architectural
  design comments (FLOW-004) are Phase 3.
- Phase 10 adds organization/system administration (ADMIN-006/007 and ROLE-008)
  and optional email/SMS delivery (FLOW-007), gated by provider approval
  (DEC-010). Email/SMS delivery remains conditional on configured
  providers (DEC-010).
- No role gains professional approval authority solely because an account has
  that role;
  DEC-007/008/028 must establish that authority.

## Role-specific product capabilities

These are cross-phase permissions and workflows, not additional phases. Enforce
them server-side and scope data to authorized projects/organizations:

- **Owner/client:** manage profile and project inputs; complete missing
  information; compare/comment on options; approve or reject stages; see
  understandable reports, estimates, and cost changes; download permitted
  documents; inspect history; invite engineers with limited access.
- **Architect:** manage assigned projects; review inputs and space requirements;
  create/edit/compare designs; manage spaces, dimensions, openings, circulation,
  regulation findings, and drawing/model exports; record professional notes and
  legally supported sign-off.
- **Structural engineer:** access the approved architecture version; define
  system/assumptions; inspect axes and load-bearing elements; run only supported
  analysis/design; review warnings/calculations; approve or request revisions.
- **Mechanical/electrical engineer:** access permitted architecture/structure;
  design supported routes/equipment; coordinate clashes and space needs; issue
  schedules/reports; record review status.
- **Estimator:** set measurement bases; inspect approved elements/specifications;
  review quantities, coefficients, price-book mappings; prepare estimates,
  scenarios, and variance reports.
- **System administrator:** manage identities, roles, organizations/projects,
  reviewed regulation/price resources, engine versions/settings, security
  events, service health, and commercial subscriptions/quotas when enabled.

## Quality and change-control gates for every phase

- Test independent logic, integrations, API contracts, authorization and
  tenant isolation, invalid/boundary/incomplete input, migrations, performance
  (including calculations and large files), reproducibility, regression, mobile
  and desktop UI, RTL/LTR, and Persian PDF fonts as applicable.
- Do not declare a release complete merely because it runs on a developer's
  machine. Require a clean installation, recorded test results, successful
  production build, manual acceptance scenarios, no open critical/security
  defects, updated documentation/version, and a rollback path.
- Track unique feature IDs and statuses; defer items only with a reason and
  return condition. Document scope-change impacts on data, APIs, security, UI,
  tests, and documents. Do not mark a feature implemented without tests and
  acceptance criteria.
- Preserve the full report format and session controls in the master
  specification's Sections 19–20. See
  [`DOCUMENTATION_POLICY.md`](DOCUMENTATION_POLICY.md).

## Master-specification traceability

This index cross-checks every numbered master-specification section against
these derivative planning documents. The master specification retains the full
requirements; this table is an index, not a replacement.

| Master section | Coverage in this documentation set |
|---:|---|
| 1 — Vision and non-negotiable principles | Architecture overview; CORE entries; phases 1–10 |
| 2 — Roles and access | Feature registry IAM/ROLE/ADMIN entries; phases 1, 3, 4, 6–10 |
| 3 — Project inputs | Feature registry INP/SITE/RULE-DATA/REQ/ENV/FILE entries; phase 1 |
| 4 — Architecture and spatial design | Feature registry ARCH/DOC entries; phases 2–4 |
| 5 — Geometry and BIM data model | BIM entries; phases 2, 3, 5 |
| 6 — Structural engine | STR entries; phase 6 |
| 7 — Mechanical/electrical systems | MEP entries; phase 7 |
| 8 — Regulations and rules | RULE entries; phases 1, 4 |
| 9 — Takeoff, prices, estimates | QTY/EST entries; phase 8 |
| 10 — Documents and reports | DOC entries; phases 3, 9 |
| 11 — AI assistant and limitations | AI entries; cross-cutting CORE-001/003; open provider decision |
| 12 — Collaboration and approvals | FLOW entries; phases 1, 9 |
| 13 — Accounts, commercialization, payments | BILL entries; phase 10 |
| 14 — Security, privacy, resilience | SEC entries; cross-cutting CORE-004; phases 0, 1, 10 |
| 15 — Technical architecture | OPS/ARCH-PLAT entries; architecture overview |
| 16 — Conceptual data model | DATA-001; architecture overview's conceptual data domains |
| 17 — Version roadmap | All 11 phases and acceptance criteria in this roadmap |
| 18 — Quality and testing | TEST-001, RELEASE-001; roadmap quality gates |
| 19 — Change control | GOV-001; documentation maintenance policy |
| 20 — Development-session instructions and final report | Documentation maintenance policy |
| 21 — Decisions for owner/specialist | Open decisions DEC-001–DEC-033 |
| 22 — Initial truth/status rule | Phase status and registry rules; no planned item is presumed implemented |
