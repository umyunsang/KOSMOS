# Quickstart: Full TUI (Ink + React + Bun)

**Branch**: `287-tui-ink-react-bun`
**Audience**: KOSMOS contributor who wants to run the TUI locally, verify the IPC bridge, and exercise the permission-gauntlet + primitive renderers without touching live `data.go.kr` APIs.

---

## Prerequisites

- Bun v1.2.x (`curl -fsSL https://bun.sh/install | bash`)
- Python 3.12+ with `uv` (existing KOSMOS baseline)
- Terminal that supports truecolor + UTF-8 (kitty, alacritty, iTerm2, Konsole, macOS Terminal, gnome-terminal)
- macOS or Linux (Windows is best-effort only)
- For Korean IME testing: macOS Korean IME (built-in) OR Linux with fcitx5 / ibus + `korean-hangul` input method

---

## 1. Bootstrap the workspace

```bash
# From repo root
uv sync                              # Python side — unchanged baseline

cd tui/
bun install                          # TUI side — installs Ink 7, React 19.2, @inkjs/ui, zod
bun run gen:ipc                      # Regenerate tui/src/ipc/frames.generated.ts from Pydantic models
```

**IME fork gate**: If the ADR at `docs/adr/NNN-korean-ime-strategy.md` selected option (a), `package.json` will pin `"ink": "npm:@jrichman/ink@6.6.9"`. The `bun install` step verifies the ADR exists; absence → install fails with an explanatory error (FR-057, SC-1 gate).

---

## 2. Run the TUI against a fixture backend (no live APIs)

```bash
# Terminal 1 — serve a fixture JSONL stream as the "backend"
cd tui/
bun run tui:fixture specs/287-tui-ink-react-bun/../tests/fixtures/smoke/route-safety.jsonl
```

Expected result:

- TUI window renders the default theme within 2 s (User Story 1 Acceptance #1).
- Conversation shows a scripted 3-turn dialog with a `resolve_location` result (`<CoordPill />` + `<AdmCodeBadge />`), a `lookup` timeseries (`<TimeseriesTable />` with `temperature_c` semantic headers), and a `verify` result (`<AuthContextCard />` Korean tier as primary).
- No `data.go.kr` network traffic (verify via `tcpdump` if desired).

---

## 3. Run the TUI against the real Python backend (stdio bridge)

```bash
# From repo root
uv run kosmos-backend --ipc stdio &        # Starts Python backend in stdio IPC mode
# (or let the TUI spawn it:)

cd tui/
bun run tui
```

What happens:

1. `tui/src/main.tsx` invokes `Bun.spawn(["uv", "run", "kosmos-backend", "--ipc", "stdio"], {stdio: ["pipe","pipe","pipe"]})`.
2. Python side binds `asyncio.StreamReader` to `sys.stdin.buffer` and writes JSONL frames to `sys.stdout.buffer`.
3. TUI renders a welcome message and a prompt.
4. Type `안녕하세요, 강남역 주변 사고 위험 알려줘`; the model streams back a response; the streaming chunks render within 50 ms each.
5. If the model calls `lookup`, the result renders via `<CollectionList />` / `<PointCard />` / etc.

**Crash demo**: `kill -9 <backend-pid>` → TUI shows `<CrashNotice />` within 5 s with KOSMOS_* env vars redacted.

---

## 4. Exercise the permission-gauntlet modal

Use the scripted fixture:

```bash
bun run tui:fixture tests/fixtures/coordinator/permission-gauntlet.jsonl
```

Expected:

1. Phase indicator shows `Research`.
2. `transport-specialist` worker row appears with status `running`.
3. A permission_request frame triggers the modal; all input is blocked.
4. Press `y` → `<PermissionGauntletModal>` disappears; a `permission_response: granted` frame is written to stdout (visible via `bun run tui --trace`).

---

## 5. Run the component tests

```bash
cd tui/
bun test                             # Full TS test suite
bun test components/primitive        # Per-renderer unit tests (one per discriminated-union arm)
bun test ipc                         # IPC bridge + codec tests
```

All renderer tests use `ink-testing-library`; fixtures are pulled from #507 (Spec 022) + #1052 (Spec 031) recorded responses per FR-035.

---

## 6. Run the soak test (100 ev/s × 10 min)

```bash
cd tui/
bun test:soak                        # Replays fixture at 100 events/sec for 10 minutes
```

Pass criteria (SC-2):

- Zero dropped frames.
- p99 chunk render latency ≤ 50 ms.
- Memory RSS growth ≤ 50 MB over the run.
- Process exits 0.

---

## 7. Upstream diff check

```bash
cd tui/
bun run diff:upstream                # Wraps scripts/diff-upstream.sh
```

For every file in `tui/src/` carrying the attribution header, the script diffs it against the corresponding `.references/claude-code-sourcemap/restored-src/` source and reports divergence. Clean output = the lift is up-to-date vs Claude Code 2.1.88.

---

## 8. Observability

Every IPC frame emits a `kosmos.ipc.frame` OTEL span (child of the session span from Spec 021):

```bash
# Start the local OTEL collector
docker compose -f docker-compose.dev.yml up -d otel-collector

# Run the TUI; spans flow to the local Langfuse at http://localhost:3000
cd tui/ && bun run tui
```

Span attributes: `kosmos.session.id`, `kosmos.frame.kind`, `kosmos.frame.direction`, `kosmos.ipc.latency_ms`.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `bun install` fails at Ink pin | ADR for IME missing | Create `docs/adr/NNN-korean-ime-strategy.md` per FR-057 |
| TUI prompt shows boxes for Korean text | Terminal font lacks Hangul coverage | Install Pretendard or Noto Sans KR |
| `assistant_chunk` render is choppy (> 50 ms) | Debug logging enabled | Set `KOSMOS_TUI_LOG_LEVEL=WARN` |
| Permission modal doesn't appear | Backend not emitting `permission_request` | Verify Spec 027 coordinator is in `waiting_permission` state |
| CJK text wraps at wrong column | `string-width` edge case (ink#688, #759) | Accepted known issue; see `tui/docs/cjk-width-known-issues.md` |
| `bun run tui` hangs on start | Backend spawn slower than 2 s on cold cache | Run `uv sync` + `uv run python -c "import kosmos"` once to warm import cache |

---

## 10. Environment variables

Register the following in `.env` (never commit):

```bash
KOSMOS_TUI_THEME=default             # default | dark | light
KOSMOS_TUI_LOG_LEVEL=WARN            # DEBUG | INFO | WARN | ERROR
KOSMOS_TUI_SUBSCRIBE_TIMEOUT_S=120   # subscribe stream timeout (seconds)
KOSMOS_TUI_IME_STRATEGY=fork         # fork | readline  (value set by ADR)
```

All `KOSMOS_TUI_*` values are redacted from crash notices per #468 guard pattern (FR-004).
