# Phase 3 — first architecture engine (in progress)

Started **2026-11-26** by the owner's explicit instruction. Phase 2 owner/specialist
acceptance is **not** recorded; this is a recorded exception, not a sign-off.
FEATURE_REGISTRY statuses are unchanged.

## Slice 1 — ARCH-001 space schedule

Input: the saved `program` requirement section (REQ-001), which must be complete.
Output: a persisted, versioned document per project (`space_schedules`, migration 0017).

Rules (see `space_schedule.py`; deterministic, nothing invented):

* One schedule entry per counted space, IDs `S-001…` in program order.
* Omitted count → one space, flagged `count_not_given`. Omitted area stays omitted,
  flagged `area_not_given`.
* Room counts are used as listed and **not** multiplied by the number of units
  (the program does not say whether counts are per unit); flagged when units > 1.
* Totals are net room areas only: a lower bound (min, else target) and an upper bound
  (max, else target). `bounds_complete` is true only when every space has an area.
* `program_exceeds_target_area` uses the lower bound (valid even when some areas are
  unknown); `program_below_target_area` is only raised when bounds are complete.
* A schedule remembers the program version it came from and is shown as stale after the
  program changes; it is replaced only by an explicit regeneration
  (`expected_version` compare-and-swap, activity event on success only).
* Permissions: read `project.view`; generate `project.requirements.edit`
  (owner, architect). Archived projects are read-only.

## Not in this slice

Layout alternatives (ARCH-002), editing spaces/walls/doors (ARCH-003), snap/undo
(ARCH-004), floors and vertical connections (ARCH-005), design versions and comments
(ARCH-006), geometry checks (ARCH-007), preliminary checks (ARCH-008), plans and
schedules export (ARCH-009, DOC-001). The schedule is a list with area ranges, not a
layout, and is not a regulatory or design approval.

## Evidence

Automated tests were added (`tests/test_space_schedule.py`, three browser tests in
`e2e/accounts.spec.mjs`). They are run by CI, not on the author's machine.
