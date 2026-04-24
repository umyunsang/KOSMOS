# Quickstart — Citizen's first K-EXAONE response

**Feature**: [spec.md](./spec.md)
**Contracts**: [contracts/llm-client.md](./contracts/llm-client.md)
**Branch**: `1633-dead-code-friendli-migration`

This quickstart is the reproducible validation path that US1 demands. A KOSMOS contributor can run it in < 10 minutes from a fresh clone; CI can run it with a mocked Python backend as a regression fence.

## Prerequisites

- Bun ≥ 1.2.x, Python ≥ 3.12, uv ≥ 0.5
- A valid FriendliAI API token (see https://friendli.ai/suite)
- Epic #1632 (P0) merged — CC 2.1.88 baseline runnable
- Epic #1633 (this) merged — dead-code eliminated + FriendliAI wired

## Setup

```bash
# 1. Clone + install
git clone git@github.com:umyunsang/KOSMOS.git
cd KOSMOS
uv sync                    # Python backend deps
cd tui && bun install      # TUI deps
cd ..

# 2. Configure FriendliAI
export KOSMOS_FRIENDLI_TOKEN="fr-xxxxxxxxxxxxxx"    # your FriendliAI token
# optional — defaults are fine:
# export KOSMOS_FRIENDLI_MODEL="LGAI-EXAONE/K-EXAONE-236B-A23B"
# export KOSMOS_FRIENDLI_BASE_URL="https://api.friendli.ai/serverless/v1"

# 3. Sanity-check Python backend
uv run python -c "from kosmos.llm.config import LLMClientConfig; cfg = LLMClientConfig(); print(cfg.model)"
# expected: LGAI-EXAONE/K-EXAONE-236B-A23B
```

## Scenario 1 — Citizen asks a civil-affairs question (US1)

```bash
# Run TUI; backend starts automatically via stdio bridge
cd tui && bun run src/main.tsx
```

**Expected UX**:
1. Splash screen renders within 500 ms. No "Claude" or "Anthropic" text anywhere.
2. Onboarding (Spec 035) runs on first launch — 5 steps, ending at `terminal-setup`. No `/login` or `/logout` options.
3. REPL prompt accepts input.
4. Type: `출산 보조금 신청 방법 알려줘`
5. **First K-EXAONE token appears within 5 seconds** (SC-001).
6. Response streams token-by-token using Spec 032 `AssistantChunkFrame` over stdio.
7. Ctrl+C exits cleanly.

**Under the hood** (for contributor verification):
- TUI process `require.cache` contains no `@anthropic-ai/sdk` entry.
- Python backend emits OTEL `gen_ai.client.invoke` span with `gen_ai.system=friendli_exaone`, `gen_ai.request.model=LGAI-EXAONE/K-EXAONE-236B-A23B`, `kosmos.prompt.hash=<64-char hex>`.
- OTLP collector (Spec 028) forwards the span to local Langfuse at `http://localhost:3000`.

## Scenario 2 — Fail-closed boot without key

```bash
unset KOSMOS_FRIENDLI_TOKEN
unset FRIENDLI_API_KEY
cd tui && bun run src/main.tsx
```

**Expected**:
- Immediate bilingual error envelope: `"FRIENDLI_API_KEY 환경변수가 필요합니다 / FRIENDLI_API_KEY environment variable required"`
- Process exits with status 1.
- No HTTP requests made (verify with `tcpdump -i any host api.friendli.ai or host api.anthropic.com` — zero packets).
- No Anthropic credential lookup in macOS Keychain (verify with Console.app → filter `security`).

## Scenario 3 — Contributor static-analysis invariants

After the branch is checked out:

```bash
# SC-002: no @anthropic-ai/sdk runtime imports
grep -rln '@anthropic-ai/sdk' tui/src --include='*.ts' --include='*.tsx' \
  | grep -v '__mocks__\|\.test\.\|\.spec\.' | wc -l
# expected: 0

# SC-006: no ant-guard branches
grep -rln 'ANT_INTERNAL\|=== "ant"' tui/src --include='*.ts' --include='*.tsx' | wc -l
# expected: 0

# SC-004: no CC version migrations
ls tui/src/migrations/migrate*.ts tui/src/migrations/reset*.ts 2>/dev/null | wc -l
# expected: 0

# SC-005: no CC telemetry callsites
grep -rln 'logEvent\|profileCheckpoint\|growthbook\|statsig' tui/src \
  --include='*.ts' --include='*.tsx' | grep -v '\.test\.' | wc -l
# expected: 0

# SC-003: main.tsx under 2,500 lines
wc -l tui/src/main.tsx
# expected: ≤ 2500

# SC-007: bun test floor
cd tui && bun test 2>&1 | tail -3
# expected: "N passed" where N ≥ 540, 0 failed

# SC-010: default main-loop model is fixed to EXAONE 4.0 32B
grep -n "LGAI-EXAONE/K-EXAONE-236B-A23B" tui/src/utils/model/model.ts
# expected: at least 1 match at the getDefaultMainLoopModel return site
```

## Scenario 4 — Spec 032 resume sanity (regression)

Validates that the P1+P2 rewire did not break Spec 032 resume semantics.

```bash
# Start TUI, send a query that will trigger a long tool call
cd tui && bun run src/main.tsx
# In REPL: "경기도 수원시 팔달구 응급실 현재 가용 병상"
# While streaming, kill backend: `pkill -f 'python -m kosmos'`
# TUI should emit resume request on reconnect, receive buffered frames, finish answer
```

**Expected**: Stream resumes from the last acknowledged `correlation_id`. No duplicate tokens on screen. No duplicate FriendliAI billable call (verify in Langfuse — one `gen_ai.client.invoke` span, not two).

## CI regression harness

Add to `.github/workflows/ci.yml` (P3 epic may formalize this, Epic #1633 suggests the stub):

```yaml
- name: Epic #1633 invariants
  run: |
    cd tui
    # SC-002
    ! grep -rln '@anthropic-ai/sdk' src --include='*.ts' --include='*.tsx' \
        | grep -v '__mocks__\|\.test\.\|\.spec\.' | read
    # SC-004
    test "$(ls src/migrations/migrate*.ts src/migrations/reset*.ts 2>/dev/null | wc -l)" -eq 0
    # SC-005
    ! grep -rln 'logEvent\|profileCheckpoint\|growthbook\|statsig' src \
        --include='*.ts' --include='*.tsx' | grep -v '\.test\.' | read
    # SC-006
    ! grep -rln 'ANT_INTERNAL\|=== "ant"' src --include='*.ts' --include='*.tsx' | read
    # SC-003
    test "$(wc -l < src/main.tsx)" -le 2500
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `FRIENDLI_API_KEY 환경변수가 필요합니다` immediately | env not set | `export KOSMOS_FRIENDLI_TOKEN=...` |
| `ErrorFrame(class=llm, code=auth)` on first turn | bad token | rotate token at https://friendli.ai/suite |
| `ErrorFrame(class=llm, code=not_found)` | model ID wrong | ensure `KOSMOS_FRIENDLI_MODEL` is `LGAI-EXAONE/K-EXAONE-236B-A23B` or unset (use default) |
| `ErrorFrame(class=network, code=ipc_transport)` | Python backend crashed | check `~/.kosmos/logs/backend.log`; Spec 032 resume should recover |
| `BackpressureSignal(kind=llm_rate_limit)` stuck | FriendliAI tier limit | wait `retry_after_ms`; Spec 019 retry runs automatically |
| Onboarding keeps asking `/login` | pre-merge build | verify commit hash ≥ Epic #1633 merge commit |

## References

- [spec.md](./spec.md) — what we're building
- [plan.md](./plan.md) — how it's built (this document's parent)
- [research.md](./research.md) — why the design decisions
- [contracts/llm-client.md](./contracts/llm-client.md) — TS surface + IPC protocol
- [data-model.md](./data-model.md) — frame reuse strategy
- `docs/vision.md § L1-A` — canonical LLM-layer decisions
- Spec 032 quickstart — IPC bridge baseline
