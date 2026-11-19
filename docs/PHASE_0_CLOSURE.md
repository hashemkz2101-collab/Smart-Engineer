# Phase 0 closure readiness review

- **Date of review:** 2026-11-16
- **Status of this document:** READINESS REVIEW — **not** a sign-off. Phase 0
  stays IN PROGRESS until the owner records evidence and approval in section 7.
- **Evidence base:** repository at commit `cf36380` (main after P0-08); GitHub
  Actions run 43815075682 on that commit; earlier recorded runs listed in
  [`ROADMAP.md`](ROADMAP.md). CI results are runner evidence (GitHub-hosted
  Ubuntu and Windows images), not a run on the owner's own machine.

Phase advancement rules come from [`PHASE_STATUS.md`](PHASE_STATUS.md): a phase
may advance only when its roadmap acceptance criteria and applicable quality
gates are evidenced, and the change must record date, evidence, owner/reviewer,
unmet criteria, and approved exceptions. No feature status in
[`FEATURE_REGISTRY.md`](FEATURE_REGISTRY.md) is changed by this review.

## 1. Roadmap acceptance criteria for Phase 0

| # | Criterion (ROADMAP.md) | Verdict | Evidence | Gap |
|---|---|---|---|---|
| 1 | Repeatable installation on Windows | **Partial** | `windows-latest` CI jobs install with frozen lockfiles and pass API tests, typecheck, build, smoke, and browser tests. README has a PowerShell setup section. | CI installs Node/Python with GitHub actions, so the README's own Windows steps (MSI/installer, pip-installed uv) have **not** been run anywhere. No run on the owner's machine. DEC-031 (accepted method) is open. |
| 2 | Backend tests pass | **Met** | 61 API tests pass on Ubuntu, Windows, and PostgreSQL 17 (PostgreSQL job: none skipped); `ruff check` clean. | The suite is small and covers the Phase 0 foundation only. |
| 3 | Frontend production build succeeds | **Met** | `next build` passes on Ubuntu and Windows runners; typecheck, ESLint, 4 smoke tests, and 47 browser tests pass. | Chromium only. |
| 4 | Setup and run documentation is complete | **Mostly met** | README covers install, run, tests, lint, browser tests, migrations, and logging/errors; ADR-0001 and OPEN_DECISIONS record decisions. | `CLAUDE.md` (master spec §20) is absent (see section 4). Windows steps unverified (criterion 1). |

## 2. Other Phase 0 deliverables (ROADMAP "Features")

| Deliverable | Verdict | Notes |
|---|---|---|
| Resolve install/build/test problems; structure, configuration, environments | Evidenced | Pinned toolchain, lockfiles, `.env.example`, validated settings. |
| Baseline domain/data models and migration management | **Partial** | Alembic with revisions `0001`–`0002`; two operational tables only. No domain model; development-database workflow undecided (DEC-009). |
| Logging, explicit error handling, automated tests, CI | Evidenced for the foundation | JSON logs with correlation ID, safe error envelope, CI on two OSes plus PostgreSQL. |
| Architecture decisions and developer setup/run instructions | **Partial** | ADR-0001 exists; later dependency choices are recorded only as provisional prose (section 4). |

## 3. Feature IDs assigned to Phase 0

Verdicts describe evidence for the **Phase 0 slice** against each criterion in
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). Many IDs are marked "0 / all"
and continue through later phases; a "Not evidenced" verdict there usually means
the product code the criterion tests does not exist yet. The owner decides which
of these must be satisfied before Phase 1 (section 5, question 6).

| ID | Verdict | Evidence in repository | Main gap |
|---|---|---|---|
| OPS-001 | Partial | Criterion 1 above | Clean-Windows run with recorded outcomes (DEC-031) |
| OPS-002 | Partial | Fresh DB created from migrations and a 0001→0002→0001 round trip preserving a row, on SQLite and PostgreSQL | No owner-approved fixture records exist |
| OPS-003 | Evidenced | Forced-error test: correlation ID logged, generic 500, no stack trace; CI fails non-zero on failure | Metrics/tracing/monitoring not selected (DEC-029) |
| OPS-004 | Partial | ADR-0001; DEC records in OPEN_DECISIONS | Provisional dependency choices lack alternatives, owner, and date |
| ARCH-PLAT-001 | Partial | `/api/v1/health` route and tests | Only one versioned route; no domain modules, so no boundary check or domain-without-DB tests yet |
| ARCH-PLAT-002 | Evidenced at fixture level | Job lifecycle with versioned input, result/error, attempts, start/end; flag off/on; migration rollback/forward | No async runner or queue (DEC-029) |
| SEC-001 | Not evidenced | Input validation errors do not echo input | No auth, tenancy, CSRF, rate limiting, TLS; depends on Phase 1 identity |
| SEC-003 | Partial | Safe errors tested | No audit log, retention, or encryption |
| SEC-005 | Partial | No secrets in repo config; `.env` ignored; database URL never logged or echoed (tested) | **No automated repository or frontend-bundle secret scan exists**, which the criterion requires |
| CORE-001 – CORE-004 | Not evidenced | — | No calculations, lifecycle artifacts, versioned models, or project data exist yet |
| AI-003 | Not evidenced | — | No AI features exist yet |
| DATA-001 | Not evidenced | Two operational tables | Conceptual-schema review of every master §16 entity not done |
| TEST-001 | Partial | Unit/integration, migrations, mobile/desktop and RTL browser tests, axe scans | No API-contract (beyond health), authorization/isolation, performance, reproducibility, regression, or Persian PDF suites |
| RELEASE-001 | Not evidenced | — | No release candidate, manual acceptance, or rollback rehearsal |
| GOV-001 | Partial | Unique IDs and statuses in the registry; evidence recorded per task in ROADMAP | Scope-impact review records not formalised |

## 4. Open items that need the owner

1. **DEC-031 — Windows verification method.** Is a `windows-latest` CI run plus
   one manual run by the owner (section 6) acceptable?
2. **DEC-029 — libraries and services.** Provisionally used, exact-pinned, and
   **not approved**: `sqlalchemy` 2.1.8, `alembic` 1.20.1, `psycopg[binary]`
   3.3.9, `@playwright/test` 1.65.1, `@axe-core/playwright` 4.14.0, `eslint`
   10.15.0, `eslint-config-next` 16.4.6, `ruff` 0.17.5, plus PostgreSQL 17 as a
   CI service container. Approve, replace, or reject each.
3. **DEC-009 — development database.** Docker or a direct PostgreSQL install?
4. **`CLAUDE.md`.** Master spec §20 and DOCUMENTATION_POLICY require it. The
   policy says to record its absence rather than invent instructions, so it has
   not been created. The owner should supply it or confirm it is not needed.
5. **API versioning.** Keep both `/health` (unversioned liveness probe) and
   `/api/v1/health`? This is a proposal, not an approved policy.
6. **Scope of the gate.** Which "0 / all" IDs in section 3 must be satisfied
   before Phase 1, and which are carried forward with a recorded rationale?
7. **A UI change to confirm.** In P0-08 the `aria-label` was removed from the
   brand link (WCAG 2.5.3, found by axe). No visual change, but the appearance
   of that component was approved in P0-04.

## 5. Recommended small items before sign-off (optional)

These are not required by the roadmap's four criteria but close concrete gaps
above. Each would be a separate, small task if the owner wants it.

- A repository and built-frontend secret scan in CI (SEC-005).
- An import-boundary check and a place for domain modules (ARCH-PLAT-001).
- CORS and security-header configuration for the API and web app (SEC-001).
- A formal decision record for the provisional dependencies (OPS-004).

## 6. Windows validation (owner action)

Run on your own Windows machine, ideally one that does not already have other
Node or Python versions. Use PowerShell and follow the README section
"Windows PowerShell" exactly as written; **do not fix anything silently**:
record every extra step you had to take, because OPS-001 requires "no manual
undocumented steps".

| Step | Command (from the repository root unless noted) | Result to record |
|---|---|---|
| 1 | README "Windows PowerShell" install block | Pass/fail; any extra step needed |
| 2 | `pnpm install --frozen-lockfile` and `uv sync --locked --all-packages` | Pass/fail; errors |
| 3 | `uv run --package smart-engineer-api --group dev ruff check apps/api` | Output |
| 4 | `uv run --package smart-engineer-api --group dev python -m unittest discover -s apps/api/tests -t apps/api` | Last lines (`Ran N tests`, `OK`) |
| 5 | `pnpm --filter @smart-engineer/web run lint` and `... run typecheck` | Pass/fail |
| 6 | `pnpm --filter @smart-engineer/web run build` then `... run test:ci` | Pass/fail; output |
| 7 | `pnpm --filter @smart-engineer/web exec playwright install chromium`, then `... run test:e2e` | `N passed` line |
| 8 | Migrations on a throwaway SQLite file: `$env:SMART_ENGINEER_DATABASE_URL="sqlite:///C:/Temp/se-check.db"` then `uv run --package smart-engineer-api alembic -c apps/api/alembic.ini upgrade head` and `... downgrade base` | Pass/fail |
| 9 | Start the API (README "Run the API locally") and open `/health`, `/api/v1/health`, `/docs` | What each shows |
| 10 | Start the frontend (README "Run the frontend") and open `http://127.0.0.1:3000` | Looks as approved? RTL correct? Theme toggle works? |

Record: Windows edition/version, date, and the outcome of each step. Paste the
results (or the failing output) into the conversation or into an issue, and add
a summary to section 7.

### Automated helper for steps 2-9

After doing step 1 by hand, `scripts/windows-validate.ps1` runs steps 2-9 in
order, never "fixes" a failure, and writes `report.md` and `full-output.log` to a
new `windows-validation-<timestamp>` folder in the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows-validate.ps1
```

Options: `-SkipInstall` (dependencies already installed) and
`-SkipBrowserTests` (skip the Chromium download and browser tests). Step 9
starts the API on port 8765 and checks `/health`, `/api/v1/health`, `/docs`,
`/openapi.json`, the correlation-ID header, and a 404; ports 3000 and 8765 must
be free. Step 10 (looking at the page) remains manual.

The script requires Windows PowerShell 5.1 or newer (included in Windows 10 and
11). On an older PowerShell it now stops with a clear message.

**Finding, 2026-11-19:** the owner's first attempt printed the banner
"Copyright (C) 2009" and PowerShell 2.0 style errors (`$PSScriptRoot` empty),
which indicates PowerShell 2.0, normally shipped with Windows 7. The Windows
version on that machine has not been confirmed. The pinned Node.js 24.22.3 and
Python 3.14.10 are not expected to install on such an old Windows (not verified
from official sources in this review), so a Windows 10 or 11 machine is needed
for step 1. This is evidence for DEC-031 and OPS-001: the minimum supported
Windows version should be decided and documented.

The script was exercised once on a GitHub `windows-latest` runner under Windows
PowerShell 5.1 and all steps passed (2026-11-16). That run used pre-installed
tools, so it validates the script, not the README's own installer steps.

## 7. Sign-off record (to be completed by the owner)

| Field | Value |
|---|---|
| Decision | _Phase 0 accepted / accepted with exceptions / not accepted_ |
| Date | |
| Owner / reviewer | |
| Evidence reviewed | _Windows run results; CI run IDs; this document_ |
| Unmet criteria | |
| Approved exceptions and carry-forward items (with rationale and re-entry condition) | |
| Decisions closed (DEC-009 / DEC-029 / DEC-031) | |

Until this table is completed, Phase 0 remains IN PROGRESS and Phase 1 must not
start (master spec §20, rule 11).
