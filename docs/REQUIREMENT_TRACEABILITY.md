# Requirement-to-feature traceability

This matrix maps each discrete requirement in
[`../SMART_ENGINEER_MASTER_SPEC.md`](../SMART_ENGINEER_MASTER_SPEC.md) to
registry IDs and phase assignments. The matrix is intentionally granular:
individual inputs, permissions, checks, controls, and outputs are not replaced
by category labels. Feature status is NOT STARTED; mapping is not implementation.
Observable acceptance tests are in
[`FEATURE_ACCEPTANCE.md`](FEATURE_ACCEPTANCE.md).

| Master ref | Individual requirement | Feature ID(s) | Phase |
|---|---|---|---:|
| 1.a | Web system manages building-project design and estimating lifecycle in Iran | PRJ-001, ARCH-001, EST-003 | 1, 3, 8 |
| 1.b | Receive site, client requirements, site constraints, and valid regulations | SITE-001/002, REQ-001/002/003, RULE-DATA-001 | 1 |
| 1.c | Generate editable architectural alternatives | ARCH-002/003 | 3 |
| 1.d | After required approvals, coordinate structure and MEP, takeoff, estimate, and technical documents | FLOW-002, STR-006, MEP-005, QTY-001/002, EST-003, DOC-002 | 6–9 |
| 1.e | Maintain one coherent, versioned digital project record, not only a plan image | CORE-003, DATA-001, DOC-002 | 0 / all |
| 1.1 | Sensitive engineering calculations use deterministic, testable, traceable engines; LLM is not the solver | CORE-001, AI-003 | 0 / all |
| 1.2 | Each output identifies conceptual, initial, under-review, reviewed, approved, or rejected state | CORE-002 | 0 / all |
| 1.3 | No drawing is represented as executable, engineering-approved, or construction-authorized without regulation checks and qualified review | CORE-002, ROLE-005, FLOW-002 | 0 / all, 9 |
| 1.4 | Regulations, standards, and price books record version, validity dates, publisher/source, and scope | RULE-001, EST-001/002 | 4, 8 |
| 1.5 | Base-model changes create a version and stale/invalidate dependent calculations/documents | CORE-003, BIM-004, STR-007 | 0 / all, 5–6 |
| 1.6 | Future capabilities are represented in architecture/data early and activated by phase acceptance | ARCH-PLAT-002, GOV-001 | 0 / all |
| 1.7 | User data access, export, deletion, and history are controlled | CORE-004, SEC-003 | 0 / all |
| 2.1.a | Owner/client registers, logs in, manages profile | IAM-001 | 1 |
| 2.1.b | Owner/client creates project and registers site/building needs | PRJ-001, INP-001/002, SITE-001, REQ-001 | 1 |
| 2.1.c | Owner/client sees follow-up questions and completes missing information | AI-001, INP-001 | 1 |
| 2.1.d | Owner/client views, compares, and comments on architecture options | ROLE-011, ARCH-006, FLOW-004 | 3 |
| 2.1.e | Owner/client approves or rejects options at stages | ROLE-005, FLOW-002 | 9 |
| 2.1.f | Owner/client sees understandable reports, estimates, and cost changes | DOC-002/003, EST-003, ROLE-005 | 8–9 |
| 2.1.g | Owner/client downloads permitted documents and views project history | DOC-004, PRJ-002 | 1, 9 |
| 2.1.h | Owner/client invites an engineer/consultant with limited access | FLOW-001, IAM-002 | 1 |
| 2.2.a | Architect manages assigned projects | ROLE-001, IAM-002 | 1 |
| 2.2.b | Architect reviews inputs and revises spatial requirements | ROLE-001, REQ-001/002 | 1 |
| 2.2.c | Architect creates, edits, and compares designs | ROLE-009, ARCH-002/003/006 | 3 |
| 2.2.d | Architect manages spaces, dimensions, openings, circulation, and relationships | ROLE-009, ARCH-003/004/005 | 3 |
| 2.2.e | Architect reviews regulations and findings | ROLE-010, RULE-002, ARCH-010 | 4 |
| 2.2.f | Architect records explanation and professional signature/approval only if legally supported | ROLE-005, DOC-002, DEC-007/008/028/033 | 9 |
| 2.2.g | Architect exports drawings and models | ROLE-009, ARCH-009, DOC-001, BIM-003 | 3, 5 |
| 2.3.a | Structural engineer accesses approved architecture version | ROLE-002 | 6 |
| 2.3.b | Structural engineer defines structural system and analysis assumptions | STR-001 | 6 |
| 2.3.c | Structural engineer reviews axis grid and load-bearing elements | STR-001/005 | 6 |
| 2.3.d | Structural engineer runs analysis/design only within supported-engine scope | STR-002/003 | 6 |
| 2.3.e | Structural engineer sees warnings, checks, and calculation reports | STR-005/006 | 6 |
| 2.3.f | Structural engineer records review, approval, or revision request | ROLE-002, STR-006, DEC-028/033 | 6 |
| 2.4.a | MEP engineer sees only permitted architecture/structure model versions | ROLE-003 | 7 |
| 2.4.b | MEP engineer designs routes/equipment in supported scope | MEP-001/002/003 | 7 |
| 2.4.c | MEP engineer checks clashes and space requirements | MEP-004/005 | 7 |
| 2.4.d | MEP engineer prepares drawings, schedules, and reports | MEP-002/003 | 7 |
| 2.4.e | MEP engineer records review status/comment | ROLE-003, MEP-005 | 7 |
| 2.5.a | Estimator defines measurement basis | ROLE-004, QTY-002 | 8 |
| 2.5.b | Estimator sees approved elements and technical specifications | ROLE-004, BIM-004 | 8 |
| 2.5.c | Estimator checks quantities, coefficients, and price-book rows | ROLE-004, QTY-002, EST-001/002 | 8 |
| 2.5.d | Estimator prepares estimate, pricing scenarios, and variance reports | ROLE-004, EST-003 | 8 |
| 2.6.a | System admin manages users, roles, organizations, and projects | ADMIN-001, ADMIN-007, ROLE-008 | 1, 10 |
| 2.6.b | System admin manages regulation and price sources through approval workflow | ROLE-006/012, ADMIN-002/004, RULE-003, EST-001 | 4, 8 |
| 2.6.c | System admin manages calculation-engine versions/settings | ROLE-007/013, ADMIN-003/005 | 6, 7 |
| 2.6.d | System admin views security events and health reports | ROLE-008, ADMIN-006, SEC-004 | 10 |
| 2.6.e | System admin manages subscriptions/quotas/invoices when commercial features are enabled | ROLE-008, ADMIN-006, BILL-002/003 | 10 |
| 2.access.1 | Backend enforces permissions; UI hiding alone is not authorization | IAM-002, SEC-001 | 0–1 |
| 2.access.2 | Access is tenant- and project-scoped | IAM-002, SEC-001, CORE-004 | 0–1 |
| 3.forms | Input forms are staged, draft-saveable, validated, resumable | INP-001 | 1 |
| 3.1.a | Project title and code | INP-002 | 1 |
| 3.1.b | Project type: residential | INP-002 | 1 |
| 3.1.c | Project type: commercial | INP-002 | 1 |
| 3.1.d | Project type: office | INP-002 | 1 |
| 3.1.e | Project type: mixed-use | INP-002 | 1 |
| 3.1.f | Project type: industrial | INP-002 | 1 |
| 3.1.g | Project type: service/other | INP-002 | 1 |
| 3.1.h | City, province, address, and geographic location | INP-002 | 1 |
| 3.1.i | Client, owner, responsible engineer, and team members | INP-002, PRJ-002 | 1 |
| 3.1.j | Project purpose: residence, investment, sale, rental, or mixed use | INP-002 | 1 |
| 3.1.k | Land deed/title, ownership, legal restrictions, and notes are recorded without automated legal-validity claims | INP-002 | 1 |
| 3.2.a | Parcel side dimensions and boundary lengths | SITE-001 | 1 |
| 3.2.b | Rectangular, polygonal, and irregular parcel shape | SITE-001, GEOM-001 | 1–2 |
| 3.2.c | Survey file or coordinates when available | SITE-001 | 1 |
| 3.2.d | Declared and computed area with discrepancy report | SITE-001, GEOM-002 | 1–2 |
| 3.2.e | Geographic north, street direction, and frontage | SITE-001 | 1 |
| 3.2.f | Road width and number of access fronts | SITE-001 | 1 |
| 3.2.g | Slope, level differences, terrain, and topography | SITE-001 | 1 |
| 3.2.h | Neighbors, shared walls, and obstacles | SITE-002 | 1 |
| 3.2.i | Trees, wells, channels, existing utilities, and easements | SITE-002 | 1 |
| 3.2.j | Optional soil/geotechnical information | SITE-002 | 1 |
| 3.2.k | Photos/documents/files retain type, date, and ownership | FILE-001 | 1 |
| 3.2.k+ | File versions, extraction and cross-file reconciliation (owner decision 2026-11-24) | FILE-002, FILE-003, FILE-004 | 1, 3, 5 |
| 3.3.a | Land use and zoning | RULE-DATA-001 | 1 |
| 3.3.b | Permitted site coverage | RULE-DATA-001 | 1 |
| 3.3.c | Density and permitted gross floor area | RULE-DATA-001 | 1 |
| 3.3.d | Permitted number of floors and building height | RULE-DATA-001 | 1 |
| 3.3.e | Setbacks and correction lines | RULE-DATA-001, GEOM-003 | 1–2 |
| 3.3.f | Minimum parking and access rules | RULE-DATA-001, ARCH-010 | 1, 4 |
| 3.3.g | Daylight, patio, courtyard, and opening rules | RULE-DATA-001, ARCH-010 | 1, 4 |
| 3.3.h | Stair, elevator, ramp, and exit rules | RULE-DATA-001, ARCH-010 | 1, 4 |
| 3.3.i | Local restrictions and municipality-specific rules | RULE-DATA-001, RULE-001 | 1, 4 |
| 3.3.j | Each rule records source, date, and supporting file/link | RULE-DATA-001, RULE-001 | 1, 4 |
| 3.3.k | Unverified rules display unknown/needs inquiry; AI guesses are never stored as law | RULE-DATA-001, AI-003 | 1 / all |
| 3.4.a | Number of units and floors | REQ-001 | 1 |
| 3.4.b | Number and type of rooms | REQ-001 | 1 |
| 3.4.c | Target area or acceptable range for each room | REQ-001 | 1 |
| 3.4.d | Kitchen, reception, living room, bathrooms, storage, laundry, special spaces | REQ-001 | 1 |
| 3.4.e | Parking, yard, terrace, balcony, roof garden, green space | REQ-001 | 1 |
| 3.4.f | Accessibility and older/disabled occupant needs | REQ-002 | 1 |
| 3.4.g | Privacy and public/private separation | REQ-002 | 1 |
| 3.4.h | Architectural style, quality, and material level | REQ-002 | 1 |
| 3.4.i | Target budget and priorities | REQ-002 | 1 |
| 3.4.j | Mandatory, preferred, and unacceptable constraints | REQ-002 | 1 |
| 3.4.k | Future expansion and change-of-use needs | REQ-002 | 1 |
| 3.4.l | Favorite reference images/designs with labels and explanations | REQ-003 | 1 |
| 3.5.a | Sourced climate, solar exposure, prevailing wind, and rainfall | ENV-001 | 1 |
| 3.5.b | Design temperature and comfort conditions | ENV-001 | 1 |
| 3.5.c | Location-related natural hazards | ENV-001 | 1 |
| 3.5.d | Sourced seismicity information | ENV-001 | 1 |
| 3.5.e | Water, electricity, gas, sewer, and telecom availability | ENV-001 | 1 |
| 3.5.f | Energy constraints and efficiency requirements | ENV-001 | 1 |
| 4.1.a | Analyze parcel shape and access fronts | GEOM-001, ARCH-002 | 2–3 |
| 4.1.b | Derive buildable area from recorded setbacks | GEOM-003 | 2 |
| 4.1.c | Check area and permitted site coverage | GEOM-003, ARCH-010 | 2, 4 |
| 4.1.d | Propose multiple alternatives with explainable criteria | ARCH-002, AI-005 | 3 |
| 4.1.e | Place spaces using relationships and privacy | ARCH-002 | 3 |
| 4.1.f | Check minimum room dimensions/areas against active rules | ARCH-010 | 4 |
| 4.1.g | Suggest orientation using sun, climate, and neighbors | ARCH-002 | 3 |
| 4.1.h | Design entry and horizontal/vertical circulation | ARCH-002/003/005 | 3 |
| 4.1.i | Preliminary stairs, elevators, parking, and ramp assessment | ARCH-008 | 3 |
| 4.1.j | Explain each option's rationale and limitations | ARCH-002, AI-005 | 3 |
| 4.2.a | Move spaces | ARCH-003 | 3 |
| 4.2.b | Resize spaces | ARCH-003 | 3 |
| 4.2.c | Rotate spaces | ARCH-003 | 3 |
| 4.2.d | Add/remove spaces | ARCH-003 | 3 |
| 4.2.e | Edit walls | ARCH-003 | 3 |
| 4.2.f | Edit doors, windows, and openings | ARCH-003 | 3 |
| 4.2.g | Lock elements and dimensions | ARCH-003 | 3 |
| 4.2.h | Snap and grid | ARCH-004 | 3 |
| 4.2.i | Dimensioning and metre/centimetre/millimetre units | ARCH-004 | 3 |
| 4.2.j | Undo/redo and change history | ARCH-004 | 3 |
| 4.2.k | Copy/repeat floors | ARCH-005 | 3 |
| 4.2.l | Multiple floors and vertical connections | ARCH-005 | 3 |
| 4.2.m | Compare two or more versions | ARCH-006 | 3 |
| 4.2.n | Comment on a specific space/element | FLOW-004 | 3 |
| 4.3.a | Detect closed-space geometry and unintended overlap | ARCH-007 | 3 |
| 4.3.b | Compare total room area with gross/building area | ARCH-007 | 3 |
| 4.3.c | Check corridor width, door width, space dimensions, and openings against active rule | ARCH-010 | 4 |
| 4.3.d | Check daylight and natural ventilation within calculable scope | ARCH-010 | 4 |
| 4.3.e | Check privacy and unwanted views | ARCH-008, ARCH-010 | 3–4 |
| 4.3.f | Check access and egress routes | ARCH-008, ARCH-010 | 3–4 |
| 4.3.g | Preliminary parking and vehicle circulation check | ARCH-008 | 3 |
| 4.3.h | Identify inaccessible or geometrically invalid spaces | ARCH-007 | 3 |
| 4.4.a | Scaled 2D plan | ARCH-009 | 3 |
| 4.4.b | Overall and detailed dimensions | ARCH-009 | 3 |
| 4.4.c | Space names and areas | ARCH-009 | 3 |
| 4.4.d | Door and window schedule | ARCH-009 | 3 |
| 4.4.e | Furniture plan when requested | ARCH-009 | 3 |
| 4.4.f | Elevations/sections in supported phases | ARCH-009 | 3+ |
| 4.4.g | PDF and image output | DOC-001 | 3 |
| 4.4.h | DXF/DWG only if implemented and compatibility-validated | DOC-001 | 3+; DEC-004 |
| 4.4.i | 3D model and IFC at BIM stages | BIM-003 | 5 |
| 5.a | Domain model independent of UI and output format | BIM-001, ARCH-PLAT-001 | 0, 3 |
| 5.b | Explicit units, coordinate system, and unit conversion | BIM-001, GEOM-002 | 2–3 |
| 5.c | Stable IDs for project, floor, space, wall, door, window, column, beam, equipment | BIM-001 | 3 |
| 5.d | 2D and 3D geometry | BIM-001, BIM-005 | 3, 5 |
| 5.e | Link elements to floor, space, system, and technical properties | BIM-001/002, BIM-005 | 3, 5 |
| 5.f | Element classification and materials | BIM-002 | 5 |
| 5.g | Spatial relationships and element connectivity | BIM-001/002, BIM-005 | 3, 5 |
| 5.h | Model history and versioning | CORE-003, BIM-001 | 0 / all, 3 |
| 5.i | Controlled IFC import/export | BIM-003 | 5; DEC-004/029 |
| 5.j | Map properties and IDs during BIM exchange | BIM-003 | 5 |
| 5.k | Report incomplete, inconsistent, unclassified elements | BIM-002/003 | 5 |
| 5.l | Quality-check model before export | BIM-002/003 | 5 |
| 5.m | Drawings, takeoff, reports derive from the specified shared model version | BIM-004 | 5 |
| 6.a | Select and record project-appropriate structural system | STR-001 | 6; DEC-002 |
| 6.b | Define materials, mechanical properties, and design assumptions | STR-001 | 6 |
| 6.c | Define axis grid and floor elevations | STR-001 | 6 |
| 6.d | Preliminary columns, beams, shear walls, and other supported elements | STR-001 | 6 |
| 6.e | Transfer gravity and lateral loads | STR-002 | 6 |
| 6.f | Define dead, live, wind, seismic loads and code combinations | STR-002 | 6; DEC-002 |
| 6.g | Analyze structure and check stability | STR-003 | 6 |
| 6.h | Check displacement, drift, forces, and design ratios | STR-003 | 6 |
| 6.i | Design reinforced-concrete and steel elements within validated solver scope | STR-003 | 6; DEC-005/014 |
| 6.j | Preliminary foundation design only with sufficient geotechnical data | STR-004 | 6 |
| 6.k | Produce calculation report and structural drawings | STR-006 | 6 |
| 6.l | Show assumptions, sources, solver version, and errors | STR-006 | 6 |
| 6.c1 | Never use default dimensions/reinforcement as a final design | STR-007 | 6 |
| 6.c2 | Check architectural/structural model consistency | STR-005 | 6 |
| 6.c3 | Detect floating columns, disconnected beams, unclear load path, irregularities | STR-005 | 6 |
| 6.c4 | Check soil and loading data sufficiency | STR-004/005 | 6 |
| 6.c5 | Record solver warnings and nonconvergence | STR-005/006 | 6 |
| 6.c6 | Enable structural-engineer review and approval/request | ROLE-002, STR-006 | 6 |
| 6.c7 | Geometry/material/load change invalidates dependent results | STR-007 | 6 |
| 6.boundary | Numerical analysis alone is not design approval | CORE-002, ROLE-002 | 0 / all, 6 |
| 6.validation | Solver validation, reference benchmarks, code checks, qualified review precede professional output | STR-003/006, RELEASE-001 | 6, 10 |
| 7.m1 | Cold and hot domestic water | MEP-001 | 7; DEC-020 |
| 7.m2 | Wastewater and vent | MEP-001 | 7; DEC-020 |
| 7.m3 | Rainwater and drainage | MEP-001 | 7; DEC-020 |
| 7.m4 | Heating, cooling, ventilation | MEP-001 | 7; DEC-020 |
| 7.m5 | Preliminary equipment selection and capacity | MEP-001 | 7 |
| 7.m6 | Duct, pipe, and riser routes | MEP-002 | 7 |
| 7.m7 | Supported calculated slopes and diameters | MEP-002 | 7; DEC-020 |
| 7.m8 | Insulation and technical specifications | MEP-002 | 7 |
| 7.m9 | Mechanical drawings, riser diagrams, and equipment schedules | MEP-002 | 7 |
| 7.e1 | Lighting and receptacle loads | MEP-003 | 7 |
| 7.e2 | Panels and circuits | MEP-003 | 7 |
| 7.e3 | Cable and conduit routes | MEP-003 | 7 |
| 7.e4 | Grounding and protection | MEP-003 | 7 |
| 7.e5 | Emergency lighting and exit signs | MEP-003 | 7 |
| 7.e6 | Fire alarm and safety systems | MEP-003 | 7 |
| 7.e7 | Network, telephone, camera, access control | MEP-003 | 7 |
| 7.e8 | Supported electrical load schedules and drawings | MEP-003 | 7 |
| 7.c1 | Detect routes clashing with beams, columns, walls, ceilings, and other services | MEP-004 | 7 |
| 7.c2 | Manage shafts and riser space | MEP-004 | 7 |
| 7.c3 | Check maintenance access | MEP-004 | 7 |
| 7.c4 | Record clash location and severity | MEP-005 | 7 |
| 7.c5 | Track clash resolution and re-approval | MEP-005 | 7 |
| 8.a | National building-code and local-regulation library | RULE-001 | 4 |
| 8.b | Official source, edition, publication date, effective date | RULE-001 | 4 |
| 8.c | Separate national, local, and project requirements | RULE-001 | 4 |
| 8.d | Retain clause text, interpretation, applicability, and citation | RULE-001 | 4 |
| 8.e | Testable rule-engine inputs and outputs | RULE-002 | 4 |
| 8.f | Show related clause beside each warning | RULE-002 | 4 |
| 8.g | Finding states: compliant, non-compliant, data-needed, human-review-needed | RULE-002 | 4 |
| 8.h | Deactivate obsolete version only with reason/date | RULE-003 | 4 |
| 8.i | Expert admin approves rule content before publication | RULE-003 | 4 |
| 8.j | Report exact applied rules for each design version | RULE-003 | 4 |
| 8.k | No LLM-generated clause/value enters rules without verified source/review | AI-003, RULE-003 | 0 / all, 4 |
| 9.q1 | Extract lengths, areas, volumes, counts, weights from model | QTY-001 | 8 |
| 9.q2 | Group quantities by floor, space, system, operation | QTY-001 | 8 |
| 9.q3 | Configurable measurement rules and coefficients | QTY-002 | 8 |
| 9.q4 | Deduct openings/apply measurement instructions | QTY-002 | 8 |
| 9.q5 | Trace every quantity to source model element | QTY-001 | 8 |
| 9.q6 | Manual correction requires reason and recorded user | QTY-002 | 8 |
| 9.q7 | Report raw, adjusted, final quantities | QTY-002 | 8 |
| 9.p1 | Official annual price books and multiple disciplines | EST-001 | 8; DEC-006 |
| 9.p2 | Retain source file, publisher, year, receipt date, file hash | EST-001 | 8 |
| 9.p3 | Retain item code, description, unit, unit price, chapter | EST-001 | 8 |
| 9.p4 | Retain decomposition and price sources when available | EST-001 | 8 |
| 9.p5 | Map takeoff items to price-book rows | EST-002 | 8 |
| 9.p6 | Keep market prices separate from official schedules | EST-002 | 8 |
| 9.p7 | Record coefficients, region, contract conditions, assumptions | EST-002 | 8 |
| 9.p8 | Compare years/versions | EST-002 | 8 |
| 9.p9 | Warn about unmapped or obsolete rows | EST-002 | 8 |
| 9.e1 | Base estimate uses selected price book | EST-003 | 8 |
| 9.e2 | Market estimate has source and date | EST-003 | 8; DEC-021 |
| 9.e3 | Split materials/labor/machinery/transport/ancillary costs when data supports it | EST-003 | 8 |
| 9.e4 | Low/medium/high economic scenarios | EST-003 | 8 |
| 9.e5 | Price and quantity sensitivity analysis | EST-003 | 8 |
| 9.e6 | Save estimate versions and compare changes | EST-003 | 8 |
| 9.e7 | State uncertainty range and exclusions | EST-003 | 8 |
| 10.d1 | Project and site summary | DOC-002 | 9 |
| 10.d2 | Client requirements | DOC-002 | 9 |
| 10.d3 | Design bases and assumptions | DOC-002 | 9 |
| 10.d4 | Regulation sources and versions | DOC-002 | 9 |
| 10.d5 | Plans, elevations, and sections | DOC-002, ARCH-009 | 3, 9 |
| 10.d6 | Space, door, window, and material schedules | DOC-002, ARCH-009 | 3, 9 |
| 10.d7 | Regulation-check report | DOC-002, RULE-002 | 4, 9 |
| 10.d8 | Structural/MEP reports only if completed and approved | DOC-002, STR-006, MEP-005 | 6–7, 9 |
| 10.d9 | Clash report and resolution status | DOC-002, MEP-005 | 7, 9 |
| 10.d10 | Takeoff/estimate bases and price sources | DOC-002, QTY-001, EST-003 | 8–9 |
| 10.d11 | Version history and approvals | DOC-002, FLOW-002 | 9 |
| 10.d12 | Warnings and items needing review | DOC-002 | 9 |
| 10.f1 | Persian right-to-left PDF | DOC-003 | 9; DEC-018 |
| 10.f2 | English PDF | DOC-003 | 9; DEC-012/018 |
| 10.f3 | Permitted embedded fonts | DOC-003 | 9; DEC-018 |
| 10.f4 | Contents and page numbers | DOC-003 | 9 |
| 10.f5 | Project title and version number | DOC-003 | 9 |
| 10.f6 | Drawing scale and units | DOC-003 | 9 |
| 10.f7 | Status watermark | DOC-003, CORE-002 | 0 / all, 9 |
| 10.f8 | Separate drawing/report exports | DOC-003 | 9 |
| 10.f9 | Secure expiring access-controlled download | DOC-004 | 9 |
| 10.f10 | Complete ZIP package | DOC-003 | 9 |
| 11.a | Persian/English project-context conversation | AI-001 | 1; DEC-027/032 |
| 11.b | Convert free text to structured client requirements | AI-001 | 1 |
| 11.c | Ask follow-up only for essential missing data | AI-001 | 1 |
| 11.d | Summarize requirements and identify contradictions | AI-001 | 1 |
| 11.e | Explain design proposals and their criteria | AI-005 | 3 |
| 11.f | Explain regulation/calculation findings with source citations | AI-006 | 4 |
| 11.g | Extract supported PDF/image/drawing data | AI-002, AI-007 | 1, 5; DEC-004/023/027 |
| 11.h | Assist element classification and takeoff row suggestions | AI-007/008 | 5, 8 |
| 11.i | Generate explanatory/report text | AI-009 | 9 |
| 11.j | Provide staged owner assistant and specialist engineer tools | AI-001, AI-009 | 1, 9 |
| 11.l1 | AI must not fabricate clauses, prices, analysis results, or engineering approval | AI-003 | 0 / all |
| 11.l2 | Factual answer has a source or is labeled proposal/estimate | AI-003, AI-005/006/008/009 | 0 / all, 3–9 |
| 11.l3 | Validate AI output against schema before model ingestion | AI-003 | 0 / all |
| 11.l4 | Malicious instructions or file text are not executed as system instructions | AI-003 | 0 / all |
| 11.l5 | Model-changing AI action requires authorized user/role confirmation | AI-003, IAM-002 | 0 / all |
| 11.l6 | Engineering/financial calculation reproducible without AI text | CORE-001, AI-003 | 0 / all |
| 12.a | Invite members and assign project-scoped roles | FLOW-001, IAM-002 | 1 |
| 12.b | Assign task, responsible person, and deadline | FLOW-005 | 9 |
| 12.c | Comment on architectural design version/space/element and on an issued document/drawing version | FLOW-004, FLOW-006 | 3, 9 |
| 12.d | Track stage status and responsible approver | FLOW-002, FLOW-005 | 9 |
| 12.e | Follow site→requirements→architecture→client approval→rules→disciplines→coordination→estimate→final check→issuance sequence | FLOW-002 | 9 |
| 12.f | Record rejection/approval with reason and time | FLOW-002, FLOW-005 | 9 |
| 12.g | Block final release while critical checks remain open | FLOW-002 | 9 |
| 12.h | In-app notifications; email/SMS only when service connected | FLOW-003, FLOW-007 | 9, 10; DEC-010 |
| 12.i | Project activity report | PRJ-002, FLOW-002 | 1, 9 |
| 13.a | Secure registration/login | IAM-001, SEC-001 | 1 |
| 13.b | Email/phone verification when required | BILL-001 | 10; DEC-010/022 |
| 13.c | Account recovery and session management | BILL-001 | 10; DEC-022 |
| 13.d | Organizations and teams | BILL-001, ADMIN-007, ROLE-008 | 10 |
| 13.e | Free, professional, organizational, and usage-credit plans | BILL-002 | 10; DEC-011 |
| 13.f | Limit projects, file volume, exports, and AI consumption | BILL-002, AI-010 | 10 |
| 13.g | Iranian payment gateway only after provider selection/contract review | BILL-003 | 10; DEC-010 |
| 13.h | Invoices, renewal, cancellation, payment history | BILL-003 | 10 |
| 13.i | Subscription admin and usage report | BILL-002/003, ADMIN-006 | 10 |
| 13.j | Trial and discount codes when required | BILL-002 | 10; DEC-011 |
| 13.secret | No API/payment secret in frontend or public repository | BILL-003, SEC-005 | 0 / 10 |
| 14.s1 | Require TLS in production | SEC-001 | 0 / all |
| 14.s2 | Securely hash passwords | SEC-001 | 0 / all |
| 14.s3 | Enforce server-side access and tenant isolation | IAM-002, SEC-001 | 0–1 |
| 14.s4 | Validate input | SEC-001 | 0 / all |
| 14.s5 | Defend against SQL injection | SEC-001 | 0 / all |
| 14.s6 | Defend against XSS | SEC-001 | 0 / all |
| 14.s7 | Defend against CSRF | SEC-001 | 0 / all |
| 14.s8 | Defend against SSRF | SEC-001 | 0 / all |
| 14.s9 | Limit file size, type, and count; scan uploads | SEC-002 | 1 |
| 14.s10 | Store files outside public paths and authorize downloads | SEC-002, DOC-004 | 1, 9 |
| 14.s11 | Manage secrets securely | SEC-005 | 0 / all |
| 14.s12 | Rate-limit and protect against brute force | SEC-001 | 0 / all |
| 14.s13 | Audit sensitive operations | SEC-003 | 0 / all |
| 14.s14 | Scheduled backups and tested restoration | SEC-004 | 10 |
| 14.s15 | Data retention/deletion policy | CORE-004, SEC-003 | 0 / all |
| 14.s16 | Encrypt sensitive data when required | SEC-003 | 0 / all; DEC-016 |
| 14.s17 | Monitor errors, health, and job queues | SEC-004, ADMIN-006 | 10 |
| 14.s18 | Handle errors without exposing stack traces/internal details | OPS-003, SEC-003 | 0 |
| 14.s19 | Incident-response plan | SEC-004 | 10 |
| 14.s20 | Penetration test and security review before public release | SEC-004, RELEASE-001 | 10 |
| 15.t1 | Next.js + TypeScript frontend proposal | OPS-004, ARCH-PLAT-001 | 0; proposal |
| 15.t2 | FastAPI + Python API proposal | OPS-004, ARCH-PLAT-001 | 0; proposal |
| 15.t3 | PostgreSQL production / SQLite development proposal | OPS-004, OPS-002 | 0; proposal |
| 15.t4 | Redis + Celery or evaluated equivalent proposal | OPS-004, ARCH-PLAT-002 | 0; proposal |
| 15.t5 | Independent geometry engine with unit tests | OPS-004, GEOM-001/004 | 0, 2; proposal |
| 15.t6 | IFC/IfcOpenShell at suitable phase | OPS-004, BIM-003 | 0, 5; proposal |
| 15.t7 | Validated structural engine (e.g. OpenSeesPy or specialist tool) selected after testing | OPS-004, STR-003 | 0, 6; DEC-005 |
| 15.t8 | ReportLab or suitable PDF engine proposal | OPS-004, DOC-003 | 0, 9; proposal |
| 15.t9 | Secure object storage proposal | OPS-004, SEC-002 | 0, 1; proposal |
| 15.t10 | Provider-independent AI Gateway records provider usage/cost | AI-004, AI-010 | unresolved / 10; DEC-032 |
| 15.t11 | Logging, metrics, tracing, error monitoring | OPS-003, SEC-004 | 0, 10 |
| 15.t12 | Automated test/build/controlled CI/CD | OPS-003, RELEASE-001 | 0 / all |
| 15.a1.1 | Logical identity module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.2 | Logical project module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.3 | Logical parcel module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.4 | Logical architecture module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.5 | Logical regulation module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.6 | Logical structure module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.7 | Logical MEP module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.8 | Logical BIM module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.9 | Logical quantity module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.10 | Logical estimating module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.11 | Logical documents module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.12 | Logical billing module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.13 | Logical notifications module boundary | ARCH-PLAT-001 | 0 |
| 15.a1.14 | Logical audit module boundary | ARCH-PLAT-001 | 0 |
| 15.a2 | Version APIs | ARCH-PLAT-001 | 0 |
| 15.a3 | Keep business logic out of UI | ARCH-PLAT-001 | 0 |
| 15.a4 | Domain model independent of database/export formats | ARCH-PLAT-001 | 0 |
| 15.a5 | Heavy jobs asynchronous and trackable | ARCH-PLAT-002 | 0 |
| 15.a6 | Each job records status, versioned input, output, error, runtime | ARCH-PLAT-002 | 0 |
| 15.a7 | Manage database changes through migrations | OPS-002, ARCH-PLAT-002 | 0 |
| 15.a8 | Feature flags for staged activation | ARCH-PLAT-002 | 0 |
| 16.a01 | Identity entity: users | DATA-001 | 0 |
| 16.a02 | Identity entity: organizations | DATA-001 | 0 |
| 16.a03 | Identity entity: memberships | DATA-001 | 0 |
| 16.a04 | Identity entity: roles | DATA-001 | 0 |
| 16.a05 | Identity entity: permissions | DATA-001 | 0 |
| 16.a06 | Identity entity: sessions | DATA-001 | 0 |
| 16.b01 | Project entity: projects | DATA-001 | 0 |
| 16.b02 | Project entity: project_members | DATA-001 | 0 |
| 16.b03 | Project entity: project_settings | DATA-001 | 0 |
| 16.c01 | Site entity: parcels | DATA-001 | 0 |
| 16.c02 | Site entity: parcel_boundaries | DATA-001 | 0 |
| 16.c03 | Site entity: site_surveys | DATA-001 | 0 |
| 16.c04 | Site entity: geolocations | DATA-001 | 0 |
| 16.c05 | Site entity: attachments | DATA-001 | 0 |
| 16.d01 | Requirement entity: client_requirements | DATA-001 | 0 |
| 16.d02 | Requirement entity: requirement_items | DATA-001 | 0 |
| 16.d03 | Requirement entity: design_briefs | DATA-001 | 0 |
| 16.e01 | Model entity: design_versions | DATA-001 | 0 |
| 16.e02 | Model entity: building_models | DATA-001 | 0 |
| 16.e03 | Model entity: building_levels | DATA-001 | 0 |
| 16.e04 | Model entity: spaces | DATA-001 | 0 |
| 16.e05 | Model entity: model_elements | DATA-001 | 0 |
| 16.f01 | Building element: walls | DATA-001 | 0 |
| 16.f02 | Building element: openings | DATA-001 | 0 |
| 16.f03 | Building element: doors | DATA-001 | 0 |
| 16.f04 | Building element: windows | DATA-001 | 0 |
| 16.f05 | Building element: stairs | DATA-001 | 0 |
| 16.f06 | Building element: elevators | DATA-001 | 0 |
| 16.f07 | Building element: parking_spaces | DATA-001 | 0 |
| 16.g01 | Model data entity: materials | DATA-001 | 0 |
| 16.g02 | Model data entity: assemblies | DATA-001 | 0 |
| 16.g03 | Model data entity: element_properties | DATA-001 | 0 |
| 16.h01 | Regulation entity: regulation_sources | DATA-001 | 0 |
| 16.h02 | Regulation entity: regulation_versions | DATA-001 | 0 |
| 16.h03 | Regulation entity: regulation_clauses | DATA-001 | 0 |
| 16.h04 | Regulation entity: rule_sets | DATA-001 | 0 |
| 16.h05 | Regulation entity: rule_runs | DATA-001 | 0 |
| 16.h06 | Regulation entity: rule_findings | DATA-001 | 0 |
| 16.i01 | Structural entity: structural_models | DATA-001 | 0 |
| 16.i02 | Structural entity: load_cases | DATA-001 | 0 |
| 16.i03 | Structural entity: load_combinations | DATA-001 | 0 |
| 16.i04 | Structural entity: analysis_jobs | DATA-001 | 0 |
| 16.i05 | Structural entity: analysis_results | DATA-001 | 0 |
| 16.i06 | Structural entity: design_checks | DATA-001 | 0 |
| 16.j01 | MEP entity: mep_systems | DATA-001 | 0 |
| 16.j02 | MEP entity: mep_elements | DATA-001 | 0 |
| 16.j03 | MEP entity: equipment | DATA-001 | 0 |
| 16.j04 | Coordination entity: clash_results | DATA-001 | 0 |
| 16.k01 | Quantity entity: quantity_takeoffs | DATA-001 | 0 |
| 16.k02 | Quantity entity: quantity_items | DATA-001 | 0 |
| 16.k03 | Quantity entity: measurement_rules | DATA-001 | 0 |
| 16.l01 | Pricing entity: price_books | DATA-001 | 0 |
| 16.l02 | Pricing entity: price_book_versions | DATA-001 | 0 |
| 16.l03 | Pricing entity: price_items | DATA-001 | 0 |
| 16.l04 | Pricing entity: price_mappings | DATA-001 | 0 |
| 16.m01 | Estimate entity: cost_estimates | DATA-001 | 0 |
| 16.m02 | Estimate entity: estimate_versions | DATA-001 | 0 |
| 16.m03 | Estimate entity: estimate_items | DATA-001 | 0 |
| 16.m04 | Estimate entity: estimate_assumptions | DATA-001 | 0 |
| 16.n01 | Document entity: documents | DATA-001 | 0 |
| 16.n02 | Document entity: document_versions | DATA-001 | 0 |
| 16.n03 | Document entity: exports | DATA-001 | 0 |
| 16.o01 | Workflow entity: approvals | DATA-001 | 0 |
| 16.o02 | Workflow entity: comments | DATA-001 | 0 |
| 16.o03 | Workflow entity: tasks | DATA-001 | 0 |
| 16.o04 | Workflow entity: notifications | DATA-001 | 0 |
| 16.p01 | Commercial entity: subscriptions | DATA-001 | 0 |
| 16.p02 | Commercial entity: plans | DATA-001 | 0 |
| 16.p03 | Commercial entity: invoices | DATA-001 | 0 |
| 16.p04 | Commercial entity: payments | DATA-001 | 0 |
| 16.p05 | Commercial entity: usage_records | DATA-001 | 0 |
| 16.q01 | Operational entity: background_jobs | DATA-001 | 0 |
| 16.q02 | Operational entity: audit_logs | DATA-001 | 0 |
| 16.q03 | Operational entity: system_settings | DATA-001 | 0 |
| 16.q04 | Operational entity: feature_flags | DATA-001 | 0 |
| 16.scope | Dependent records carry project_id and organization_id when applicable | DATA-001, IAM-002 | 0–1 |
| 16.delete | Delete/archive preserves defined policy and referential integrity | CORE-004, DATA-001 | 0 / all |
| 17.0.a | Inspect starter; fix install/build/test issues | OPS-001 | 0 |
| 17.0.b | Standardize project structure/configuration/environments | OPS-001 | 0 |
| 17.0.c | Design initial migrations/models | OPS-002 | 0 |
| 17.0.d | Logging, error handling, CI tests | OPS-003 | 0 |
| 17.0.e | Record architecture decisions | OPS-004 | 0 |
| 17.0.exit | Windows clean install; backend tests; frontend build; run docs | OPS-001–004 | 0 |
| 17.1.a | Initial registration/login and roles | IAM-001/002, ROLE-001 | 1 |
| 17.1.b | Project create/edit/list/archive | PRJ-001 | 1 |
| 17.1.c | Staged site/client forms | INP-001, SITE-001/002, REQ-001/002/003 | 1 |
| 17.1.d | Draft saving and validation | INP-001 | 1 |
| 17.1.e | Secure photo/file upload | FILE-001, SEC-002 | 1 |
| 17.1.f | Dashboard and activity history | PRJ-001/002 | 1 |
| 17.1.exit | Complete initial project input journey; backend permissions tested | PRJ-001, IAM-002, INP-001 | 1 |
| 17.2.a | Rectangular and irregular parcels | GEOM-001 | 2 |
| 17.2.b | Area, perimeter, orientation, boundaries | GEOM-001/002 | 2 |
| 17.2.c | Recorded setbacks/buildable envelope | GEOM-003 | 2 |
| 17.2.d | Units and coordinate conventions | GEOM-002 | 2 |
| 17.2.e | Boundary/invalid geometry tests | GEOM-004 | 2 |
| 17.2.f | 2D parcel display/edit | GEOM-004 | 2 |
| 17.2.exit | Reference and numerical geometry tests match | GEOM-001/004 | 2 |
| 17.3.a | Physical program and space list | ARCH-001 | 3 |
| 17.3.b | Multiple conceptual layouts | ARCH-002, AI-005 | 3 |
| 17.3.c | Walls, spaces, doors, windows, dimensions | ROLE-009, ARCH-003/004 | 3 |
| 17.3.d | Interactive edit, undo/redo, versions | ARCH-003/004/006 | 3 |
| 17.3.e | Multiple/repeated floors | ARCH-005 | 3 |
| 17.3.f | Initial geometry/area checks | ARCH-007 | 3 |
| 17.3.g | Conceptual PDF with status label | DOC-001, CORE-002 | 3 |
| 17.3.exit | Editable, saved, compared, reproducible design; limitations shown | ARCH-002–009 | 3 |
| 17.4.a | Official versioned rule-data ingestion | RULE-001 | 4 |
| 17.4.b | Rule engine | RULE-002 | 4 |
| 17.4.c | Compliance/noncompliance report with clause citation | RULE-002 | 4 |
| 17.4.d | Supported daylight/access/stair/parking/dimension checks | ARCH-010 | 4 |
| 17.4.e | Admin rule source approval panel | RULE-003 | 4 |
| 17.4.exit | Each result traces to rule/version; missing data is not guessed | RULE-001/002/003 | 4 |
| 17.5.a | 3D model derived from shared model | BIM-005 | 5 |
| 17.5.b | Floors, heights, materials | BIM-002/005 | 5 |
| 17.5.c | IFC import/export | BIM-003 | 5 |
| 17.5.d | Model quality and property mapping | BIM-002/003 | 5 |
| 17.5.e | Link model to drawings and schedules | BIM-004 | 5 |
| 17.5.exit | Exchange check preserves critical IDs/properties | BIM-003 | 5 |
| 17.6.a | Structural system and materials | STR-001 | 6 |
| 17.6.b | Loads and combinations | STR-002 | 6 |
| 17.6.c | Selected-engine analysis | STR-003 | 6 |
| 17.6.d | Supported code checks | STR-003 | 6 |
| 17.6.e | Calculation report and engineer review | STR-006, ROLE-002 | 6 |
| 17.6.exit | Benchmarks, independent validation, specialist approval | STR-003/006 | 6 |
| 17.7.a | Priority mechanical/electrical scope | MEP-001/003 | 7 |
| 17.7.b | Risers/equipment | MEP-001/002 | 7 |
| 17.7.c | Routes/schedules | MEP-002/003 | 7 |
| 17.7.d | Clash detection/resolution | MEP-004/005 | 7 |
| 17.7.exit | Reference examples and specialist approval workflow pass | MEP-001–005 | 7 |
| 17.8.a | Model quantity extraction | QTY-001 | 8 |
| 17.8.b | Measurement rules/manual review | QTY-002 | 8 |
| 17.8.c | Official versioned price-book import | EST-001 | 8 |
| 17.8.d | Mapping and variance analysis | EST-002/003 | 8 |
| 17.8.e | Independently sourced/time-stamped market prices | EST-002/003 | 8 |
| 17.8.f | Scenarios and cost reports | EST-003 | 8 |
| 17.8.exit | Traceable quantities/costs compared with manual takeoff | QTY-001/002, EST-003 | 8 |
| 17.9.a | Comprehensive project PDF | DOC-002/003 | 9 |
| 17.9.b | Versioned drawings/schedules | ARCH-009, BIM-004, DOC-003 | 3, 5, 9 |
| 17.9.c | Document completeness checks | DOC-002 | 9 |
| 17.9.d | Role-based approvals/audit trail | ROLE-005, FLOW-002 | 9 |
| 17.9.e | Lock issued version/manage revisions | CORE-003, FLOW-002 | 9 |
| 17.9.exit | Sample project traceable from input through final dossier | DOC-002/003/004 | 9 |
| 17.10.a | Multi-organization/subscription | BILL-001/002 | 10 |
| 17.10.b | Payment/invoicing | BILL-003 | 10 |
| 17.10.c | Usage limits/AI cost management | BILL-002, AI-010 | 10 |
| 17.10.d | Monitoring, backup, recovery | SEC-004 | 10 |
| 17.10.e | Load/security/penetration tests | SEC-004, RELEASE-001 | 10 |
| 17.10.f | Production deployment/support plan | OPS-004, SEC-004 | 10 |
| 17.10.exit | Security, recovery, load, and support evidence documented | SEC-004, RELEASE-001 | 10 |
| 18.t1 | Unit tests for independent logic | TEST-001 | 0 / all |
| 18.t2 | Integration tests between modules | TEST-001 | 0 / all |
| 18.t3 | API contract tests | TEST-001 | 0 / all |
| 18.t4 | Authorization and user-data-isolation tests | TEST-001, IAM-002 | 0 / all |
| 18.t5 | Invalid, boundary, incomplete input tests | TEST-001 | 0 / all |
| 18.t6 | Database migration tests | TEST-001, OPS-002 | 0 / all |
| 18.t7 | Calculation/large-file performance tests | TEST-001 | 0 / all; DEC-015 |
| 18.t8 | Output reproducibility tests | TEST-001, CORE-001/003 | 0 / all |
| 18.t9 | Regression tests | TEST-001 | 0 / all |
| 18.t10 | Mobile and desktop UI tests | TEST-001 | 0 / all |
| 18.t11 | RTL/LTR and Persian PDF font tests | TEST-001, DOC-003 | 0 / all, 9 |
| 18.g1 | Clean-environment install | RELEASE-001 | 0 / all |
| 18.g2 | Execute and record tests | RELEASE-001 | 0 / all |
| 18.g3 | Successful production build | RELEASE-001 | 0 / all |
| 18.g4 | Manual acceptance scenarios | RELEASE-001 | 0 / all |
| 18.g5 | No open critical/security issues | RELEASE-001 | 0 / all |
| 18.g6 | Update documentation/version | GOV-001 | 0 / all |
| 18.g7 | Previous release can be rolled back | RELEASE-001 | 0 / all |
| 19.g1 | Master specification governs product scope | GOV-001 | 0 / all |
| 19.g2 | New requests first enter the appropriate spec section | GOV-001 | 0 / all |
| 19.g3 | Assign unique feature identifiers | GOV-001 | 0 / all |
| 19.g4 | Use lifecycle statuses Planned/In Progress/Implemented/Tested/Released/Blocked/Deferred | GOV-001 | 0 / all |
| 19.g5 | No feature is Implemented without tests and acceptance criteria | GOV-001 | 0 / all |
| 19.g6 | Scope change records database/API/security/UI/test/document impact | GOV-001 | 0 / all |
| 19.g7 | Before phase, review linked features and dependencies | GOV-001 | 0 / all |
| 19.g8 | After phase, update spec, changelog, and status/checklist | GOV-001 | 0 / all |
| 19.g9 | Deferred scope records reason and return condition | GOV-001 | 0 / all |
| 19.g10 | Prevent parallel implementations/duplicate concepts | GOV-001, DATA-001 | 0 / all |
| 20.1 | Read CLAUDE.md and full master spec first | GOV-001 | Every development session |
| 20.2 | Inspect real code/tests/status, not prior claims | GOV-001 | Every development session |
| 20.3 | Announce phase, goal, dependencies, files, acceptance before coding | GOV-001 | Every development session |
| 20.4 | Implement only active phase while preserving future-compatible architecture | GOV-001, ARCH-PLAT-001 | Every development session |
| 20.5 | Do not remove/simplify future scope without approval | GOV-001 | Every development session |
| 20.6 | Never use test data as real regulation/pricing data | AI-003, RULE-001, EST-001 | Every development session |
| 20.7 | Add calculation tests and reference examples | CORE-001, TEST-001 | Every calculation change |
| 20.8 | Run relevant tests/build and report actual output | TEST-001, RELEASE-001 | Every change |
| 20.9 | Update master spec, changelog, and phase checklist | GOV-001 | Phase completion |
| 20.10 | Report gaps, assumptions, risks, and owner decisions separately | GOV-001 | Every task report |
| 20.11 | Do not start next phase before acceptance unless explicitly directed | GOV-001 | Every phase |
| 20.12 | Never label conceptual/experimental output as engineering-approved | CORE-002 | 0 / all |
| 20.report.a | Final report summary | GOV-001 | Every task report |
| 20.report.b | Files created/changed | GOV-001 | Every task report |
| 20.report.c | Related feature IDs | GOV-001 | Every task report |
| 20.report.d | Tests run and actual results | GOV-001 | Every task report |
| 20.report.e | Untested items and reasons | GOV-001 | Every task report |
| 20.report.f | Risks and limitations | GOV-001 | Every task report |
| 20.report.g | Spec/roadmap status | GOV-001 | Every task report |
| 20.report.h | Exact run command | GOV-001 | Every task report |
| 21.1 | Decide priority cities/municipalities | RULE-001, DEC-001 | Before Phase 4 |
| 21.2 | Decide structural code versions/scope | STR-002, DEC-002 | Before Phase 6 |
| 21.3 | Decide first-market project types | INP-002, DEC-003 | Before Phase 1 scope freeze |
| 21.4 | Decide CAD/BIM formats | BIM-003, DOC-001, DEC-004 | Before format implementation |
| 21.5 | Decide valid engineering engines and licenses | STR-003, MEP-001, DEC-005 | Before Phases 6–7 |
| 21.6 | Decide official price source/update method | EST-001, DEC-006 | Before Phase 8 |
| 21.7 | Decide professional/legal responsibility | CORE-002, DEC-007 | Before professional output |
| 21.8 | Decide digital signature/engineer approval requirements | ROLE-005, DEC-008 | Before approval/signature |
| 21.9 | Decide hosting/resources/storage/job queue | OPS-004, DEC-009 | Phase 0 / production |
| 21.10 | Decide payment/SMS/email/AI providers | BILL-003, FLOW-007, AI-004, DEC-010 | Before integrations |
| 21.11 | Decide pricing and commercial packages | BILL-002, DEC-011 | Before Phase 10 |
| 21.12 | Decide English scope and non-Iran markets | DOC-003, DEC-012 | Before external-market scope |
| 21.13 | Decide AI Gateway rollout phase/provider/data/cost boundaries | AI-004, DEC-032 | Before AI infrastructure/provider integration |
| 21.14 | Decide review/approval/rejection authority, evidence, and legal transition rules | CORE-002, ROLE-005, DEC-033 | Before enabling these lifecycle transitions |
| 22.a | Treat master as target scope, not implementation evidence | PHASE_STATUS, FEATURE_ACCEPTANCE | All phases |
| 22.b | Determine each feature's actual state from code and tests, not document presence | FEATURE_REGISTRY, PHASE_STATUS, GOV-001 | Every status update |

## Coverage rules

- Each row is an independently identifiable master requirement, not a feature
  category. Repeated phase-roadmap items intentionally point to the same feature
  ID when they describe the same capability.
- Every referenced ID must exist in `FEATURE_REGISTRY.md`, have a
  feature-specific acceptance criterion in `FEATURE_ACCEPTANCE.md`, and remain
  **NOT STARTED** until implementation evidence is reviewed.
- Where a phase or authority cannot be determined from the specification,
  this matrix cites the relevant open decision; it does not resolve it.
