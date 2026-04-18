# tests/agents — Agent Swarm Core Test Suite

Test suite for spec 027 (Agent Swarm Core, Epic #13).

## Running

```bash
uv run pytest tests/agents/
uv run pytest tests/agents/ -v --durations=10   # timing report
```

## Test inventory

| File | Count | What it covers |
|------|-------|----------------|
| `test_agent_message_schema.py` | 6 | AgentMessage Pydantic schemas (FR-015..FR-017) |
| `test_context.py` | — | AgentContext construction and default IDs |
| `test_coordinator_plan_schema.py` | 5 | CoordinatorPlan / PlanStep schema invariants |
| `test_coordinator_phases.py` | 9 | Coordinator 4-phase workflow integration (FR-001..FR-012) |
| `test_cooperative_cancellation.py` | 6 | FR-006: cancel flag, cancel_and_wait(), SC-003 timing |
| `test_cancel_no_crossrun_replay.py` | 4 | FR-019, research.md C9: cross-run replay isolation |
| `test_mailbox_corrupt_skip.py` | 4 | FR-020: truncated .json files skipped with WARNING |
| `test_mailbox_crash_replay.py` | 4 | FR-019, SC-005: crash-replay FIFO + consumed marker |
| `test_mailbox_fifo.py` | 5 | FR-018: per-sender FIFO ordering |
| `test_mailbox_file.py` | 8 | FR-014..FR-022: FileMailbox send + on-disk layout |
| `test_messages.py` | 10 | AgentMessage message type payloads |
| `test_no_new_deps.py` | 1 | SC-008: [project.dependencies] baseline enforcement |
| `test_observability_spans.py` | 6 | FR-028..FR-031, SC-006: OTel span emission |
| `test_permission_delegation.py` | 5 | FR-023..FR-025: permission request/response routing |
| `test_permission_denied.py` | 5 | FR-023: permission denied flow end-to-end |
| `test_plan.py` | 8 | CoordinatorPlan status, partial plan, no-results plan |
| `test_solo_role_compat.py` | 5 | FR-013: role=solo returns plan without worker dispatch |
| `test_synthesis_tool_gate.py` | 3 | FR-004/FR-038: synthesis LLM never sees tool definitions |
| `test_worker_lifecycle.py` | 7 | FR-005..FR-008: worker run, error, cancel, disallowed tool |
| `test_zero_live_api.py` | 1 | SC-010: no live data.go.kr / FriendliAI calls |

**Total: 111 tests**

## Timing (SC-003 compliance)

Run `uv run pytest tests/agents/ --durations=10` last verified:

```
slowest 10 durations (0.40s total wall clock):
  0.03s call  test_agent_message_schema.py::test_task_message_schema
  0.02s call  test_context.py::test_coordinator_id_default
  0.01s call  test_cooperative_cancellation.py::test_cancel_propagates_to_worker_task
  ...
```

All tests complete in under 0.40s. The cooperative-cancellation tests run in
under 0.02s each — well within the SC-003 requirement of 500ms for `cancel_and_wait()`.

## No live API calls

All tests use `StubLLMClient` (conftest.py) or `_SlowLLMClient`/`_ScriptedLLMClient` stubs
that bypass `LLMClient.__init__` via `object.__new__`. No test makes a real HTTP request
to `data.go.kr`, `api.friendli.ai`, or any external host. Enforced by `test_zero_live_api.py`.

## OTel span capture strategy

`test_observability_spans.py` uses `monkeypatch.setattr` to replace the module-level
`_tracer` objects in `kosmos.agents.coordinator`, `kosmos.agents.worker`, and
`kosmos.agents.mailbox.file_mailbox` with tracers backed by an `InMemorySpanExporter`.
This avoids the global-provider-override guard in the OTel SDK.
