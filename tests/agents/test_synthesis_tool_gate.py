# SPDX-License-Identifier: Apache-2.0
"""Test T019 — FR-004, FR-038: synthesis phase must NOT inject tools into LLM call.

When `_call_synthesis_llm()` runs, the LLM client's stream() must be called with
tools=None (empty ToolRegistry → export_core_tools_openai() → [] → None).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from kosmos.agents.coordinator import Coordinator
from kosmos.agents.mailbox.messages import AgentMessage
from tests.agents.conftest import StubLLMClient, build_test_registry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_in_memory_mailbox():  # type: ignore[no-untyped-def]
    """Build the in-memory mailbox with real async generator methods."""

    class _InMemoryMailbox:
        def __init__(self) -> None:
            self._messages: list[AgentMessage] = []

        async def send(self, message: AgentMessage) -> None:
            self._messages.append(message)

        async def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
            for msg in list(self._messages):
                if msg.recipient == recipient:
                    yield msg

        async def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
            for msg in list(self._messages):
                if msg.recipient == recipient:
                    yield msg

    return _InMemoryMailbox()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_synthesis_llm_receives_no_tools() -> None:
    """FR-004, FR-038: synthesis LLM call must have tools=None.

    The `_call_synthesis_llm` method uses an empty ToolRegistry,
    which means export_core_tools_openai() returns [], which evaluates
    to None via `list(raw_defs) or None` in _query_inner.
    """
    synthesis_json = json.dumps(
        {
            "steps": [
                {
                    "ministry": "civil_affairs",
                    "action": "Submit form",
                    "depends_on": [],
                    "execution_mode": "parallel",
                }
            ],
            "message": "Plan ready.",
        }
    )

    llm = StubLLMClient(responses=[synthesis_json])
    mailbox = _make_in_memory_mailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    await coordinator._call_synthesis_llm(
        citizen_request="I need to transfer my residence.",
        result_summaries=["Worker 'civil_affairs': record output, 2 turn(s)"],
    )

    # The LLM must have been called exactly once with tools=None
    assert llm._stub_call_count == 1, (
        f"Expected exactly 1 LLM call, got {llm._stub_call_count}"
    )
    actual_tools = llm._stub_tools_args[0]
    assert actual_tools is None, (
        f"FR-004/FR-038 VIOLATED: synthesis LLM received tools={actual_tools!r}, "
        "expected None (empty ToolRegistry must suppress all tool injection)."
    )


@pytest.mark.asyncio
async def test_synthesis_tool_gate_with_multiple_calls() -> None:
    """Synthesis always passes tools=None regardless of how many times it's called."""
    synthesis_json = '{"steps": [], "message": "empty"}'
    llm = StubLLMClient(responses=[synthesis_json, synthesis_json])
    mailbox = _make_in_memory_mailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    await coordinator._call_synthesis_llm("Request A", [])
    await coordinator._call_synthesis_llm("Request B", ["summary1"])

    assert all(t is None for t in llm._stub_tools_args), (
        f"All synthesis calls must pass tools=None; got {llm._stub_tools_args!r}"
    )


@pytest.mark.asyncio
async def test_synthesis_tool_gate_contrast_with_worker_tools() -> None:
    """Contrast: synthesis is deliberately tool-free.

    With an empty registry, tools=None regardless of caller context.
    """
    synthesis_json = '{"steps": [], "message": "ok"}'
    llm = StubLLMClient(responses=[synthesis_json])
    mailbox = _make_in_memory_mailbox()

    coordinator = Coordinator(
        session_id=uuid4(),
        llm_client=llm,
        tool_registry=build_test_registry(),  # empty = no tools
        mailbox=mailbox,  # type: ignore[arg-type]
    )

    await coordinator._call_synthesis_llm("citizen query", [])

    # Confirm the isolation invariant
    for call_tools in llm._stub_tools_args:
        assert call_tools is None, (
            "Synthesis LLM must NEVER receive tools — "
            f"got {call_tools!r}"
        )
