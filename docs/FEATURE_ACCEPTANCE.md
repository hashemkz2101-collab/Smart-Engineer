# Feature-specific acceptance criteria

These are planned, observable acceptance tests, not evidence that a feature is
implemented. Every feature remains **NOT STARTED**. Tests use controlled
fixtures and expected outputs; where a legal, regulatory, licensing, provider,
format, or numerical-tolerance decision is unresolved, acceptance is blocked
until that decision is recorded. Do not substitute invented real-world data.

| Feature ID | Testable acceptance criteria |
|---|---|
| CORE-001 | For each delivered engineering calculation, the same versioned input produces the same result and warnings in the approved reference fixture; changing the input changes the recorded input/version; disabling the LLM leaves the calculation result reproducible. |
| CORE-002 | Every generated project artifact stores exactly one lifecycle state from the six-state lifecycle in [`OUTPUT_STATUS_LIFECYCLE.md`](OUTPUT_STATUS_LIFECYCLE.md); no artifact can display “Approved” without the authorized human approval event and audit record (DEC-033). |
| CORE-003 | Editing a base-model element creates a new model version; a test enumerating its dependents marks prior calculations/documents stale and prevents their presentation as current. |
| CORE-004 | Automated access tests prove a user can access/export only authorized project data; a deletion/archive test preserves referential integrity and records the actor and outcome under the approved retention policy (DEC-016/026). |
| OPS-001 | A clean Windows environment can install and run the documented starter without manual undocumented steps; setup commands and outcomes are recorded (DEC-031). |
| OPS-002 | A fresh database can be created from the initial migration sequence; upgrading from the prior schema preserves the approved fixture records and migration history. |
| OPS-003 | A forced application error is logged with a correlation identifier and safe user response, with no stack trace/secrets exposed; CI executes the configured test suite and reports failures non-zero. |
| OPS-004 | Each Phase 0 architecture choice has a decision record with status (proposed/approved/deferred), rationale, alternatives, owner, date, and affected feature IDs; unresolved choices remain labeled unresolved. |
| IAM-001 | Registration, login, profile update, invalid credentials, recovery, and session lifecycle tests match the approved authentication policy (DEC-022); secrets never appear in responses/logs. |
| IAM-002 | A role/permission matrix test allows each authorized project action and denies the same action for an unassigned role, another tenant, and an unauthenticated caller at the backend/API boundary. |
| ROLE-001 | For all six named roles, a permission-matrix test records allowed/denied Phase 1 actions; owner intake and architect input/space-review permissions are scoped to assigned projects. |
| ROLE-002 | A structural engineer can read only the assigned, approved architecture version; attempts to read an unapproved version or perform an action outside structural scope return denial and an audit event. |
| ROLE-003 | MEP access tests prove the assigned MEP role can read only permitted architecture/structure versions and cannot modify structural/architectural data through an alternate API path. |
| ROLE-004 | Estimator tests prove access is limited to approved model/specification versions and that quantity/price/estimate actions are denied to unassigned roles. |
| ROLE-005 | Client stage approval and professional review actions are separately recorded; legal professional approval remains disabled unless DEC-007/008/028 establish an authorized role and process. |
| ROLE-006 | Only an authorized system administrator can publish regulation content after the required review; a project user and an administrator without the required authority are denied, and the publication event is audited. |
| ROLE-007 | An authorized system administrator can select a supported structural-engine version for future jobs; prior jobs retain their original engine/version/settings and unauthorized changes are denied and audited. |
| ROLE-008 | Only an authorized system administrator can perform the Phase 10 organization, system-health/security, subscription, and quota actions; ordinary project roles are denied and every action is audited. |
| ROLE-009 | Architect-role tests permit create/edit/compare/export only for assigned projects and supported design versions; the same actions are denied for unassigned projects and unrelated roles. |
| ROLE-010 | Architect-role tests permit reading/reviewing assigned-project rule findings but deny editing/publishing regulation source content; unrelated project access is denied. |
| ROLE-011 | Client-role tests permit reading/comparing/commenting on assigned conceptual options and deny access to unassigned options; the client comment does not set an approval state. |
| ROLE-012 | Only an authorized system administrator can publish a reviewed price-book version; unreviewed content and unauthorized publication attempts are rejected, and the published source/version and actor are retained. |
| ROLE-013 | An authorized system administrator can select a supported MEP-engine version for future jobs; prior jobs retain their original engine/version/settings and unauthorized changes are denied and audited. |
| PRJ-001 | Create/read/update/list/archive tests show only the caller's authorized projects; archived projects leave active listings but remain retrievable only according to the approved archive policy. |
| PRJ-002 | A project member change and a project update each produce an ordered activity record with project, actor, action, and timestamp; unauthorized users cannot read the log. |
| INP-001 | Each intake step can be saved incomplete, resumed, and validated; invalid fields identify the field and reason, while valid partial data remains persisted after a reload. |
| INP-002 | A project fixture round-trips title/code, project type, city/province/address/geolocation, client/owner/responsible engineer/team, purpose, and land-title/ownership/legal notes without asserting legal validity. |
| SITE-001 | Rectangular and irregular parcel fixtures round-trip side lengths/boundaries, survey/coordinates, declared and computed area, north/street orientation, road width/access fronts, slope/elevation/topography; declared/computed discrepancy is explicitly reported. |
| SITE-002 | A site fixture preserves neighbor/shared-wall/barrier, tree/well/channel/existing-utility/easement, and optional soil/geotechnical values as distinct fields; omitted optional soil data is reported as missing, not defaulted. |
| RULE-DATA-001 | For each zoning field (use/zone, coverage, density/allowable floor area, floors/height, setbacks/corrections, parking/access, daylight/patio/courtyard/openings, stairs/elevator/ramp/exit, local constraints), the record stores source/date/document; unverified values display unknown/needs inquiry. |
| REQ-001 | A requirement fixture round-trips unit/floor counts, room counts/types, target area or range, and named spaces: kitchen, reception, living, bathrooms, storage, laundry, special spaces, parking, yard, terrace, balcony, roof garden, and green space. |
| REQ-002 | A fixture independently records accessibility/older or disabled occupants, public/private separation, style, quality/material level, target budget/priorities, mandatory/preferred/unacceptable constraints, future expansion, and change-of-use needs. |
| REQ-003 | Each reference image/example retains its label and explanation and remains linked to the correct project after reload/export. |
| ENV-001 | Environmental inputs retain source and location/date for climate, solar exposure, prevailing wind, rainfall, design temperature/comfort, natural hazards, seismicity, water/electricity/gas/sewer/telecom availability, and energy constraints. |
| FILE-001 | Upload tests enforce approved type/size/count limits, persist type/date/owner/project metadata, reject disallowed files, and serve no file publicly; scanning and quarantine behavior passes the approved file policy (DEC-023). |
| FILE-002 | A re-upload keeps the earlier version; each version shows time and uploader; two versions can be compared; a prior version can be restored without deleting later ones; the version used as takeoff/estimate basis is recorded and a newer version marks dependent calculations as possibly stale. |
| FILE-003 | Each supported type yields the extracted items listed for it with source location and uncertainty; unsupported or failed extraction is reported, and no design or calculation requires extraction to have run. |
| FILE-004 | Discrepancies between files are listed with both sources and routed to engineer review; nothing is auto-corrected; changed files list the calculations they may affect. |
| GEOM-001 | Approved rectangular, polygonal, and irregular parcel fixtures return expected boundary lengths, perimeter, area, and orientation within the approved numerical tolerance; invalid/self-intersecting fixtures return explicit invalid results, not plausible areas (DEC-014/025). |
| GEOM-002 | Equivalent geometry expressed in each supported coordinate/unit system converts to the same canonical coordinates and computed area within the approved tolerance; the chosen coordinate reference system is recorded (DEC-014/025). |
| GEOM-003 | A fixture with an explicitly sourced, versioned setback produces the expected buildable boundary; missing, expired, or unverified setback inputs produce “unknown/needs inquiry” and never a guessed envelope (DEC-013/030). |
| GEOM-004 | The 2D parcel editor saves/reloads the tested boundary unchanged; reference, edge, degenerate, and invalid geometry cases match their expected classifications and values. Supported local coordinates, units, development tolerances, source/validity gating and current evidence are specified in [PHASE_2_PLAN.md](PHASE_2_PLAN.md); no independent survey or legal approval is implied. |
| ARCH-001 | A design brief produces a persisted space schedule whose counts and target-area ranges exactly match the approved input fixture, including unmet requirements flagged rather than silently dropped. |
| ARCH-002 | Given a fixed parcel and brief, the generator returns at least two distinct conceptual alternatives or a specific infeasibility result; each alternative includes its criteria, source inputs, and limitations. |
| BIM-001 | A base-model round-trip preserves stable IDs for project, level, space, wall, door, window, column, beam, and equipment plus explicit units, coordinate basis, 2D geometry, and relationships. |
| ARCH-003 | Move/resize/rotate/add/delete and lock/unlock actions on space, wall, door, window, and opening fixtures persist; locked geometry rejects edits with an explicit reason. |
| ARCH-004 | Snap/grid and dimension operations produce expected coordinates/dimensions in m, cm, and mm; undo followed by redo returns the exact prior/subsequent model version. |
| ARCH-005 | Copying a typical floor creates distinct stable element IDs while preserving configured geometry/relationships; vertical connections point to valid levels. |
| ARCH-006 | Two saved versions can be selected and compared with changed elements identified; a comment is attached to the chosen version and stable element/space ID. |
| ARCH-007 | The checker flags an open boundary, unintended overlap, inaccessible/invalid space, and area-total mismatch in separate fixtures; valid fixtures return no such finding. Rule-based minimum dimensions are not represented as compliant without verified rules. |
| ARCH-008 | Each preliminary privacy, view, access/egress, parking, vehicle-turning, stair, elevator, and ramp check returns a finding or explicit unsupported/data-needed result; none is labeled formal regulatory compliance. |
| ARCH-009 | Exported plan fixtures contain scale, overall/detail dimensions, room names/areas, door/window schedules, optional furniture when requested, and only supported elevations/sections; measurements match source-model values. |
| DOC-001 | PDF and image exports are generated from the same selected design version and carry the Conceptual watermark; DXF/DWG is enabled only after DEC-004 and compatibility fixtures pass. |
| RULE-001 | A regulation fixture stores authority/source, clause, interpretation, applicability, edition, publication/effective dates, scope (national/local/project), and version; unapproved sources cannot become active (DEC-001/013). |
| RULE-002 | For each approved rule fixture, the rule engine produces deterministic input/version/output and one of compliant, non-compliant, data-needed, or human-review-needed; every finding links to its clause. |
| RULE-003 | Only an authorized expert administrator can publish regulation content; deactivation requires reason/date; historical design runs retain the exact previously applied rule version. |
| ARCH-010 | Approved reference cases for daylight/ventilation, privacy, access/egress, parking, stairs, dimensions, and openings return expected findings with clause/version links; unsupported cases return needs-review, not compliant (DEC-019/025). |
| ADMIN-001 | Admin user, role, and project-access actions are individually authorized and audited; unauthorized role escalation and cross-project changes are denied. |
| ADMIN-002 | Regulation publication rejects unreviewed content; a published version retains the authorized approver, source, effective dates, and immutable history. |
| ADMIN-003 | Structural-engine version/settings changes are recorded and linked to subsequent structural jobs; earlier jobs continue to resolve their original settings. |
| ADMIN-004 | Price-book publication rejects unreviewed content; each published version retains the approved source, effective date, reviewer, and immutable history. |
| ADMIN-005 | MEP-engine version/settings changes are recorded and linked to subsequent MEP jobs; earlier jobs continue to resolve their original settings. |
| ADMIN-006 | Security/health dashboard fixtures show the corresponding recorded events and service states; subscription/quota actions are available only under the approved Phase 10 policy and are audited. |
| ADMIN-007 | Organization/team/system-setting actions follow the approved authorization matrix, reject cross-organization access, and record actor, target, change, and time. |
| BIM-002 | Model QA identifies a fixture with missing classification, material, required property, or broken spatial connection and reports element IDs and issue type; complete fixture passes. |
| BIM-003 | IFC import/export fixtures preserve mapped stable IDs and required properties; round-trip loss is reported by element/property; supported schema/version scope requires DEC-004/029. |
| BIM-004 | A drawing, schedule, quantity, or report request records one model-version ID; changing that version causes stale outputs to be marked and prevents them being presented as current. |
| BIM-005 | A 3D model fixture derived from a specified base-model version preserves element IDs and level/element relationships; changing the base version creates a distinct 3D version and marks dependent outputs stale. |
| STR-001 | A structural model fixture records selected system, material properties, assumptions, axes, levels, and supported preliminary load-bearing elements; missing required properties are reported, not defaulted (DEC-002/005). |
| STR-002 | Each supported dead/live/wind/seismic load case and combination round-trips with source/code version; benchmark fixture outputs match the approved reference within approved tolerance (DEC-002/014). |
| STR-003 | For each declared supported solver benchmark, analysis reports stability, displacement, drift, forces, and design ratios and matches independently reviewed expected ranges; unsupported systems are rejected explicitly (DEC-002/005/014). |
| STR-004 | Foundation analysis refuses to produce a design when required geotechnical fields are absent; with an approved soil fixture, inputs, assumptions, and supported preliminary output are traceable (DEC-014). |
| STR-005 | Dedicated fixtures flag floating columns, disconnected beams, unclear load path, defined irregularity, insufficient soil/load data, solver warning, and non-convergence with source element/job IDs. |
| STR-006 | A calculation report includes model/input version, assumptions, sources, solver/version, warnings/errors, checks, result, reviewer identity, and review timestamp; reviewer can approve or request revision only within assigned scope (DEC-007/028). |
| STR-007 | Changing geometry, material, or load creates a new input version and marks dependent analysis/design results stale; default dimensions/reinforcement are never emitted as final design values. |
| MEP-001 | Supported mechanical fixtures separately represent cold/hot water, wastewater/vent, rainwater/drainage, heating/cooling/ventilation, and preliminary equipment/capacity; unsupported systems are explicit (DEC-020). |
| MEP-002 | For supported mechanical fixtures, route/riser geometry, calculated slope/diameter, insulation/specifications, drawing, riser diagram, and equipment schedule trace to the same model/system version (DEC-020). |
| MEP-003 | Supported electrical fixtures report lighting/receptacle loads, panel/circuit, cable/conduit route, grounding/protection, emergency lighting/exit, fire/life-safety, network/telephone/camera/access-control elements, and load schedules; unsupported scope is explicit (DEC-020). |
| MEP-004 | Clash fixtures identify route intersections with beam, column, wall, ceiling, and other MEP elements; shaft/riser and maintenance-access constraints are included in findings. |
| MEP-005 | Every clash record has location, severity, affected IDs, status, assignee/review outcome; resolving it creates a recheck result tied to a new model version. |
| QTY-001 | Model fixture takeoff returns length, area, volume, count, and weight where applicable; every item links to source element and groups correctly by floor, space, system, and operation. |
| QTY-002 | Measurement-rule fixtures apply configured coefficients/opening deductions and produce raw/adjusted/final values; manual override without reason/user audit is rejected. |
| EST-001 | An imported official price-book fixture retains source file/hash, publisher, year, receipt date, code, description, unit, price, chapter, and available decomposition; required missing metadata blocks publication (DEC-006). |
| EST-002 | Mapping tests flag unmapped/obsolete rows, preserve official and market prices as separate sourced/date-stamped records, and retain region/coefficient/contract assumptions across edition comparison (DEC-006/021). |
| EST-003 | An estimate version reproduces totals from the selected quantities/prices/assumptions; low/mid/high cases, sensitivity, uncertainty range, and exclusions are present and compare against prior version. |
| DOC-002 | A dossier built from a fixed project version includes every available required section and labels absent/unapproved discipline outputs as incomplete; its plans/schedules link to ARCH-009/BIM-004 source versions. |
| DOC-003 | Persian RTL and English PDF fixtures pass text direction/font embedding checks and include contents, page numbers, project/version, drawing scale/units, and the watermark corresponding to the artifact state. |
| DOC-004 | An authorized user can download a document before expiry; an unauthorized user and an expired link are denied; export records identify document version and access event. |
| AI-001 | On a Persian and English requirement fixture, output validates against the approved schema, preserves stated facts, asks only about missing essential fields, and flags contradictory inputs without resolving them silently. |
| AI-002 | For each approved supported PDF/image fixture, extracted fields match the annotated expected values, validate against the approved schema, and leave original project/model data unchanged absent authorized confirmation (DEC-023/027). |
| AI-003 | Adversarial prompt/document fixtures cannot cause system-instruction execution; unsupported factual claims lack source and are labeled suggestion/estimate; model mutation requires authorized confirmation; calculation fixtures reproduce with AI disabled. |
| AI-004 | No provider integration is accepted until DEC-032 chooses its phase, provider boundary, data handling, and cost/usage contract; once approved, contract tests prove provider substitution preserves request/result/audit schema. |
| AI-005 | A fixed brief produces explainable conceptual design suggestions linked to criteria and limitations; generated suggestions do not alter the base model until an authorized user confirms the specific change. |
| AI-006 | A regulation-finding fixture explanation cites the exact rule version/clause; if no verified source exists, output explicitly reports that and does not fabricate a requirement. |
| AI-007 | Supported drawing/BIM fixture extraction matches the annotated element/property fixture and schema; unsupported format/version is rejected with an explicit reason (DEC-004/023/027). |
| AI-008 | Given a takeoff and price catalog fixture, AI suggestions are distinguishable from accepted mappings; the quantity, price, and mapping remain unchanged until authorized confirmation. |
| AI-009 | Generated text reports use only permission-visible, versioned project facts; factual sentences have source references or explicit suggestion/estimate labels; unauthorized project facts are absent. |
| AI-010 | For an approved plan/usage fixture, every AI request has attributable provider/model, project/tenant, usage, cost, and quota outcome; totals reconcile to the fixture ledger (DEC-010/011/027/032). |
| FLOW-001 | Invitation tests prove an authorized project owner can invite/revoke a member with a bounded role; invitee access is denied before acceptance and scoped after acceptance; all changes are audited. |
| FLOW-002 | A workflow fixture advances through the specified stages only when prerequisites and assigned approver actions exist; an open critical finding blocks final issuance; decisions retain actor/time/reason. |
| FLOW-003 | Each in-app notification identifies a triggering project event and authorized recipient; duplicate delivery behavior and read state match the approved workflow, and unauthorized recipients cannot retrieve it. |
| FLOW-004 | An architectural comment remains attached to its selected design version, space, or element after a model revision; history retains the original target/version, author, and time. |
| FLOW-005 | A task record requires project, responsible user, and due date; unauthorized reassignment is denied; task status changes and approval/rejection explanations appear in project history. |
| FLOW-006 | A comment on an issued drawing/document identifies its immutable document version, target, author, and time; revisions do not retarget prior comments and access follows document permissions. |
| FLOW-007 | Email/SMS delivery is attempted only after DEC-010 provider/contract approval and with configured credentials; a provider fixture records success/failure against the event and recipient without exposing credentials. |
| BILL-001 | Account verification, recovery, session inspection/revocation, and organization/team membership pass the approved identity and legal policy tests (DEC-017/022/026). |
| BILL-002 | A plan fixture enforces project, file-volume, export, and AI-use quotas at the server boundary; usage reports and trial/discount entitlements reconcile to recorded usage (DEC-011/015). |
| BILL-003 | Payment sandbox contract tests prove invoice, renewal, cancellation, and payment-history state transitions with the selected provider; secrets are absent from frontend bundles/logs (DEC-010/011). |
| SEC-001 | Security tests deny cross-tenant access and exercise validation, SQL injection, XSS, CSRF, SSRF, rate-limit, brute-force, TLS, and password-hash controls against documented cases. |
| SEC-002 | File-limit, type-validation, malware test fixture, quarantine, private-storage, and authorized-download tests pass the approved file/security policy (DEC-023). |
| SEC-003 | Sensitive actions emit immutable audit entries; retention/deletion and required encryption tests match the approved policy; simulated internal errors expose no stack trace or secret (DEC-016/026). |
| SEC-004 | A scheduled backup restores a representative test dataset within approved recovery targets; monitoring detects injected service/job failure; documented incident and penetration-test findings have disposition (DEC-015/024). |
| SEC-005 | Repository and frontend-bundle scans find no configured secret fixture; runtime access/rotation follows the approved secret policy, and a credential is not exposed in logs or client responses. |
| ARCH-PLAT-001 | Contract tests show versioned API routes; domain tests run without UI/database/export adapters; configured domain modules have no cross-boundary import violations. |
| ARCH-PLAT-002 | An async job fixture records status, versioned input, output/error, and start/end time; migration rollback/forward and feature-flag off/on tests give the documented behavior. |
| DATA-001 | The conceptual schema review checklist accounts for every entity in master Section 16; every dependent record has project scope and organization scope where required, with referential-integrity/archive tests. |
| TEST-001 | CI produces passing results for unit, integration, API contract, authorization/isolation, invalid/boundary/incomplete input, migrations, performance, reproducibility, regression, mobile/desktop, RTL/LTR, and Persian PDF font suites when applicable. |
| RELEASE-001 | A release candidate passes clean-install, recorded tests, production build, manual acceptance, critical/security defect gate, docs/version update, and rollback rehearsal; missing evidence blocks release. |
| GOV-001 | Every feature has a unique ID, current lifecycle status, acceptance evidence, and trace to spec; deferred items include rationale/re-entry condition; scope-change review records DB/API/security/UI/test/docs impact. |
## Status rule

Acceptance criteria describe future tests only. Passing a criterion is not
asserted here; status remains NOT STARTED until implementation and evidence are
reviewed under the master specification's lifecycle and release gates.
