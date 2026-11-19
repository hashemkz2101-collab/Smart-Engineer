# Phase status

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
| 0 | Infrastructure and development standards | ACCEPTED WITH EXCEPTIONS (2026-11-19) | P0-03 API shell and completed P0-04 Next.js shell; Linux dependency installation, typecheck/build, and focused API/frontend tests verified. P0-04 initial appearance approved by user. P0-05 CI workflow (Ubuntu + Windows) added; its first run (2026-11-15, PR #1) passed API tests and web typecheck/build/smoke on both runners; this is runner evidence, not a developer-machine Windows install. P0-06 API foundation (env settings, JSON logging with correlation IDs, safe error envelope, `/api/v1` route) added; 24 API tests passed in CI on both runners (2026-11-15, PR #3). P0-07 database foundation (SQLAlchemy, Alembic baseline `0001`, `feature_flags` and `background_jobs` only) added; 43 API tests passed in CI, including a PostgreSQL 17 job (2026-11-16, PR #4); library choices are provisional pending DEC-029/DEC-009. P0-08 (2026-11-16, PR #5): migration `0002` (versioned job input and result), feature-flag and job-lifecycle services, ruff and ESLint, and 47 Playwright browser tests (responsive 320–1440px, RTL, keyboard, theme, axe WCAG A/AA) passed in CI on Ubuntu and Windows runners; 61 API tests passed including on PostgreSQL 17; the axe run found and led to a fix of one real labelling defect on the brand link. Manual screen-reader and real-device testing, a Windows install on the owner's own machine, full Phase 0 gates, and broader OPS-001/OPS-003/TEST-001 criteria remain outstanding at acceptance time. Owner decision 2026-11-19: appearance approved; manual Windows verification waived (not passed; DEC-031 resolved to rely on `windows-latest` CI); exceptions and carry-forward items are recorded in [`PHASE_0_CLOSURE.md`](PHASE_0_CLOSURE.md) section 7. |
| 1 | Product core and project management | NOT STARTED | Phase 0 accepted with exceptions (2026-11-19) and the owner instructed to proceed. DEC-009 and the listed libraries (part of DEC-029) were approved on 2026-11-19; DEC-022 (authentication policy) is only partly decided (email and password chosen) and must be completed before IAM-001. |
| 2 | Site and reliable geometry engine | NOT STARTED | Depends on Phase 1 acceptance and reference geometry tests. |
| 3 | First architecture engine | NOT STARTED | Depends on Phase 2 acceptance. |
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
