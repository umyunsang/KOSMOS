#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

if [[ -d /opt/homebrew/opt/bun/bin ]]; then
  export PATH="/opt/homebrew/opt/bun/bin:$PATH"
fi
if [[ -d /opt/homebrew/opt/uv/bin ]]; then
  export PATH="/opt/homebrew/opt/uv/bin:$PATH"
fi

if [[ -n "${UMMAYA_DEMO_BIN:-}" ]]; then
  exec "$UMMAYA_DEMO_BIN"
fi

if [[ -x "$ROOT_DIR/node_modules/.bin/ummaya" ]]; then
  exec "$ROOT_DIR/node_modules/.bin/ummaya"
fi

exec "$ROOT_DIR/bin/ummaya"
