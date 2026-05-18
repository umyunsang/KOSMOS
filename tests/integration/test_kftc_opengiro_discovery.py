# SPDX-License-Identifier: Apache-2.0
"""Discovery and schema tests for KFTC OpenGiro send adapters."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from ummaya.tools.executor import ToolExecutor
from ummaya.tools.lookup import lookup
from ummaya.tools.models import LookupSearchInput
from ummaya.tools.register_all import register_all_tools
from ummaya.tools.registry import ToolRegistry


@pytest.fixture(scope="module")
def loaded_registry() -> tuple[ToolRegistry, ToolExecutor]:
    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry)
    register_all_tools(registry, executor)
    return registry, executor


def test_opengiro_send_adapters_are_registered_for_discovery(
    loaded_registry: tuple[ToolRegistry, ToolExecutor],
) -> None:
    registry, _executor = loaded_registry
    ids = {tool.id for tool in registry.all_tools()}

    assert "mock_kftc_opengiro_bill_send_v1" in ids
    assert "mock_kftc_opengiro_payment_send_v1" in ids

    bill = registry.lookup("mock_kftc_opengiro_bill_send_v1")
    payment = registry.lookup("mock_kftc_opengiro_payment_send_v1")
    assert bill.primitive == "send"
    assert payment.primitive == "send"
    assert bill.policy is not None
    assert payment.policy is not None
    assert bill.policy.citizen_facing_gate == "send"
    assert payment.policy.citizen_facing_gate == "send"


def test_opengiro_korean_payment_query_surfaces_send_candidate(
    loaded_registry: tuple[ToolRegistry, ToolExecutor],
) -> None:
    registry, executor = loaded_registry

    async def _run() -> list[str]:
        result = await lookup(
            LookupSearchInput(mode="search", query="오픈지로 지로 납부 결제URL 생성", top_k=10),
            registry=registry,
            executor=executor,
            session_identity="test-kftc-opengiro",
        )
        return [candidate.tool_id for candidate in result.candidates]

    ids = asyncio.run(_run())
    assert "mock_kftc_opengiro_payment_send_v1" in ids


def test_opengiro_schema_exports_exist_after_generation() -> None:
    schema_dir = Path("docs/api/schemas")
    bill_path = schema_dir / "mock_kftc_opengiro_bill_send_v1.json"
    payment_path = schema_dir / "mock_kftc_opengiro_payment_send_v1.json"

    assert bill_path.exists()
    assert payment_path.exists()

    bill = json.loads(bill_path.read_text(encoding="utf-8"))
    payment = json.loads(payment_path.read_text(encoding="utf-8"))
    assert bill["title"] == "mock_kftc_opengiro_bill_send_v1"
    assert payment["title"] == "mock_kftc_opengiro_payment_send_v1"
    assert "operation" in bill["properties"]
    assert "operation" in payment["properties"]
    assert "_OpaqueOutput" in bill["$defs"]
    assert "_OpaqueOutput" in payment["$defs"]
