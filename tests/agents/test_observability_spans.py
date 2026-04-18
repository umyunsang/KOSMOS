# SPDX-License-Identifier: Apache-2.0
"""Test T041 — FR-028..FR-031, SC-006: OTel span emission.

Verifies:
(a) Exactly 4 gen_ai.agent.coordinator.phase spans (research, synthesis,
    implementation, verification).
(b) gen_ai.agent.mailbox.message spans emitted per send() call.
(c) Message body NEVER appears in any span attribute (PIPA).

Strategy: Patch the module-level `_tracer` objects in coordinator and
mailbox modules with tracers derived from an InMemorySpanExporter-backed
TracerProvider. This avoids OTel's global-provider-override guard.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from kosmos.agents.mailbox.messages import (
    AgentMessage,
    MessageType,
    ResultPayload,
    TaskPayload,
)
from kosmos.tools.models import LookupMeta, LookupRecord
from tests.agents.conftest import StubLLMClient, build_test_registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_provider_and_exporter() -> tuple[TracerProvider, InMemorySpanExporter]:
    """Create a TracerProvider wired to an InMemorySpanExporter."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def _spans_named(exporter: InMemorySpanExporter, name: str) -> list[Any]:
    return [s for s in exporter.get_finished_spans() if s.name == name]


@pytest.fixture
def span_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Patch module-level _tracer in coordinator, worker, and mailbox with a
    captured provider. Returns the InMemorySpanExporter to assert against.
    """
    import kosmos.agents.coordinator as _coord_mod
    import kosmos.agents.mailbox.file_mailbox as _fm_mod
    import kosmos.agents.worker as _worker_mod

    provider, exporter = _make_provider_and_exporter()

    coord_tracer = provider.get_tracer("kosmos.agents.coordinator")
    worker_tracer = provider.get_tracer("kosmos.agents.worker")
    fm_tracer = provider.get_tracer("kosmos.agents.mailbox.file_mailbox")

    monkeypatch.setattr(_coord_mod, "_tracer", coord_tracer)
    monkeypatch.setattr(_worker_mod, "_tracer", worker_tracer)
    monkeypatch.setattr(_fm_mod, "_tracer", fm_tracer)

    return exporter


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coordinator_emits_four_phase_spans(
    tmp_path: Any, span_exporter: InMemorySpanExporter
) -> None:
    """FR-028: exactly 4 gen_ai.agent.coordinator.phase spans are emitted."""
    from kosmos.agents.coordinator import Coordinator
    from kosmos.agents.mailbox.file_mailbox import FileMailbox

    session_id = uuid4()
    llm = StubLLMClient(responses=["", "", "", ""])
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=100)

    coordinator = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,
    )
    await coordinator.run("What is the emergency hospital near Gangnam?")

    phase_spans = _spans_named(span_exporter, "gen_ai.agent.coordinator.phase")
    assert len(phase_spans) == 4, (
        f"FR-028: expected 4 coordinator phase spans, got {len(phase_spans)}\n"
        f"Span names: {[s.name for s in span_exporter.get_finished_spans()]}"
    )

    phase_values = {
        s.attributes.get("kosmos.agent.coordinator.phase")
        for s in phase_spans  # type: ignore[union-attr]
    }
    expected_phases = {"research", "synthesis", "implementation", "verification"}
    assert phase_values == expected_phases, (
        f"FR-028: expected phases {expected_phases}, got {phase_values}"
    )


@pytest.mark.asyncio
async def test_coordinator_phase_span_attributes(
    tmp_path: Any, span_exporter: InMemorySpanExporter
) -> None:
    """FR-028: each phase span carries kosmos.agent.coordinator.phase attribute."""
    from kosmos.agents.coordinator import Coordinator
    from kosmos.agents.mailbox.file_mailbox import FileMailbox

    session_id = uuid4()
    llm = StubLLMClient(responses=["", "", "", ""])
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=100)

    coordinator = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,
    )
    await coordinator.run("Test query")

    for span in _spans_named(span_exporter, "gen_ai.agent.coordinator.phase"):
        phase_attr = span.attributes.get("kosmos.agent.coordinator.phase")  # type: ignore[union-attr]
        assert phase_attr is not None, "Phase span must have kosmos.agent.coordinator.phase"
        assert phase_attr in ("research", "synthesis", "implementation", "verification"), (
            f"Phase attribute has unexpected value: {phase_attr!r}"
        )


@pytest.mark.asyncio
async def test_mailbox_send_emits_span(tmp_path: Any, span_exporter: InMemorySpanExporter) -> None:
    """FR-030: each FileMailbox.send() emits one gen_ai.agent.mailbox.message span."""
    from kosmos.agents.mailbox.file_mailbox import FileMailbox

    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=100)

    msg = AgentMessage(
        sender="coordinator",
        recipient="worker-test",
        msg_type=MessageType.task,
        payload=TaskPayload(instruction="Do a lookup", specialist_role="civil_affairs"),
    )
    await mailbox.send(msg)

    mailbox_spans = _spans_named(span_exporter, "gen_ai.agent.mailbox.message")
    assert len(mailbox_spans) == 1, (
        f"FR-030: expected 1 mailbox.message span per send(), got {len(mailbox_spans)}"
    )

    span = mailbox_spans[0]
    attrs = span.attributes or {}

    assert attrs.get("kosmos.agent.mailbox.msg_type") == msg.msg_type.value
    assert attrs.get("kosmos.agent.mailbox.sender") == msg.sender
    assert attrs.get("kosmos.agent.mailbox.recipient") == msg.recipient


@pytest.mark.asyncio
async def test_mailbox_send_multiple_spans(
    tmp_path: Any, span_exporter: InMemorySpanExporter
) -> None:
    """FR-030: N sends emit N gen_ai.agent.mailbox.message spans."""
    from kosmos.agents.mailbox.file_mailbox import FileMailbox

    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=100)

    n = 3
    for i in range(n):
        msg = AgentMessage(
            sender="coordinator",
            recipient=f"worker-{i}",
            msg_type=MessageType.task,
            payload=TaskPayload(instruction=f"Task {i}", specialist_role="civil_affairs"),
        )
        await mailbox.send(msg)

    mailbox_spans = _spans_named(span_exporter, "gen_ai.agent.mailbox.message")
    assert len(mailbox_spans) == n, f"FR-030: expected {n} mailbox spans, got {len(mailbox_spans)}"


@pytest.mark.asyncio
async def test_span_attributes_never_contain_message_body(
    tmp_path: Any, span_exporter: InMemorySpanExporter
) -> None:
    """FR-031 (PIPA): message body must never appear in any span attribute."""
    from kosmos.agents.coordinator import Coordinator
    from kosmos.agents.mailbox.file_mailbox import FileMailbox

    session_id = uuid4()
    llm = StubLLMClient(responses=["", "", "", ""])
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=100)

    sensitive_instruction = "SENSITIVE_PAYLOAD_MARKER"

    coordinator = Coordinator(
        session_id=session_id,
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,
    )
    await coordinator.run(sensitive_instruction)

    all_spans = span_exporter.get_finished_spans()
    for span in all_spans:
        for key, value in (span.attributes or {}).items():
            assert sensitive_instruction not in str(value), (
                f"PIPA: span {span.name!r} attribute {key!r} contains message body: {value!r}"
            )


@pytest.mark.asyncio
async def test_mailbox_span_correlation_id_attribute(
    tmp_path: Any, span_exporter: InMemorySpanExporter
) -> None:
    """FR-030: mailbox.message span has kosmos.agent.mailbox.correlation_id attribute."""
    import datetime as _dt

    from kosmos.agents.mailbox.file_mailbox import FileMailbox

    session_id = uuid4()
    mailbox = FileMailbox(session_id=session_id, root=tmp_path, max_messages=100)

    cid = uuid4()
    meta = LookupMeta(
        source="lookup",
        fetched_at=_dt.datetime.now(_dt.UTC),
        request_id=str(uuid4()),
        elapsed_ms=1,
    )
    record = LookupRecord(kind="record", item={"data": "x"}, meta=meta)
    result_msg = AgentMessage(
        sender="worker-a",
        recipient="coordinator",
        msg_type=MessageType.result,
        payload=ResultPayload(lookup_output=record, turn_count=1),
        correlation_id=cid,
    )

    await mailbox.send(result_msg)

    mailbox_spans = _spans_named(span_exporter, "gen_ai.agent.mailbox.message")
    assert len(mailbox_spans) == 1
    span = mailbox_spans[0]
    cid_attr = (span.attributes or {}).get("kosmos.agent.mailbox.correlation_id")
    assert cid_attr == str(cid), f"FR-030: expected correlation_id={cid}, got {cid_attr!r}"
