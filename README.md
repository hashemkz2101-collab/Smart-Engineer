# Smart Engineer

Smart Engineer is a proposed bilingual (Persian/English) web platform for
building-project design, engineering coordination, quantity takeoff, estimating,
and project documentation in Iran.

## Approved architecture baseline

The approved P0-01 direction is a **Next.js + TypeScript** frontend, a
**FastAPI + Python** backend, and **PostgreSQL**, organized as a **Modular
Monolith**. The frontend and backend communicate through a **REST API documented
with OpenAPI**.

The workspace pins Next.js 16.4.6, React/React DOM 19.3.1, TypeScript 5.9.3,
FastAPI 0.163.0, Node.js 24.22.3, Python 3.14.10, pnpm 12.16.1, and uv 0.13.8.
These are reproducible development-tool and dependency baselines, not evidence
that the architecture has been implemented. Hosting, database provisioning,
deployment, and other open decisions remain unselected.

The application shell currently includes the P0-03 minimal FastAPI API and the
P0-04 Persian-first Next.js frontend shell. It does not include database
integration, schema, migrations, authentication, or engineering features.
Phase 0 remains in progress; registered feature statuses remain unchanged and
the broader phase acceptance criteria are not yet complete.

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
