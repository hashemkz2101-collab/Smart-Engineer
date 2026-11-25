# Databases

Smart Engineer supports **PostgreSQL** and **MySQL/MariaDB** (ADR-0002). Pick one per
installation with `SMART_ENGINEER_DATABASE_URL`; nothing else in the code or settings changes.

| Engine | URL | Minimum version | Driver |
|---|---|---|---|
| PostgreSQL | `postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME` | 14+ (CI: 17) | psycopg 3 (included) |
| MySQL | `mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME` | 8.0.16+ (CI: 8.0) | PyMySQL (included) |
| MariaDB | `mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME` | 10.5+ (CI: 10.11) | PyMySQL (included) |

Special characters in a password must be URL-encoded. Never commit or paste the real URL.

## PostgreSQL setup

```sql
CREATE USER smart_engineer WITH PASSWORD '...';
CREATE DATABASE smart_engineer OWNER smart_engineer;
```

## MySQL / MariaDB setup

```sql
CREATE DATABASE smart_engineer CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;
CREATE USER 'smart_engineer'@'%' IDENTIFIED BY '...';
GRANT ALL PRIVILEGES ON smart_engineer.* TO 'smart_engineer'@'%';
```

In cPanel use "MySQL Databases" (create database, user, add user with all privileges). The
migration tries to set the database default collation to `utf8mb4_bin` itself (case-sensitive
keys like PostgreSQL); if the account may not, it prints a warning and you should recreate the
database with that collation. MySQL 8 users created with the default `caching_sha2_password`
plugin need TLS, a Unix socket, or PyMySQL's `cryptography` package; the simplest fix is
`ALTER USER ... IDENTIFIED WITH mysql_native_password BY '...'`. MariaDB needs nothing extra.

## Migrations

Same commands for both (from the repository root):

```bash
uv run --package smart-engineer-api alembic -c apps/api/alembic.ini upgrade head
uv run --package smart-engineer-api alembic -c apps/api/alembic.ini downgrade base
```

Never run them against a database holding real data without a backup.

## Tests

Set `SMART_ENGINEER_TEST_DATABASE_URL` (PostgreSQL) and/or
`SMART_ENGINEER_TEST_MYSQL_DATABASE_URL` (MySQL/MariaDB) to **disposable** databases; the tests
drop all their tables. An engine whose variable is unset is reported as skipped.

## Hosting note (cPanel)

The API needs Python 3.14 and the web app Node 24. A shared cPanel host examined on
2026-11-24 offered Python 3.5 and Node 20 ("Setup Python App" is also WSGI-only while the API is
ASGI), so it can hold a MySQL database but cannot run the application. A VPS (or running the
stack locally) is needed for that, with either database.

## Moving data between engines (design only, not implemented)

Needs the owner's approval before any tool is written. Approach: export table by table in
dependency order through SQLAlchemy (not raw dumps) into a neutral file (JSON Lines per table,
UUIDs as 32-char hex, timestamps as UTC ISO-8601 with microseconds, JSON as JSON), import with
foreign keys deferred or in dependency order, then verify row counts and per-table checksums and
run the integrity checks. Risks: text collation differences (duplicates that differ only by case
cannot exist on MySQL with a case-insensitive database), the `alembic_version` row, file
storage (files live outside the database and must be copied separately), and large tables.
Always dry-run into an empty database and keep the source untouched.
