# SPDX-License-Identifier: Apache-2.0
"""Spec 1979 T020 — PIPA §26 trustee acknowledgment round-trip tests.

Verifies that when the manifest declares `processes_pii: true`, the
emitted PermissionRequestFrame surfaces:
  - trustee_org_name (for citizen-visible "수탁 기관" line)
  - First 16 chars of acknowledgment_sha256 (for citizen verification)

Per FR-012, the citizen MUST see who handles their PII before granting
access. This is the PIPA §26 trustee responsibility surface.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from kosmos.ipc.frame_schema import IPCFrame, PermissionRequestFrame
from kosmos.plugins.consent_bridge import IPCConsentBridge


@dataclass
class _StubAck:
    trustee_org_name: str
    acknowledgment_sha256: str


@dataclass
class _StubManifest:
    plugin_id: str
    permission_layer: int
    processes_pii: bool
    pipa_trustee_acknowledgment: _StubAck | None = None


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


async def _resolve_pending(pending: dict[str, asyncio.Future[Any]]) -> None:
    for _ in range(50):
        if pending:
            break
        await asyncio.sleep(0.02)
    request_id = next(iter(pending))
    response = type("StubResponse", (), {"decision": "allow_once", "request_id": request_id})()
    pending[request_id].set_result(response)


@pytest.mark.asyncio
async def test_pii_manifest_includes_trustee_in_description_ko() -> None:
    """T020 — Korean description must surface the trustee org name."""
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

    manifest = _StubManifest(
        plugin_id="health_check",
        permission_layer=2,
        processes_pii=True,
        pipa_trustee_acknowledgment=_StubAck(
            trustee_org_name="국민건강보험공단",
            acknowledgment_sha256="a" * 64,
        ),
    )

    bridge_task = asyncio.create_task(
        asyncio.to_thread(bridge, _StubEntry(), _StubVersion(), manifest)
    )
    await asyncio.create_task(_resolve_pending(pending))
    result = await bridge_task

    assert result is True
    rfs = [f for f in sink.frames if isinstance(f, PermissionRequestFrame)]
    assert len(rfs) == 1
    assert "국민건강보험공단" in rfs[0].description_ko
    # First 16 chars of the SHA-256 are surfaced
    assert "a" * 16 in rfs[0].description_ko


@pytest.mark.asyncio
async def test_pii_manifest_includes_trustee_in_description_en() -> None:
    """T020 — English fallback description includes the trustee org."""
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

    manifest = _StubManifest(
        plugin_id="benefits_check",
        permission_layer=3,
        processes_pii=True,
        pipa_trustee_acknowledgment=_StubAck(
            trustee_org_name="Ministry of Health and Welfare",
            acknowledgment_sha256="b" * 64,
        ),
    )

    bridge_task = asyncio.create_task(
        asyncio.to_thread(bridge, _StubEntry(), _StubVersion(), manifest)
    )
    await asyncio.create_task(_resolve_pending(pending))
    await bridge_task

    rfs = [f for f in sink.frames if isinstance(f, PermissionRequestFrame)]
    assert len(rfs) == 1
    assert "Ministry of Health and Welfare" in rfs[0].description_en
    assert "b" * 16 in rfs[0].description_en


@pytest.mark.asyncio
async def test_non_pii_manifest_omits_trustee_fields() -> None:
    """T020 — processes_pii=False manifest must NOT inject trustee/ack fields."""
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

    # Even with a trustee block defined, processes_pii=False suppresses it.
    manifest = _StubManifest(
        plugin_id="public_lookup",
        permission_layer=1,
        processes_pii=False,
        pipa_trustee_acknowledgment=_StubAck(
            trustee_org_name="should_not_appear",
            acknowledgment_sha256="c" * 64,
        ),
    )

    bridge_task = asyncio.create_task(
        asyncio.to_thread(bridge, _StubEntry(), _StubVersion(), manifest)
    )
    await asyncio.create_task(_resolve_pending(pending))
    await bridge_task

    rfs = [f for f in sink.frames if isinstance(f, PermissionRequestFrame)]
    assert len(rfs) == 1
    assert "should_not_appear" not in rfs[0].description_ko
    assert "should_not_appear" not in rfs[0].description_en
    assert "ack-sha256" not in rfs[0].description_ko
    assert "ack-sha256" not in rfs[0].description_en


@pytest.mark.asyncio
async def test_pii_manifest_with_null_acknowledgment_omits_hash() -> None:
    """T020 — defensive: processes_pii=True with no ack block omits hash."""
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

    manifest = _StubManifest(
        plugin_id="pii_no_ack",
        permission_layer=2,
        processes_pii=True,
        pipa_trustee_acknowledgment=None,
    )

    bridge_task = asyncio.create_task(
        asyncio.to_thread(bridge, _StubEntry(), _StubVersion(), manifest)
    )
    await asyncio.create_task(_resolve_pending(pending))
    await bridge_task

    rfs = [f for f in sink.frames if isinstance(f, PermissionRequestFrame)]
    assert len(rfs) == 1
    # No trustee/ack fields should appear in the description
    assert "ack-sha256" not in rfs[0].description_ko
    assert "수탁 기관" not in rfs[0].description_ko
