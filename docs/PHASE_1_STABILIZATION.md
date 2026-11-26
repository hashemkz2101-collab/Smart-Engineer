# Phase 1 core stabilization — 2026-11-25

## Scope and authority
The owner requested stabilizing the existing Phase 1 implementation, not rerunning
the earlier tests, and implementing the next phase immediately. The next phase is
Phase 2. That explicit instruction allows its start with outstanding items below;
it does **not** approve all remaining Phase 1 scope or a production release.

No `.git` directory or `CLAUDE.md` exists in this supplied copy. No branch,
commit, push, release, or real-database migration has been performed.

## Corrected defects
1. Versioned documents previously read a version and then wrote unconditionally.
   A stale ORM identity map (or overlapping edits) could overwrite version 2 while
   claiming to save version 2 again. `versioned_documents.write_document` now
   performs `UPDATE ... WHERE version = expected_version`, atomically increments
   the version, and reports the existing domain `version_conflict` (HTTP 409) if
   no row matched. The same helper covers intake, site, requirements, zoning and
   environment. Duplicate first inserts conflict, unrelated FK/CHECK failures are
   not disguised, and activity is committed only with a successful write.
2. `file_service.compare_versions` previously calculated latest from only the two
   selected versions. In a series with versions 1, 2 and 3, comparing 1/2 incorrectly
   called version 2 latest and a non-stale takeoff basis. It now uses the maximum
   live version of the entire series, consistently with listing and basis marking.
3. The parcel editor retains its draft on HTTP 409. Reloading and discarding it is
   now an explicit action rather than a silent form remount.

## Evidence and no-rerun policy
- Reused earlier successes: 9 configuration/permission tests, 4 scanner unit tests,
  syntax checks for 89 Python files / 17 JavaScript modules, and whole-API Ruff.
  These checks were not repeated as baseline suites.
- The earlier full SQLite API run finished: **352 reported, 220 executed and
  passed, 132 PostgreSQL-dependent tests skipped** (2624.291 s). It was not
  restarted. Python's unittest discovery had loaded its modules before source
  edits; this is baseline evidence, not evidence about the new implementation.
  Old CI descriptions remain historical only.
- New tests in `test_stabilization.py` and `test_geometry.py` are the verification
  of this change. Their first disk-backed attempt was stopped to avoid repeated
  slow filesystem setup; isolated shared-memory SQLite is used for the new tests.
  Initial successful new-test execution exposed cleanup warnings in the test
  fixture's pool; the fixture was corrected to an explicit thread-safe QueuePool.
- TypeScript and changed-file frontend ESLint passed after the editor was added.
- Current numerical/API test, build and live-preview outcomes are maintained in
  `PHASE_2_PLAN.md`; nothing unexecuted is counted as passing.

## Still outstanding — not erased by stabilization
- Phase 1 AI intake / file-analysis features and provider/privacy decisions.
- Reference examples are textual/linked; full links to uploaded reference images
  and content extraction are not implemented by this change.
- A real production antivirus integration (production files remain pending),
  backup/recovery exercises, retention/deletion/encryption policy, load tests and
  operational deployment decisions.
- Profile/commercial capabilities beyond the current account flows and legally
  recognized professional approval/signature workflows.
- A disposable PostgreSQL verification database is not configured here.
- Playwright's pinned Chromium download returned regional HTTP 403. An already
  installed Microsoft Edge was then used through Playwright's official `msedge`
  channel: **8 new UI checks and 1 new real full-stack scenario passed**. This
  is Edge evidence, not evidence of the pinned Chromium build or other browsers.

## Rollback / persistence
The stabilization adds no tables or migrations and preserves existing API error
codes and records. Phase 2 stores optional metadata in existing JSON documents.
Reverting source must retain those keys or remove them deliberately; never delete
project data to roll back code. Dependency changes are pinned in `uv.lock`.
