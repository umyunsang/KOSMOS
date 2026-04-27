# SPDX-License-Identifier: Apache-2.0
"""Asyncio-based JSONL stdio reader/writer loop for the TUI ↔ backend IPC bridge.

Protocol
--------
* Every frame is a single line of JSON terminated by a newline (``\\n``).
* The backend reads frames from ``stdin`` and writes frames to ``stdout``.
* ``stderr`` is reserved for diagnostic / log output; TUI consumes it for crash notices.
* Graceful shutdown: ``SIGTERM`` / ``SIGINT`` → drain in-flight work → write
  ``session_event {event="exit"}`` → flush stdout → exit 0.
* ``stdout`` is flushed after every written frame (FR-005 ordering invariant).

Usage
-----
This module is invoked by the CLI when ``--ipc stdio`` is passed::

    uv run kosmos --ipc stdio

The ``run()`` coroutine is the public entry point; it blocks until the session
exits.  The ``write_frame()`` helper is available for code that needs to push
frames from outside this module.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import sys
import time
import uuid
from collections.abc import Callable
from datetime import UTC
from types import FrameType
from typing import TYPE_CHECKING, Any, Literal, cast

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from pydantic import TypeAdapter, ValidationError

from kosmos.ipc.envelope import attach_envelope_span_attributes
from kosmos.ipc.frame_schema import (
    ErrorFrame,
    IPCFrame,
    SessionEventFrame,
)

if TYPE_CHECKING:
    from kosmos.session.manager import SessionManager

logger = logging.getLogger(__name__)

# Module-level tracer — follows the same pattern as kosmos.tools.executor and
# kosmos.engine.query (trace.get_tracer(__name__) at module load time).
_tracer = trace.get_tracer(__name__)

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_frame_adapter: TypeAdapter[Any] = TypeAdapter(IPCFrame)


def _serialize_primitive_result(raw: object) -> dict[str, Any]:
    """Coerce a primitive return value to a JSON-serialisable dict.

    Pydantic models go through ``model_dump(mode="json")``; everything else
    falls back to ``{"raw": str(value)}`` so the envelope round-trip stays
    safe. Helper extracted from inline expressions to keep the dispatcher
    body under the line-length limit.
    """
    dump = getattr(raw, "model_dump", None)
    if callable(dump):
        result = dump(mode="json")
        if isinstance(result, dict):
            return result
        return {"raw": result}
    return {"raw": str(raw)}


# Module-level stdout lock — prevents interleaved JSON if multiple async tasks
# write simultaneously (guards the flush-after-every-frame invariant).
_stdout_lock: asyncio.Lock | None = None


def _get_stdout_lock() -> asyncio.Lock:
    global _stdout_lock
    if _stdout_lock is None:
        _stdout_lock = asyncio.Lock()
    return _stdout_lock


# ---------------------------------------------------------------------------
# Frame I/O primitives
# ---------------------------------------------------------------------------


async def write_frame(
    frame: IPCFrame,
    *,
    _assembly_start_ns: int | None = None,
    tx_cache_state: Literal["miss", "hit", "stored"] | None = None,
) -> None:
    """Serialise *frame* to a single JSON line and write it to stdout.

    Flushes stdout immediately after every frame to preserve the FIFO ordering
    invariant required by the TUI (FR-005).

    Thread-safety: serialised by ``_stdout_lock`` so concurrent coroutines
    cannot interleave partial JSON.

    OTEL: emits a ``kosmos.ipc.frame`` child span (FR-053) with direction
    ``"outbound"``.  ``_assembly_start_ns`` is the ``time.monotonic_ns()``
    captured by the caller before building the frame payload; when absent,
    the span clock starts at the write call itself.  ``tx_cache_state`` is
    forwarded from the :class:`~kosmos.ipc.transaction_lru.TransactionLRU`
    path for irreversible-tool frames (Spec 032 T048 / FR-053).
    """
    t0_ns = _assembly_start_ns if _assembly_start_ns is not None else time.monotonic_ns()
    payload = frame.model_dump_json() + "\n"
    encoded = payload.encode("utf-8")
    lock = _get_stdout_lock()
    with _tracer.start_as_current_span("kosmos.ipc.frame") as span:
        try:
            async with lock:
                sys.stdout.buffer.write(encoded)
                sys.stdout.buffer.flush()
            latency_ms = (time.monotonic_ns() - t0_ns) / 1_000_000
            span.set_attribute("kosmos.session.id", frame.session_id)
            span.set_attribute("kosmos.frame.kind", frame.kind)
            span.set_attribute("kosmos.frame.direction", "outbound")
            span.set_attribute("kosmos.ipc.latency_ms", latency_ms)
            attach_envelope_span_attributes(frame, tx_cache_state=tx_cache_state)
        except Exception as exc:  # noqa: BLE001
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR))
            raise


def _write_frame_sync(frame: IPCFrame) -> None:
    """Synchronous variant used in signal handlers (no event loop available)."""
    payload = frame.model_dump_json() + "\n"
    sys.stdout.buffer.write(payload.encode("utf-8"))
    sys.stdout.buffer.flush()


# ---------------------------------------------------------------------------
# Reader loop
# ---------------------------------------------------------------------------


async def _reader_loop(
    stream: asyncio.StreamReader,
    on_frame: Callable[[IPCFrame], Any],
    session_id: str,
) -> None:
    """Read newline-delimited JSON frames from *stream* and dispatch them.

    Malformed lines are logged at ERROR and an ``error`` frame is sent back
    rather than crashing the loop (data-model.md § 1.4).
    """
    while True:
        try:
            line = await stream.readline()
        except (asyncio.IncompleteReadError, ConnectionResetError):
            logger.debug("stdin EOF or connection reset — stopping reader loop")
            break

        if not line:
            logger.debug("stdin EOF — stopping reader loop")
            break

        raw = line.decode("utf-8", errors="replace").strip()
        if not raw:
            continue  # skip blank lines

        try:
            frame = _frame_adapter.validate_json(raw)
        except (ValidationError, ValueError) as exc:
            logger.error("IPC decode error: %s | raw=%r", exc, raw[:200])
            # Emit an error frame back to the TUI (malformed input from TUI
            # should be surfaced, not silently dropped).
            err_frame = ErrorFrame(
                session_id=session_id,
                correlation_id=str(uuid.uuid4()),
                role="backend",
                ts=_utcnow(),
                kind="error",
                code="ipc_decode_error",
                message="Failed to decode IPC frame from TUI",
                details={"raw_preview": raw[:200]},
            )
            await write_frame(err_frame)
            continue

        logger.debug("IPC frame received: kind=%s session=%s", frame.kind, frame.session_id)
        _dispatch_start_ns = time.monotonic_ns()
        with _tracer.start_as_current_span("kosmos.ipc.frame") as span:
            try:
                result = on_frame(frame)
                if asyncio.iscoroutine(result):
                    await result
                latency_ms = (time.monotonic_ns() - _dispatch_start_ns) / 1_000_000
                span.set_attribute("kosmos.session.id", frame.session_id)
                span.set_attribute("kosmos.frame.kind", frame.kind)
                span.set_attribute("kosmos.frame.direction", "inbound")
                span.set_attribute("kosmos.ipc.latency_ms", latency_ms)
                attach_envelope_span_attributes(frame)
            except Exception as exc:  # noqa: BLE001
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                logger.exception("on_frame handler raised: %s", exc)


# ---------------------------------------------------------------------------
# Shutdown helpers
# ---------------------------------------------------------------------------


def _utcnow() -> str:
    """Return current UTC time as RFC 3339 string."""
    from datetime import datetime

    return (
        datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{datetime.now(tz=UTC).microsecond // 1000:03d}Z"
    )


async def _emit_exit_frame(session_id: str) -> None:
    """Write a ``session_event {event='exit'}`` frame and flush stdout."""
    exit_frame = SessionEventFrame(
        session_id=session_id,
        correlation_id=str(uuid.uuid4()),
        role="backend",
        ts=_utcnow(),
        kind="session_event",
        event="exit",
        payload={},
    )
    await write_frame(exit_frame)
    logger.debug("Emitted session_event exit frame")


# ---------------------------------------------------------------------------
# Session-event dispatcher
# ---------------------------------------------------------------------------


async def _dispatch_session_event(
    event: str,
    payload: dict[str, Any],
    session_id: str,
    sm: SessionManager,
    shutdown: asyncio.Event,
    correlation_id: str,
) -> None:
    """Route a ``session_event`` frame to the appropriate :class:`SessionManager` method.

    This helper is intentionally kept free of any ``try/except`` so that the
    caller (``_handle_frame``) can catch errors uniformly and emit an
    ``ErrorFrame`` back to the TUI (FR-010 resilience rule).

    Parameters
    ----------
    event:
        One of ``save | load | list | resume | new | exit``.
    payload:
        Event-specific payload dict from the inbound frame.
    session_id:
        The ``session_id`` carried on the inbound frame — used for reply frames.
    sm:
        Active :class:`~kosmos.session.manager.SessionManager` instance.
    shutdown:
        Event that signals the stdio loop to exit when set.
    """
    from kosmos.session.store import list_sessions as _list_sessions

    if event == "new":
        meta = await sm.new_session()
        reply = SessionEventFrame(
            session_id=meta.session_id,
            correlation_id=correlation_id,
            role="backend",
            ts=_utcnow(),
            kind="session_event",
            event="new",
            payload={"session_id": meta.session_id},
        )
        await write_frame(reply)
        logger.debug("session_event new — created session %s", meta.session_id)

    elif event == "save":
        # save_turn is called by the tool-loop per-turn; /save is a checkpoint
        # command.  Emit an ack so the TUI can update its status bar.
        active_sid = sm.session_id or session_id
        reply = SessionEventFrame(
            session_id=active_sid,
            correlation_id=correlation_id,
            role="backend",
            ts=_utcnow(),
            kind="session_event",
            event="save",
            payload={"session_id": active_sid},
        )
        await write_frame(reply)
        logger.debug("session_event save — ack for session %s", active_sid)

    elif event == "list":
        metas = await _list_sessions(session_dir=sm._session_dir)  # noqa: SLF001
        sessions_payload = [
            {
                "id": m.session_id,
                "created_at": m.created_at.isoformat(),
                "turn_count": m.message_count // 2,
            }
            for m in metas
        ]
        active_sid = sm.session_id or session_id
        reply = SessionEventFrame(
            session_id=active_sid,
            correlation_id=correlation_id,
            role="backend",
            ts=_utcnow(),
            kind="session_event",
            event="list",
            payload={"sessions": sessions_payload},
        )
        await write_frame(reply)
        logger.debug("session_event list — returned %d sessions", len(sessions_payload))

    elif event == "resume":
        target_id: str = payload["id"]
        messages = await sm.resume_session(target_id)
        reply = SessionEventFrame(
            session_id=target_id,
            correlation_id=correlation_id,
            role="backend",
            ts=_utcnow(),
            kind="session_event",
            event="load",
            payload={
                "session_id": target_id,
                "messages": [msg.model_dump(mode="json") for msg in messages],
            },
        )
        await write_frame(reply)
        logger.debug(
            "session_event resume — loaded session %s (%d messages)",
            target_id,
            len(messages),
        )

    elif event == "load":
        # load is backend → TUI only; reject TUI → backend direction.
        err = ErrorFrame(
            session_id=session_id,
            correlation_id=correlation_id,
            role="backend",
            ts=_utcnow(),
            kind="error",
            code="invalid_direction",
            message="session_event 'load' is a backend-to-TUI frame; TUI must use 'resume'",
            details={"event": event},
        )
        await write_frame(err)
        logger.warning("session_event load received from TUI — rejected (invalid direction)")

    elif event == "exit":
        logger.debug("session_event exit — setting shutdown flag")
        shutdown.set()

    else:
        # Forward-compatible: unknown events are logged and dropped.
        logger.warning("Unknown session_event: %r", event)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def run(  # noqa: C901
    session_id: str | None = None,
    on_frame: Callable[[IPCFrame], Any] | None = None,
    session_manager: SessionManager | None = None,
) -> None:
    """Run the asyncio JSONL stdio loop until stdin closes or a signal arrives.

    Parameters
    ----------
    session_id:
        Session ULID shared with the TUI.  If omitted a random placeholder is
        used (suitable for smoke tests).
    on_frame:
        Callable invoked for every inbound ``IPCFrame``.  May be a coroutine
        function.  Defaults to the built-in ``_handle_frame`` handler that
        echoes ``user_input`` frames and routes ``session_event`` frames to the
        session manager.
    session_manager:
        :class:`~kosmos.session.manager.SessionManager` instance used by the
        default ``_handle_frame`` handler to implement session lifecycle
        operations.  When ``None`` a default ``SessionManager()`` is
        constructed (uses ``~/.kosmos/sessions``).
    """
    from kosmos.session.manager import SessionManager as _SessionManager

    sid = session_id or str(uuid.uuid4())
    logger.info("IPC stdio loop starting — session_id=%s", sid)

    # Resolve session manager; always non-None inside this coroutine.
    _sm: _SessionManager = session_manager if session_manager is not None else _SessionManager()

    # Install shutdown flag
    _shutdown = asyncio.Event()

    def _handle_signal(signum: int, _frame: FrameType | None = None) -> None:
        sig_name = signal.Signals(signum).name
        logger.info("Received signal %s — initiating graceful shutdown", sig_name)
        _shutdown.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _handle_signal, int(sig))
        except (ValueError, NotImplementedError):
            # Windows or restricted environments — fall back to signal.signal
            signal.signal(sig, _handle_signal)

    # Connect asyncio StreamReader to sys.stdin.buffer
    stdin_reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(stdin_reader)
    transport, _ = await loop.connect_read_pipe(lambda: protocol, sys.stdin.buffer)

    # Default on_frame: route `user_input` to the FriendliAI LLM (Epic #1633
    # FR-007/FR-017) and `session_event` to the session manager. Wraps every
    # handler in try/except so malformed payloads never crash the loop
    # (FR-010).
    #
    # Per-session conversation history is kept in `_llm_sessions` below; each
    # user_input appends one message, the model's reply is appended as
    # assistant, and subsequent turns see the full history. System prompt is
    # loaded lazily from Spec 026 PromptLoader on first turn.
    _llm_sessions: dict[str, list[dict[str, object]]] = {}
    _llm_client_ref: list[object] = []  # holds the singleton LLMClient
    _llm_system_prompt_cached: list[str | None] = [None]

    # Spec 1978 T026 — pending tool calls registry per data-model.md D1.
    # Keyed by call_id (ULID emitted in ToolCallFrame), valued by an asyncio
    # Future that resolves when the matching ToolResultFrame arrives.
    _pending_calls: dict[str, asyncio.Future[Any]] = {}

    # Spec 1978 T043-T049 — pending permission requests (D2 invariant).
    # Keyed by request_id (UUID4), resolved when the TUI sends a
    # permission_response frame with the matching request_id.
    # Timeout = 60s; synthetic deny on expiry.
    _pending_perms: dict[str, asyncio.Future[Any]] = {}

    # Per-session auto-approved tool IDs (allow_session grants).
    # Keyed by session_id → set of tool_ids approved for the session lifetime.
    _session_grants: dict[str, set[str]] = {}

    async def _ensure_llm_client() -> object:
        if not _llm_client_ref:
            from kosmos.llm.client import LLMClient  # noqa: PLC0415
            from kosmos.llm.config import LLMClientConfig  # noqa: PLC0415

            cfg = LLMClientConfig()
            _llm_client_ref.append(LLMClient(config=cfg))
        return _llm_client_ref[0]

    async def _ensure_system_prompt() -> str | None:
        if _llm_system_prompt_cached[0] is not None:
            return _llm_system_prompt_cached[0] or None
        try:
            from pathlib import Path  # noqa: PLC0415

            from kosmos.context.prompt_loader import PromptLoader  # noqa: PLC0415

            # Default manifest lives at repo-root/prompts/manifest.yaml. The
            # stdio backend runs from repo root when invoked via
            # `uv run kosmos --ipc stdio`, so resolve relative to CWD.
            manifest = Path("prompts") / "manifest.yaml"
            if not manifest.is_file():
                _llm_system_prompt_cached[0] = ""
                return None
            loader = PromptLoader(manifest_path=manifest)
            _llm_system_prompt_cached[0] = loader.load("system_v1")
        except Exception:  # noqa: BLE001
            _llm_system_prompt_cached[0] = ""  # remember "tried and failed"
        return _llm_system_prompt_cached[0] or None

    async def _handle_user_input_llm(frame: IPCFrame) -> None:  # noqa: C901
        from kosmos.ipc.frame_schema import (  # noqa: PLC0415
            AssistantChunkFrame,
            UserInputFrame,
        )
        from kosmos.llm.models import ChatMessage  # noqa: PLC0415

        if not isinstance(frame, UserInputFrame):
            return

        history = _llm_sessions.setdefault(frame.session_id, [])
        if not history:
            system_text = await _ensure_system_prompt()
            if system_text:
                history.append({"role": "system", "content": system_text})
        history.append({"role": "user", "content": frame.text})

        client = await _ensure_llm_client()
        messages: list[ChatMessage] = []
        for m in history:
            role = str(m.get("role", "user"))
            content = m.get("content")
            if role in ("system", "user", "assistant", "tool") and isinstance(content, str):
                messages.append(
                    ChatMessage(
                        role=role,  # type: ignore[arg-type]
                        content=content,
                    )
                )

        message_id = str(uuid.uuid4())
        assistant_text_chunks: list[str] = []
        stream_error: Exception | None = None

        try:
            async for event in client.stream(  # type: ignore[attr-defined]
                messages=messages, max_tokens=2048
            ):
                event_type = getattr(event, "type", None)
                if event_type == "content_delta":
                    delta = getattr(event, "content", "") or ""
                    if delta:
                        assistant_text_chunks.append(delta)
                        chunk_frame = AssistantChunkFrame(
                            session_id=frame.session_id,
                            correlation_id=frame.correlation_id,
                            role="llm",
                            ts=_utcnow(),
                            kind="assistant_chunk",
                            message_id=message_id,
                            delta=delta,
                            done=False,
                        )
                        await write_frame(chunk_frame)
                elif event_type == "done":
                    break
                elif event_type == "error":
                    stream_error = RuntimeError(
                        str(getattr(event, "content", "unknown stream error"))
                    )
                    break
        except Exception as exc:  # noqa: BLE001
            stream_error = exc

        full_text = "".join(assistant_text_chunks)
        if stream_error is not None:
            err = ErrorFrame(
                session_id=frame.session_id,
                correlation_id=frame.correlation_id or str(uuid.uuid4()),
                role="llm",
                ts=_utcnow(),
                kind="error",
                code="llm_stream_error",
                message=str(stream_error),
                details={"message_id": message_id},
            )
            await write_frame(err)
            return

        # Terminal chunk — done=True signals end-of-turn to the TS side.
        terminal = AssistantChunkFrame(
            session_id=frame.session_id,
            correlation_id=frame.correlation_id,
            role="llm",
            ts=_utcnow(),
            kind="assistant_chunk",
            message_id=message_id,
            delta="",
            done=True,
        )
        await write_frame(terminal)

        history.append({"role": "assistant", "content": full_text})

    import os as _os_chat_env  # noqa: PLC0415

    # Spec 1978 T030 — tool-result wait timeout (env-overridable).
    # contracts/tool-bridge-protocol.md gates the asyncio.gather on this value.
    _TOOL_RESULT_TIMEOUT_S = float(  # noqa: N806 — env-derived constant, function-scoped to avoid module-import-time env reads
        _os_chat_env.environ.get("KOSMOS_TOOL_RESULT_TIMEOUT_SECONDS", "120")
    )
    # Spec 1978 T029 — bound the CC query-engine agentic loop to prevent
    # infinite tool-recall. KOSMOS adopts the CC 2.1.88 query engine
    # architecture (native function calling + streaming + parallel tool
    # dispatch), NOT the academic ReAct paradigm — see memory
    # `feedback_kosmos_uses_cc_query_engine`. The KOSMOS_REACT_MAX_TURNS env
    # name is preserved for backward compatibility with already-shipped
    # configuration; the documented variable is logically the agentic-loop
    # max-turn cap.
    _AGENTIC_LOOP_MAX_TURNS = int(  # noqa: N806 — env-derived constant
        _os_chat_env.environ.get(
            "KOSMOS_AGENTIC_LOOP_MAX_TURNS",
            _os_chat_env.environ.get("KOSMOS_REACT_MAX_TURNS", "8"),
        )
    )
    # Spec 1978 T053 — eager-import the Mock adapter tree so every adapter
    # self-registers with its primitive dispatcher before the first chat
    # turn arrives. Equivalent to plan.md "Mock adapter activation"; failure
    # is logged-only because Live tooling can still serve simple queries.
    try:
        import kosmos.tools.mock  # noqa: F401, PLC0415
    except Exception:  # noqa: BLE001
        logger.exception("failed to import kosmos.tools.mock — Mock adapters unavailable")

    # -----------------------------------------------------------------------
    # Spec 1978 T043-T049/T052 — Permission gauntlet bridge
    # -----------------------------------------------------------------------

    _PERM_TIMEOUT_S: float = float(  # noqa: N806 — env-derived constant
        _os_chat_env.environ.get("KOSMOS_PERMISSION_TIMEOUT_SECONDS", "60")
    )

    # Primitives that require a citizen permission request when called outside
    # an existing session-grant. Spec 033 Layer 1 (L1) exempts verify/lookup/
    # resolve_location (read-only, public-tier); submit/subscribe are side-
    # effecting (Layer 2/3) and always enter the bridge.
    _PERMISSION_GATED_PRIMITIVES: frozenset[str] = frozenset({"submit", "subscribe"})  # noqa: N806

    async def _check_permission_gate(
        call_id: str,
        fname: str,
        args_obj: dict[str, object],
        session_id: str,
        correlation_id: str,
    ) -> bool:
        """Return True if the tool call is permitted to proceed.

        For gated primitives (submit/subscribe):
        1. Check session_grants cache — auto-allow if already approved.
        2. Emit PermissionRequestFrame and await citizen decision (60 s).
        3. On allow_session: cache grant; write consent receipt.
        4. On allow_once: write consent receipt, no cache.
        5. On deny or timeout: emit synthetic tool_result with error, return False.

        For non-gated primitives (lookup/resolve_location/verify): return True
        immediately without touching the bridge.
        """
        from kosmos.ipc.frame_schema import (  # noqa: PLC0415
            PermissionRequestFrame,
            ToolResultEnvelope,
            ToolResultFrame,
        )

        if fname not in _PERMISSION_GATED_PRIMITIVES:
            with _tracer.start_as_current_span("kosmos.permission") as span:
                span.set_attribute("kosmos.permission.mode", "auto_allow")
                span.set_attribute("kosmos.permission.decision", "allow_once")
                span.set_attribute("kosmos.tool.dispatched", fname)
            return True

        # Check session grant cache first (allow_session shortcut — T048).
        session_grant_set = _session_grants.get(session_id, set())
        tool_key = f"{fname}:{args_obj.get('tool_id', fname)}"
        if tool_key in session_grant_set:
            with _tracer.start_as_current_span("kosmos.permission") as span:
                span.set_attribute("kosmos.permission.mode", "auto_allow")
                span.set_attribute("kosmos.permission.decision", "allow_session")
                span.set_attribute("kosmos.tool.dispatched", fname)
            logger.debug("permission: session_grant hit for %s session=%s", tool_key, session_id)
            return True

        # Determine risk level and description from primitive type
        _PRIM_RISK: dict[str, str] = {"submit": "high", "subscribe": "medium"}  # noqa: N806
        _PRIM_KO: dict[str, str] = {  # noqa: N806
            "submit": "정부 API에 데이터를 제출합니다. 이 작업은 되돌릴 수 없습니다.",
            "subscribe": "공공 데이터 스트림을 구독합니다.",
        }
        _PRIM_EN: dict[str, str] = {  # noqa: N806
            "submit": "Submit data to a government API. This action is irreversible.",
            "subscribe": "Subscribe to a public data stream.",
        }

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        _pending_perms[request_id] = loop.create_future()

        with _tracer.start_as_current_span("kosmos.permission") as perm_span:
            perm_span.set_attribute("kosmos.permission.mode", "ask")
            perm_span.set_attribute("kosmos.tool.dispatched", fname)

            try:
                await write_frame(
                    PermissionRequestFrame(
                        session_id=session_id,
                        correlation_id=correlation_id,
                        role="backend",
                        ts=_utcnow(),
                        kind="permission_request",
                        request_id=request_id,
                        worker_id="main",
                        primitive_kind=fname,  # type: ignore[arg-type]
                        description_ko=_PRIM_KO.get(fname, "도구를 실행합니다."),
                        description_en=_PRIM_EN.get(fname, "Invoke tool."),
                        risk_level=_PRIM_RISK.get(fname, "medium"),  # type: ignore[arg-type]
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("permission: failed to emit permission_request: %s", exc)
                _pending_perms.pop(request_id, None)
                perm_span.set_attribute("kosmos.permission.decision", "deny")
                return False

            # Await citizen decision with timeout (D2 invariant).
            decision_frame: Any = None
            try:
                decision_frame = await asyncio.wait_for(
                    _pending_perms[request_id],
                    timeout=_PERM_TIMEOUT_S,
                )
                perm_span.set_attribute("kosmos.permission.decision", "allow_once")
            except TimeoutError:
                logger.warning(
                    "permission: timeout waiting for response to request_id=%s", request_id
                )
                perm_span.set_attribute("kosmos.permission.decision", "timeout")
                _pending_perms.pop(request_id, None)
                # Emit synthetic denied tool_result so the LLM turn resolves.
                denied_env = ToolResultEnvelope(
                    kind=cast("Any", fname),
                    **{"error": "permission_timeout", "denied": True},
                )
                fut = _pending_calls.get(call_id)
                if fut and not fut.done():
                    denied_result_frame = ToolResultFrame(
                        session_id=session_id,
                        correlation_id=correlation_id,
                        role="backend",
                        ts=_utcnow(),
                        kind="tool_result",
                        call_id=call_id,
                        envelope=denied_env,
                    )
                    fut.set_result(denied_result_frame)
                return False
            finally:
                _pending_perms.pop(request_id, None)

            # Map PermissionResponseFrame.decision → allow/deny per Spec 1978
            # ADR-0002. Spec 287 baseline emitted only "granted" / "denied"; the
            # 3-decision UI vocabulary (allow_once | allow_session | deny) is
            # accepted now that frame_schema.py extends the Literal.
            raw_decision: str = getattr(decision_frame, "decision", "denied")
            is_deny = raw_decision in {"denied", "deny"}
            is_allow_session = raw_decision == "allow_session"
            if is_deny:
                perm_span.set_attribute("kosmos.permission.decision", "deny")
                # Emit synthetic denied tool_result.
                denied_env2 = ToolResultEnvelope(
                    kind=cast("Any", fname),
                    **{"error": "permission_denied", "denied": True},
                )
                fut2 = _pending_calls.get(call_id)
                if fut2 and not fut2.done():
                    denied_result_frame2 = ToolResultFrame(
                        session_id=session_id,
                        correlation_id=correlation_id,
                        role="backend",
                        ts=_utcnow(),
                        kind="tool_result",
                        call_id=call_id,
                        envelope=denied_env2,
                    )
                    fut2.set_result(denied_result_frame2)
                return False

            # Granted — write consent receipt + optionally update session grant cache.
            receipt_id = str(uuid.uuid4())
            decision_label = "allow_session" if is_allow_session else "allow_once"
            perm_span.set_attribute("kosmos.permission.decision", decision_label)
            perm_span.set_attribute("kosmos.consent.receipt_id", receipt_id)

            # Spec 1978 T049 — allow_session caches the tool_id so subsequent
            # same-session same-tool calls bypass the bridge entirely (handled
            # at the top of this function via _session_grants lookup).
            if is_allow_session:
                tool_id_for_cache = str(args_obj.get("tool_id", fname))
                _session_grants.setdefault(session_id, set()).add(tool_id_for_cache)
            try:
                import json as _json_receipt  # noqa: PLC0415
                from pathlib import Path as _Path  # noqa: PLC0415

                consent_dir = _Path.home() / ".kosmos" / "memdir" / "user" / "consent"
                consent_dir.mkdir(parents=True, exist_ok=True)
                receipt_path = consent_dir / f"{receipt_id}.json"
                receipt_data = {
                    "receipt_id": receipt_id,
                    "session_id": session_id,
                    "tool_id": str(args_obj.get("tool_id", fname)),
                    "primitive": fname,
                    "decision": decision_label,
                    "granted_at": _utcnow(),
                    "revoked_at": None,
                }
                receipt_path.write_text(
                    _json_receipt.dumps(receipt_data, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.debug("permission: wrote consent receipt %s", receipt_id)
            except Exception as exc:  # noqa: BLE001
                logger.warning("permission: failed to write consent receipt: %s", exc)

            return True

    async def _handle_permission_response(frame: IPCFrame) -> None:
        """Spec 1978 T047 — consume permission_response and resolve pending Future.

        Maps incoming PermissionResponseFrame.request_id to the waiting
        _pending_perms entry. Frames with no matching request_id are logged
        and silently dropped (forward-compat: stale responses after timeout).
        """
        from kosmos.ipc.frame_schema import PermissionResponseFrame  # noqa: PLC0415

        if not isinstance(frame, PermissionResponseFrame):
            return
        fut = _pending_perms.pop(frame.request_id, None)
        if fut is None:
            logger.debug(
                "permission_response with no pending request (request_id=%s) — ignoring",
                frame.request_id,
            )
            return
        if not fut.done():
            fut.set_result(frame)

    # -----------------------------------------------------------------------
    # Spec 1978 T053b — internal primitive dispatcher
    # -----------------------------------------------------------------------

    async def _dispatch_primitive(  # noqa: C901, PLR0912
        call_id: str,
        fname: str,
        args_obj: dict[str, object],
        session_id: str,
        correlation_id: str,
    ) -> None:
        """Dispatch a single primitive call internally and resolve its pending Future.

        Called immediately after a tool_call frame is emitted and the Future
        is registered in _pending_calls. Routes by fname, awaits the primitive,
        wraps the result in a ToolResultFrame, emits it to the TUI, then
        resolves _pending_calls[call_id] so the agentic-loop continuation can
        inject the result as a role="tool" message.

        Permission gate: submit/subscribe go through _check_permission_gate
        first. On denial/timeout, the gate itself resolves the Future with an
        error envelope, so this function exits early without double-resolution.

        OTEL: sets kosmos.tool.dispatched on the existing session span.
        """

        from kosmos.ipc.frame_schema import (  # noqa: PLC0415
            ToolResultEnvelope,
            ToolResultFrame,
        )

        with _tracer.start_as_current_span("kosmos.tool.dispatch") as span:
            span.set_attribute("kosmos.tool.dispatched", fname)
            span.set_attribute("kosmos.session.id", session_id)

            # ----- Permission gate (T043-T049) -----
            allowed = await _check_permission_gate(
                call_id, fname, args_obj, session_id, correlation_id
            )
            if not allowed:
                # Gate already resolved the Future with an error envelope.
                span.set_attribute("kosmos.permission.decision", "deny")
                return

            result_payload: dict[str, object] = {}
            dispatch_error: str | None = None
            # Each primitive returns a different Pydantic model. Annotate as
            # Any so the branches below can assign without mypy assignment
            # narrowing complaints.
            raw: Any

            try:
                if fname == "verify":
                    from kosmos.primitives.verify import (  # noqa: PLC0415
                        verify,
                    )

                    # Accept both `family` (citizen-facing tool schema) and
                    # `family_hint` (primitive's internal arg name) — KOSMOS
                    # tools-bridge tolerates both.
                    family_hint = str(args_obj.get("family_hint") or args_obj.get("family") or "")
                    session_ctx = cast("dict[str, object]", args_obj.get("session_context") or {})
                    raw = await verify(family_hint=family_hint, session_context=session_ctx)
                    result_payload = {
                        "family": family_hint,
                        "result": _serialize_primitive_result(raw),
                    }

                elif fname == "lookup":
                    from kosmos.tools.executor import ToolExecutor  # noqa: PLC0415
                    from kosmos.tools.lookup import lookup  # noqa: PLC0415
                    from kosmos.tools.models import (  # noqa: PLC0415
                        LookupFetchInput,
                        LookupSearchInput,
                    )
                    from kosmos.tools.registry import ToolRegistry  # noqa: PLC0415

                    mode = str(args_obj.get("mode", "search"))
                    registry = ToolRegistry()
                    executor = ToolExecutor(registry=registry)
                    inp_lk: LookupSearchInput | LookupFetchInput
                    if mode == "search":
                        inp_lk = LookupSearchInput(
                            mode="search",
                            query=str(args_obj.get("query", "")),
                            domain=cast("Any", args_obj.get("domain")),
                            top_k=cast("Any", args_obj.get("top_k")),
                        )
                    else:
                        inp_lk = LookupFetchInput(
                            mode="fetch",
                            tool_id=str(args_obj.get("tool_id", "")),
                            params=cast("dict[str, object]", args_obj.get("params") or {}),
                        )
                    raw = await lookup(
                        inp_lk,
                        registry=registry,
                        executor=executor,
                        session_identity=session_id,
                    )
                    result_payload = {
                        "kind": "lookup",
                        "result": _serialize_primitive_result(raw),
                    }

                elif fname == "resolve_location":
                    from kosmos.tools.models import ResolveLocationInput  # noqa: PLC0415
                    from kosmos.tools.resolve_location import resolve_location  # noqa: PLC0415

                    inp_rl = ResolveLocationInput(
                        query=str(args_obj.get("query", "")),
                        want=str(args_obj.get("want", "coords_and_admcd")),  # type: ignore[arg-type]
                    )
                    raw = await resolve_location(inp_rl)
                    result_payload = {
                        "kind": "resolve_location",
                        "result": _serialize_primitive_result(raw),
                    }

                elif fname == "submit":
                    from kosmos.primitives.submit import submit  # noqa: PLC0415

                    raw = await submit(
                        tool_id=str(args_obj.get("tool_id", "")),
                        params=cast("dict[str, object]", args_obj.get("params") or {}),
                        session_id=session_id,
                    )
                    result_payload = {
                        "kind": "submit",
                        "result": _serialize_primitive_result(raw),
                    }

                elif fname == "subscribe":
                    # T069 streaming events are deferred. Return the SubscriptionHandle.
                    from kosmos.primitives.subscribe import (  # noqa: PLC0415
                        SubscribeInput,
                        subscribe,
                    )

                    inp_sub = SubscribeInput(
                        tool_id=str(args_obj.get("tool_id", "")),
                        params=cast("dict[str, object]", args_obj.get("params") or {}),
                        lifetime_seconds=int(cast("Any", args_obj.get("lifetime_seconds", 300))),
                    )
                    iterator_or_error = subscribe(inp_sub)
                    if hasattr(iterator_or_error, "_handle"):
                        # T069 deferred — keep handle attribute reachable for
                        # future streaming wiring; for now we only confirm
                        # iterator construction and emit a synthetic envelope.
                        result_payload = {
                            "kind": "subscribe",
                            "subscription_id": str(uuid.uuid4()),
                            "tool_id": inp_sub.tool_id,
                            "status": "opened",
                            "note": "Streaming events deferred (T069).",
                        }
                    else:
                        # AdapterNotFoundError or similar
                        result_payload = {
                            "kind": "subscribe",
                            "error": str(iterator_or_error),
                            "tool_id": str(args_obj.get("tool_id", "")),
                        }

                else:
                    dispatch_error = f"unknown primitive {fname!r}"

            except Exception as exc:  # noqa: BLE001
                logger.exception("_dispatch_primitive: %s dispatch failed: %s", fname, exc)
                dispatch_error = str(exc)

            if dispatch_error:
                result_payload = {
                    "kind": fname,
                    "error": dispatch_error,
                    "tool_id": str(args_obj.get("tool_id", fname)),
                }

            # Build ToolResultEnvelope + ToolResultFrame.
            # ToolResultEnvelope uses extra="allow" so extra payload fields are kept.
            # Strip any payload-level "kind" so the kwarg is single-valued.
            payload_kw = {k: v for k, v in result_payload.items() if k != "kind"}
            envelope = ToolResultEnvelope(kind=cast("Any", fname), **payload_kw)
            result_frame = ToolResultFrame(
                session_id=session_id,
                correlation_id=correlation_id,
                role="backend",
                ts=_utcnow(),
                kind="tool_result",
                call_id=call_id,
                envelope=envelope,
            )

            # Emit to TUI for display.
            try:
                await write_frame(result_frame)
            except Exception as exc:  # noqa: BLE001
                logger.warning("_dispatch_primitive: failed to emit tool_result frame: %s", exc)

            # Resolve the pending Future so the agentic loop can continue.
            fut = _pending_calls.pop(call_id, None)
            if fut is not None and not fut.done():
                fut.set_result(result_frame)

    async def _handle_chat_request(frame: IPCFrame) -> None:  # noqa: C901, PLR0915
        """Spec 1978 ADR-0001 — tools-aware chat handler.

        Implements the CC (Claude Code 2.1.88) query-engine agentic loop —
        native function calling + token streaming + parallel tool dispatch
        + content_block accumulation, NOT the academic ReAct paradigm
        (text-marker-based Thought/Action). See memory
        ``feedback_kosmos_uses_cc_query_engine`` for the architectural
        rationale.

        Replaces ``_handle_user_input_llm`` for ``ChatRequestFrame``. Streams
        text deltas as ``AssistantChunkFrame``, emits one ``ToolCallFrame``
        per K-EXAONE function-call, awaits each matching ``ToolResultFrame``
        via ``_pending_calls`` Futures, then injects synthetic
        ``role="tool"`` messages into the local history and re-invokes
        ``LLMClient.stream`` (agentic-loop continuation per ADR-0005).

        Loop is bounded by ``KOSMOS_AGENTIC_LOOP_MAX_TURNS`` (default 8;
        also accepts the legacy ``KOSMOS_REACT_MAX_TURNS``) and the
        per-call wait by ``KOSMOS_TOOL_RESULT_TIMEOUT_SECONDS`` (default 120).
        """
        from kosmos.ipc.frame_schema import (  # noqa: PLC0415
            AssistantChunkFrame,
            ChatRequestFrame,
            ToolCallFrame,
        )
        from kosmos.llm.models import (  # noqa: PLC0415
            ChatMessage as LLMChatMessage,
        )
        from kosmos.llm.models import (
            FunctionCall as LLMFunctionCall,
        )
        from kosmos.llm.models import (
            ToolCall as LLMToolCall,
        )
        from kosmos.llm.models import (
            ToolDefinition as LLMToolDefinition,
        )

        if not isinstance(frame, ChatRequestFrame):
            return

        # Build LLMClient input from the frame payload. Conversation history
        # lives in the TUI per ADR-0005 — backend receives the full slate.
        llm_messages: list[LLMChatMessage] = []
        if frame.system:
            llm_messages.append(LLMChatMessage(role="system", content=frame.system))
        for m in frame.messages:
            llm_messages.append(
                LLMChatMessage(
                    role=m.role,
                    content=m.content,
                    name=m.name,
                    tool_call_id=m.tool_call_id,
                )
            )

        llm_tools: list[LLMToolDefinition] = []
        for t in frame.tools:
            llm_tools.append(LLMToolDefinition.model_validate(t.model_dump()))

        client = await _ensure_llm_client()

        # ---- CC query-engine agentic loop ---------------------------------
        import json as _json  # noqa: PLC0415

        for _turn in range(_AGENTIC_LOOP_MAX_TURNS):
            message_id = str(uuid.uuid4())
            assistant_text_chunks: list[str] = []
            tool_call_buf: dict[int, dict[str, str]] = {}
            stream_error: Exception | None = None

            try:
                async for event in client.stream(  # type: ignore[attr-defined]
                    messages=llm_messages,
                    tools=llm_tools or None,
                    temperature=frame.temperature,
                    top_p=frame.top_p,
                    max_tokens=frame.max_tokens,
                ):
                    event_type = getattr(event, "type", None)
                    if event_type == "content_delta":
                        delta = getattr(event, "content", "") or ""
                        if delta:
                            assistant_text_chunks.append(delta)
                            await write_frame(
                                AssistantChunkFrame(
                                    session_id=frame.session_id,
                                    correlation_id=frame.correlation_id,
                                    role="llm",
                                    ts=_utcnow(),
                                    kind="assistant_chunk",
                                    message_id=message_id,
                                    delta=delta,
                                    done=False,
                                )
                            )
                    elif event_type == "thinking_delta":
                        # K-EXAONE chain-of-thought channel — mirrors CC's
                        # Anthropic ``thinking_delta`` content_block_delta
                        # (``kosmos/llm/_cc_reference/claude.ts:2148-2161``).
                        # Forward as an AssistantChunkFrame on the
                        # ``thinking`` channel; the TUI's deps.ts projects
                        # this to a ``stream_event{thinking_delta}`` and
                        # ``handleMessageFromStream`` routes it via
                        # ``onUpdateLength`` into ``streamingThinking`` so
                        # ``AssistantThinkingMessage`` paints the reasoning
                        # inline. CoT is *not* appended to
                        # ``assistant_text_chunks`` — the inline-tool-call
                        # XML parser only inspects the visible answer
                        # channel, and we never persist reasoning back to
                        # the LLM context.
                        thinking_text = getattr(event, "thinking", "") or ""
                        if thinking_text:
                            await write_frame(
                                AssistantChunkFrame(
                                    session_id=frame.session_id,
                                    correlation_id=frame.correlation_id,
                                    role="llm",
                                    ts=_utcnow(),
                                    kind="assistant_chunk",
                                    message_id=message_id,
                                    delta="",
                                    thinking=thinking_text,
                                    done=False,
                                )
                            )
                    elif event_type == "tool_call_delta":
                        idx = int(getattr(event, "tool_call_index", 0) or 0)
                        slot = tool_call_buf.setdefault(idx, {"id": "", "name": "", "args": ""})
                        cid = getattr(event, "tool_call_id", None)
                        if cid:
                            slot["id"] = cid
                        fname = getattr(event, "function_name", None)
                        if fname:
                            slot["name"] = fname
                        fargs = getattr(event, "function_args_delta", None)
                        if fargs:
                            slot["args"] += fargs
                    elif event_type == "done":
                        break
                    elif event_type == "error":
                        stream_error = RuntimeError(
                            str(getattr(event, "content", "unknown stream error"))
                        )
                        break
            except Exception as exc:  # noqa: BLE001
                stream_error = exc

            if stream_error is not None:
                await write_frame(
                    ErrorFrame(
                        session_id=frame.session_id,
                        correlation_id=frame.correlation_id or str(uuid.uuid4()),
                        role="llm",
                        ts=_utcnow(),
                        kind="error",
                        code="llm_stream_error",
                        message=str(stream_error),
                        details={"message_id": message_id},
                    )
                )
                return

            # No tool calls this turn → terminal chunk + exit agentic loop.
            if not tool_call_buf:
                await write_frame(
                    AssistantChunkFrame(
                        session_id=frame.session_id,
                        correlation_id=frame.correlation_id,
                        role="llm",
                        ts=_utcnow(),
                        kind="assistant_chunk",
                        message_id=message_id,
                        delta="",
                        done=True,
                    )
                )
                return

            # ---- T027/T029 — emit tool_call frames + register Futures -----
            loop = asyncio.get_event_loop()
            issued_calls: list[tuple[str, str]] = []  # (call_id, name)
            assistant_tool_calls: list[LLMToolCall] = []
            for idx in sorted(tool_call_buf.keys()):
                slot = tool_call_buf[idx]
                call_id = slot["id"] or str(uuid.uuid4())
                try:
                    args_obj = _json.loads(slot["args"]) if slot["args"] else {}
                except _json.JSONDecodeError:
                    args_obj = {"_raw": slot["args"]}
                if not isinstance(args_obj, dict):
                    args_obj = {"_value": args_obj}

                fname = slot["name"]
                if fname not in {
                    "lookup",
                    "resolve_location",
                    "submit",
                    "subscribe",
                    "verify",
                }:
                    await write_frame(
                        ErrorFrame(
                            session_id=frame.session_id,
                            correlation_id=frame.correlation_id or str(uuid.uuid4()),
                            role="llm",
                            ts=_utcnow(),
                            kind="error",
                            code="unknown_tool",
                            message=f"Model requested unknown tool {fname!r}",
                            details={"call_id": call_id},
                        )
                    )
                    continue

                _pending_calls[call_id] = loop.create_future()
                issued_calls.append((call_id, fname))
                assistant_tool_calls.append(
                    LLMToolCall(
                        id=call_id,
                        type="function",
                        function=LLMFunctionCall(
                            name=fname,
                            arguments=_json.dumps(args_obj),
                        ),
                    )
                )
                await write_frame(
                    ToolCallFrame(
                        session_id=frame.session_id,
                        correlation_id=frame.correlation_id,
                        role="backend",
                        ts=_utcnow(),
                        kind="tool_call",
                        call_id=call_id,
                        name=fname,  # type: ignore[arg-type]
                        arguments=args_obj,
                    )
                )

                # Spec 1978 T053b — fire internal primitive dispatch as a
                # background task. The task resolves _pending_calls[call_id]
                # when the primitive returns, allowing the gather below to
                # proceed without waiting for an external tool_result frame.
                asyncio.create_task(
                    _dispatch_primitive(
                        call_id,
                        fname,
                        args_obj,
                        frame.session_id,
                        frame.correlation_id,
                    ),
                    name=f"primitive-{fname}-{call_id[:8]}",
                )

            # If every tool call was rejected (whitelist), terminate.
            if not issued_calls:
                await write_frame(
                    AssistantChunkFrame(
                        session_id=frame.session_id,
                        correlation_id=frame.correlation_id,
                        role="llm",
                        ts=_utcnow(),
                        kind="assistant_chunk",
                        message_id=message_id,
                        delta="",
                        done=True,
                    )
                )
                return

            # Append the assistant message that requested tools — the CC
            # query-engine contract requires the function-call envelope to
            # precede the tool messages in the next turn.
            full_text = "".join(assistant_text_chunks)
            llm_messages.append(
                LLMChatMessage(
                    role="assistant",
                    content=full_text,
                    tool_calls=assistant_tool_calls,
                )
            )

            # ---- Await tool_result Futures (gated by T030 timeout) -------
            tasks = [_pending_calls[cid] for cid, _ in issued_calls]
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=_TOOL_RESULT_TIMEOUT_S,
                )
            except TimeoutError:
                # Per contracts/tool-bridge-protocol.md timeout → synthetic
                # error result. Drop pending entries to avoid leaks.
                for cid, _ in issued_calls:
                    pending = _pending_calls.pop(cid, None)
                    if pending and not pending.done():
                        pending.cancel()
                await write_frame(
                    ErrorFrame(
                        session_id=frame.session_id,
                        correlation_id=frame.correlation_id or str(uuid.uuid4()),
                        role="backend",
                        ts=_utcnow(),
                        kind="error",
                        code="tool_timeout",
                        message=(f"Tool result timeout after {_TOOL_RESULT_TIMEOUT_S:.0f}s"),
                        details={
                            "call_ids": [cid for cid, _ in issued_calls],
                        },
                    )
                )
                return

            # ---- Inject tool messages, continue agentic loop --------------
            for (cid, fname), result in zip(issued_calls, results, strict=False):
                if isinstance(result, BaseException):
                    payload = _json.dumps({"error": "tool_dispatch_failed", "detail": str(result)})
                else:
                    # ToolResultFrame.envelope is a Pydantic model.
                    envelope = getattr(result, "envelope", None)
                    if envelope is not None and hasattr(envelope, "model_dump"):
                        payload = _json.dumps(
                            envelope.model_dump(),
                            ensure_ascii=False,
                            default=str,
                        )
                    else:
                        payload = _json.dumps({"result": str(result)}, ensure_ascii=False)
                llm_messages.append(
                    LLMChatMessage(
                        role="tool",
                        content=payload,
                        name=fname,
                        tool_call_id=cid,
                    )
                )

            # Loop back: re-invoke client.stream with extended history.

        # Loop bound exhausted — emit terminal chunk anyway so the TUI
        # un-spins; the model will not be re-invoked beyond the bound.
        logger.warning(
            "agentic loop hit KOSMOS_AGENTIC_LOOP_MAX_TURNS=%d; terminating",
            _AGENTIC_LOOP_MAX_TURNS,
        )
        await write_frame(
            AssistantChunkFrame(
                session_id=frame.session_id,
                correlation_id=frame.correlation_id,
                role="llm",
                ts=_utcnow(),
                kind="assistant_chunk",
                message_id=str(uuid.uuid4()),
                delta="",
                done=True,
            )
        )

    async def _handle_tool_result(frame: IPCFrame) -> None:
        """Spec 1978 T028 — consume ``tool_result`` and resolve pending Future.

        Looks up ``_pending_calls[call_id]``; if found, sets the Future
        result so any awaiting ``_handle_chat_request`` continuation can
        resume the agentic loop. Frames with no matching pending call are
        logged at debug level (out-of-band tool results are tolerated for
        the demo path; deep validation deferred to subsequent commits).
        """
        from kosmos.ipc.frame_schema import ToolResultFrame  # noqa: PLC0415

        if not isinstance(frame, ToolResultFrame):
            return
        fut = _pending_calls.pop(frame.call_id, None)
        if fut is None:
            logger.debug(
                "tool_result with no pending call (call_id=%s) — ignoring",
                frame.call_id,
            )
            return
        if not fut.done():
            fut.set_result(frame)

    # KOSMOS_IPC_HANDLER env var selects the user_input handler:
    #   - "llm" (default): route UserInputFrame → LLMClient.stream() → FriendliAI
    #   - "echo": mirror UserInputFrame back as AssistantChunkFrame "[echo] {text}"
    # Echo mode is used by integration tests that spawn the real backend but
    # must not depend on FRIENDLI_API_KEY or network reachability.
    import os as _os  # noqa: PLC0415

    _handler_mode = (_os.environ.get("KOSMOS_IPC_HANDLER") or "llm").lower()

    async def _handle_user_input_echo(frame: IPCFrame) -> None:
        from kosmos.ipc.frame_schema import (  # noqa: PLC0415
            AssistantChunkFrame,
            UserInputFrame,
        )

        if not isinstance(frame, UserInputFrame):
            return

        echo_frame = AssistantChunkFrame(
            session_id=frame.session_id,
            correlation_id=frame.correlation_id,
            role="backend",
            ts=_utcnow(),
            kind="assistant_chunk",
            message_id=str(uuid.uuid4()),
            delta=f"[echo] {frame.text}",
            done=True,
        )
        await write_frame(echo_frame)

    if on_frame is None:

        async def _handle_frame(frame: IPCFrame) -> None:  # noqa: C901
            if frame.kind == "user_input":
                try:
                    if _handler_mode == "echo":
                        await _handle_user_input_echo(frame)
                    else:
                        await _handle_user_input_llm(frame)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("user_input handler failed: %s", exc)
                    err = ErrorFrame(
                        session_id=frame.session_id,
                        correlation_id=frame.correlation_id or str(uuid.uuid4()),
                        role="llm",
                        ts=_utcnow(),
                        kind="error",
                        code="llm_handler_error",
                        message=f"LLM handler failed: {exc}",
                        details={},
                    )
                    await write_frame(err)

            elif frame.kind == "chat_request":
                # Spec 1978 ADR-0001 — tools-aware chat path.
                try:
                    await _handle_chat_request(frame)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("chat_request handler failed: %s", exc)
                    err = ErrorFrame(
                        session_id=frame.session_id,
                        correlation_id=frame.correlation_id or str(uuid.uuid4()),
                        role="llm",
                        ts=_utcnow(),
                        kind="error",
                        code="chat_request_error",
                        message=f"chat_request handler failed: {exc}",
                        details={},
                    )
                    await write_frame(err)

            elif frame.kind == "tool_result":
                # Spec 1978 T028 — resolve pending tool call Future.
                try:
                    await _handle_tool_result(frame)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("tool_result handler failed: %s", exc)

            elif frame.kind == "permission_response":
                # Spec 1978 T047 — resolve pending permission Future.
                try:
                    await _handle_permission_response(frame)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("permission_response handler failed: %s", exc)

            elif frame.kind == "session_event":
                evt = frame.event
                payload = frame.payload
                try:
                    await _dispatch_session_event(
                        evt,
                        payload,
                        frame.session_id,
                        _sm,
                        _shutdown,
                        frame.correlation_id,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception("session_event handler raised: %s", exc)
                    err = ErrorFrame(
                        session_id=frame.session_id,
                        correlation_id=str(uuid.uuid4()),
                        role="backend",
                        ts=_utcnow(),
                        kind="error",
                        code="session_event_error",
                        message=f"Failed to handle session_event {evt!r}: {exc}",
                        details={"event": evt},
                    )
                    await write_frame(err)

        on_frame = _handle_frame

    # Spec 1978 T081 / ADR-0004 — root span ``kosmos.session`` covers the
    # entire stdio session lifetime. All inbound/outbound frame spans
    # (kosmos.ipc.frame), LLM chat spans, tool dispatch spans, and
    # permission spans are nested under this root via OTEL implicit
    # context propagation. Closes at session exit (graceful shutdown
    # path or session_event{event=exit}).
    with _tracer.start_as_current_span("kosmos.session") as _session_span:
        _session_span.set_attribute("kosmos.session.id", sid)
        _session_span.set_attribute("kosmos.ipc.handler_mode", _handler_mode)

        # Run reader loop concurrently with shutdown watcher
        reader_task = asyncio.create_task(
            _reader_loop(stdin_reader, on_frame, sid),
            name="ipc-reader",
        )
        shutdown_task = asyncio.create_task(_shutdown.wait(), name="ipc-shutdown")

        done, pending = await asyncio.wait(
            {reader_task, shutdown_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Record which task completed first so post-mortem traces show
        # whether the session ended on stdin EOF (reader_task) vs SIGTERM /
        # session_event{event=exit} (shutdown_task).
        if reader_task in done:
            _session_span.set_attribute("kosmos.session.exit_reason", "stdin_closed")
        elif shutdown_task in done:
            _session_span.set_attribute("kosmos.session.exit_reason", "shutdown_signal")

        # Cancel whatever is still running
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task

        # Emit exit frame and flush
        try:
            await _emit_exit_frame(sid)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to emit exit frame: %s", exc)

        transport.close()
        logger.info("IPC stdio loop exited cleanly — session_id=%s", sid)


__all__ = [
    "run",
    "write_frame",
]
