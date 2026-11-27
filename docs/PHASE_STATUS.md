# Phase status

Current review: **2026-11-25**. The owner explicitly requested Phase 1
stabilization and immediate Phase 2 implementation. This authorizes starting
Phase 2 with the recorded exceptions; it is not a declaration that every Phase 1
feature or production gate is complete. Current evidence and limits are in
[PHASE_1_STABILIZATION.md](PHASE_1_STABILIZATION.md) and
[PHASE_2_PLAN.md](PHASE_2_PLAN.md).

Historical Phase 0 account (some statements describe earlier snapshots):
Phase 0 is in progress. This status is based on repository evidence, not on
roadmap presence. P0-04's implementation is complete and its initial visual
appearance was approved by the user; this completes that task only, not Phase 0
or its broader acceptance criteria. Automated browser checks (responsive,
keyboard, theme, axe accessibility) now run in CI (P0-08); manual
screen-reader and real-device testing and a Windows install on the owner's own
machine remain unverified. A closure readiness review (criteria vs evidence,
open owner decisions, Windows validation steps, and a blank sign-off record) is
in [`PHASE_0_CLOSURE.md`](PHASE_0_CLOSURE.md); it is not a sign-off.

Allowed project feature states are defined in the master specification:
Planned, In Progress, Implemented, Tested, Released, Blocked, and Deferred.
Phase lifecycle is tracked here separately. A phase may advance only when its
roadmap acceptance criteria and applicable quality gates are evidenced.

| Phase | Name | Status | Acceptance evidence / blocker |
|---:|---|---|---|
| 0 | Infrastructure and development standards | IN PROGRESS | P0-03 API shell and completed P0-04 Next.js shell; Linux dependency installation, typecheck/build, and focused API/frontend tests verified. P0-04 initial appearance approved by user. P0-05 CI workflow (Ubuntu + Windows) added; its first run (2026-11-15, PR #1) passed API tests and web typecheck/build/smoke on both runners; this is runner evidence, not a developer-machine Windows install. P0-06 API foundation (env settings, JSON logging with correlation IDs, safe error envelope, `/api/v1` route) added; 24 API tests passed in CI on both runners (2026-11-15, PR #3). P0-07 database foundation (SQLAlchemy, Alembic baseline `0001`, `feature_flags` and `background_jobs` only) added; 43 API tests passed in CI, including a PostgreSQL 17 job (2026-11-16, PR #4); library choices are provisional pending DEC-029/DEC-009. P0-08 (2026-11-16, PR #5): migration `0002` (versioned job input and result), feature-flag and job-lifecycle services, ruff and ESLint, and 47 Playwright browser tests (responsive 320–1440px, RTL, keyboard, theme, axe WCAG A/AA) passed in CI on Ubuntu and Windows runners; 61 API tests passed including on PostgreSQL 17; the axe run found and led to a fix of one real labelling defect on the brand link. Manual screen-reader and real-device testing, a Windows install on the owner's own machine, full Phase 0 gates, and broader OPS-001/OPS-003/TEST-001 criteria remain outstanding. |
| 1 | Product core and project management | IN PROGRESS — stabilization | Account/organization/project flows, scoped roles, staged inputs, attachments, versions and admin audit exist through P1-20. Atomic document-save and file-comparison regressions corrected on 2026-11-25. Acceptance, remaining AI/file-analysis requirements and production controls are tracked separately in PHASE_1_STABILIZATION.md. |
| 2 | Site and reliable geometry engine | IN PROGRESS — explicitly authorized 2026-11-25 | GEOM-001–004 implementation: deterministic local-plane geometry, explicit units, sourced per-edge clearances and editable SVG parcel canvas. See PHASE_2_PLAN.md for numerical contract, evidence and limits. No legal/survey approval implied. |
| 3 | First architecture engine | IN PROGRESS — explicitly authorized 2026-11-26 (exception: Phase 2 owner/specialist acceptance not yet recorded) | ARCH-001 (space schedule) ARCH-002 (conceptual layout alternatives as blocks, or a specific infeasibility result) and ARCH-003 (editable base design model with locks) and ARCH-004 (m/cm/mm units, grid snap, undo/redo history). See PHASE_3_PLAN.md. No geometry checks, versions, rule checks or exports yet. |
| 4 | Regulations and architectural validation | NOT STARTED | Depends on Phase 3 acceptance and verified regulation sources. |
| 5 | 3D and BIM | NOT STARTED | Depends on the versioned model and Phase 3 acceptance; exchange criteria remain to be decided. |
| 6 | Structural engineering | NOT STARTED | Depends on supported code/solver decisions, adequate data, benchmarks, independent validation, and specialist review. |
| 7 | MEP and coordination | NOT STARTED | Depends on model/structure coordination and selected, validated supported scope. |
| 8 | Quantity takeoff and estimating | NOT STARTED | Depends on model, measurement rules, and approved price data sources. |
| 9 | Professional documents and approval workflow | NOT STARTED | Depends on applicable prior-phase outputs, approval/status policy, and traceability. |
| 10 | Commercialization and public release | NOT STARTED | Depends on provider, legal/business, operational, and security decisions and required prior-phase gates. |

Any change from NOT STARTED must include date, evidence, owner/reviewer, unmet
criteria, and approved exceptions. Do not infer completion from documents,
mock data, or feature plans.
