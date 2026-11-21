# Phase 1 plan — product core and project management

Status: in progress. Decisions: see OPEN_DECISIONS.md (Phase 1 section).
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
| P1-08 | Site/land data: parcel geometry and area report, access/orientation, terrain, surroundings, optional soil | SITE-001, SITE-002 | in review |
| P1-09+ | Zoning inputs (RULE-DATA), requirements (REQ), files (DEC-023), security | RULE-DATA, REQ, FILE-001, SEC-002 | planned |

## Data model (P1-01)
users, organizations, memberships, projects, project_members. Foreign keys
never cascade deletes; archived projects keep `status='archived'` with
`archived_at` set (database CHECK). Emails are lowercase and unique.

## Rules
Every dependent record carries project_id (and organization_id where needed).
Each increment ships with tests that run on SQLite and PostgreSQL, and is
accepted only on real CI evidence.
