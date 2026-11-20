# Phase 1 plan — product core and project management

Status: in progress. Decisions: see OPEN_DECISIONS.md (Phase 1 section).
Feature statuses in FEATURE_REGISTRY.md are not changed by this plan.

## Increments
| ID | Scope | Features | State |
|----|-------|----------|-------|
| P1-01 | Identity/organization/project data model, migration 0003 | foundation for IAM-001/002, ROLE-001, PRJ-001/002 | in review |
| P1-02 | Auth backend: register, login, logout, sessions, CSRF, lockout, recovery (delivery blocked on DEC-010) | IAM-001 | planned |
| P1-03 | Organizations, memberships, invitations, role checks | IAM-002, ROLE-001 | planned |
| P1-04 | Project create/list/read/update/archive/restore with audit events | PRJ-001, PRJ-002 | planned |
| P1-05 | Persian RTL frontend for the above | IAM/PRJ | planned |
| P1-06+ | Input forms, site, requirements, files (DEC-023), security | INP, SITE, REQ, FILE-001, SEC-002 | planned |

## Data model (P1-01)
users, organizations, memberships, projects, project_members. Foreign keys
never cascade deletes; archived projects keep `status='archived'` with
`archived_at` set (database CHECK). Emails are lowercase and unique.

## Rules
Every dependent record carries project_id (and organization_id where needed).
Each increment ships with tests that run on SQLite and PostgreSQL, and is
accepted only on real CI evidence.
