# aimock Quickstart — KOSMOS Operator Guide

> **Spec**: `specs/debug-infra-rebuild/RFC.md § P0`
> **Status**: Phase 2 deliverable — OPT-IN only.
> Default KOSMOS path (real FriendliAI) is unchanged.

---

## What is aimock?

[aimock](https://aimock.copilotkit.dev/) (formerly llmock) is a deterministic fake-LLM HTTP server by CopilotKit. It serves OpenAI-compatible `/v1/chat/completions` responses from fixture JSON files, with configurable streaming physics (`ttft` / `tps` / `jitter`).

KOSMOS uses it to replace the live FriendliAI K-EXAONE endpoint in:
- CI smoke tests (bounded 5-10 s per scenario instead of 30-90 s)
- Local regression runs when FriendliAI is unavailable or rate-limited
- Reproducing specific LLM response shapes (e.g., multi-tool call regression)

---

## Prerequisites

- Docker Engine 24+ with Compose v2 (same as `docker-compose.dev.yml`)
- The `tests/fixtures/llm/` directory (already in the repo)

---

## Start aimock

```bash
# From the repo root:
docker compose -f docker-compose.aimock.yml up -d

# Verify it is healthy (takes ~10 s):
docker compose -f docker-compose.aimock.yml ps
# Expected: aimock   running (healthy)

# Optional: tail logs
docker compose -f docker-compose.aimock.yml logs -f
```

aimock listens on **`http://localhost:4010`** (override with `KOSMOS_AIMOCK_PORT` env var).

---

## Point KOSMOS at aimock

Set two environment variables **before** launching the TUI or running pytest:

```bash
export KOSMOS_FRIENDLI_BASE_URL=http://localhost:4010/v1
export KOSMOS_FRIENDLI_TOKEN=aimock-test
```

`KOSMOS_FRIENDLI_TOKEN` can be any non-empty string — aimock does not validate auth.

Both variables map to `LLMClientConfig` in `src/kosmos/llm/config.py` and are
picked up automatically by the existing pydantic-settings load path.

---

## Run the busan weather scenario against aimock

### Option A — TUI interactive

```bash
export KOSMOS_FRIENDLI_BASE_URL=http://localhost:4010/v1
export KOSMOS_FRIENDLI_TOKEN=aimock-test
bun run tui
# In the TUI, type: 부산 날씨
# Expected: aimock returns a single tool_call to lookup(kma_forecast_fetch)
#           TTFT ≈ 200 ms, TPS ≈ 50 tokens/sec
```

### Option B — tmux capture (non-interactive, recordable)

```bash
export KOSMOS_FRIENDLI_BASE_URL=http://localhost:4010/v1
export KOSMOS_FRIENDLI_TOKEN=aimock-test
bash scripts/tui-tmux-capture.sh /tmp/aimock-smoke \
     specs/debug-infra-rebuild/scenarios/busan-weather.sh
# Check: grep "kma_forecast_fetch" /tmp/aimock-smoke/snap-tool-dispatched.txt
```

### Option C — pytest (unit / integration, no TUI)

```bash
export KOSMOS_FRIENDLI_BASE_URL=http://localhost:4010/v1
export KOSMOS_FRIENDLI_TOKEN=aimock-test
uv run pytest tests/llm tests/ipc -x -q
# Suite must still pass 510+ tests.
# aimock is a transport-level drop-in; no test code changes needed.
```

---

## Stop aimock

```bash
docker compose -f docker-compose.aimock.yml down
```

---

## Fixture reference

All fixtures live in `tests/fixtures/llm/`. The server config is `tests/fixtures/llm/aimock.json`.

| File | Trigger phrase | Purpose |
|---|---|---|
| `busan-weather.json` | `부산 날씨` (contains) | Single-tool: `lookup(kma_forecast_fetch)` with valid `lat/lon/base_date/base_time` |
| `busan-multi-tool.json` | `부산 날씨 여러 도구` (contains) | Regression: emits 3 `toolCalls` — verifies `parallel_tool_calls=False` drops extras (Spec 2521 regression) |

### Fixture JSON format

```json
{
  "fixtures": [
    {
      "match": {
        "userMessageContains": "substring to match in the last user turn"
      },
      "response": {
        "toolCalls": [
          {
            "name": "function_name",
            "arguments": { "param": "value" }
          }
        ]
      },
      "streaming": {
        "ttft": 200,
        "tps": 50,
        "jitter": 50
      }
    }
  ]
}
```

- `match.userMessageContains` — case-sensitive substring match on the latest user message
- `match.userMessage` — exact match (use for single known phrases)
- `response.content` — plain text response (alternative to `toolCalls`)
- `response.toolCalls` — array of function calls following OpenAI tool-use schema
- `streaming.ttft` — time-to-first-token in milliseconds (default: aimock default)
- `streaming.tps` — tokens per second (default: aimock default)
- `streaming.jitter` — ±jitter in milliseconds added to each chunk delay

---

## Hard constraints (do not violate)

1. **aimock is OPT-IN**. KOSMOS runs against real FriendliAI by default. Never set
   `KOSMOS_FRIENDLI_BASE_URL=http://localhost:4010` in `.env` committed to the repo.
2. **Do not add aimock to CI workflows** yet. That is the next Epic's job.
3. **Real-FriendliAI tests** remain gated behind `@pytest.mark.live` — aimock does not
   replace them, it supplements them.
4. **`KOSMOS_FRIENDLI_TOKEN` must remain non-empty** even for aimock — the pydantic
   validator in `LLMClientConfig` rejects blank tokens before the request reaches aimock.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ConnectionRefusedError: [Errno 61]` | aimock not running | `docker compose -f docker-compose.aimock.yml up -d` |
| All responses are `{"error":"no fixture matched"}` | User message doesn't match any `userMessageContains` | Add a fixture or adjust the match phrase |
| `KOSMOS_FRIENDLI_TOKEN must not be empty` | Token env var not set | `export KOSMOS_FRIENDLI_TOKEN=aimock-test` |
| Container exits immediately | Image pull failed | `docker pull ghcr.io/copilotkit/aimock:latest` |
| Port 4010 already in use | Another service on that port | `KOSMOS_AIMOCK_PORT=4011 docker compose -f docker-compose.aimock.yml up -d` and set `KOSMOS_FRIENDLI_BASE_URL=http://localhost:4011/v1` |
