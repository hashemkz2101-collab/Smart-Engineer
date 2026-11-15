# Architecture overview

This document separates **confirmed product constraints**, the **approved
architecture baseline**, and **proposed implementation choices**. The master
specification remains authoritative for product requirements. The baseline
records an approved direction; it does not mean the application architecture
has been implemented or that implementation details and external services
have been selected. See [ADR-0001](adr/ADR-0001-approved-architecture-baseline.md).

## Confirmed by the master specification

- Product: web-based project lifecycle/design/estimating system for the Iranian
  market, with Persian and English as target languages and owner/client and
  engineering users.
- Engineering calculations must be deterministic, testable, traceable, and
  reproducible independently of AI-generated text.
- Every output carries a clear lifecycle/review status. Unreviewed work must
  not be represented as approved for construction or professional use.
- The six output states are Conceptual, Initial, Under Review, Reviewed,
  Approved, and Rejected. The transition and watermark proposal is documented
  in [`OUTPUT_STATUS_LIFECYCLE.md`](OUTPUT_STATUS_LIFECYCLE.md); professional
  authority to grant review/approval remains decision-gated.
- Regulation, standard, price-book, model, calculation, and document versions
  and their sources must be traceable. Changes invalidate or stale dependent
  results/documents.
- Backend authorization and tenant/project-scoped access are mandatory; UI
  visibility is not an authorization control.
- The model/domain must be independent of the UI, persistence technology, and
  export format. A versioned BIM/building model is the shared source for
  drawings, schedules, takeoff, and reports.
- Heavy jobs are asynchronous and traceable, with versioned inputs, outputs,
  errors, and runtime. APIs are versioned; database changes use migrations;
  feature flags support staged activation.
- Required logical boundaries are identity, projects, parcels, architecture,
  regulations, structure, MEP, BIM, quantity, estimating, documents, billing,
  notifications, and audit.
- Project data access, export, deletion/archival, retention, integrity, and
  audit history must be controlled.
- Future capabilities are anticipated but activated only in gated phases.
  Security, quality, rollback, and qualified professional review are release
  constraints, not optional enhancements.

## Approved architecture baseline

The following high-level direction is approved in principle:

| Area | Approved baseline | Scope limitation |
|---|---|---|
| Frontend | Next.js 16.4.6 + React 19.3.1 + TypeScript 5.9.3 | P0-02 pins these workspace versions; UI libraries and deployment remain undecided. |
| Backend | FastAPI 0.163.0 + Python 3.14.10 | P0-02 pins these workspace versions; additional libraries and deployment remain undecided. |
| Database | PostgreSQL | Hosting, configuration, access layer, and operational policies remain undecided. |
| Architecture style | Modular Monolith | Domain boundaries are required; specific deployment topology and any future worker/service split remain undecided. |
| API contract | REST API documented with OpenAPI | Endpoint details and API versioning policy remain subject to implementation design. |
| Frontend/backend boundary | Frontend communicates with backend through the documented API boundary | The frontend is not an authorization or domain-logic authority. |
| Engineering calculations | Deterministic, testable, traceable backend modules | An LLM must never be the authoritative engineering calculation engine. |

This approval is limited to architectural direction. It does not approve any
particular library, identity or AI provider, hosting/infrastructure provider,
queue, storage service, licensing choice, service limit, or operational
configuration. Those choices remain subject to the open-decision register.
Phase status and feature status are unchanged; no implementation is implied.

## Other proposed technology choices — not approved or finalized

The master specification proposes the following additional implementation
choices. Each remains a proposal until evaluated and recorded as an approved
decision:

| Area | Proposal in master specification | Status |
|---|---|---|
| Background processing | Redis + Celery or an equivalent after evaluation | PROPOSED |
| Geometry | Independent geometry library/engine with unit tests | PROPOSED |
| BIM | IFC and IfcOpenShell at an appropriate phase | PROPOSED |
| Structural analysis | Validated engine such as OpenSeesPy or a suitable specialist tool, selected after testing | PROPOSED |
| PDF | ReportLab or a suitable document engine | PROPOSED |
| File storage | Secure object storage | PROPOSED |
| AI | Provider-independent AI Gateway with cost/usage recording | PROPOSED |
| Observability | Logging, metrics, tracing, and error monitoring | PROPOSED |
| Delivery | Automated tests, build, and controlled CI/CD release | PROPOSED |

Hosting, queue, storage provider, AI model/provider, payment and messaging
providers, library licenses, and supported service limits are open decisions;
see [`OPEN_DECISIONS.md`](OPEN_DECISIONS.md).

## Architectural responsibilities and boundaries

- **Frontend:** presents responsive user experiences and gathers user input.
  It calls the backend through the documented REST/OpenAPI contract. It must
  not be trusted to enforce authorization or to own authoritative domain
  calculations.
- **Backend:** exposes the API, validates untrusted input, enforces
  authentication/authorization once those capabilities are approved and
  implemented, applies project/tenant scope, and owns domain behavior. It is
  organized as a modular monolith with explicit domain boundaries. Deterministic
  engineering calculation modules belong here and must be independently
  testable and traceable.
- **Database:** PostgreSQL is the approved database direction for persisted
  application data. It stores data through backend-controlled access; clients
  must not bypass backend authorization. Schema, access-layer, hosting,
  backup, and retention details remain undecided.
- **API boundary:** REST resources and OpenAPI documentation define the
  frontend/backend contract. The contract is the integration boundary; it does
  not determine endpoint details or deployment topology.

Tenant/project-scoped authorization must be enforced by the backend on every
protected operation. Data access must be scoped to the authorized tenant and
project; frontend visibility is never an access-control mechanism. Authentication
assurance and session rules remain open under DEC-022. This baseline does not
implement authentication or authorization.

## Proposed logical structure

An eventual repository may use a monorepo with a web application, API, shared
domain/geometry packages, background worker, tests, documentation, and
deployment configuration. This is still a proposal; the approved baseline
does not select a repository layout. Do not create source directories merely
because they appear here.

The backend boundaries should map to the specified domain modules. The
Modular Monolith direction does not authorize premature microservices or
decide how asynchronous workloads will be hosted. Deterministic engineering
engines should expose explicit inputs, versions, outputs, warnings, and
testable contracts. The AI Gateway may assist with extraction/explanation only
within approved scope; it cannot be a source of authoritative calculations,
rules, prices, solver results, or approvals. AI-004 and dependent AI features
remain gated and are not activated by this baseline.

## Conceptual data domains

The following are expected conceptual entities, not a finalized schema. Names
and normalization are to be decided during database design:

- **Identity and tenancy:** users, organizations, memberships, roles,
  permissions, sessions.
- **Projects and site:** projects, project members/settings, parcels,
  boundaries, surveys, geolocations, attachments.
- **Requirements and design:** client requirements, requirement items, design
  briefs/versions, building models/levels, spaces, model elements, walls,
  openings, doors, windows, stairs, elevators, parking spaces, materials,
  assemblies, element properties.
- **Regulations:** sources, versions, clauses, rule sets/runs/findings.
- **Structure:** structural models, load cases/combinations, analysis jobs and
  results, design checks.
- **MEP and coordination:** systems, elements, equipment, clash results.
- **Quantity and estimating:** takeoffs/items, measurement rules, price books
  and versions/items/mappings, cost estimates and versions/items/assumptions.
- **Documents and workflow:** documents/versions, exports, approvals,
  comments, tasks, notifications.
- **Commercial and operations:** subscriptions, plans, invoices, payments,
  usage records, background jobs, audit logs, system settings, feature flags.

Dependent records must be project-scoped and organization-scoped where
appropriate. Deletion or archival must preserve referential integrity and
follow an approved policy.

## Architecture and release gates

- Keep business logic out of the UI and domain objects independent of database
  and export representations.
- Version APIs, migrations, model data, rules, price books, solver inputs and
  results, and issued documents as applicable.
- A source-model change must identify dependent calculations, rules, drawings,
  quantities, estimates, and reports that need invalidation or regeneration.
- Async work must expose state, versioned inputs, outputs, errors, and elapsed
  time; errors must be explicit and must not expose internal stack traces.
- Protect secrets, uploaded files, and project data; enforce access in the
  backend and audit sensitive actions.
- Do not publish professional engineering outputs before validated supported
  scope, reference/benchmark tests, independent review where required, and
  qualified human review.
- Apply the master specification's clean-install, test, build, manual
  acceptance, security, documentation, and rollback gates to releases.
