# ADR-0002: PostgreSQL and MySQL/MariaDB support

- **Status:** Accepted by the project owner (instruction of 2026-11-25).
- **Relation to ADR-0001:** ADR-0001 records PostgreSQL as the approved database direction.
  That decision is not withdrawn: PostgreSQL stays fully supported and is the engine used by
  the full-stack browser tests. This ADR adds MySQL/MariaDB as a second, equally supported
  engine.

## Why

The owner's current hosting offers MySQL/MariaDB (cPanel) while a future server may offer
PostgreSQL. The same source must run on either without rewriting application logic.
(Note: the shared cPanel host examined on 2026-11-24 also lacks the required Python 3.14 and
Node 24, so MySQL support alone does not make that host usable; see docs/DATABASES.md.)

## Decision

- Both **PostgreSQL** and **MySQL/MariaDB** are officially supported.
- The engine is chosen only by `SMART_ENGINEER_DATABASE_URL`:
  `postgresql+psycopg://...` or `mysql+pymysql://...`. SQLite stays for development and
  tests only and is refused in production.
- Each installation has **one** primary database. There is no replication or
  synchronization between engines.
- SQLAlchemy and Alembic remain the shared access and migration layer. Models, services and
  the API are not duplicated per engine.
- Driver: **PyMySQL** (pure Python, no C libraries, so it installs on any host). The
  `mysql://` (mysqlclient) scheme is rejected on purpose.

## How real differences are handled

| Difference | Handling |
|---|---|
| Time zones | One policy: every timestamp is stored as UTC and read back as an aware UTC `datetime` (`db/types.py`). MySQL sessions are set to `+00:00`; columns are `DATETIME(6)` and server defaults `CURRENT_TIMESTAMP(6)` (`db/mysql_compat.py`), so microsecond precision matches PostgreSQL. |
| Text comparison | MySQL is case-insensitive by default. Migrations set the database default to `utf8mb4_bin` before creating tables, giving PostgreSQL-like case-sensitive keys and checks. |
| Character set | `utf8mb4` on every connection (Persian text and emoji). |
| UUID | SQLAlchemy `Uuid`: native on PostgreSQL, `CHAR(32)` on MySQL; values are identical in Python. |
| JSON | SQLAlchemy `JSON`: `jsonb`/`json` on PostgreSQL, `JSON` on MySQL, text-backed on MariaDB. No JSON-specific query operators are used. |
| CHECK constraints | Kept as is. They require MySQL 8.0.16+ or MariaDB 10.2.1+ (older MySQL ignores them silently). A failed check is reported as the same integrity error on every engine. |
| Strictness | MySQL sessions add `STRICT_ALL_TABLES` so oversized or invalid values fail instead of being truncated; InnoDB is forced. |
| Migrations | One chain for both engines. Where MySQL differs (it will not drop an index a foreign key needs), the migration order was changed in a way that is equivalent on PostgreSQL and SQLite. No engine-specific migration branches were needed. |

## Verified and not verified

- Verified in CI: the full API test suite, including migrations up and down, schema/model
  equality, UUID/JSON/time/Persian round trips, constraints, transactions and the account,
  organization, project, file and access-control tests, on PostgreSQL 17, MySQL 8.0 and
  MariaDB 10.11.
- Not verified: the full-stack browser tests run on PostgreSQL only; MySQL 5.7, MariaDB 10.5
  or older and MySQL 8.4+ with `caching_sha2_password` over plain TCP (needs PyMySQL's
  optional `cryptography` package or TLS) have not been tested; real cPanel hosts;
  production load behaviour.
- Moving data between engines is not implemented (docs/DATABASES.md describes the design).
