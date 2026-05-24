# SPDX-License-Identifier: Apache-2.0
"""Concrete adapter tool-call frame contract tests."""

from __future__ import annotations

from uuid import uuid4

from ummaya.ipc.frame_schema import ToolCallFrame


def test_tool_call_frame_accepts_concrete_adapter_name() -> None:
    """ToolCallFrame.name must carry the concrete model-called adapter id."""

    frame = ToolCallFrame(
        session_id=str(uuid4()),
        correlation_id=str(uuid4()),
        role="backend",
        ts="2026-05-24T00:00:00Z",
        kind="tool_call",
        call_id="call-kma-current",
        name="kma_current_observation",
        arguments={"nx": 97, "ny": 74, "base_date": "20260524", "base_time": "1600"},
    )

    assert frame.name == "kma_current_observation"
    assert frame.arguments["nx"] == 97
