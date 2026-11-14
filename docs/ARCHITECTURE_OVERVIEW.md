# Architecture overview

This document separates **confirmed product constraints** from **proposed
implementation choices**. The master specification is authoritative. Nothing
in this overview means the application architecture has been implemented or
that a proposed technology has been selected.

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

## Proposed technology choices — not approved or finalized

The master specification proposes the following target stack. Each item remains
a proposal until evaluated and recorded as an approved architecture decision:

| Area | Proposal in master specification | Status |
|---|---|---|
| Frontend | Next.js + TypeScript | PROPOSED |
| Backend API | FastAPI + Python | PROPOSED |
| Operational database | PostgreSQL; SQLite only for development/sample use | PROPOSED |
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

## Proposed logical structure

An eventual repository may use a monorepo with a web application, API, shared
domain/geometry packages, background worker, tests, documentation, and
deployment configuration. This is a proposal only; Phase 0 must inspect the
actual starter and approve the structure before implementation. Do not create
these source directories merely because they appear here.

The backend boundaries should map to the specified domain modules. Module
boundaries do not prescribe a microservice deployment: deployment topology is
unresolved. Deterministic engineering engines should expose explicit inputs,
versions, outputs, warnings, and testable contracts. The AI Gateway may assist
with extraction/explanation but cannot be a source of authoritative rules,
prices, solver results, or approvals.

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
