# Documentation maintenance policy

## Authority and scope

- `SMART_ENGINEER_MASTER_SPEC.md` is the product-scope source of truth.
- `docs/ROADMAP.md` translates its phase scope, dependencies, and acceptance
  criteria into delivery planning.
- `docs/PHASE_STATUS.md` records evidenced phase lifecycle status.
- `docs/FEATURE_REGISTRY.md` is the stable-ID index for requirements and their
  phase/dependency/status traceability.
- `docs/FEATURE_ACCEPTANCE.md` contains one observable acceptance criterion per
  registered feature ID.
- `docs/REQUIREMENT_TRACEABILITY.md` maps each individual master-spec
  requirement to feature IDs and phase assignments.
- `docs/OUTPUT_STATUS_LIFECYCLE.md` records all six output states, proposed
  transitions, actor controls, and unresolved authority decisions.
- `docs/OPEN_DECISIONS.md` records unresolved owner/specialist choices; it must
  not turn a proposal or assumption into an approved decision.
- `docs/ARCHITECTURE_OVERVIEW.md` distinguishes confirmed constraints from
  proposals and approved choices.
- `CHANGELOG.md` records notable repository/product-documentation changes and
  must not imply that planned features are implemented.

## Required updates

1. **Before accepting new scope:** identify the affected master-spec section(s),
   feature IDs, phases, dependencies, data/API/security/UI/test/document impact,
   acceptance criteria, and any decision that must be resolved. Record approved
   scope changes in the master specification or a versioned appendix before
   implementation.
2. **Before a phase starts:** read the complete master specification and
   applicable feature entries; verify phase prerequisites and acceptance
   criteria; resolve blocking open decisions or record the explicitly approved
   limited scope. Update status only when work actually starts. Verify every
   scoped feature ID has an acceptance criterion and every individual
   requirement has a traceability row.
3. **During implementation:** keep feature status truthful. Do not mark a
   feature Implemented without tests and acceptance criteria; distinguish
   implemented, tested, and released states. Record blockers/deferred work with
   rationale and return condition.
4. **At phase completion/release:** update the master specification,
   `CHANGELOG.md`, roadmap/checklist, feature statuses, and `PHASE_STATUS.md`;
   record actual test/build/manual-acceptance evidence, known limitations,
   risks, and rollback information. Never mark completion based only on
   documentation, mock data, or developer-machine behavior.
5. **When resolving a decision:** record the decision, rationale, approver,
   date, evidence, affected feature IDs/phases, and any superseded decision.
   Update `OPEN_DECISIONS.md` and the architecture/roadmap/master spec as needed.
6. **When changing architecture:** state which parts are confirmed, proposed,
   selected, or deferred; record impacts on persistence, APIs, security,
   deployment, tests, licensing, and future phases. Do not silently replace a
   proposed technology with a confirmed choice.

## Traceability and review

- Every capability has one stable, unique feature ID; never reuse an ID.
- Keep each registry entry traceable to master-spec sections, phase, actual
  prerequisites, a feature-specific acceptance criterion, and current status.
  Splitting a grouped feature must preserve all original requirements and link
  the original ID to its phase-specific children.
- A deferred/out-of-scope item retains its requirement, rationale, and
  condition for reconsideration. Do not delete, simplify, or silently omit
  future-phase requirements.
- Cross-check changes across the master specification, roadmap, registry,
  phase status, open decisions, architecture overview, and changelog.
- When documents disagree, the master specification governs product scope;
  report the inconsistency and correct derivative documents rather than
  silently weakening a requirement.

## Required development-session behavior

Follow the master specification's Section 20 workflow: read `CLAUDE.md` and the
complete master specification before development (if `CLAUDE.md` is absent,
record that fact rather than inventing instructions); inspect the actual code,
tests, and phase status before work; announce phase, scope, dependencies,
affected files, and acceptance criteria before coding; work only within the
authorized phase; add reference tests for calculations; run relevant tests and
builds; report real results, untested items, assumptions, risks, limitations,
document/status changes, and exact run instructions. The completion report must
include summary, files changed, feature IDs, tests and actual results, untested
items and reasons, risks/limitations, documentation and roadmap status, and
exact run commands. Do not start a later phase until the current phase passes
acceptance unless explicitly directed.
