#!/usr/bin/env bash
# Stops the API and web app. Options: --services-only (leave databases running),
# --reset (also delete the throwaway databases and uploaded demo files).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

for name in api web; do
  if [ -f ".dev/$name.pid" ]; then
    pid="$(cat ".dev/$name.pid")"
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    rm -f ".dev/$name.pid"
  fi
done

[ "${1:-}" = "--services-only" ] && exit 0

if docker info >/dev/null 2>&1; then
  if [ "${1:-}" = "--reset" ]; then
    docker compose -f dev/docker-compose.yml --profile postgres --profile mysql down -v
    rm -rf .dev/files .dev/smart_engineer_dev.db
    echo "Throwaway databases and demo files deleted."
  else
    docker compose -f dev/docker-compose.yml --profile postgres --profile mysql stop
  fi
fi
