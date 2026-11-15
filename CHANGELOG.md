# Changelog

Notable repository and product-documentation changes are recorded here. This log
does not imply that planned application features have been implemented.

## Unreleased

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
  smoke tests can start and stop the production server themselves. The workflow
  has not yet been executed on GitHub; it is not evidence of passing tests or of
  Windows installation until a recorded run exists.
- Phase 0 is in progress; registered product feature statuses remain unchanged.
