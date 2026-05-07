# Real-Use Debug Infra Quickstart

Run the two regression scenarios locally with fixture/mock credentials or a local model fixture. Do not run live public-service API calls in CI.

```bash
KOSMOS_PTY_SAMPLE_FRAMES=1 \
  bun scripts/bun-pty-capture.ts \
  specs/2773-rollback-debug-infra/captures/hadan-emergency \
  specs/2773-rollback-debug-infra/scripts/hadan-emergency.bun-pty.ts

python scripts/tui-realuse-audit.py \
  specs/2773-rollback-debug-infra/captures/hadan-emergency \
  --expect-chain 'resolve_location,nmc_emergency_search' \
  --require-expanded-trace \
  --strict-frames
```

```bash
KOSMOS_PTY_SAMPLE_FRAMES=1 \
  bun scripts/bun-pty-capture.ts \
  specs/2773-rollback-debug-infra/captures/dadae-weather \
  specs/2773-rollback-debug-infra/scripts/dadae-weather.bun-pty.ts

python scripts/tui-realuse-audit.py \
  specs/2773-rollback-debug-infra/captures/dadae-weather \
  --expect-chain 'resolve_location,kma_forecast_fetch' \
  --require-expanded-trace \
  --strict-frames
```

The audit fails when:

- a recoverable `lat/lon` parameter error reaches the final answer without a visible `resolve_location -> lookup` retry,
- a tool error is present but raw PTY output lacks red/error ANSI styling,
- Ctrl+O expansion does not expose request/response trace fields,
- raw IPC JSON appears in the citizen-visible terminal,
- the capture contains only a final screen and no intermediate frames.

## Scenario Matrix

List the real-use matrix:

```bash
python scripts/tui-realuse-matrix.py --list
```

Dry-run the P0 command set without launching the TUI:

```bash
python scripts/tui-realuse-matrix.py --priority P0 --dry-run
```

Run one scenario:

```bash
python scripts/tui-realuse-matrix.py --id LOC-WEATHER-DADAE-001
```

The matrix intentionally spans lookup, `resolve_location`, verify, submit, subscribe, permission denial, UI command overlays, raw IPC leakage, and multi-turn contamination checks. It is derived from `eval/scenarios/national_ax_citizen_requests_v1.yaml` plus the adapter catalog in `docs/api/README.md`.
