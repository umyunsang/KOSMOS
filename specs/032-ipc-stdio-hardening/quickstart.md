# Quickstart — IPC stdio hardening (Spec 032)

**Audience**: KOSMOS developers validating Spec 032 end-to-end before merge.
**Prerequisites**: `uv sync` complete, `tui/` bun deps installed, no `.env` tampering.
**Time budget**: ~15 minutes on a modern laptop.

> This quickstart proves the 4 user stories in spec.md are wired end-to-end. It does NOT ship production-grade civic flows — it validates IPC envelope, backpressure signaling, reconnect handshake, and tx dedup via synthetic scripts.

---

## 0. Environment sanity

```bash
cd /Users/um-yunsang/KOSMOS
uv sync
cd tui && bun install && cd ..
uv run pytest tests/ipc/ -q   # baseline: existing Spec 031 tests pass
```

Expected: all existing IPC tests (`tests/ipc/test_frame_schema.py`, etc.) stay green. Spec 032 adds tests; it does not break prior ones.

---

## 1. Scenario A — Schema round-trip (FR-001..010)

**Validates**: US4 (trace trail end-to-end), FR-003 UUIDv7, FR-007 JSON Schema commit, FR-010 byte-equal rebuild.

### 1.1 Regenerate and diff the JSON Schema

```bash
uv run python -c "
from kosmos.ipc.frame_schema import ipc_frame_json_schema
import json
print(json.dumps(ipc_frame_json_schema(), indent=2, sort_keys=True))
" > /tmp/frame.schema.actual.json

diff <(jq -S . tui/src/ipc/schema/frame.schema.json) <(jq -S . /tmp/frame.schema.actual.json)
```

Expected: **no diff**. Any diff means the Python discriminated union drifted from the committed schema — rebuild and re-commit.

### 1.2 Emit a single frame, validate with the schema

```bash
uv run python - <<'PY'
import json
from datetime import datetime, timezone
from uuid import uuid4
from kosmos.ipc.frame_schema import UserInputFrame

f = UserInputFrame(
    version="1.0",
    session_id="s-quickstart",
    correlation_id=str(uuid4()),  # UUIDv7 preferred in prod
    role="tui",
    frame_seq=0,
    ts=datetime.now(timezone.utc).isoformat(),
    text="서울 노원구 교통사고 통계 알려줘",
)
print(f.model_dump_json())
PY
```

Expected: one NDJSON line, well-formed, with `"version":"1.0"` + `"role":"tui"` + `"frame_seq":0`.

---

## 2. Scenario B — 세션 드롭 → 복구 (US1, P1)

**Validates**: FR-018..025, resume-handshake contract, ring buffer replay.

### 2.1 Boot the synthetic backend

```bash
uv run python -m kosmos.ipc.demo.session_backend --session-id s-demo &
BACKEND=$!
```

(The synthetic backend is a Spec 032 test harness under `src/kosmos/ipc/demo/` — it drives a single session through a scripted frame sequence.)

### 2.2 Drive a TUI that survives a kill-9

```bash
bun tui/src/ipc/demo/resume_probe.ts --session s-demo --after-frames 20 --then kill-stdin
```

Expected console output (Korean + English for developer clarity):

```
[probe] applied 20 frames (frame_seq 0..19)
[probe] stdin closed; reconnecting …
[probe] sent resume_request (last_seen_frame_seq=19)
[probe] received resume_response (replay_count=5, resumed_from_frame_seq=20)
[probe] applied 5 replayed frames (frame_seq 20..24)
[probe] session recovered ✓
```

### 2.3 Kill the backend

```bash
kill $BACKEND
```

---

## 3. Scenario C — 부처 429 가시화 (US2, P1)

**Validates**: FR-011..017, `BackpressureSignalFrame` with `upstream_429`, HUD dual-locale.

### 3.1 Fire a synthetic 429 from the mock ministry server

```bash
uv run python -m kosmos.ipc.demo.upstream_429_probe --retry-after 15
```

Expected one-line output (pretty-printed):

```json
{
  "kind": "backpressure",
  "role": "backend",
  "signal": "throttle",
  "source": "upstream_429",
  "retry_after_ms": 15000,
  "hud_copy_ko": "부처 API가 혼잡합니다. 15초 후 자동 재시도합니다.",
  "hud_copy_en": "Ministry API rate-limited. Retrying in 15s."
}
```

### 3.2 Verify the TUI renders the Korean copy

```bash
bun tui/src/ipc/demo/hud_probe.ts --fixture /tmp/backpressure-throttle.json
```

Expected: terminal shows a banner reading **"부처 API가 혼잡합니다. 15초 후 자동 재시도합니다."** with a live countdown.

---

## 4. Scenario D — 민원 중복 제출 차단 (US3, P1)

**Validates**: FR-026..033, Stripe 3-step dedup, LRU pin on `is_irreversible=true`, audit coupling.

### 4.1 Register a fake irreversible tool

```bash
uv run python -m kosmos.ipc.demo.register_irreversible_fixture  # seeds AdapterRegistration
```

### 4.2 Double-submit the same transaction_id

```bash
uv run pytest tests/ipc/test_tx_dedup.py::test_double_submit_hits_cache -q
```

Expected:

- Test passes.
- First call executes and writes `ToolCallAuditRecord(status="ok", correlation_id=..., transaction_id=T1)`.
- Second call hits cache, writes `ToolCallAuditRecord(status="dedup_hit", correlation_id=... (new), transaction_id=T1)`.
- Returned response of the second call is byte-equal to the first.

### 4.3 Observe the OTEL spans

```bash
uv run pytest tests/ipc/test_tx_dedup.py::test_cache_state_span_attribute -q
```

Expected: span for second call has attribute `kosmos.ipc.tx.cache_state = "hit"`.

---

## 5. Scenario E — End-to-end correlation trace (US4, P2)

**Validates**: FR-003 correlation_id propagation, OTEL span attribute promotion.

### 5.1 Drive a full turn

```bash
uv run python -m kosmos.ipc.demo.full_turn_probe --session s-trace > /tmp/trace.ndjson
```

### 5.2 Assert the correlation_id is stable across frames

```bash
jq -s '[.[] | .correlation_id] | unique | length' /tmp/trace.ndjson
```

Expected output: `1` — exactly one correlation_id threads through `user_input → tool_call → tool_result → assistant_chunk → payload_end`.

### 5.3 Assert span linkage

```bash
uv run pytest tests/ipc/test_otel_correlation.py -q
```

Expected: every span in the turn has `kosmos.ipc.correlation_id` set to the same UUIDv7 value.

---

## 6. Full regression

```bash
uv run pytest tests/ipc/ -q
cd tui && bun test ipc && cd ..
```

Both commands must exit zero. A green baseline here means Spec 032 is landable.

---

## 7. Rollback

Nothing to roll back — Spec 032 is purely additive:

- `_BaseFrame` gains 5 fields (default-compatible).
- 9 new arms join the discriminated union; existing arms untouched.
- No database, no migrations.

If the branch must be abandoned, `git checkout main && git branch -D 032-ipc-stdio-hardening` is sufficient.

---

## 8. Troubleshooting

| Symptom                                                                  | Likely cause                                                                        | Fix                                                                 |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `diff` in Scenario 1.1 reports `version` or `role` missing                | Pydantic model not rebuilt                                                          | Ensure all arms inherit extended `_BaseFrame`; re-run test.         |
| `resume_rejected(reason="ring_evicted")` in Scenario 2                   | `--after-frames > 256`; ring overflowed during idle                                 | Use smaller value or increase `KOSMOS_IPC_RING_SIZE`.               |
| `throttle` frame missing `retry_after_ms`                                | Adapter forgot to parse `Retry-After`                                               | Add `clamp(retry_after_ms, 1000, 900000)` in adapter.               |
| `test_double_submit_hits_cache` fails with two distinct `receipt_id`      | LRU not pinning `is_irreversible=true`                                             | Check `AdapterRegistration.is_irreversible` fixture.                |
| `correlation_id` drift across frames                                     | Emitter forgot to propagate from originating `user_input`                          | Wire emission through `RunContext.correlation_id`.                  |

---

## 9. Next step

Once this quickstart exits clean on your machine, the spec is in implement-readiness. Proceed to `/speckit-tasks` → `/speckit-analyze` → `/speckit-taskstoissues` → `/speckit-implement` with Agent Teams α/β/γ/δ dispatched per plan.md § Parallel-Safe Workstream Factoring.
