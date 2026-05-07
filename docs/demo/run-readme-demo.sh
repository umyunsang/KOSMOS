#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

clear
cd "$ROOT_DIR/tui"

export UMMAYA_FRIENDLI_TOKEN="sk-readme-demo"
export UMMAYA_FRIENDLI_SESSION_ACTIVE="1"
export UMMAYA_ONBOARDING_AUTO_COMPLETE="1"
export UMMAYA_BACKEND_CMD="uv run python $ROOT_DIR/docs/demo/readme_scenario_backend.py"
export NODE_ENV="test"
export IS_DEMO="1"

exec bun src/entrypoints/cli.tsx
