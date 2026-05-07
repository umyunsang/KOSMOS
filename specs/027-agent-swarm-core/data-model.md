# Phase 1 Data Model — Agent Swarm Core

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Date**: 2026-04-18

All models are Pydantic v2 with `model_config = ConfigDict(extra="forbid")`. Frozen models declare `frozen=True`. The `Any` type is forbidden (Constitution Principle III).

---

## Module map

```text
src/kosax/agents/
├── context.py         # AgentContext
├── plan.py            # CoordinatorPlan, PlanStep, PlanStatus, ExecutionMode, StepStatus
├── errors.py          # AgentConfigurationError, AgentIsolationViolation,
│                      # MailboxOverflowError, MailboxWriteError, PermissionDeniedError
└── mailbox/
    ├── base.py        # Mailbox (abstract)
    ├── messages.py    # AgentMessage + 6 Payload union members + MessageType enum
    └── file_mailbox.py  # FileMailbox (concrete)
```

---

## 1. `AgentContext` — frozen per-worker injection

Module: `src/kosax/agents/context.py`
FR traces: FR-010

```python
from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from kosax.llm.client import LLMClient
from kosax.tools.registry import ToolRegistry

class AgentContext(BaseModel):
    """Immutable per-worker context pinned at spawn time."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,  # LLMClient, ToolRegistry are non-Pydantic
    )

    session_id: UUID
    """Session identifier; shared across coordinator + all workers in this session."""

    specialist_role: str = Field(min_length=1, max_length=64)
    """Worker's specialist role (e.g., 'transport', 'welfare', 'civil_affairs').

    Must be non-empty — coordinator raises AgentConfigurationError at spawn if empty.
    """

    coordinator_id: str = Field(default="coordinator", frozen=True)
    """Sender ID of the coordinator. Always the literal string 'coordinator'."""

    worker_id: str = Field(min_length=1, max_length=128)
    """Unique sender ID of this worker. Format: 'worker-<role>-<uuid4>'."""

    tool_registry: ToolRegistry
    """Tool registry — MUST be restricted to {'lookup', 'resolve_location'}.

    The restriction is asserted by Coordinator.spawn_worker() before AgentContext
    construction; AgentContext itself cannot validate this at __init__ time because
    ToolRegistry is not a Pydantic model.
    """

    llm_client: LLMClient
    """Shared LLM client (per-session semaphore reused per Spec 019)."""
```

**Invariants enforced elsewhere**:
- `tool_registry.tool_ids() == {"lookup", "resolve_location"}` — asserted in `Coordinator.spawn_worker()` (FR-011).
- `worker_id` is unique across a session — enforced by `uuid4()` in the coordinator's spawn helper.

---

## 2. Mailbox message schema

Module: `src/kosax/agents/mailbox/messages.py`
FR traces: FR-016, FR-025

### 2.1 `MessageType` enum

```python
from enum import StrEnum

class MessageType(StrEnum):
    task = "task"
    result = "result"
    error = "error"
    permission_request = "permission_request"
    permission_response = "permission_response"
    cancel = "cancel"
```

### 2.2 Six payload union members (all frozen)

```python
from kosax.tools.models import LookupCollection, LookupRecord, LookupTimeseries
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from uuid import UUID

class TaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["task"] = "task"
    instruction: str = Field(min_length=1)
    specialist_role: str = Field(min_length=1, max_length=64)

class ResultPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["result"] = "result"
    lookup_output: LookupRecord | LookupCollection | LookupTimeseries = Field(
        discriminator="kind"
    )
    turn_count: int = Field(ge=0)

class ErrorPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["error"] = "error"
    error_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False

class PermissionRequestPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["permission_request"] = "permission_request"
    tool_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)

class PermissionResponsePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["permission_response"] = "permission_response"
    granted: bool
    tool_id: str = Field(min_length=1)

class CancelPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["cancel"] = "cancel"
    reason: str = Field(min_length=1, default="coordinator_requested")
```

### 2.3 Closed discriminated union

```python
from typing import Annotated

AgentMessagePayload = Annotated[
    TaskPayload
    | ResultPayload
    | ErrorPayload
    | PermissionRequestPayload
    | PermissionResponsePayload
    | CancelPayload,
    Field(discriminator="kind"),
]
"""Closed union — six variants, no Any, no open-ended dict."""
```

### 2.4 `AgentMessage`

```python
from datetime import datetime, UTC

class AgentMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    sender: str = Field(min_length=1, max_length=128)
    recipient: str = Field(min_length=1, max_length=128)
    msg_type: MessageType
    payload: AgentMessagePayload
    timestamp: datetime
    correlation_id: UUID | None = None

    @model_validator(mode="after")
    def _msg_type_matches_payload_kind(self) -> "AgentMessage":
        """Invariant: msg_type enum value == payload.kind string."""
        if self.msg_type.value != self.payload.kind:
            raise ValueError(
                f"msg_type={self.msg_type.value!r} does not match "
                f"payload.kind={self.payload.kind!r}"
            )
        return self
```

---

## 3. Coordinator output

Module: `src/kosax/agents/plan.py`
FR traces: FR-005

```python
from enum import StrEnum

class PlanStatus(StrEnum):
    complete = "complete"
    partial = "partial"
    no_results = "no_results"
    failed = "failed"

class ExecutionMode(StrEnum):
    sequential = "sequential"
    parallel = "parallel"

class StepStatus(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    complete = "complete"
    failed = "failed"

class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    ministry: str = Field(min_length=1, max_length=64)
    action: str = Field(min_length=1)
    depends_on: list[int] = Field(default_factory=list)
    """Indices into CoordinatorPlan.steps; empty list means 'no predecessors'."""
    execution_mode: ExecutionMode
    status: StepStatus = StepStatus.pending

class CoordinatorPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: UUID
    status: PlanStatus
    steps: list[PlanStep]
    worker_correlation_ids: list[UUID]
    """Every correlation_id of the worker `result` messages that contributed.

    Zero-orphan-id invariant (SC-002): every element here MUST correspond to a
    result message delivered before the Synthesis phase began.
    """
    message: str | None = None
    """Human-readable summary; populated when status is `no_results` or `partial`."""

    @model_validator(mode="after")
    def _depends_on_indices_are_valid(self) -> "CoordinatorPlan":
        n = len(self.steps)
        for i, step in enumerate(self.steps):
            for dep in step.depends_on:
                if not 0 <= dep < n:
                    raise ValueError(
                        f"steps[{i}].depends_on references out-of-range index {dep}"
                    )
                if dep == i:
                    raise ValueError(f"steps[{i}].depends_on references itself")
        return self
```

---

## 4. Mailbox interface

Module: `src/kosax/agents/mailbox/base.py`
FR traces: FR-014, FR-022

```python
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

class Mailbox(ABC):
    """Abstract interface so Phase 3 Redis backend drops in without
    coordinator/worker changes.
    """

    @abstractmethod
    async def send(self, message: AgentMessage) -> None:
        """At-least-once delivery. MUST fsync before returning.

        Raises:
            MailboxOverflowError: per-session message cap exceeded.
            MailboxWriteError: filesystem unwritable or fsync failed.
        """

    @abstractmethod
    async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        """Yield messages addressed to `recipient` in per-sender FIFO order.

        Cross-sender ordering is unspecified.  Blocks indefinitely when no
        messages are pending (caller must use `asyncio.wait_for` for timeouts).
        """

    @abstractmethod
    async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        """On coordinator startup: yield unread messages from prior runs.

        Messages are marked consumed after successful processing; subsequent
        replays do not re-emit them.
        """
```

---

## 5. `FileMailbox` on-disk layout

Module: `src/kosax/agents/mailbox/file_mailbox.py`

```text
$KOSAX_AGENT_MAILBOX_ROOT/
└── <session_id>/
    ├── coordinator/
    │   ├── <message_id>.json             # unconsumed
    │   ├── <message_id>.json.consumed    # marker: reader processed this
    │   └── ...
    └── worker-<role>-<uuid4>/
        ├── <message_id>.json
        ├── <message_id>.json.consumed
        └── ...
```

**File write order** (per `send`):

1. Serialize `AgentMessage` to JSON bytes via `model_dump_json()`.
2. Write to `<dir>/<id>.json.tmp` with `os.open(flags=O_WRONLY|O_CREAT|O_EXCL, mode=0o600)`.
3. `write()` + `os.fsync(fd)` + `close(fd)`.
4. `os.rename(tmp, final)` — atomic on POSIX.
5. `os.fsync(dir_fd)` to persist the directory entry.
6. Only then `send()` returns.

**Consumption marker** (per reader-ack):

1. Create `<id>.json.consumed.tmp` with `os.open(O_WRONLY|O_CREAT|O_EXCL, 0o600)`.
2. `write(b"")` + `os.fsync(fd)` + `close(fd)`.
3. `os.rename(tmp, final)`.
4. `os.fsync(dir_fd)`.

**Overflow check** (FR-021): before step 2 of the write order, count `.json` files under `<session_id>/` (excluding `.consumed` markers). If `≥ KOSAX_AGENT_MAILBOX_MAX_MESSAGES`, raise `MailboxOverflowError`.

**Routing invariant** (FR-025): `receive(recipient)` walks `<session_id>/*/` and yields only messages whose `recipient` field equals the argument. Messages addressed to a different recipient are NOT yielded — even if the caller has read access to the filesystem. The invariant is enforced in code, not in POSIX permissions.

---

## 6. Exceptions

Module: `src/kosax/agents/errors.py`

```python
class AgentConfigurationError(ValueError):
    """AgentContext rejected at spawn — e.g., empty specialist_role,
    tool registry containing tools other than lookup/resolve_location.
    """

class AgentIsolationViolation(RuntimeError):
    """Detected an attempt to mutate state shared across workers."""

class MailboxOverflowError(RuntimeError):
    """Per-session mailbox message cap exceeded (FR-021)."""

class MailboxWriteError(IOError):
    """Filesystem unwritable, fsync failed, or mailbox root uninitialisable."""

class PermissionDeniedError(RuntimeError):
    """Raised inside the worker when ConsentGateway returns False.

    Caught by Worker.run() and converted into an `error` message to the
    coordinator (FR-026). Not propagated to the outer caller.
    """
```

---

## 7. State transitions

### 7.1 Coordinator phase machine

```text
IDLE ──dispatch()──► RESEARCH ──all workers done──► SYNTHESIS
                         │                              │
                         │                              ▼
                         │                         produces CoordinatorPlan
                         │                              │
                         ▼                              ▼
                    cancel()─────────► CANCELLED   IMPLEMENTATION
                                                        │
                                                        ▼
                                                   VERIFICATION
                                                        │
                                                        ▼
                                                      DONE
```

Each transition emits exactly one `gen_ai.agent.coordinator.phase` span (FR-028, SC-006).

### 7.2 Worker lifecycle

```text
SPAWNED ──run()──► RUNNING ──tool loop ends──► POSTING_RESULT ──► DONE
                      │
                      │ LookupError(auth_required)
                      ▼
                  WAIT_CONSENT ──permission_response granted──► RUNNING
                      │
                      │ denied
                      ▼
                  POSTING_ERROR ──► DONE
                      │
                      │ cancel received OR parent task cancelled
                      ▼
                  CANCELLED (asyncio.CancelledError propagates)
```

---

## 8. Observability attribute inventory

Module: `src/kosax/observability/semconv.py` (extended)
FR traces: FR-028..FR-031

New string constants (all `kosax.agent.*`):

| Constant | Value | Used by span |
|---|---|---|
| `KOSAX_AGENT_COORDINATOR_PHASE` | `"kosax.agent.coordinator.phase"` | `gen_ai.agent.coordinator.phase` |
| `KOSAX_AGENT_ROLE` | `"kosax.agent.role"` | `gen_ai.agent.worker.iteration` |
| `KOSAX_AGENT_SESSION_ID` | `"kosax.agent.session_id"` | `gen_ai.agent.worker.iteration` |
| `KOSAX_AGENT_MAILBOX_MSG_TYPE` | `"kosax.agent.mailbox.msg_type"` | `gen_ai.agent.mailbox.message` |
| `KOSAX_AGENT_MAILBOX_CORRELATION_ID` | `"kosax.agent.mailbox.correlation_id"` | `gen_ai.agent.mailbox.message` |
| `KOSAX_AGENT_MAILBOX_SENDER` | `"kosax.agent.mailbox.sender"` | `gen_ai.agent.mailbox.message` |
| `KOSAX_AGENT_MAILBOX_RECIPIENT` | `"kosax.agent.mailbox.recipient"` | `gen_ai.agent.mailbox.message` |

These names MUST be submitted to Epic #501's boundary table before any collector deploys (FR-031).

---

## 9. Settings fields (extension to `KosaxSettings`)

Module: `src/kosax/settings.py` (additive)
FR traces: FR-032..FR-036

```python
class KosaxSettings(BaseSettings):
    ...  # existing fields

    # --- Agent swarm (Epic #13) ---
    agent_mailbox_root: Path = Field(
        default_factory=lambda: Path.home() / ".kosax" / "mailbox",
    )
    """Root directory for FileMailbox (KOSAX_AGENT_MAILBOX_ROOT)."""

    agent_mailbox_max_messages: int = Field(default=1000, ge=100, le=10_000)
    """Per-session message cap (KOSAX_AGENT_MAILBOX_MAX_MESSAGES)."""

    agent_max_workers: int = Field(default=4, ge=1, le=16)
    """Max concurrent workers per coordinator (KOSAX_AGENT_MAX_WORKERS)."""

    agent_worker_timeout_seconds: int = Field(default=120, ge=10, le=600)
    """Worker timeout before coordinator cancels (KOSAX_AGENT_WORKER_TIMEOUT_SECONDS)."""
```

All four fields documented in `docs/configuration.md § Agent Swarm` (FR-036).

---

## Phase 1 Exit Checklist

- [x] Every entity in spec § Key Entities mapped to a Pydantic v2 model above.
- [x] No `Any` / `dict[str, Any]` on any public field.
- [x] All models use `extra="forbid"`; frozen where immutability is required.
- [x] Discriminated union on `AgentMessagePayload.kind` closed at six branches.
- [x] State-transition diagrams match spec FRs.
- [x] Observability attributes listed as constants (no string duplication).
- [x] Settings fields match FR-032..FR-036 ranges and defaults.

**Phase 1 data-model gate**: PASS.
