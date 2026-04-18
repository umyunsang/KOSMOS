# Quickstart — Agent Swarm Core (Epic #13)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-04-18

This quickstart orients a contributor (or a future `/speckit-implement` Teammate) to the Agent Swarm Core work. It walks through environment setup, the expected module layout, the test harness, and how to exercise the coordinator end-to-end against recorded fixtures.

---

## 1. Prerequisites

- Python 3.12+ and `uv >= 0.5` installed.
- Epic #507 (2-tool facade + 4 seed adapters) is merged — confirmed via `gh issue view 507` (CLOSED).
- Epic #468 (env-var catalog via `KosmosSettings`) is merged — confirmed via `gh issue view 468` (CLOSED).
- No live `data.go.kr` API keys required — this Epic runs entirely on fixture tapes.

```bash
# From repo root
uv sync
uv run pytest tests/agents/ -v    # Will start passing as /speckit-implement lands tasks
```

---

## 2. Environment variables

Four new `KOSMOS_AGENT_*` variables are introduced. Defaults are fail-closed and sufficient for local development and CI:

```bash
# Optional — override only if you need to debug a custom layout
export KOSMOS_AGENT_MAILBOX_ROOT="$HOME/.kosmos/mailbox"     # default
export KOSMOS_AGENT_MAILBOX_MAX_MESSAGES=1000                # default; range [100, 10000]
export KOSMOS_AGENT_MAX_WORKERS=4                            # default; range [1, 16]
export KOSMOS_AGENT_WORKER_TIMEOUT_SECONDS=120               # default; range [10, 600]
```

All four land in `src/kosmos/settings.py::KosmosSettings` and are documented in `docs/configuration.md § Agent Swarm` (FR-036).

---

## 3. Module layout (after /speckit-implement lands)

```text
src/kosmos/agents/
├── __init__.py              # Re-exports: Coordinator, Worker, AgentContext, CoordinatorPlan,
│                            #             FileMailbox, ConsentGateway
├── coordinator.py           # Coordinator + 4-phase state machine
├── worker.py                # Worker (wraps engine.query._query_inner)
├── context.py               # AgentContext (Pydantic v2 frozen)
├── consent.py               # ConsentGateway ABC + AlwaysGrantConsentGateway stub
├── plan.py                  # CoordinatorPlan + PlanStep
├── errors.py                # AgentConfigurationError, MailboxOverflowError, ...
└── mailbox/
    ├── __init__.py
    ├── base.py              # Mailbox ABC
    ├── messages.py          # AgentMessage + 6 payload union members
    └── file_mailbox.py      # FileMailbox (fsync + FIFO + replay)
```

---

## 4. Minimal programmatic usage

```python
import asyncio
from uuid import uuid4
from kosmos.agents import (
    Coordinator, AgentContext, FileMailbox, CoordinatorPlan
)
from kosmos.agents.consent import AlwaysGrantConsentGateway
from kosmos.llm.client import LLMClient
from kosmos.tools.registry import ToolRegistry
from kosmos.tools.mvp_surface import build_mvp_registry   # from Epic #507

async def demo():
    session_id = uuid4()
    llm = LLMClient(...)                     # per-session instance (Spec 019 semaphore)
    registry = build_mvp_registry()          # lookup + resolve_location only
    mailbox = FileMailbox(session_id=session_id)
    consent = AlwaysGrantConsentGateway()    # stub; real impl is #287

    coord = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=registry,
        mailbox=mailbox,
        consent_gateway=consent,
    )

    plan: CoordinatorPlan = await coord.run(
        citizen_request="이사 준비 중인데, 전입신고랑 자동차 주소변경이랑 건강보험 주소변경 다 해야 하는데"
    )
    for step in plan.steps:
        print(f"{step.ministry}: {step.action} ({step.execution_mode}, depends_on={step.depends_on})")

asyncio.run(demo())
```

**Backward compatibility**: If you pass `role="solo"` (or instantiate `QueryEngine` directly), the existing Phase 1 single-agent loop runs unchanged — FR-007 + SC-007 guarantee this.

---

## 5. Testing locally

```bash
# Unit tests — fastest feedback
uv run pytest tests/agents/test_coordinator_phases.py -v
uv run pytest tests/agents/test_mailbox_file.py -v

# Integration tests — use fixture tapes from #507
uv run pytest tests/agents/ -v

# The cooperative-cancellation test asserts wall-clock ≤ 500 ms
uv run pytest tests/agents/test_cooperative_cancellation.py -v --durations=10

# The crash-replay test writes a synthetic result message to a tmp mailbox,
# restarts the coordinator, and asserts the message is replayed.
uv run pytest tests/agents/test_mailbox_crash_replay.py -v
```

All integration tests are offline — no live `data.go.kr` calls. This is enforced by fixture-tape inspection (SC-010).

---

## 6. Debugging a session

The mailbox is human-readable. To inspect a live or crashed session:

```bash
# Find the session directory
ls ~/.kosmos/mailbox/

# Pretty-print a specific message
uv run python -c "
import json, sys
from pathlib import Path
msg_file = Path('~/.kosmos/mailbox/<session_id>/coordinator/<message_id>.json').expanduser()
print(json.dumps(json.loads(msg_file.read_text()), indent=2, ensure_ascii=False))
"

# Check which messages are unread (no .consumed marker)
find ~/.kosmos/mailbox/<session_id> -name '*.json' \
  | while read f; do [ -e "$f.consumed" ] || echo "UNREAD: $f"; done
```

---

## 7. Observability

When OTLP export is configured (Spec 021), the Langfuse dashboard surfaces three span types:

- `gen_ai.agent.coordinator.phase` — one per phase transition, attribute `kosmos.agent.coordinator.phase` ∈ {research, synthesis, implementation, verification}.
- `gen_ai.agent.worker.iteration` — one per worker tool-loop iteration, attributes `kosmos.agent.role` + `kosmos.agent.session_id`.
- `gen_ai.agent.mailbox.message` — one per `send`, attributes `kosmos.agent.mailbox.msg_type`, `kosmos.agent.mailbox.correlation_id`, `kosmos.agent.mailbox.sender`, `kosmos.agent.mailbox.recipient`.

These attributes are declared as string constants in `src/kosmos/observability/semconv.py` (FR-031) and submitted to Epic #501's boundary table.

**Privacy note**: Message bodies are NEVER included as span attributes (PIPA — no PII in telemetry). Only metadata (types, IDs, routing) appears in traces.

---

## 8. Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `AgentConfigurationError: tool_registry contains unexpected tools` | Registry has an adapter beyond `lookup`/`resolve_location` | Use `build_mvp_registry()` from Epic #507; the agent layer never sees per-API tools. |
| `MailboxWriteError: permission denied` on first run | `KOSMOS_AGENT_MAILBOX_ROOT` not writable | Default is `~/.kosmos/mailbox`; ensure `$HOME` is writable or override the var to a tmpdir. |
| `MailboxOverflowError` in long sessions | > 1000 messages in a session | Either reset the session or raise `KOSMOS_AGENT_MAILBOX_MAX_MESSAGES` (clamped at 10000). |
| Cooperative cancellation exceeds 500 ms | Worker stuck in blocking call (e.g., `json.dump`) | Wrap heavy fs work in `asyncio.to_thread()`; inspect `test_cooperative_cancellation.py` for pattern. |
| Synthesis phase calls `lookup` (test fails) | Coordinator passed full tool registry to synthesis LLM | Pass an empty `[]` for tool definitions during synthesis; FR-004 + FR-038 are the invariants. |
| Cross-run messages replay on new session | Same `session_id` reused after a cancel | Cross-run replay applies only to the same session — use a fresh UUID4 per citizen session (spec edge case 3). |

---

## 9. Relationship to other Epics

| Epic | Status | How this Epic interacts |
|---|---|---|
| #507 MVP Main-Tool | CLOSED | Provides the 2-tool facade + 4 seed adapters that workers consume. |
| #468 Secrets & Config | CLOSED | `KosmosSettings` hosts the 4 new `KOSMOS_AGENT_*` fields. |
| #019 Phase 1 Hardening | Merged | Per-session LLM semaphore reused unchanged; no new rate-limit infra. |
| #021 OTel GenAI | Merged | `kosmos.agent.*` attributes extend the existing namespace. |
| #501 OTLP Collector | OPEN | Receives the new `kosmos.agent.*` attributes in its boundary table (FR-031). |
| #14 Ministry Specialists | OPEN | Ships ministry-specific system prompts that slot into `AgentContext.specialist_role`; depends on this Epic. |
| #287 TUI | OPEN | Real `ConsentGateway` implementation replacing this Epic's stub. |
| #21 Agent Swarm Production | OPEN | Redis Streams backend, DLQ, cross-process mailbox — all preserve this Epic's `Mailbox` ABC. |

---

## 10. Next steps

After this plan is merged:

1. `/speckit-tasks` — generates `tasks.md` breaking the 40 FRs into dependency-ordered tasks (estimated ~20-28 Task issues).
2. `/speckit-analyze` — cross-artifact consistency check.
3. `/speckit-taskstoissues` — creates GitHub Task sub-issues linked to Epic #13 and resolves the 6 `NEEDS TRACKING` markers from spec § Deferred Items into real placeholder issues.
4. `/speckit-implement` — Agent Teams parallel execution (Teammate sonnet models).

**Readiness**: The plan, research, data model, and contracts are internally consistent and trace every decision to a reference. No open NEEDS CLARIFICATION. No unresolved constitution gates. Ready for `/speckit-tasks`.
