# SPDX-License-Identifier: Apache-2.0
"""Unit tests for AgentContext frozen Pydantic v2 model.

Covers:
- Rejection of unknown fields (extra="forbid")
- Rejection of empty specialist_role (min_length=1)
- Immutability after construction (frozen=True)

T013 — FR-010.
"""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec
from uuid import uuid4

import pytest
from pydantic import ValidationError

from kosmos.agents.context import AgentContext
from kosmos.llm.client import LLMClient
from kosmos.tools.registry import ToolRegistry


def _mock_registry() -> ToolRegistry:
    return create_autospec(ToolRegistry, instance=True)


def _mock_llm() -> LLMClient:
    return create_autospec(LLMClient, instance=True)


def _make_context(**overrides: object) -> AgentContext:
    """Build a valid AgentContext with optional field overrides."""
    defaults: dict[str, object] = {
        "session_id": uuid4(),
        "specialist_role": "transport",
        "worker_id": f"worker-transport-{uuid4()}",
        "tool_registry": _mock_registry(),
        "llm_client": _mock_llm(),
    }
    defaults.update(overrides)
    return AgentContext(**defaults)  # type: ignore[arg-type]


def test_valid_construction() -> None:
    """A correctly-constructed AgentContext should not raise."""
    ctx = _make_context()
    assert ctx.specialist_role == "transport"
    assert ctx.coordinator_id == "coordinator"


def test_reject_unknown_field() -> None:
    """extra='forbid' must reject unknown fields."""
    with pytest.raises(ValidationError, match="extra_fields_not_permitted|Extra inputs"):
        _make_context(unexpected_field="boom")


def test_reject_empty_specialist_role() -> None:
    """specialist_role must not be empty (min_length=1)."""
    with pytest.raises(ValidationError, match="string_too_short|min_length"):
        _make_context(specialist_role="")


def test_reject_specialist_role_too_long() -> None:
    """specialist_role must be ≤ 64 characters (max_length=64)."""
    with pytest.raises(ValidationError, match="string_too_long|max_length"):
        _make_context(specialist_role="x" * 65)


def test_immutable_after_construction() -> None:
    """frozen=True must prevent field mutation."""
    ctx = _make_context()
    with pytest.raises((TypeError, ValidationError)):
        ctx.specialist_role = "mutated"  # type: ignore[misc]


def test_coordinator_id_default() -> None:
    """coordinator_id defaults to the literal string 'coordinator'."""
    ctx = _make_context()
    assert ctx.coordinator_id == "coordinator"


def test_worker_id_non_empty() -> None:
    """worker_id must not be empty (min_length=1)."""
    with pytest.raises(ValidationError, match="string_too_short|min_length"):
        _make_context(worker_id="")


def test_session_id_is_uuid() -> None:
    """session_id must accept a UUID."""
    sid = uuid4()
    ctx = _make_context(session_id=sid)
    assert ctx.session_id == sid
