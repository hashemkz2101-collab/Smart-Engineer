#!/usr/bin/env bash
# One-time setup of a fresh Codespace: tools and locked dependencies. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")/../.."

UV_VERSION="0.13.8"   # same as CI
if ! command -v uv >/dev/null 2>&1 || [ "$(uv --version | awk '{print $2}')" != "$UV_VERSION" ]; then
  python3 -m pip install --user --break-system-packages "uv==$UV_VERSION" 2>/dev/null \
    || pip install --user "uv==$UV_VERSION"
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "== Python $(cat .python-version) and API dependencies"
uv python install "$(cat .python-version)"
uv sync --locked --all-packages

echo "== Web dependencies (Node $(node --version))"
pnpm install --frozen-lockfile

echo "== Setup finished. Start everything with: scripts/dev/up.sh"
