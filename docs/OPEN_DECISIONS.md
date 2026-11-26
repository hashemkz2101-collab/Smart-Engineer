# Open decisions

These items are unresolved by the master specification. This register records
questions, not answers. Do not make a choice by assumption or present an
unverified source, legal interpretation, model, solver, price, or service as
approved. Decisions require the product owner and, where appropriate, qualified
technical, legal, regulatory, or security review.

The high-level architecture direction is approved in principle as recorded in
[ADR-0001](adr/ADR-0001-approved-architecture-baseline.md) and
[`ARCHITECTURE_OVERVIEW.md`](ARCHITECTURE_OVERVIEW.md). That approval does not
close or partially resolve any entry in this register. In particular,
DEC-009, DEC-015, DEC-022, DEC-024, DEC-029, DEC-031, and DEC-032 remain open;
all other decisions and their dependencies also remain open unless separately
approved and recorded under the decision policy below.

| ID | Open decision | Category | Affects / decision needed before |
|---|---|---|---|
| DEC-001 | Which cities and municipalities are first-priority for regulation coverage? | Regulatory / business | Phase 1 input defaults; Phase 4 active rule scope |
| DEC-002 | Which structural code editions, systems, and calculation scope will be supported? | Regulatory / technical | Phase 6 |
| DEC-003 | Which project types are prioritized for the initial market? | Product / business | Phase 1 scope and acceptance scenarios |
| DEC-004 | Which CAD/BIM formats, versions, and interoperability expectations are required? | Technical / product | Phases 3, 5, and 9 |
| DEC-005 | Which structural and MEP engines are valid for the intended use, and what are their license terms? | Technical / legal | Phases 6–7 |
| DEC-006 | What are the official price-book sources, ingestion process, update cadence, and usage permissions? | Regulatory / business / legal | Phase 8 |
| DEC-007 | What professional/legal responsibility attaches to each output, and what may be called reviewed, approved, executable, or construction-authorized? | Legal / professional | Phases 6, 7, and 9; public release |
| DEC-008 | Are digital signatures required; which form, identity assurance, and legal acceptance apply to engineer approval? | Legal / technical | Phases 1 and 9 |
| DEC-009 | Which hosting, resource limits, storage, and job-queue services are acceptable? | Technical / operations | Phase 0 architecture decisions and Phase 10 |
| DEC-010 | Which payment, SMS, email, and AI providers will be used, and under what contracts/terms? | Technical / legal / business | Phases 1, 9, and 10 as applicable |
| DEC-011 | What pricing, plan entitlements, usage limits, and commercial packages are approved? | Business | Phase 10 |
| DEC-012 | What English-language scope and non-Iran markets, if any, are planned for later phases? | Product / business / legal | Product localization and future-market planning |
| DEC-013 | Which regulation authorities/documents are authoritative for each jurisdiction; who interprets, reviews, versions, and withdraws them? | Regulatory / governance | Phase 4 |
| DEC-014 | What are the validated scope, benchmark set, numerical tolerances, independent review method, and solver release policy for each engineering engine? | Technical / professional | Phases 2, 4, 6, 7, and 8 |
| DEC-015 | What are quantitative performance targets, maximum supported file sizes/types/counts, and target load/concurrency? | Technical / operations | Phase 0 test baseline and Phase 10 load acceptance |
| DEC-016 | What are retention, deletion, archival, recovery-point/recovery-time, and sensitive-data encryption policies? | Legal / privacy / security | Phases 1 and 10 |
| DEC-017 | What organization/tenant lifecycle, project invitation, role assignment, and data-export/deletion permissions apply? | Product / security / legal | Phases 1 and 10 |
| DEC-018 | Which approved fonts, PDF rendering approach, localization coverage, and document-status vocabulary apply? | Product / legal / technical | Phases 3 and 9 |
| DEC-019 | What are the first supported architecture rules and their authoritative sources, applicability inputs, and numerical acceptance tolerances? | Regulatory / technical | Phases 3–4 |
| DEC-020 | What are the initial supported MEP systems, materials, units, capacity methods, and reference examples? | Technical / professional | Phase 7 |
| DEC-021 | Which market-price sources may be used, how are prices dated/geographically scoped/licensed, and how is uncertainty characterized? | Business / legal / technical | Phase 8 |
| DEC-022 | What are the supported authentication assurance, account recovery, email/phone verification, and session-management requirements? | Security / product / legal | Phases 0–1 and 10 |
| DEC-023 | Which file formats may be uploaded; what scanning, quarantine, extraction, and retention controls are required per type? | Security / technical / legal | Phase 1 |
| DEC-024 | What are release, support, incident-response ownership, rollback, backup, and recovery exercise schedules? | Operations / security / business | Phases 0 and 10 |
| DEC-025 | What acceptance datasets, manual scenarios, role matrices, and numerical thresholds make each qualitative phase exit measurable? | Product / quality / technical | Before each phase gate |
| DEC-026 | What legal/privacy obligations apply to project location, ownership documents, personal data, and user-uploaded files in target jurisdictions? | Legal / privacy / regulatory | Before production data and public release |
| DEC-027 | Which AI models/providers, data handling terms, retention behavior, cost controls, and evaluation criteria are acceptable? | Technical / legal / business | AI features and Phase 10 commercialization |
| DEC-028 | What engineering-document review/approval roles, authority, withdrawal, and amendment workflow apply to issued versions? | Professional / legal / product | Phases 6, 7, and 9 |
| DEC-029 | Which external libraries/services (geometry, IFC, PDF, observability, queue) are selected after evaluating capability, maintenance, licensing, and deployment constraints? | Technical / legal | Phase 0 and the applicable later phases |
| DEC-030 | Phase 2/3 require recorded setbacks and preliminary architecture checks, while the official versioned rule library/engine is Phase 4. What verified-rule inputs may those earlier phases consume, and how must preliminary results be distinguished from Phase 4 findings? | Regulatory / technical / product | Before Phase 2/3 acceptance criteria are finalized |
| DEC-031 | How will Phase 0's repeatable Windows-installation acceptance criterion be tested, given that the current Codespace environment is Linux? | Technical / quality | Phase 0 validation planning |
| DEC-032 | Which phase, provider boundary, data-handling constraints, and acceptance gates apply to implementing the AI Gateway, model-provider substitution, prompt/file processing, and usage/cost telemetry? | Technical / legal / privacy / business | Before implementing AI infrastructure or connecting an AI provider |
| DEC-033 | Which project roles have legal authority to move an artifact to Reviewed, Approved, or Rejected; what evidence/signature and client-vs-professional approval rules apply; and which transitions are legally recognized? | Legal / professional / product | Before enabling the Reviewed/Approved/Rejected transitions or issuing professional documents |

DEC-013–DEC-033 make explicit decisions implied by requirements and the proposed
architecture; they do not narrow or replace the twelve decision topics in
Section 21 of the master specification. A decision is not closed until the
answer, rationale, approver, date, evidence, and affected feature/phase IDs are
recorded in an approved decision record. Changes to the specification itself
must follow the documentation maintenance policy.

### DEC-029 — narrowly scoped P0-03 dependency approval

For the P0-03 minimal FastAPI shell only, the project owner approved
`httpx==0.28.1` and `uvicorn==0.54.0` as API development-group dependencies:
HTTPX supports FastAPI's TestClient, and Uvicorn runs the local ASGI application.
They are not runtime dependencies. This limited approval does not select other
libraries or services and does not resolve DEC-029, which remains OPEN.

### DEC-029 / DEC-009 — provisional P0-07 database choices (owner confirmation pending)

For P0-07 the owner asked to proceed without answering the open questions, so
the assistant used its proposal as a provisional implementation: SQLAlchemy
2.1.8 (ORM/core), Alembic 1.20.1 (migrations), and psycopg 3.3.9 with the binary
extra (PostgreSQL driver), added as exact-pinned runtime dependencies of
`apps/api`. PostgreSQL 17 is used only as a disposable CI service container.
This is not an approved decision record: the owner has not recorded an
approval, rationale, or evidence review, and DEC-029 and DEC-009 remain OPEN.
Until confirmed, these choices may be replaced; no development-database hosting
method (Docker or direct install) has been chosen.

P0-08 added further development-only dependencies on the same provisional
basis: `@playwright/test` 1.65.1 and `@axe-core/playwright` 4.14.0 (browser and
accessibility tests), `eslint` 10.15.0 and `eslint-config-next` 16.4.6 (web
lint), and `ruff` 0.17.5 (Python lint). They are exact-pinned and not shipped in
the application. They are likewise not an approved decision record.

### DEC-029 / DEC-030 — limited Phase 2 implementation decision (2026-11-25)

The owner requested immediate Phase 2 implementation and approved its implementation
plan. For GEOM-001–004 only, Shapely **2.2.0** is selected (BSD-3-Clause; official
CPython 3.14 Windows x64 wheel verified in
[PyPI release metadata](https://pypi.org/pypi/shapely/2.2.0/json)). Other libraries,
services, geodetic transformation and deployment choices remain undecided.

The supported computation frame is local Cartesian metres, with m/cm/mm boundary
input/display conversion. Descriptive survey references do not trigger a hidden
projection. Setback clearance consumes explicitly mapped edges and user-recorded
sources with revision, verification and validity interval. Missing/unverified/
expired inputs remain unknown. Conservative Euclidean distance-to-segment clearance
with bounded round-join approximation is an initial geometric model, not an
interpretation of official correction lines or regulatory compliance. Legal
interpretation, independently approved survey tolerance, official regulation
publishing and the Phase 4 rule engine stay open under DEC-013/014/025/030.
See PHASE_2_PLAN.md for the complete contract and remaining acceptance work.

### Phase 1 decisions — owner-delegated, assistant-proposed (2026-11-19)

The owner instructed the assistant to decide the remaining Phase 1 questions
("این تصمیمات رو خودت بگیر"). These are recorded as the owner's delegation plus
the assistant's proposal, not as independent owner review. Items touching law or
privacy are **development defaults** pending DEC-026 legal review and must be
revisited before RELEASE-001. Any item can be reversed by the owner.

- **DEC-022 (remainder, authentication policy).** Email + password (owner
  approved). Passwords hashed with stdlib scrypt (no new dependency). Sessions:
  opaque 32-byte random token, stored hashed (SHA-256), HttpOnly SameSite=Lax
  cookie (Secure in production), 14-day absolute and 24-hour idle limits,
  logout revokes, password change revokes other sessions. CSRF: token header on
  unsafe methods plus Origin check. Password policy: 10–128 characters, no
  composition rules, rejects the email local part and a small denylist.
  Brute-force: 5 failures in 15 minutes lock the account for 15 minutes.
  Recovery: single-use hashed token, 1-hour expiry, responses never reveal
  whether an email exists, all sessions revoked on reset; real delivery is
  blocked on DEC-010. Email verification is a setting (off in dev/test, on in
  production). MFA and phone/SMS login are deferred. IP addresses are not stored.
- **DEC-017 (tenant, roles, invitations).** The organization is the tenant;
  registration creates a personal organization owned by the user. Organization
  roles: owner/admin/member. A project belongs to exactly one organization.
  Project roles: owner, architect, structural_engineer, mep_engineer,
  quantity_surveyor; system administrator is a platform flag on users, never a
  project role. Invitations use a hashed single-use token valid 7 days, shown as
  a link until a mailer exists (DEC-010). Only the organization owner may export
  or delete organization data.
- **DEC-016 (archive part only).** Archiving is a soft state (`archived_at`,
  `archived_by`); archived projects are hidden from active lists, read-only,
  visible through an archived filter to organization owners/admins and the
  project owner, and can be restored. No automatic deletion in Phase 1.
  Retention periods, hard deletion, encryption at rest, and backup RPO/RTO stay
  OPEN pending DEC-026.
- **DEC-003 (first project types).** residential_house, residential_apartment,
  commercial, mixed_use, other; single-family residential is the first
  acceptance scenario. Assistant assumption; more types need only a migration.
- **DEC-023 (formats and requirements answered by the owner, 2026-11-24; scanner, retention
  and encryption stay OPEN).** Allowed: PDF, DXF, DWG, IFC, XLSX (and XLS, CSV), DOCX (and
  DOC), plus PNG/JPEG/WebP; macro files (DOCM, XLSM) excluded for now. Detected from the
  file bytes with a matching extension; per-type size limits (25 MiB documents, 50 MiB
  CAD/BIM, development defaults) and 100 files per project. The owner also requires
  extraction, cross-file reconciliation and versioning later, and that the software never
  depends on uploads (see docs/FILE_REQUIREMENTS_GAP_ANALYSIS.md). Files are stored privately (not served statically) and
  downloaded only through an authorized endpoint. The built-in scanner flags the EICAR
  test signature and PDFs with active content into quarantine, but is not an antivirus:
  outside development a clean verdict is not granted and files stay pending until a real
  scanner is selected. CAD/BIM formats (DEC-004), extraction (AI-002/DEC-027), retention
  periods and encryption at rest remain undecided.

- **DEC-010 (partly answered by the owner, 2026-11-23).** Account confirmation and
  password recovery go through email. Delivery is plain SMTP, so any provider can be
  used by configuration (still to be chosen and contracted by the owner; nothing is
  provider specific in code). Subscription payment will use the Zibal gateway
  (Phase 10, BILL-003); the owner holds the Zibal merchant code. It is a server-side
  secret: it must never be committed, put in the frontend, or pasted in chat. Nothing
  of Zibal is built in Phase 1. Still open under DEC-010: SMS provider, AI provider,
  and the legal/contract review of the gateway and the mail provider.
