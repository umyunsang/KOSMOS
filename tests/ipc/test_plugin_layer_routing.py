# SPDX-License-Identifier: Apache-2.0
"""Spec 1979 T019 — 3-layer routing integration tests.

Verifies that IPCConsentBridge populates the PermissionRequestFrame's
risk_level field correctly per the manifest's permission_layer:
  - layer=1 → risk_level="low"
  - layer=2 → risk_level="medium"
  - layer=3 → risk_level="high"

Per FR-011 + FR-014, the layer routing comes from the manifest with no
per-invocation override. The TUI gauntlet renders the layer-color glyph
(green ⓵ / orange ⓶ / red ⓷) based on this risk_level.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from kosmos.ipc.frame_schema import IPCFrame, PermissionRequestFrame
from kosmos.plugins.consent_bridge import IPCConsentBridge


@dataclass
class _StubManifest:
    plugin_id: str
    permission_layer: int
    processes_pii: bool = False
    pipa_trustee_acknowledgment: Any = None


@dataclass
class _StubVersion:
    version: str = "1.0.0"


@dataclass
class _StubEntry:
    name: str = "test"


class _FrameSink:
    def __init__(self) -> None:
        self.frames: list[IPCFrame] = []

    async def write(self, frame: IPCFrame) -> None:
        self.frames.append(frame)


async def _resolve_pending(pending: dict[str, asyncio.Future[Any]], decision: str) -> None:
    """Wait for the bridge to register a future then resolve it."""
    for _ in range(50):
        if pending:
            break
        await asyncio.sleep(0.02)
    request_id = next(iter(pending))
    response = type("StubResponse", (), {"decision": decision, "request_id": request_id})()
    pending[request_id].set_result(response)


@pytest.mark.parametrize(
    ("layer", "expected_risk"),
    [
        (1, "low"),
        (2, "medium"),
        (3, "high"),
    ],
)
@pytest.mark.asyncio
async def test_layer_maps_to_risk_level(layer: int, expected_risk: str) -> None:
    """T019 — manifest permission_layer → risk_level on PermissionRequestFrame."""
    sink = _FrameSink()
    pending: dict[str, asyncio.Future[Any]] = {}
    loop = asyncio.get_running_loop()

    bridge = IPCConsentBridge(
        write_frame=sink.write,
        pending_perms=pending,
        session_id="test",
        timeout_seconds=2.0,
        loop=loop,
    )

    manifest = _StubManifest(plugin_id=f"plugin_l{layer}", permission_layer=layer)

    bridge_task = asyncio.create_task(
        asyncio.to_thread(bridge, _StubEntry(), _StubVersion(), manifest)
    )
    await asyncio.create_task(_resolve_pending(pending, "allow_once"))
    result = await bridge_task

    assert result is True
    request_frames = [f for f in sink.frames if isinstance(f, PermissionRequestFrame)]
    assert len(request_frames) == 1
    assert request_frames[0].risk_level == expected_risk
    # Layer info is also in the description for citizen visibility
    assert f"Layer {layer}" in request_frames[0].description_ko
    assert f"Layer {layer}" in request_frames[0].description_en


@pytest.mark.asyncio
async def test_revocation_resolves_to_false() -> None:
    """T019 — citizen denial path returns False (fail-closed per Constitution §II)."""
    sink = _FrameSink()
    pending: dict[str, asyncio.Future[Any]] = {}
    loop = asyncio.get_running_loop()

    bridge = IPCConsentBridge(
        write_frame=sink.write,
        pending_perms=pending,
        session_id="test",
        timeout_seconds=2.0,
        loop=loop,
    )

    bridge_task = asyncio.create_task(
        asyncio.to_thread(bridge, _StubEntry(), _StubVersion(), _StubManifest("p1", 2))
    )
    await asyncio.create_task(_resolve_pending(pending, "deny"))
    result = await bridge_task

    assert result is False


@pytest.mark.asyncio
async def test_unknown_decision_treated_as_denial() -> None:
    """T019 — defensive: unrecognized decision returns False (fail-closed)."""
    sink = _FrameSink()
    pending: dict[str, asyncio.Future[Any]] = {}
    loop = asyncio.get_running_loop()

    bridge = IPCConsentBridge(
        write_frame=sink.write,
        pending_perms=pending,
        session_id="test",
        timeout_seconds=2.0,
        loop=loop,
    )

    bridge_task = asyncio.create_task(
        asyncio.to_thread(bridge, _StubEntry(), _StubVersion(), _StubManifest("p1", 1))
    )
    await asyncio.create_task(_resolve_pending(pending, "unknown_decision"))
    result = await bridge_task

    assert result is False
