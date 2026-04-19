# SPDX-License-Identifier: Apache-2.0
"""T051 — End-to-end correlation_id / transaction_id OTEL attribute tests (Spec 032).

Verifies (FR-027 / FR-053):
- Every ``kosmos.ipc.frame`` span emitted during a synthetic full turn shares
  the same ``kosmos.ipc.correlation_id`` attribute value.
- The irreversible tool-call frame's outbound span carries
  ``kosmos.ipc.tx.cache_state="miss"`` on first write, and ``"hit"`` on a
  replayed retransmission after a resume handshake.
- ``kosmos.ipc.transaction_id`` is present on irreversible tool-call frames
  and absent on streaming chunks.

Strategy: monkeypatch the module-level ``_tracer`` in ``kosmos.ipc.stdio``
with a dedicated ``TracerProvider`` backed by an ``InMemorySpanExporter``
(mirrors ``tests/ipc/test_otel_span.py``).  Frames are emitted via
``write_frame`` with a fake stdout buffer; no subprocess.
"""

from __future__ import annotations

import io
import sys
import uuid
from datetime import UTC, datetime

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from kosmos.ipc.frame_schema import (
    AssistantChunkFrame,
    ToolCallFrame,
    UserInputFrame,
)
from kosmos.ipc.otel_constants import (
    KOSMOS_IPC_CORRELATION_ID,
    KOSMOS_IPC_TRANSACTION_ID,
    KOSMOS_IPC_TX_CACHE_STATE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ts() -> str:
    now = datetime.now(tz=UTC)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


class _FakeBuffer:
    def __init__(self) -> None:
        self._buf = io.BytesIO()

    def write(self, data: bytes) -> None:
        self._buf.write(data)

    def flush(self) -> None:
        pass


class _FakeStdout:
    def __init__(self) -> None:
        self.buffer = _FakeBuffer()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import kosmos.ipc.stdio as stdio_mod

    monkeypatch.setattr(stdio_mod, "_tracer", provider.get_tracer("kosmos.ipc"))
    exporter.clear()
    return exporter


@pytest.fixture()
def fake_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    from kosmos.ipc import stdio as stdio_mod

    monkeypatch.setattr(sys, "stdout", _FakeStdout())
    monkeypatch.setattr(stdio_mod, "_stdout_lock", None)


# ---------------------------------------------------------------------------
# T051-A: All frames in a full turn share one correlation_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_turn_shares_one_correlation_id(
    mem_exporter: InMemorySpanExporter,
    fake_stdout: None,
) -> None:
    """Synthetic full turn → every span has identical kosmos.ipc.correlation_id."""
    from kosmos.ipc import stdio as stdio_mod

    session_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())

    # Simulate a full turn: tool_call + 2 chunks.
    tool_call = ToolCallFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="tool_call",
        call_id=str(uuid.uuid4()),
        name="lookup",
        arguments={"tool_id": "koroad_accident_hazard_search", "q": "대전"},
        transaction_id=str(uuid.uuid4()),
    )
    chunk_one = AssistantChunkFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="assistant_chunk",
        message_id=str(uuid.uuid4()),
        delta="검색 결과는 ",
        done=False,
    )
    chunk_two = AssistantChunkFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="assistant_chunk",
        message_id=chunk_one.message_id,
        delta="다음과 같습니다.",
        done=True,
    )

    await stdio_mod.write_frame(tool_call, tx_cache_state="miss")
    await stdio_mod.write_frame(chunk_one)
    await stdio_mod.write_frame(chunk_two)

    ipc_spans = [s for s in mem_exporter.get_finished_spans() if s.name == "kosmos.ipc.frame"]
    assert len(ipc_spans) == 3, (
        f"Expected 3 kosmos.ipc.frame spans, got {len(ipc_spans)}: "
        f"{[s.name for s in mem_exporter.get_finished_spans()]}"
    )

    corr_ids = {dict(s.attributes or {}).get(KOSMOS_IPC_CORRELATION_ID) for s in ipc_spans}
    assert corr_ids == {correlation_id}, (
        f"correlation_id must be constant across a turn, got {corr_ids}"
    )


# ---------------------------------------------------------------------------
# T051-B: transaction_id is present on tool_call, absent on chunks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transaction_id_present_only_on_irreversible_tool_call(
    mem_exporter: InMemorySpanExporter,
    fake_stdout: None,
) -> None:
    from kosmos.ipc import stdio as stdio_mod

    session_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    tx_id = str(uuid.uuid4())

    tool_call = ToolCallFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="tool_call",
        call_id=str(uuid.uuid4()),
        name="lookup",
        arguments={"tool_id": "koroad_accident_hazard_search", "q": "서울"},
        transaction_id=tx_id,
    )
    chunk = AssistantChunkFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="assistant_chunk",
        message_id=str(uuid.uuid4()),
        delta="streaming…",
        done=True,
    )

    await stdio_mod.write_frame(tool_call, tx_cache_state="miss")
    await stdio_mod.write_frame(chunk)

    ipc_spans = [s for s in mem_exporter.get_finished_spans() if s.name == "kosmos.ipc.frame"]
    assert len(ipc_spans) == 2

    by_kind = {
        dict(s.attributes or {}).get("kosmos.frame.kind"): dict(s.attributes or {})
        for s in ipc_spans
    }

    tool_attrs = by_kind["tool_call"]
    assert tool_attrs.get(KOSMOS_IPC_TRANSACTION_ID) == tx_id
    assert tool_attrs.get(KOSMOS_IPC_TX_CACHE_STATE) == "miss"

    chunk_attrs = by_kind["assistant_chunk"]
    assert KOSMOS_IPC_TRANSACTION_ID not in chunk_attrs, (
        f"assistant_chunk must not carry transaction_id: {chunk_attrs}"
    )


# ---------------------------------------------------------------------------
# T051-C: Replay → same transaction_id, tx.cache_state transitions miss → hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tx_cache_state_transitions_miss_then_hit_on_replay(
    mem_exporter: InMemorySpanExporter,
    fake_stdout: None,
) -> None:
    """First emit: miss.  Replay after resume handshake: hit.  Same transaction_id."""
    from kosmos.ipc import stdio as stdio_mod

    session_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    tx_id = str(uuid.uuid4())

    tool_call = ToolCallFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="backend",
        ts=_ts(),
        kind="tool_call",
        call_id=str(uuid.uuid4()),
        name="lookup",
        arguments={"tool_id": "koroad_accident_hazard_search", "q": "부산"},
        transaction_id=tx_id,
    )

    # First emit → miss (new transaction).
    await stdio_mod.write_frame(tool_call, tx_cache_state="miss")
    # Retransmit after resume → hit (cache already populated).
    await stdio_mod.write_frame(tool_call, tx_cache_state="hit")

    ipc_spans = [s for s in mem_exporter.get_finished_spans() if s.name == "kosmos.ipc.frame"]
    assert len(ipc_spans) == 2

    states = [dict(s.attributes or {}).get(KOSMOS_IPC_TX_CACHE_STATE) for s in ipc_spans]
    assert states == ["miss", "hit"], f"Expected ['miss','hit'], got {states}"

    tx_ids = {dict(s.attributes or {}).get(KOSMOS_IPC_TRANSACTION_ID) for s in ipc_spans}
    assert tx_ids == {tx_id}, f"transaction_id must be preserved across replay: {tx_ids}"


# ---------------------------------------------------------------------------
# T051-D: Inbound user_input span carries correlation_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inbound_user_input_span_has_correlation_id(
    mem_exporter: InMemorySpanExporter,
) -> None:
    import asyncio

    from kosmos.ipc.stdio import _reader_loop

    session_id = str(uuid.uuid4())
    correlation_id = str(uuid.uuid4())
    frame_in = UserInputFrame(
        session_id=session_id,
        correlation_id=correlation_id,
        role="tui",
        ts=_ts(),
        kind="user_input",
        text="안녕하세요",
    )
    payload = (frame_in.model_dump_json() + "\n").encode("utf-8")

    reader = asyncio.StreamReader()
    reader.feed_data(payload)
    reader.feed_eof()

    async def _on_frame(_f: object) -> None:
        return None

    await _reader_loop(reader, _on_frame, session_id)

    ipc_spans = [s for s in mem_exporter.get_finished_spans() if s.name == "kosmos.ipc.frame"]
    assert len(ipc_spans) == 1
    attrs = dict(ipc_spans[0].attributes or {})
    assert attrs.get(KOSMOS_IPC_CORRELATION_ID) == correlation_id
