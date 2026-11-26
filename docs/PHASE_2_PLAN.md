# Phase 2 — local-plane geometry and parcel editor

Implementation date: **2026-11-25**. Feature IDs: GEOM-001/002/003/004.
The owner explicitly authorized starting this phase after stabilizing the current
Phase 1 core. Formal full-phase acceptance and release remain separate.

## Implemented contract
- The independent `smart_engineer_api.geometry` module computes rectangular,
  polygonal and concave parcel area, perimeter, side lengths, local bearings,
  geographic bearings only with a recorded north angle, orientation and bounds.
- Internal boundary coordinates and dimensions remain metres. `canonicalize`
  accepts m/cm/mm for boundary coordinates/dimensions only; declared area remains
  m² and independently recorded survey points/side lengths retain their existing
  metre contract. The editor converts display coordinates without changing the
  stored shape. No arithmetic result supplied by the browser is trusted.
- Coordinates are **local Cartesian X right / Y up**, with a recorded local frame.
  Existing `coordinate_system` text is a descriptive survey reference, not an
  automatic UTM/EPSG/geographic transformation. Actual projection/transformation
  requires a separately validated future implementation; unsupported frames are
  rejected, not silently treated as metres.
- At most 200 boundary vertices; coordinates bounded to ±10,000,000 m; rectangles
  have sides 0.01–100,000 m. Non-finite, duplicate, zero-edge, degenerate,
  self-intersecting and insufficient-clearance geometries are rejected explicitly.
  There is no hidden polygon repair, convex-hull substitution or guessed area.
- Stable translated shoelace summation avoids cancellation on large coordinates.
  Area discrepancy classification uses raw values **before** display rounding.
- Responses carry engine version, canonical units, parcel input hash, source
  record versions and numerical development defaults. Results are calculated
  from current inputs, not an unversioned cache.

## Numerical defaults — not approved survey tolerances
Length epsilon: 1e-7 m; area epsilon: 1e-8 m²; discrepancy threshold: 1% (existing
Phase 1 development default). Distances use double precision. Boundary outputs
are not rounded before topology operations. These defaults are reference-test
contracts, not a statement of legal/survey accuracy or approval by a specialist.

## GEOM-003 — sourced setback clearance
`SiteSection` and `ZoningRecord` remain the single source of truth; no duplicate
parcel/model table was introduced. Optional metadata fits their existing JSON.

Each edge is explicitly assigned front/rear/left/right and consumes that recorded
metre clearance. Missing clearances are not zero. Adding/removing/reordering
vertices in the UI clears the assignment so it must be confirmed again.

A computational source must contain type, date/calendar, title or reference,
`source_revision`, `source_verified=true` and ISO Gregorian `valid_from` /
`valid_until`. Expired/future/incomplete/unverified sources do not produce an
envelope. Existing Phase 1 records remain readable; they simply require these
additional fields before being used for this calculation. Free-text correction
lines are not interpreted automatically: they require human review.

The geometric method subtracts the union of Euclidean distance exclusions around
**the actual finite boundary segments**, handling concavity, holes, disjoint
pieces and empty results. Circular joins are conservatively circumscribed with
at most 0.001 m extra clearance; thus the approximation does not claim extra
buildable space. Straight-offset reference comparisons account for this small
conservative bias. It is not a generalized interpretation of local statutory
setback/correction-line rules. A maximum footprint area is reported separately
only if the coverage record has its own complete valid source; no footprint
layout is invented from a percentage.

All results are marked preliminary and based on user-entered sources. Source
verification here is the recorder's explicit statement, not independent municipal
verification, legal compliance, engineering approval or a construction permit.
The official Phase 4 regulation engine and DEC-013/014/025 remain separate.

## API, authorization and UI
- GET `/api/v1/projects/{id}/geometry`: current saved geometry and source versions.
- POST `/api/v1/projects/{id}/geometry/preview`: validated normalized draft report,
  without database writes; the response includes canonical parcel data.
- Existing PUT `/api/v1/projects/{id}/site/parcel`: save with expected version.
  The atomic document helper prevents overwriting a newer edit.
- Existing backend project view/edit permissions, CSRF and origin checks, tenant
  isolation and archived-project read-only policy are reused.

The parcel form contains a responsive SVG drafting sheet: grid, vertices and
edges, numeric and pointer editing, keyboard arrows (Shift for ten steps),
rectangle creation, free polygon drawing, vertex add/remove, zoom/fit, m/cm/mm
view units, optional snap, edge assignment, source reasons and hatched envelopes.
Numeric inputs are an accessible alternative to dragging; dark/light and RTL/LTR
coordinate presentation follow the existing site. Draft changes do not become
saved data until the section is saved. A 409 retains the draft and offers an
explicit discard/reload action. Late preview responses are ignored.

## Verification evidence
| Check | Outcome |
|---|---|
| Earlier configuration/permissions/scanner/syntax/Ruff baseline | Reused, not rerun at owner's request |
| Earlier full SQLite API suite | **352 reported: 220 executed/passed, 132 skipped**, 2624.291 s; reused baseline, not rerun and not proof of new code |
| New reference + stabilization/API tests | **19 passed** (initial in-memory run); test-fixture cleanup warnings corrected afterward |
| Eight new integration tests after explicit QueuePool fixture correction | **8 passed in 3.580 s**, no SQLite thread-cleanup errors |
| New frontend TypeScript | **Passed** |
| ESLint on geometry editor, site form and changed supporting frontend files | **Passed** |
| Production build of updated frontend | **Passed**, including Next.js TypeScript stage |
| Targeted Ruff | Import/line-length issues fixed; final changed-file check recorded when finished |
| Playwright Chromium installation | **Blocked**: CDN HTTP 403, service not available in this location |
| New automated browser geometry specs | **8 passed** in installed Microsoft Edge (`msedge`): desktop/mobile, units, pointer/keyboard, conflict, read-only and axe scan |
| New real full-stack geometry scenario | **1 passed** in installed Microsoft Edge; browser → Next.js → FastAPI → disposable migrated SQLite, no API mocks |
| Live web/API preview | Launched with disposable, Alembic-migrated SQLite; real project and 10×20 m parcel report rendered (200 m², 60 m); screenshot/layout inspected |
| PostgreSQL, manual screen reader, real device | Not executed here |

The new tests use isolated shared-memory SQLite databases with a thread-safe
QueuePool; they never open existing project data. The inherited FastAPI
TestClient/HTTPX deprecation warning remains an upstream dependency warning,
not an application-test failure. No pre-existing test suite was restarted.

## Repeatable local preview (disposable data)
From the project root, prepare dependencies once:

```powershell
uv sync --locked --all-packages
```

```powershell
pnpm install --frozen-lockfile
```

Run the temporary API (creates/migrates its own database; no SMTP sends):

```powershell
uv run --locked --package smart-engineer-api --group dev python scripts/run-geometry-preview.py
```

In a second terminal, build/start the web app:

```powershell
pnpm --filter @smart-engineer/web run build
```

```powershell
pnpm --filter @smart-engineer/web run start
```

Open `http://127.0.0.1:3000`, register a disposable account, create a project and
use **داده‌های زمین → قطعه و مساحت → بوم زمین**. A normal graceful API shutdown
removes the temporary data; a force-kill or machine crash may leave its directory
in the operating system's temporary folder. This launcher is **not** production
configuration and must never be used for data intended to persist.

For future verification of only the newly added tests (not run again automatically):

```powershell
$env:PYTHONPATH = "apps/api"; uv run --locked --package smart-engineer-api --group dev python -m unittest tests.test_stabilization tests.test_geometry
```

Where the pinned Chromium download is unavailable but Microsoft Edge is already
installed, set `PLAYWRIGHT_CHANNEL=msedge` to use that installed browser. For a
local disposable API/web pair already started with the preview launcher, set
`SMART_ENGINEER_REUSE_SERVERS=1` for the full-stack config. Defaults remain
unchanged in CI (fresh servers and pinned Chromium). Select only
`e2e/geometry.spec.mjs` or `e2e-fullstack/geometry.spec.mjs`, not the legacy suites.

## Remaining acceptance / limits
No design generation, architectural-plan editing, structural/MEP calculation,
IFC/BIM model, quantity takeoff, pricing, PDF issuance or legal approval was added.
Automatic geodetic transformation and official rule interpretation are unsupported.
A numerical result is not a Phase 2 owner/specialist sign-off. The Phase 1
outstanding scope and production security/operations controls remain listed in
`PHASE_1_STABILIZATION.md` rather than being silently waived.
