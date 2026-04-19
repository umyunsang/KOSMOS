# IPC Frame Contracts — Spec 287 TUI

**Branch**: `287-tui-ink-react-bun`
**Source of truth**: Python Pydantic v2 models at `src/kosmos/ipc/frame_schema.py` (to be created by task T-BACKEND-001).
**Consumer**: TypeScript TUI via generated types at `tui/src/ipc/frames.generated.ts` (emitted by `tui/scripts/gen-ipc-types.ts`).

These JSON Schemas are reference artifacts — they MUST match the `model_json_schema()` output of the Pydantic models. A CI gate compares them and fails on drift.

## Authority

| Contract | Python source | Generated TS location | CI enforcement |
|---|---|---|---|
| `ipc-frames.schema.json` | `IPCFrame` discriminated union | `tui/src/ipc/frames.generated.ts` | `tui/scripts/gen-ipc-types.ts --check` |
| Per-arm schemas | `UserInputFrame`, `AssistantChunkFrame`, … | Union variants | Same |

## Frame arms (10 total)

| Arm | Direction | File |
|---|---|---|
| `user_input` | TUI → backend | `user-input.schema.json` |
| `assistant_chunk` | backend → TUI | `assistant-chunk.schema.json` |
| `tool_call` | backend → TUI | `tool-call.schema.json` |
| `tool_result` | backend → TUI | `tool-result.schema.json` |
| `coordinator_phase` | backend → TUI | `coordinator-phase.schema.json` |
| `worker_status` | backend → TUI | `worker-status.schema.json` |
| `permission_request` | backend → TUI | `permission-request.schema.json` |
| `permission_response` | TUI → backend | `permission-response.schema.json` |
| `session_event` | bidirectional | `session-event.schema.json` |
| `error` | backend → TUI | `error.schema.json` |

## Cross-spec contract reuse

`tool_result.envelope` re-uses Spec 031 primitive envelopes via `$ref`:

| Nested primitive | Upstream contract |
|---|---|
| `lookup` | `specs/022-mvp-main-tool/contracts/lookup.output.schema.json` (existing) |
| `resolve_location` | Same — Spec 022 (`ResolveBundle` slots) |
| `submit` | `specs/031-five-primitive-harness/contracts/submit.output.schema.json` |
| `subscribe` | `specs/031-five-primitive-harness/contracts/subscribe.output.schema.json` |
| `verify` | `specs/031-five-primitive-harness/contracts/verify.output.schema.json` |

## Framing

- Transport: newline-delimited JSON (JSONL).
- Each line is exactly one valid JSON object matching `ipc-frames.schema.json`.
- UTF-8 encoding only. No BOM. `\n` terminates every frame, including the last one before SIGTERM.

## Versioning

- Breaking changes to any frame schema MUST bump the `x-ipc-protocol-version` attribute in the union root schema.
- v1 protocol = this document.
- The TUI reads `x-ipc-protocol-version` from the first `session_event` frame; mismatch → `<CrashNotice />` with upgrade hint.

## Testing

- Python-side: `tests/ipc/test_frame_schema.py` (round-trip `model_validate_json` on every arm).
- TypeScript-side: `tui/tests/ipc/codec.test.ts` (zod parse of every arm from fixture JSONL).
- Cross-language: `tui/scripts/gen-ipc-types.ts --check` verifies the generated TS matches Pydantic schemas byte-for-byte (excluding comments).
