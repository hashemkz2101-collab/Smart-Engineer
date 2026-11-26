# Smart Engineer

Smart Engineer is a proposed bilingual (Persian/English) web platform for
building-project design, engineering coordination, quantity takeoff, estimating,
and project documentation in Iran.

## Approved architecture baseline

The approved P0-01 direction is a **Next.js + TypeScript** frontend, a
**FastAPI + Python** backend, and **PostgreSQL or MySQL/MariaDB** (chosen per
installation, ADR-0002), organized as a **Modular
Monolith**. The frontend and backend communicate through a **REST API documented
with OpenAPI**.

The workspace pins Next.js 16.4.6, React/React DOM 19.3.1, TypeScript 5.9.3,
FastAPI 0.163.0, Node.js 24.22.3, Python 3.14.10, pnpm 12.16.1, and uv 0.13.8.
These are reproducible development-tool and dependency baselines, not evidence
that the architecture has been implemented. Hosting, database provisioning,
deployment, and other open decisions remain unselected.

The application currently includes the FastAPI API foundation (settings,
structured logging with correlation IDs, a safe error envelope, a versioned
`/api/v1` route, SQLAlchemy/Alembic migrations with two operational tables,
feature-flag and job-lifecycle services) and the Persian-first Next.js frontend
shell, with lint, unit, integration, and browser tests in CI. It does not
include authentication, project data, or engineering features. Phase 0 remains
in progress; registered feature statuses remain unchanged and the broader phase
acceptance criteria are not yet complete (see
[`docs/PHASE_0_CLOSURE.md`](docs/PHASE_0_CLOSURE.md)).

## Development workspace

- `apps/web` is the pnpm-managed Next.js/TypeScript workspace package.
- `apps/api` is the uv-managed Python workspace package and declares FastAPI.
- `pnpm-lock.yaml` and `uv.lock` pin the dependency resolutions. Use the
  frozen/locked install commands below; do not update lockfiles during a
  reproducible install.

### Run the API locally

From the repository root, synchronize the locked workspace dependencies:

```bash
uv sync --locked --all-packages
```

Start the API bound to the local machine only:

```bash
uv run --package smart-engineer-api --group dev uvicorn --app-dir apps/api --reload --host 127.0.0.1 --port 8000 smart_engineer_api.main:app
```

The health endpoint is at `http://127.0.0.1:8000/health`. Interactive
documentation is at `http://127.0.0.1:8000/docs`, and the OpenAPI schema is at
`http://127.0.0.1:8000/openapi.json` (`/redoc` is also available by default).
The health response contains only `{"status":"ok"}` and does not check a
database or expose configuration. `/health` is the unversioned liveness probe;
versioned API routes live under `/api/v1` (currently `GET /api/v1/health`).

Settings are read from the process environment (see `.env.example`, which is a
template and is not loaded automatically): `SMART_ENGINEER_ENV`
(`development`/`test`/`production`) and `SMART_ENGINEER_LOG_LEVEL`
(`DEBUG`…`CRITICAL`). Invalid values stop startup with an explicit error.

Every response carries an `X-Correlation-ID` header. A valid incoming value
(1–64 letters, digits, `.`, `_`, `-`) is reused; otherwise one is generated.
Logs are JSON lines on stderr that include the correlation ID; query strings
are never logged. Errors use one envelope,
`{"error": {"code", "message", "correlation_id"}}`; unhandled errors return a
generic 500 with no stack trace, and the full traceback is logged server-side.

### Authentication API (P1-02, backend only)

Endpoints under `/api/v1/auth`: `register`, `login`, `me`, `logout`,
`change-password`, `password-reset/request`, `password-reset/confirm`. They need
`SMART_ENGINEER_DATABASE_URL` (otherwise they return 503). The session is an
HttpOnly `se_session` cookie (Secure in production); state-changing requests that
use the session must send the `X-CSRF-Token` value returned by `login`/`me`.
A browser `Origin` that is not the API's own host is rejected unless listed in
`SMART_ENGINEER_ALLOWED_ORIGINS` (comma-separated, e.g. `http://localhost:3000`).
Also: `email-verification/request` (always answers 202; a repeat inside 60 seconds is
ignored) and `email-verification/confirm`. Registration sends a confirmation link when
email verification is required (production), and login stays refused until the link
is used (24 hours, single use).

Email is sent over any SMTP server (DEC-010): set `SMART_ENGINEER_SMTP_HOST`,
`SMART_ENGINEER_MAIL_FROM` and `SMART_ENGINEER_PUBLIC_URL` (the site's address, used in
links), plus `SMART_ENGINEER_SMTP_PORT` (default 587), `SMART_ENGINEER_SMTP_SECURITY`
(`starttls` default, `ssl`, `none`), `SMART_ENGINEER_SMTP_USERNAME` and
`SMART_ENGINEER_SMTP_PASSWORD`. Without them, development and tests keep messages in
memory only, and production refuses to start (verified email is required there).
Delivery failures are logged without the address or token and never shown to the caller.

Uploaded files are scanned by ClamAV running on your own server (SEC-002, DEC-023): install
`clamav-daemon`, set `StreamMaxLength 60M` in `clamd.conf` (files may be up to 50 MiB), keep
signatures fresh with `freshclam`, and point the API at it with `SMART_ENGINEER_CLAMAV_HOST`
and `SMART_ENGINEER_CLAMAV_PORT` (or `SMART_ENGINEER_CLAMAV_SOCKET`). Bind clamd to localhost or
a private network only; it has no authentication. If the scanner is unreachable the file stays
`pending` and is never served; run `python -m smart_engineer_api.manage rescan-files` (for
example from cron) to scan pending files once it is back. Without a scanner, production keeps
every upload pending.
Organization and project invitations are emailed too (the inviter also still gets the link).

### Running the web app together with the API (development)

The web app proxies `/api/*` to the API (default `http://127.0.0.1:8000`, override
with `SMART_ENGINEER_API_ORIGIN` when building/starting the web app). Start the API
with a database and allow the web origin, for example:

```bash
SMART_ENGINEER_DATABASE_URL=sqlite:///dev.db \
SMART_ENGINEER_ALLOWED_ORIGINS=http://127.0.0.1:3000 \
uv run --package smart-engineer-api --group dev uvicorn --app-dir apps/api --host 127.0.0.1 --port 8000 smart_engineer_api.main:app
```

Run the migrations first (see below). Pages: `/register`, `/login`, `/projects`,
`/organization`. The browser tests use a mocked API (they check the interface, not
the backend); a full web + API + database run is a manual check for now.

### Try it in a browser (GitHub Codespaces)

Create a Codespace on this repository and the app starts by itself with demo accounts; see
[docs/CODESPACES.md](docs/CODESPACES.md). The same scripts work on any Linux machine with
Docker: `scripts/dev/setup.sh` once, then `scripts/dev/up.sh`.

### Database migrations

The database URL comes from `SMART_ENGINEER_DATABASE_URL`: PostgreSQL
(`postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME`) or MySQL/MariaDB
(`mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME`); setup details, requirements and
limits of each are in [docs/DATABASES.md](docs/DATABASES.md). It is not needed to run
the API or its health endpoints. To apply or roll back migrations, from the
repository root:

```bash
uv run --package smart-engineer-api alembic -c apps/api/alembic.ini upgrade head
uv run --package smart-engineer-api alembic -c apps/api/alembic.ini downgrade base
```

The migration tests run on SQLite by default. To also run them against your own
disposable PostgreSQL database (they drop its tables), set
`SMART_ENGINEER_TEST_DATABASE_URL`; for MySQL or MariaDB set
`SMART_ENGINEER_TEST_MYSQL_DATABASE_URL`. A database whose variable is not set is reported
as skipped, never as passed. CI runs PostgreSQL 17, MySQL 8.0 and MariaDB 10.11. How a
database should be run during development is still undecided (DEC-009).

Run the API tests from the repository root:

```bash
uv run --package smart-engineer-api --group dev python -m unittest discover -s apps/api/tests -t apps/api
```

Windows setup and execution have not been tested; verification remains
outstanding under DEC-031.

### Run the frontend

From the repository root, start the development server on the local machine:

```bash
pnpm --filter @smart-engineer/web run dev
```

Open `http://127.0.0.1:3000`. The initial interface is Persian and right-to-left;
its light/dark theme follows the operating-system preference until a user
selects a theme, which is remembered in local storage.

Run the TypeScript check and production build with:

```bash
pnpm --filter @smart-engineer/web run typecheck
pnpm --filter @smart-engineer/web run build
```

To run the HTTP smoke tests, keep the development server running in one
terminal and run this command from the repository root in another:

```bash
pnpm --filter @smart-engineer/web run test
```

The smoke tests target `http://127.0.0.1:3000` by default. Windows frontend
installation, execution, and UI behavior have not been tested locally.

To run the same checks as CI (build, then start the production server, run the
smoke tests, and stop the server automatically), run from the repository root:

```bash
pnpm --filter @smart-engineer/web run build
pnpm --filter @smart-engineer/web run test:ci
```

The GitHub Actions workflow in `.github/workflows/ci.yml` runs the API tests and
these web steps on Ubuntu and Windows runners. Its results become evidence only
once a run is recorded.

### Lint and browser tests

```bash
uv run --package smart-engineer-api --group dev ruff check apps/api
pnpm --filter @smart-engineer/web run lint
```

Browser tests use Playwright with Chromium against the production build. Install
the browser once, then build and run (from the repository root):

```bash
pnpm --filter @smart-engineer/web exec playwright install chromium
pnpm --filter @smart-engineer/web run build
pnpm --filter @smart-engineer/web run test:e2e
```

They check the RTL layout at several widths, keyboard operation, the theme
toggle, and automated accessibility scans (axe-core). Automated scans do not
replace manual screen-reader and real-device testing.

### GitHub Codespaces / Linux

Install or select the pinned Node.js runtime with nvm, then install the pinned
Python runtime and uv:

```bash
nvm install 24.22.3
nvm use 24.22.3
python3 -m pip install --user uv==0.13.8
uv python install 3.14.10
```

In a new shell, ensure the selected Node.js is active, then prepare dependencies:

```bash
npm install --global pnpm@12.16.1
node --version
pnpm --version
uv --version
uv python find 3.14.10
pnpm install --frozen-lockfile
uv sync --locked --all-packages
```

### Windows PowerShell

Download and install the exact official Node.js MSI and Python installer, then
install the pinned package managers. The downloads are versioned, official
release URLs:

```powershell
Invoke-WebRequest https://nodejs.org/dist/v24.22.3/node-v24.22.3-x64.msi -OutFile node-v24.22.3-x64.msi
Start-Process msiexec.exe -Wait -ArgumentList '/i', '.\node-v24.22.3-x64.msi', '/qn'
Invoke-WebRequest https://www.python.org/ftp/python/3.14.10/python-3.14.10-amd64.exe -OutFile python-3.14.10-amd64.exe
Start-Process .\python-3.14.10-amd64.exe -Wait -ArgumentList '/quiet', 'InstallAllUsers=0', 'PrependPath=1', 'Include_launcher=1'
```

Open a new PowerShell window so the installers' PATH updates take effect:

```powershell
node --version
npm install --global pnpm@12.16.1
$env:PATH = "$(npm config get prefix);$env:PATH"
pnpm --version
py -3.14 -m pip install --user uv==0.13.8
$uvScripts = py -3.14 -c "import sysconfig; print(sysconfig.get_path('scripts', 'nt_user'))"
$env:PATH = "$uvScripts;$env:PATH"
uv --version
uv python install 3.14.10
uv python find 3.14.10
pnpm install --frozen-lockfile
uv sync --locked --all-packages
```

### Windows validation script

After installing the tools by hand (above), `scripts/windows-validate.ps1` runs
the Phase 0 Windows checks (dependency install, lint, API tests, web build and
tests, browser tests, migrations, live API check) and writes a report:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\windows-validate.ps1
```

See `docs/PHASE_0_CLOSURE.md` (section 6) for what it covers and does not cover.

### Verify resolved framework versions

Run these commands from the repository root after installing dependencies:

```bash
pnpm --filter @smart-engineer/web exec next --version
pnpm --filter @smart-engineer/web exec tsc --version
pnpm --filter @smart-engineer/web exec node -p "require('react/package.json').version"
pnpm --filter @smart-engineer/web exec node -p "require('react-dom/package.json').version"
uv run --package smart-engineer-api --locked python -c "import fastapi; print(fastapi.__version__)"
```

The same verification commands work in PowerShell. Expected outputs, in order:
`16.4.6`, `Version 5.9.3`, `19.3.1`, `19.3.1`, and `0.163.0`.

No personal computer or permanent server needs to stay on for initial
development. A developer can work in a Codespace during active sessions; this
baseline does not require hosting or a continuously running service.

## Documentation

- [`SMART_ENGINEER_MASTER_SPEC.md`](SMART_ENGINEER_MASTER_SPEC.md) is the
  product-scope source of truth.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) defines the gated Phase 0–10 roadmap.
- [`docs/PHASE_STATUS.md`](docs/PHASE_STATUS.md) records phase status.
- [`docs/PHASE_0_CLOSURE.md`](docs/PHASE_0_CLOSURE.md) is the Phase 0 closure
  readiness review, Windows validation steps, and owner sign-off record.
- [`docs/FEATURE_REGISTRY.md`](docs/FEATURE_REGISTRY.md) lists stable feature
  IDs and dependencies.
- [`docs/FEATURE_ACCEPTANCE.md`](docs/FEATURE_ACCEPTANCE.md) defines planned,
  feature-specific acceptance tests.
- [`docs/REQUIREMENT_TRACEABILITY.md`](docs/REQUIREMENT_TRACEABILITY.md) maps
  specification requirements to feature IDs and phases.
- [`docs/OPEN_DECISIONS.md`](docs/OPEN_DECISIONS.md) tracks unresolved
  decisions; P0-02 does not close any of them.
- [`docs/ARCHITECTURE_OVERVIEW.md`](docs/ARCHITECTURE_OVERVIEW.md) records the
  approved architecture baseline and its scope.
- [`docs/adr/ADR-0001-approved-architecture-baseline.md`](docs/adr/ADR-0001-approved-architecture-baseline.md)
  records the P0-01 architecture decision.
- [`docs/OUTPUT_STATUS_LIFECYCLE.md`](docs/OUTPUT_STATUS_LIFECYCLE.md) defines
  the proposed output review-state workflow, subject to recorded legal and
  professional authority decisions.
- [`docs/DOCUMENTATION_POLICY.md`](docs/DOCUMENTATION_POLICY.md) defines update
  and traceability requirements.
- [`CHANGELOG.md`](CHANGELOG.md) records notable documentation and product
  changes; entries do not imply feature implementation.
