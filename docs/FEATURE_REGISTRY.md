# Feature registry

This registry assigns stable IDs to the complete planned scope represented by
the master specification. Feature names are concise labels, not permission to
remove details: the master specification remains authoritative. Grouped entries
retain their full feature detail in the roadmap and cited specification
sections.

**Initial status for every row: NOT STARTED.** These are application features;
writing this registry is not implementation. Dependencies refer to IDs in this
table or to a named phase acceptance gate. `—` means no product-feature
prerequisite beyond phase entry. Feature-specific, observable acceptance
criteria for every ID are maintained in
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md). Requirement-level traceability
is maintained in [`REQUIREMENT_TRACEABILITY.md`](REQUIREMENT_TRACEABILITY.md).

| Feature ID | Phase | Feature group | Dependencies | Spec sections | Status |
|---|---:|---|---|---|---|
| CORE-001 | 0 / all | Deterministic, traceable engineering computations; AI is not a solver | — | 1, 6–9, 11, 18 | NOT STARTED |
| CORE-002 | 0 / all | Output lifecycle/status, qualified review boundary, no unsupported approval claims | — | 1, 6–7, 10, 12, 20 | NOT STARTED |
| CORE-003 | 0 / all | Versioned models, source versions, dependency invalidation and reproducible outputs | — | 1, 5–10, 16 | NOT STARTED |
| CORE-004 | 0 / all | User-owned project data, scoped access, export, deletion/archival, auditability | — | 1–2, 14, 16 | NOT STARTED |
| OPS-001 | 0 | Starter assessment, reproducible environments, structure/configuration and run docs | — | 15, 17.0, 18 | NOT STARTED |
| OPS-002 | 0 | Domain/data foundation and migration strategy | OPS-001 | 15–16, 17.0 | NOT STARTED |
| OPS-003 | 0 | Logging, explicit error handling, CI and test baseline | OPS-001 | 14–15, 17.0, 18 | NOT STARTED |
| OPS-004 | 0 | Record architecture decisions; keep proposals and approved decisions distinct | OPS-001 | 15, 17.0, 21 | NOT STARTED |
| IAM-001 | 1 | Registration, login, profile and initial roles | OPS-002, OPS-003 | 2, 13, 14, 17.1 | NOT STARTED |
| IAM-002 | 1 | Backend-enforced role/permission checks and project/tenant scoping | IAM-001, PRJ-001 | 2, 14, 16 | NOT STARTED |
| ROLE-001 | 1 | Define the six role identities, permission catalog, project-scope policy, owner/client intake permissions, and architect project-input/space-review permissions | IAM-001, IAM-002 | 2 | NOT STARTED |
| ROLE-002 | 6 | Structural-engineer access only to approved architecture versions; structural model/analysis/review actions restricted to assigned role and project | ROLE-001, BIM-001, STR-001 | 2, 6 | NOT STARTED |
| ROLE-003 | 7 | Mechanical/electrical engineer access limited to permitted architecture/structure versions and supported MEP coordination/review actions | ROLE-001, BIM-001, MEP-001 | 2, 7 | NOT STARTED |
| ROLE-004 | 8 | Estimator access to approved elements/specifications and permission to set measurement bases, review quantities/prices, and prepare estimates | ROLE-001, QTY-001, EST-001 | 2, 9 | NOT STARTED |
| ROLE-005 | 9 | Client design-option comparisons/comments/stage decisions, professional review/sign-off actions where legally supported, and role-scoped document access | ROLE-001, FLOW-002, DOC-002 | 2, 10, 12 | NOT STARTED |
| ROLE-006 | 4 | System-administrator permission to publish approved regulation resources through the regulation review workflow | ROLE-001, ADMIN-002 | 2, 8 | NOT STARTED |
| ROLE-007 | 6 | System-administrator permission to manage supported structural-engine versions/settings without silently changing prior job versions | ROLE-001, ADMIN-003, STR-001 | 2, 6 | NOT STARTED |
| ROLE-008 | 10 | System-administrator permissions for organizations, system health/security views, subscriptions, quotas, and commercial controls | ROLE-001, ADMIN-006, ADMIN-007 | 2, 13–14 | NOT STARTED |
| ROLE-009 | 3 | Architect permissions to create/edit/compare assigned-project designs and export supported drawings/models | ROLE-001, ARCH-003, ARCH-009 | 2, 4 | NOT STARTED |
| ROLE-010 | 4 | Architect permission to access and review regulation findings for assigned projects, without publishing or altering approved regulation content | ROLE-001, RULE-002 | 2, 8 | NOT STARTED |
| ROLE-011 | 3 | Owner/client permission to view, compare, and comment on assigned-project conceptual options; approval remains a separate Phase 9 action | ROLE-001, ARCH-006, FLOW-004 | 2, 4.2, 12 | NOT STARTED |
| ROLE-012 | 8 | System-administrator permission to publish approved price-book versions through the price-data review workflow | ROLE-001, ADMIN-004 | 2, 9 | NOT STARTED |
| ROLE-013 | 7 | System-administrator permission to manage supported MEP-engine versions/settings without silently changing prior job versions | ROLE-001, ADMIN-005, MEP-001 | 2, 7 | NOT STARTED |
| PRJ-001 | 1 | Create, edit, list, archive projects; project settings and dashboard | IAM-001 | 2, 3.1, 12, 16, 17.1 | NOT STARTED |
| PRJ-002 | 1 | Project activity history and team/member association | PRJ-001, IAM-002 | 2, 12, 16–17 | NOT STARTED |
| INP-001 | 1 | Staged, validated, resumable/draft project intake | PRJ-001 | 3, 17.1 | NOT STARTED |
| INP-002 | 1 | Project identity, type, city/address/geolocation, purpose, people and non-automated legal-status notes | INP-001 | 3.1 | NOT STARTED |
| SITE-001 | 1 | Parcel boundaries/shape/survey, declared and computed area, orientation, frontage/access, terrain | INP-001 | 3.2 | NOT STARTED |
| SITE-002 | 1 | Neighbors, shared walls, obstacles, trees, wells, channels, existing utilities, easements, soil/geotechnical data | SITE-001 | 3.2 | NOT STARTED |
| RULE-DATA-001 | 1 | Record zoning/building-control inputs and source references; unknown/unverified data remains unknown | INP-001, SITE-001 | 3.3 | NOT STARTED |
| REQ-001 | 1 | Client unit/floor/room/area program and space needs | INP-001 | 3.4 | NOT STARTED |
| REQ-002 | 1 | Accessibility, privacy, style/quality/materials, budget/priorities, mandatory/preferred/unacceptable needs, expansion/change-of-use | REQ-001 | 3.4 | NOT STARTED |
| REQ-003 | 1 | Reference images/examples with labels and explanations | REQ-001 | 3.4 | NOT STARTED |
| ENV-001 | 1 | Sourced climate, sun, wind, rainfall, comfort/design temperature, natural hazards/seismicity, utilities and energy constraints | SITE-001 | 3.5 | NOT STARTED |
| FILE-001 | 1 | Secure attachment upload and metadata: type, date, ownership; controlled storage/access | PRJ-001, IAM-002 | 3.2, 14 | NOT STARTED |
| FILE-002 | 1 | File versions: keep prior versions, record upload time and uploader, compare versions, restore a prior version, mark the version used as takeoff/estimate basis (owner requirement, DEC-023) | FILE-001, CORE-003 | 3.2, 16 | NOT STARTED |
| FILE-003 | 3 | Per-type content extraction from uploaded PDF, DXF/DWG, IFC, Excel and Word files (text, tables, layers, dimensions, storeys, spaces, formulas); optional, never a prerequisite | FILE-001, AI-003 | 4, 5, 11 | NOT STARTED |
| FILE-004 | 5 | Cross-file reconciliation (PDF vs DWG, IFC vs drawings, Excel vs drawing quantities, Word vs specifications) with discrepancies flagged for engineer review and impact of a changed file on earlier calculations | FILE-002, FILE-003, BIM-003 | 5, 11 | NOT STARTED |
| GEOM-001 | 2 | Rectangular, polygonal, irregular parcel boundary and geometry calculations | SITE-001 | 3.2, 4, 17.2 | NOT STARTED |
| GEOM-002 | 2 | Explicit coordinate systems, units/conversions, orientation and declared/computed area discrepancy | GEOM-001 | 3.2, 5, 17.2 | NOT STARTED |
| GEOM-003 | 2 | Apply recorded setbacks and derive buildable envelope | GEOM-001, RULE-DATA-001 | 3.3, 4.1, 8 | NOT STARTED |
| GEOM-004 | 2 | Numerical reference, invalid/boundary geometry tests and editable 2D site canvas | GEOM-001, GEOM-002 | 17.2, 18 | NOT STARTED |
| ARCH-001 | 3 | Physical program and space/room list | REQ-001, GEOM-003 | 4.1, 17.3 | NOT STARTED |
| ARCH-002 | 3 | Explainable multiple conceptual layouts; site, access, privacy, orientation, sunlight/climate/neighbor considerations and limitations | ARCH-001, ENV-001 | 4.1, 11 | NOT STARTED |
| BIM-001 | 3 | UI/format-independent base building model, stable project/floor/space/element IDs, explicit units/coordinates, 2D geometry and relationships | GEOM-002 | 5, 16 | NOT STARTED |
| ARCH-003 | 3 | Edit spaces/walls/doors/windows/openings; move/resize/rotate/add/delete and lock elements/dimensions | ARCH-002, BIM-001 | 4.2 | NOT STARTED |
| ARCH-004 | 3 | Snap/grid, dimensioning and m/cm/mm display; undo/redo and change history | ARCH-003 | 4.2 | NOT STARTED |
| ARCH-005 | 3 | Multiple floors, vertical connections, typical-floor copy/repetition | ARCH-003, BIM-001 | 4.2 | NOT STARTED |
| ARCH-006 | 3 | Design versioning, compare two or more versions, comments on space/element | ARCH-003 | 4.2, 12, 16 | NOT STARTED |
| ARCH-007 | 3 | Geometry closure/overlap, area totals, invalid/no-access spaces, basic dimensions and area checks | ARCH-003, GEOM-003 | 4.3 | NOT STARTED |
| ARCH-008 | 3 | Preliminary privacy/views, access/egress, parking/vehicle movement, stair/elevator/ramp checks; do not imply formal regulatory compliance | ARCH-003, GEOM-003 | 4.1, 4.3 | NOT STARTED |
| ARCH-009 | 3 | Scaled plans, dimensions, room names/areas, door/window schedules, optional furniture, supported elevations/sections | ARCH-003, BIM-001 | 4.4 | NOT STARTED |
| DOC-001 | 3 | Conceptual PDF/image export with explicit conceptual status; DXF/DWG only after compatibility validation | ARCH-009 | 4.4, 10 | NOT STARTED |
| RULE-001 | 4 | Official, sourced, versioned national/local/project regulation library and applicability | RULE-DATA-001 | 3.3, 8, 17.4 | NOT STARTED |
| RULE-002 | 4 | Deterministic testable rule engine, clause-linked findings, compliant/noncompliant/data-needed/human-review states | RULE-001, BIM-001 | 4.3, 8 | NOT STARTED |
| RULE-003 | 4 | Expert-admin approval, obsolete-version reason/date, version-specific applied-rule report | RULE-001, IAM-002 | 8 | NOT STARTED |
| ARCH-010 | 4 | Regulation-backed daylight/ventilation, privacy, access/egress, parking, stairs, dimensions and opening checks with rule/version findings | ARCH-007, RULE-002 | 4.3, 8 | NOT STARTED |
| ADMIN-001 | 1 | Admin management of users, roles, and project access | IAM-002, PRJ-001 | 2 | NOT STARTED |
| ADMIN-002 | 4 | Admin review/approval/publishing workflow for regulation resources | RULE-003 | 2, 8 | NOT STARTED |
| ADMIN-003 | 6 | Management/versioning of structural calculation engine and settings | STR-001 | 2, 6 | NOT STARTED |
| ADMIN-004 | 8 | Admin review/approval/publishing workflow for official price-book resources | EST-001 | 2, 9 | NOT STARTED |
| ADMIN-005 | 7 | Management/versioning of supported MEP engine and settings | MEP-001 | 2, 7 | NOT STARTED |
| ADMIN-006 | 10 | Security-event/service-health views and subscription/quota administration when commercial features are enabled | SEC-004, BILL-002 | 2, 13–14 | NOT STARTED |
| ADMIN-007 | 10 | Organization/team and system-setting administration | ADMIN-001, BILL-001 | 2, 13, 16 | NOT STARTED |
| BIM-002 | 5 | Model classification, materials/assemblies/properties, spatial/element relationships and model QA | BIM-001 | 5, 16 | NOT STARTED |
| BIM-003 | 5 | Controlled IFC import/export; preserve/map IDs and properties; report incomplete/inconsistent/unclassified elements | BIM-001, BIM-002 | 5 | NOT STARTED |
| BIM-004 | 5 | Derive drawings, takeoff and reports from one specified model version | BIM-001, BIM-002 | 1, 5, 9–10 | NOT STARTED |
| BIM-005 | 5 | Derive versioned 3D building geometry, levels/elevations, and model relationships from the shared Phase 3 base model | BIM-001 | 5, 16 | NOT STARTED |
| STR-001 | 6 | Structural system, materials/mechanical properties, assumptions, grids, floor levels and preliminary element placement | BIM-001, BIM-002 | 6, 17.6 | NOT STARTED |
| STR-002 | 6 | Gravity/lateral load transfer; dead/live/wind/seismic cases and code-based combinations | STR-001, RULE-001 | 6 | NOT STARTED |
| STR-003 | 6 | Validated-scope analysis/stability, displacement, drift, force and design ratios; concrete/steel design | STR-002 | 6 | NOT STARTED |
| STR-004 | 6 | Preliminary foundations only with sufficient geotechnical data | STR-003, SITE-002 | 6 | NOT STARTED |
| STR-005 | 6 | Architecture coordination; floating/disconnected elements, unclear load path, irregularity, insufficient data, solver warnings/nonconvergence | STR-001, STR-002 | 6 | NOT STARTED |
| STR-006 | 6 | Traceable assumptions/sources/solver version/errors/calculation report; engineer review/approval/revision | STR-003, STR-005 | 6, 10, 12 | NOT STARTED |
| STR-007 | 6 | Stale structural results on geometry/material/load changes; prohibit final use of default dimensions/reinforcement | CORE-003, STR-001 | 1, 6 | NOT STARTED |
| MEP-001 | 7 | Mechanical water, wastewater/vent, rain/drainage, HVAC systems and preliminary equipment/capacity | BIM-001, BIM-002 | 7 | NOT STARTED |
| MEP-002 | 7 | Mechanical routes, risers, supported slopes/diameters, insulation/specifications, drawings, diagrams/schedules | MEP-001 | 7 | NOT STARTED |
| MEP-003 | 7 | Electrical/low-voltage loads, panels/circuits, routes, grounding/protection, emergency/exit, fire/life safety, network/telephony/camera/access control and schedules | BIM-001, BIM-002 | 7 | NOT STARTED |
| MEP-004 | 7 | Cross-discipline clashes with structure/architecture/services; shafts, risers and maintenance access | MEP-002, MEP-003, STR-001 | 7 | NOT STARTED |
| MEP-005 | 7 | Clash location/severity, resolution workflow and re-review | MEP-004 | 7, 10, 12 | NOT STARTED |
| QTY-001 | 8 | Model-derived length/area/volume/count/weight; group by floor/space/system/operation; source-element traceability | BIM-004 | 9 | NOT STARTED |
| QTY-002 | 8 | Measurement rules/coefficient configuration, opening deductions, raw/adjusted/final quantities, reasoned audited manual corrections | QTY-001 | 9 | NOT STARTED |
| EST-001 | 8 | Versioned official annual/discipline price books, provenance/hash/metadata, codes/descriptions/units/prices/chapters and available decompositions | — | 9 | NOT STARTED |
| EST-002 | 8 | Map takeoff items; separate dated/sourced market prices; region/contract/coefficient assumptions; editions and unmapped/obsolete warnings | QTY-002, EST-001 | 9 | NOT STARTED |
| EST-003 | 8 | Official/market estimates; supported cost breakdown, versions, comparisons, low/mid/high scenarios, sensitivity, uncertainty and exclusions | EST-002 | 9 | NOT STARTED |
| DOC-002 | 9 | Complete project dossier with inputs, assumptions, regulation versions, architectural drawings/schedules, discipline outputs, clashes, takeoff/estimate, history, approvals, warnings | PRJ-002, ARCH-009, BIM-004, RULE-002, STR-006, MEP-005, EST-003 | 10 | NOT STARTED |
| DOC-003 | 9 | Persian RTL/English PDF, permitted embedded fonts, contents/pages/project/version, scale/units, status watermark, separate exports and complete ZIP | DOC-002 | 10 | NOT STARTED |
| DOC-004 | 9 | Access-controlled expiring downloads and secure document versions/exports | FILE-001, IAM-002, DOC-003 | 10, 14, 16 | NOT STARTED |
| AI-001 | 1 | Persian/English project-aware intake dialogue; structure client text as requirements; ask only for essential missing data; summarize contradictions | INP-001, AI-004 | 11 | NOT STARTED |
| AI-002 | 1 | Extract information from supported PDFs/images attached to the project; file formats and provider behavior are decision-gated | FILE-001, AI-003, AI-004 | 11 | NOT STARTED |
| AI-003 | 0 / all | No fabricated rules/prices/analysis/approvals; source or suggestion/estimate label; schema validation; untrusted-file instruction isolation; authorized confirmation for model changes; reproducible calculations independent of AI text | CORE-001, CORE-002 | 1, 11 | NOT STARTED |
| AI-004 | UNRESOLVED (DEC-032) | Provider-independent AI Gateway boundary, provider substitution, and usage/cost telemetry; phase of application implementation requires a decision | OPS-004 | 13, 15 | NOT STARTED |
| AI-005 | 3 | Generate/explain conceptual design suggestions only as labeled proposals with criteria and limitations; never mutate the base model without authorized confirmation | AI-001, AI-004, ARCH-001, AI-003 | 4, 11 | NOT STARTED |
| AI-006 | 4 | Explain regulation/computation findings with links to the exact rule/source or label the answer as a suggestion when no authoritative source exists | RULE-002, AI-003, AI-004 | 8, 11 | NOT STARTED |
| AI-007 | 5 | Extract/classify supported drawing/BIM elements; validate extracted data against schema and report source/uncertainty; supported formats require DEC-004/023/027 | BIM-003, AI-003, AI-004 | 5, 11 | NOT STARTED |
| AI-008 | 8 | Suggest element classification and takeoff-to-price-item mappings without changing measured quantities or approved mappings absent authorized confirmation | QTY-001, EST-001, AI-003, AI-004 | 9, 11 | NOT STARTED |
| AI-009 | 9 | Generate project explanations/reports and role-specific assistance from versioned, permission-filtered project facts; factual claims carry sources or proposal labels | DOC-002, AI-003, AI-004 | 10–11 | NOT STARTED |
| AI-010 | 10 | Attribute AI usage/cost to configured plans/quotas and produce auditable consumption records; depends on approved gateway/provider and commercial policy | BILL-002, AI-004 | 13, 15 | NOT STARTED |
| FLOW-001 | 1 | Invite project members and grant/revoke project-scoped roles with recorded actor, target, permission scope, and timestamp | IAM-002, PRJ-001 | 2, 12 | NOT STARTED |
| FLOW-004 | 3 | Comment on a specific architectural design version, space, or element; retain author, target, time, and version context | ARCH-006, FLOW-001 | 4.2, 12 | NOT STARTED |
| FLOW-005 | 9 | Assign tasks with responsible person and due date; record stage status and approver; preserve timestamped approval/rejection explanation | FLOW-001, ROLE-005 | 12 | NOT STARTED |
| FLOW-002 | 9 | Staged project workflow, critical-check issuance gate, approval trail, revision management and project activity report | FLOW-001, DOC-002 | 12 | NOT STARTED |
| FLOW-003 | 9 | In-app notifications linked to project events and recipients | FLOW-001 | 12 | NOT STARTED |
| FLOW-006 | 9 | Comments on issued documents/drawings retain document-version and author context | FLOW-001, DOC-002 | 10, 12 | NOT STARTED |
| FLOW-007 | 10 | Optional email/SMS notification delivery through a configured, approved provider | FLOW-003 | 12–13 | NOT STARTED |
| BILL-001 | 10 | Secure account confirmation/recovery/session lifecycle; organization/team support | IAM-001, IAM-002 | 2, 13, 16 | NOT STARTED |
| BILL-002 | 10 | Free/pro/organization/credit plans, project/file/export/AI quotas, trials/discounts as needed, subscriptions/usage reporting | BILL-001 | 13, 16 | NOT STARTED |
| BILL-003 | 10 | Selected/contract-reviewed Iranian payment, invoices, renewals, cancellations, payment history; no secrets in frontend/public repository | BILL-002 | 13–14 | NOT STARTED |
| SEC-001 | 0 / all | Security architecture and controls: TLS in production, secure password hashing, backend authorization/tenant isolation, validation, SQLi/XSS/CSRF/SSRF defenses, rate limiting/brute-force protections | OPS-001 | 2, 14 | NOT STARTED |
| SEC-002 | 1 | File type/size/count limits, scanning, non-public storage, authorized downloads | FILE-001 | 13–14 | NOT STARTED |
| SEC-003 | 0 / all | Sensitive-operation audit logs, retention/deletion, sensitive-data encryption as required, safe errors/no stack traces | OPS-003, CORE-004 | 14, 16 | NOT STARTED |
| SEC-004 | 10 | Monitoring, scheduled backups, recovery tests, incident response, penetration/security review before public release | OPS-003 | 14, 17.10, 18 | NOT STARTED |
| SEC-005 | 0 / all | Protect secrets and API/payment keys; never expose them in frontend code or public repositories | OPS-001 | 13–14 | NOT STARTED |
| ARCH-PLAT-001 | 0 | Versioned APIs, clear domain module boundaries, business logic outside UI, domain independent of database/export formats | OPS-001, OPS-004 | 15 | NOT STARTED |
| ARCH-PLAT-002 | 0 / all | Async traceable heavy jobs with versioned inputs/output/error/timing; feature flags; migrations | OPS-002, OPS-003 | 15–16 | NOT STARTED |
| DATA-001 | 0 / all | Conceptual identity/org/project/site/requirements/model/regulation/engineering/MEP/quantity/estimate/document/workflow/billing/job/audit/settings entities and scoped relationship integrity | OPS-002 | 16 | NOT STARTED |
| TEST-001 | 0 / all | Unit, integration, API contract, authorization/isolation, invalid/boundary/incomplete input, migration, performance, reproducibility, regression, UI, mobile/desktop, RTL/LTR/PDF tests | OPS-003 | 18 | NOT STARTED |
| RELEASE-001 | 0 / all | Clean-install, recorded tests, production build, manual acceptance, no critical/security defects, updated docs/version, rollback gate | OPS-003 | 18 | NOT STARTED |
| GOV-001 | 0 / all | Unique IDs/statuses; tested acceptance before completion; scope-impact review; deferred rationale/re-entry; no duplicate concepts | OPS-004 | 19–20 | NOT STARTED |

## Phase-specific splits and dependency rationale

All 88 IDs present in the original registry were retained. New IDs below split
multi-phase responsibilities while retaining their scope and traceability:

- The original `ROLE-001` role bundle is retained as the Phase 1 role catalog
  and base permission feature. `ROLE-002`–`ROLE-006` move structural, MEP,
  estimating, approval, and regulation-administration actions to the phases
  that introduce those capabilities. `ROLE-007`/`ROLE-013` separate structural
  and MEP engine administration; `ROLE-008` carries Phase 10 commercial/system
  administration; `ROLE-012` adds price-book publishing permission;
  `ROLE-009` carries architect design-edit/export permissions into Phase 3;
  `ROLE-010` adds architect regulation-review permissions in Phase 4; and
  `ROLE-011` adds client option-view/comment permissions in Phase 3.
  Requirement mapping is in Section 2 of
  [`REQUIREMENT_TRACEABILITY.md`](REQUIREMENT_TRACEABILITY.md).
- The original `AI-001` intake assistant is Phase 1; conceptual design, rule
  explanation, model extraction, takeoff mapping, and dossier text are separated
  into `AI-005`–`AI-009`. `AI-002` retains Phase 1 file extraction, with format
  and provider gates. `AI-004` is unresolved pending DEC-032; Phase 10 cost
  accounting is isolated as `AI-010`.
- The original `FLOW-001` is Phase 1 invitations/membership only. Design
  comments are `FLOW-004` (Phase 3) and `FLOW-006` (Phase 9 issued documents);
  task assignment is `FLOW-005` (Phase 9), stage approvals remain `FLOW-002`,
  in-app notifications are `FLOW-003` (Phase 9), and optional email/SMS
  delivery is `FLOW-007` (Phase 10).

Dependency decisions requested for review:

- **AI-004:** its former `BILL-002` dependency is removed. Provider abstraction
  and gateway telemetry are architectural concerns, not inherently dependent
  on subscription billing; their rollout phase is unresolved by DEC-032.
  `AI-010` retains dependencies on both `AI-004` and `BILL-002`, because
  commercial usage attribution requires a gateway usage event and an approved
  plan/quota model.
- **ROLE-001:** remains dependent on `IAM-001` and `IAM-002`; role definitions
  and backend enforcement need an identity/project permission foundation.
  Discipline actions are moved to role-specific features dependent on their
  corresponding discipline/model records, avoiding a Phase 1 dependency on
  future structural, MEP, or estimating modules.
- **FLOW-001:** depends on `IAM-002` and `PRJ-001` because invitations require
  an existing project and server-enforced scoped permissions. Tasks/comments
  are separate because they attach to later design/workflow objects.
- **DOC-002:** `ARCH-009` and `BIM-004` are added prerequisites because the
  dossier includes architectural plans/schedules and must identify the
  model-version source. Discipline reports remain included only when available
  and approved, as required by the master specification.
- **GEOM-001:** `ENV-001` is removed as a dependency. Parcel boundary, area,
  perimeter, and orientation calculations require parcel geometry (`SITE-001`)
  but not climate/hazard inputs. Environmental data remains a dependency of
  climate-aware architectural suggestions (`ARCH-002`).

## Registry rules

- IDs are stable; do not recycle an ID. Add new entries rather than renumbering.
- A feature stays NOT STARTED until implementation evidence exists. Use the
  master specification's Planned, In Progress, Implemented, Tested, Released,
  Blocked, and Deferred lifecycle when work begins; record evidence and blockers.
- Dependencies are actual prerequisites, not merely nearby rows. Phase gates
  remain mandatory even when not repeated in each row.
- A grouped feature may be split into more granular IDs before implementation;
  do not drop requirements during a split. Preserve links to the master-spec
  section and update this registry, acceptance criteria, traceability, roadmap,
  open decisions, and status together.
