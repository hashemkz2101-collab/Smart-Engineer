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

## Slice 2 — ARCH-002 conceptual layout alternatives

Inputs, each from its single source of truth: the buildable envelope (site parcel +
zoning setbacks/coverage through the Phase 2 geometry report) and the persisted space
schedule. Output: a persisted, versioned document per project (`layout_proposals`,
migration 0018) holding either **at least two distinct alternatives** or a **specific
infeasibility result**, with the version of every source it used (a change marks it stale).

Rules (see `layout.py`; deterministic, nothing invented):

* An alternative is a set of axis-aligned **space blocks** inside the envelope per floor,
  not walls, doors, windows or a plan. Same envelope is assumed on every floor.
* Block area = target area, else the midpoint of a complete min/max range (recorded as
  `area_basis`). A space with no usable area, outdoor spaces and parking are **not
  placed and are reported with a reason**; every schedule space is either placed or listed.
* Three strategies (`privacy_bands`, `largest_first_compact`, `largest_first_mirrored`);
  identical results are merged, and fewer than two distinct ones is itself reported
  (`fewer_than_two_distinct_alternatives`).
* A recorded coverage maximum caps the net room area per floor. Capacity is checked first
  (`required_area_exceeds_capacity`). Missing or unverified inputs give specific reasons
  (`parcel_invalid_or_missing`, `envelope_not_computed` + the geometry reasons,
  `space_schedule_missing/stale`, …).
* Each alternative lists the criteria applied, assumptions (for example the front edge not
  being identified), what was **not evaluated** (orientation/daylight, views, circulation,
  structure, stairs/egress, regulations) and its limitations.
* Permissions as for the schedule; archived projects are read-only.

## Slice 3 — ARCH-003 editable design model

A persisted working model per project (`design_models`, migration 0019): a JSON document in
metres on the parcel's local plane with **stable element IDs that are never reused**
(`E-0001…`), explicit units and schema version. It is created by importing a chosen layout
alternative (`POST …/design/import-layout`; spaces keep their `schedule_space_id`; replacing
an existing design needs an explicit `replace`; a stale layout is refused). It changes only
through explicit operations (`POST …/design/edit`, `expected version`, atomic batch of up to
50): `add`, `move`, `resize`, `rotate`, `delete`, `lock`, `unlock`, `set`.

* Element types: space, wall, door, window, opening. Doors/windows/openings are hosted on a
  wall (offset and width along it) and must stay inside it.
* Spaces stay axis-aligned (rotation in multiples of 90°); walls may have any direction.
* **Locks:** a locked element rejects every edit except `unlock`, with
  `element_locked` and the element ID; a locked door/window/opening pins its wall
  (`hosted_element_locked`). A failed batch writes nothing and records no event.
* Values are rejected, never clamped (positive sizes, finite, ±100 000 m, ≤5000 elements).
* New permission `project.design.edit` (owner, architect); everyone with `project.view` can
  read. Archived projects are read-only.

Not done here, by design: overlap/closure/area checks (ARCH-007), multi-floor copy and vertical connections (ARCH-005), design versions,
compare and comments (ARCH-006), preliminary checks (ARCH-008), plans/exports (ARCH-009).
This is a minimal base model with stable IDs and 2D geometry; formal BIM-001 acceptance
(relationships, format independence, floors, coordinates) is **not** claimed.

## Slice 4 — ARCH-004 units, snap and undo/redo

* **Units:** `POST …/design/edit` accepts `unit` (`m`, `cm`, `mm`; default `m`). Length values
  in operations and new elements are converted **exactly** (Decimal arithmetic) to metres
  before validation; storage stays in metres. Rotation degrees are never scaled.
* **Snap:** optional `snap: {grid, unit?}` (grid 0.001–100 m). Only geometry an operation
  adds, moves or resizes is snapped, to the nearest multiple of the grid, **ties away from
  zero**; untouched elements are unchanged and rotation is not snapped. A snap that would
  shrink an element to zero is refused (`snap_collapses_element`); an unusable grid is
  `invalid_snap`.
* **History:** `design_history` (migration 0020) keeps one full snapshot per change (import
  and every successful edit), up to 200 per project, plus a `head_seq` pointer on the model.
  `POST …/design/undo` and `…/redo` (body `{version}`) move the pointer and store the
  recorded snapshot as a **new version**, so undo then redo returns exactly the prior and
  subsequent model data. A new edit after an undo discards the redo side. Errors:
  `nothing_to_undo`, `nothing_to_redo`, `version_conflict`. `GET …/design/history` lists the
  last 50 entries (operations, unit/snap, actor). Models created before this slice get a
  baseline entry on their next change. Both need `project.design.edit`; archived projects
  are read-only.
* The project-page panel gained a unit selector (display and input), a snap selector,
  undo/redo buttons and a history list.

Still not here: coordinate-level snapping to other elements' edges/endpoints (grid only).

## Not in this slice

Floors and vertical connections (ARCH-005), design versions and comments
(ARCH-006), geometry checks (ARCH-007), preliminary checks (ARCH-008), plans and
schedules export (ARCH-009, DOC-001). The schedule is a list with area ranges, not a
layout, and is not a regulatory or design approval.

## Evidence

Automated tests were added (`tests/test_space_schedule.py`, three browser tests in
`e2e/accounts.spec.mjs`). They are run by CI, not on the author's machine.
