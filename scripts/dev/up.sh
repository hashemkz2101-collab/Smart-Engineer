#!/usr/bin/env bash
# Starts everything needed to try Smart Engineer in a browser: a throwaway database,
# migrations, demo accounts, the API (0.0.0.0:8000) and the web app (0.0.0.0:3000).
#
#   scripts/dev/up.sh                      # PostgreSQL, production-mode web (default)
#   scripts/dev/up.sh --db mysql           # MySQL instead
#   scripts/dev/up.sh --db sqlite          # no Docker needed
#   scripts/dev/up.sh --web dev            # Next.js dev server (hot reload, slower first load)
#   scripts/dev/up.sh --rebuild            # rebuild the web app after changing code
# Defaults can also come from SMART_ENGINEER_DEV_DB and SMART_ENGINEER_DEV_WEB.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p .dev

DB="${SMART_ENGINEER_DEV_DB:-postgres}"
WEB="${SMART_ENGINEER_DEV_WEB:-prod}"
REBUILD=0
while [ $# -gt 0 ]; do
  case "$1" in
    --db) DB="$2"; shift 2 ;;
    --web) WEB="$2"; shift 2 ;;
    --rebuild) REBUILD=1; shift ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done
case "$DB" in postgres|mysql|sqlite) ;; *) echo "--db must be postgres, mysql or sqlite" >&2; exit 2 ;; esac
case "$WEB" in prod|dev) ;; *) echo "--web must be prod or dev" >&2; exit 2 ;; esac

if [ "${SMART_ENGINEER_ENV:-development}" = "production" ]; then
  echo "Refusing to run: SMART_ENGINEER_ENV=production. This script is for local trials only." >&2
  exit 2
fi

"$ROOT/scripts/dev/down.sh" --services-only >/dev/null 2>&1 || true

# --- Throwaway database (never an existing one: the URL is built here, not read) --------
unset SMART_ENGINEER_DATABASE_URL
if [ "$DB" != "sqlite" ] && ! docker info >/dev/null 2>&1; then
  echo "Docker is not available here; using SQLite instead (data stays in .dev/)." >&2
  DB=sqlite
fi
case "$DB" in
  postgres)
    docker compose -f dev/docker-compose.yml --profile postgres up -d --wait postgres
    export SMART_ENGINEER_DATABASE_URL="postgresql+psycopg://smart_engineer:dev_only_password@127.0.0.1:5432/smart_engineer_dev" # secret-scan:allow
    ;;
  mysql)
    docker compose -f dev/docker-compose.yml --profile mysql up -d --wait mysql
    export SMART_ENGINEER_DATABASE_URL="mysql+pymysql://smart_engineer:dev_only_password@127.0.0.1:3306/smart_engineer_dev" # secret-scan:allow
    ;;
  sqlite)
    export SMART_ENGINEER_DATABASE_URL="sqlite:///$ROOT/.dev/smart_engineer_dev.db"
    ;;
esac

# --- Where the browser will open the site -----------------------------------------------
if [ -n "${CODESPACE_NAME:-}" ]; then
  WEB_URL="https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
else
  WEB_URL="http://localhost:3000"
fi
export SMART_ENGINEER_ENV=development
export SMART_ENGINEER_ALLOWED_ORIGINS="$WEB_URL,http://localhost:3000,http://127.0.0.1:3000"
export SMART_ENGINEER_FILE_STORAGE_DIR="$ROOT/.dev/files"
export SMART_ENGINEER_API_ORIGIN="http://127.0.0.1:8000"
export SMART_ENGINEER_DEV_ORIGINS="*.app.github.dev,*.githubpreview.dev"
export PYTHONPATH="$ROOT/apps/api"
API=(uv run --package smart-engineer-api --group dev)

echo "== Applying database migrations ($DB)"
"${API[@]}" alembic -c apps/api/alembic.ini upgrade head
echo "== Demo accounts"
"${API[@]}" python -m smart_engineer_api.manage seed-demo

wait_for() { # url, seconds, name
  for _ in $(seq 1 "$2"); do
    if curl -fsS -o /dev/null "$1" 2>/dev/null; then return 0; fi
    sleep 1
  done
  echo "$3 did not become ready; see the log in .dev/" >&2
  return 1
}

echo "== Starting the API on 0.0.0.0:8000"
setsid nohup "${API[@]}" uvicorn --app-dir apps/api --host 0.0.0.0 --port 8000 \
  smart_engineer_api.main:app >.dev/api.log 2>&1 &
echo $! >.dev/api.pid
wait_for "http://127.0.0.1:8000/health" 90 "The API"

echo "== Starting the web app on 0.0.0.0:3000 ($WEB mode)"
if [ "$WEB" = "prod" ]; then
  if [ "$REBUILD" = 1 ] || [ ! -f apps/web/.next/BUILD_ID ]; then
    pnpm --filter @smart-engineer/web build
  fi
  setsid nohup pnpm --filter @smart-engineer/web exec next start --hostname 0.0.0.0 --port 3000 \
    >.dev/web.log 2>&1 &
else
  setsid nohup pnpm --filter @smart-engineer/web exec next dev --hostname 0.0.0.0 --port 3000 \
    >.dev/web.log 2>&1 &
fi
echo $! >.dev/web.pid
wait_for "http://127.0.0.1:3000/" 180 "The web app"

cat >.dev/urls.txt <<URLS

  Smart Engineer is running.

  Open this in your browser (phone or computer):
      $WEB_URL

  Demo accounts (password for all: Demo Password 2026 Local):
      owner@demo.smart-engineer.test       project owner
      architect@demo.smart-engineer.test   architect
      structural@demo.smart-engineer.test  structural engineer
      qs@demo.smart-engineer.test          quantity surveyor
      admin@demo.smart-engineer.test       system administrator (/admin)
  Or register your own account on the sign-up page.

  Database: $DB (throwaway)   Logs: .dev/api.log, .dev/web.log
  Stop: scripts/dev/down.sh     Fresh data: scripts/dev/down.sh --reset

URLS
cat .dev/urls.txt
