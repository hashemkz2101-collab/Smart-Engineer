# Phase 1 plan — product core and project management

Status: in progress; current core stabilization is recorded in
[PHASE_1_STABILIZATION.md](PHASE_1_STABILIZATION.md). On 2026-11-25 the owner
explicitly authorized starting Phase 2 after stabilizing the current core, without
rerunning the earlier tests. This is not acceptance of missing Phase 1 features.
Decisions: see OPEN_DECISIONS.md (Phase 1 section).
Feature statuses in FEATURE_REGISTRY.md are not changed by this plan.

## Increments
| ID | Scope | Features | State |
|----|-------|----------|-------|
| P1-01 | Identity/organization/project data model, migration 0003 | foundation for IAM-001/002, ROLE-001, PRJ-001/002 | in review |
| P1-02 | Auth backend: register, login, logout, sessions, CSRF, lockout, recovery (delivery blocked on DEC-010) | IAM-001 | merged (backend only; email delivery pending DEC-010) |
| P1-03 | Organizations, memberships, invitations, role checks | IAM-002, ROLE-001 | merged (backend only) |
| P1-04 | Project create/list/read/update/archive/restore with audit events | PRJ-001, PRJ-002 | merged (backend only) |
| P1-05 | Persian RTL frontend for the above | IAM/PRJ | merged (UI tested against a mocked API; not yet run against the real API by the owner) |
| P1-06 | Full-stack CI run: real web + API + PostgreSQL, unmocked workflows | IAM-001/002, PRJ-001/002, FLOW-001 | merged |
| P1-07 | Staged project intake: identity, location, people, land-status notes | INP-001, INP-002 | merged |
| P1-08 | Site/land data: parcel geometry and area report, access/orientation, terrain, surroundings, optional soil | SITE-001, SITE-002 | merged |
| P1-09 | Zoning/building-control inputs with source, date and verification; unverified values stay unknown / needs inquiry | RULE-DATA-001 | merged |
| P1-10 | Client requirements: space program, preferences/constraints, reference examples (label + explanation + link) | REQ-001, REQ-002, REQ-003 | merged |
| P1-11 | Environmental and technical conditions with source, location and date | ENV-001 | merged |
| P1-12 | Project file attachments: type/size/count limits, private storage, quarantine, authorized download (DEC-023 development defaults) | FILE-001, SEC-002 | merged |
| P1-13 | System administration: user list/search, activate/deactivate, system-admin grant/revoke, project access management (metadata and roles only), append-only admin audit log, command-line bootstrap of the first administrator | ADMIN-001 | merged |
| P1-14 | Project invitations (FLOW-001 refinement): owner invites an outsider by email straight into a project with a bounded project role; no access before acceptance; every step recorded in project activity | FLOW-001 | merged |
| P1-15 | Hardening: defensive security headers on API and web (CSP frame/base/form/object limits, nosniff, no-store for API, HSTS in production), tracked-file secret scan in CI | SEC-001, SEC-005 | merged |
| P1-16 | Email authentication (DEC-010 owner answer): SMTP delivery, email verification at registration and resend, recovery email, production fails closed without a mail server | IAM-001, BILL-001 | merged |
| P1-17 | Invitation emails: organization and project invitations are emailed (the one-time link is still shown to the inviter as a fallback) | FLOW-001, IAM-001 | merged |
| P1-19 | File formats and upload safety (DEC-023 owner decisions): DXF, DWG, IFC, XLSX/XLS/CSV, DOCX/DOC by content; macro files and unsafe archives refused; embedded/linked Office content quarantined; per-type size limits | FILE-001, SEC-002 | merged |
| P1-20 | File versions: new versions keep earlier ones with uploader and time, restore as a new version, recorded-fact comparison, takeoff basis marker (owner and quantity surveyor) with a stale warning when a newer version exists (FILE-002) | FILE-002 | merged |
| P1-21 | Real malware scanning through ClamAV on the owner's server, fail closed, rescan command (SEC-002, DEC-023) | SEC-002 | merged |
| P1-22 | PostgreSQL and MySQL/MariaDB support through `SMART_ENGINEER_DATABASE_URL`; migrations and tests on both engines (ADR-0002) | — | merged |
| P1-23 | GitHub Codespaces trial environment: throwaway database, demo accounts, API and web on forwarded ports | — | merged |
| P1-24+ | Later AI features and remaining hardening (see CHANGELOG) | — | planned |

## Data model (P1-01)
users, organizations, memberships, projects, project_members. Foreign keys
never cascade deletes; archived projects keep `status='archived'` with
`archived_at` set (database CHECK). Emails are lowercase and unique.

## Rules
Every dependent record carries project_id (and organization_id where needed).
Each increment ships with tests that run on SQLite and PostgreSQL, and is
accepted only on real CI evidence.
