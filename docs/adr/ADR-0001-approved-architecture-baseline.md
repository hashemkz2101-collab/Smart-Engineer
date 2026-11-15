# ADR-0001: Approved Architecture Baseline

- **Status:** Accepted in principle / baseline approved; implementation details
  remain subject to open decisions.
- **Decision scope:** High-level architecture direction only.
- **Authority:** Project owner approval recorded for Phase 0 / P0-01.
- **Related records:** [Architecture overview](../ARCHITECTURE_OVERVIEW.md),
  [open decisions](../OPEN_DECISIONS.md), and the
  [master specification](../../SMART_ENGINEER_MASTER_SPEC.md).

## Context and goals

Smart Engineer is planned as a web-based project and engineering platform with
multiple future domains, including project management, parcel geometry,
architectural design, regulations, visualization/BIM, structural engineering,
MEP, quantity surveying and estimating, documents and approvals, collaboration,
and commercialization. The architecture must support those phases without
activating or simplifying their requirements prematurely.

The architecture must provide clear frontend/backend responsibilities,
testable contracts, backend-enforced security, and a foundation for
deterministic and traceable engineering work. The master specification remains
the source of truth for product scope and constraints.

## Approved architecture direction

The project owner has approved the following direction in principle:

- **Frontend:** Next.js + TypeScript.
- **Backend:** FastAPI + Python.
- **Database:** PostgreSQL.
- **Architecture style:** Modular Monolith.
- **API contract:** REST API with OpenAPI documentation.
- **Frontend/backend communication:** through the documented API boundary.
- **Engineering calculations:** deterministic, testable, traceable backend
  modules. An LLM must never be delegated authoritative engineering
  calculations.

This approves architectural direction, not implementation details. P0-02
separately pins workspace versions for reproducible development; those pins do
not select deployment runtimes or settle other open decisions. This ADR does
not approve an ORM, authentication provider, hosting/infrastructure, storage,
job queue, monitoring service, AI provider, external service, licensing terms,
or resource limits.

## Why a Modular Monolith

The project has multiple connected domains and substantial requirements for
shared project scope, versioned models, auditability, and dependent-output
invalidation. A modular monolith provides explicit domain boundaries while
keeping early development, local testing, transactions, and deployment
operations simpler than a distributed microservice system. It also avoids
introducing network failure modes and service-to-service authorization before
there is evidence that independent deployment or scaling is needed.

Modules must retain clear interfaces and avoid bypassing domain boundaries.
This decision does not prevent a future, evidence-based extraction of a
background worker or service, but such a change requires a separately reviewed
decision. It does not choose the deployment provider or topology.

## Responsibilities and boundaries

### Frontend

The Next.js/TypeScript frontend presents user experiences and collects input.
It communicates with the backend through the documented REST/OpenAPI
contract. It must not be trusted to enforce access control, and it must not
own authoritative domain or engineering calculations.

### Backend

The FastAPI/Python backend owns API behavior, server-side input validation,
domain operations, and authorization enforcement. Its modular boundaries
should correspond to the product domains as those phases are approved. Future
engineering calculation modules must run on the backend and expose explicit,
versioned inputs and traceable outputs.

This ADR does not implement authentication or authorize any product feature.
Authentication assurance, sessions, role details, and feature-level
authorization remain governed by their requirements and open decisions.

### Database

PostgreSQL is the approved direction for persisted application data. Database
access remains backend-controlled. Database schema design, migration tooling,
ORM/data-access libraries, hosting, backup, retention, recovery, and
operational configuration are not selected by this ADR.

### API

REST with OpenAPI documentation is the agreed integration boundary between
frontend and backend. OpenAPI describes the contract; it does not itself
provide authorization. Endpoint design, API versioning details, generated
client tooling, and deployment/network configuration remain implementation
decisions.

## Engineering calculation integrity

- Authoritative engineering calculations must be deterministic and
  independently testable, with defined inputs, units, versions, outputs,
  warnings, and traceability.
- LLMs may not replace engineering calculation engines or be treated as the
  authoritative source of calculation results, rules, prices, solver outputs,
  or professional approvals.
- Applicable standards, regulations, price lists, models, and calculation
  engines must retain source/version/validity metadata as required by the
  specification.
- Changes to foundational inputs or models must identify dependent outputs
  that need to be invalidated or marked stale.
- Conceptual or unverified outputs must not be represented as approved
  construction documents. AI does not grant human review or approval.

These are architectural constraints for later phases, not approval to
implement engineering or AI features now.

## Security and tenant/project isolation

- Backend authorization is mandatory; frontend visibility is not an
  authorization control.
- Every protected operation must enforce the authorized tenant and project
  scope server-side and must not trust a client-supplied scope without
  verification.
- Sensitive access and state changes must be auditable as required by the
  specification.
- Secrets and sensitive project data must not be exposed in client code,
  logs, or error responses.
- Authentication assurance, session policy, data retention, encryption,
  operational controls, and monitoring details remain open decisions.

This ADR establishes principles only. It does not implement authentication,
authorization, audit logging, or tenant/project data models.

## Consequences and trade-offs

- The frontend and backend use different languages and ecosystems. This
  supports the planned Python backend domains but increases dependency,
  tooling, CI, and maintenance overhead.
- A documented API boundary improves separation and enables independently
  testable contracts, but requires disciplined API evolution and may add
  client-generation and integration work.
- PostgreSQL provides the selected relational database direction, while
  provider, schema, spatial extensions, and operations remain to be evaluated.
- Modular Monolith boundaries reduce early distributed-systems complexity,
  but modules must remain disciplined to avoid a tightly coupled codebase.
- The architecture supports future domains without authorizing their early
  implementation.

## Explicitly deferred decisions

The following remain unresolved and must not be treated as approved by this
ADR:

- **DEC-009:** Hosting, infrastructure, storage, queues, and service limits.
- **DEC-015:** Performance and capacity targets.
- **DEC-022:** Authentication assurance and session policy.
- **DEC-024:** Operations, backups, recovery, monitoring, and support.
- **DEC-029:** Libraries, external services, and licenses.
- **DEC-031:** Windows clean-install and testing policy.
- **DEC-032:** AI Gateway, provider, data handling, and cost.

All other entries in the open-decision register, including their dependencies,
remain unresolved unless explicitly approved in a separate decision record.
AI-004 and all dependent AI features remain gated; this ADR does not assign an
implementation phase or activate them.

## Implementation and review

No application code, project scaffold, package manifest, database schema, or
deployment configuration is authorized by this ADR alone. Before implementation,
resolve or explicitly gate the applicable open decisions, add more detailed
ADRs where needed, and retain the master specification's requirements and
phase boundaries. Revisit this decision if technical evidence, legal
constraints, operating costs, or project requirements materially change.
