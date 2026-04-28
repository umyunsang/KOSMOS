# SPDX-License-Identifier: Apache-2.0
"""Unit tests for IPCConsentBridge (Spec 1979 / T015).

Verifies the bridge behaviour for all decision branches:
  - allow_once / allow_session / granted → returns True
  - deny / denied → returns False
  - timeout (asyncio.TimeoutError) → returns False (fail-closed per §II)
  - PIPA processes_pii=True → request frame carries acknowledgment_sha256
  - permission_layer=3 → request frame carries risk_level="high"
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from kosmos.ipc.frame_schema import IPCFrame, PermissionRequestFrame
from kosmos.plugins.consent_bridge import IPCConsentBridge

# ---------------------------------------------------------------------------
# Stub objects matching installer.ConsentPrompt signature
# ---------------------------------------------------------------------------


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
    version: str


@dataclass
class _StubEntry:
    name: str


def _build_manifest(
    layer: int = 1, pii: bool = False, trustee: str | None = None
) -> _StubManifest:
    ack = None
    if pii and trustee is not None:
        ack = _StubAck(
            trustee_org_name=trustee,
            acknowledgment_sha256="a" * 64,
        )
    return _StubManifest(
        plugin_id=f"test_plugin_l{layer}",
        permission_layer=layer,
        processes_pii=pii,
        pipa_trustee_acknowledgment=ack,
    )


class _FrameSink:
    """Captures every frame written via the mock write_frame callable."""

    def __init__(self) -> None:
        self.frames: list[IPCFrame] = []

    async def write(self, frame: IPCFrame) -> None:
        self.frames.append(frame)


# ---------------------------------------------------------------------------
# Decision branch tests
# ---------------------------------------------------------------------------


class TestConsentDecisionBranches:
    """Each test pre-resolves the future with a specific decision."""

    @pytest.mark.asyncio
    async def test_allow_once_returns_true(self) -> None:
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

        # Pre-resolve the future shortly after the bridge schedules its emit
        async def _resolve_after_emit() -> None:
            # Wait for the bridge to register a future
            for _ in range(50):
                if pending:
                    break
                await asyncio.sleep(0.02)
            # Resolve with allow_once
            request_id = next(iter(pending))
            response = type(
                "StubResponse",
                (),
                {"decision": "allow_once", "request_id": request_id},
            )()
            pending[request_id].set_result(response)

        bridge_call_task = asyncio.create_task(
            asyncio.to_thread(
                bridge,
                _StubEntry(name="x"),
                _StubVersion(version="1.0"),
                _build_manifest(layer=1),
            )
        )
        resolver_task = asyncio.create_task(_resolve_after_emit())
        result = await bridge_call_task
        await resolver_task

        assert result is True
        assert any(isinstance(f, PermissionRequestFrame) for f in sink.frames)

    @pytest.mark.asyncio
    async def test_deny_returns_false(self) -> None:
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

        async def _resolve_with_deny() -> None:
            for _ in range(50):
                if pending:
                    break
                await asyncio.sleep(0.02)
            request_id = next(iter(pending))
            response = type(
                "StubResponse",
                (),
                {"decision": "deny", "request_id": request_id},
            )()
            pending[request_id].set_result(response)

        bridge_call_task = asyncio.create_task(
            asyncio.to_thread(
                bridge,
                _StubEntry(name="x"),
                _StubVersion(version="1.0"),
                _build_manifest(layer=1),
            )
        )
        resolver_task = asyncio.create_task(_resolve_with_deny())
        result = await bridge_call_task
        await resolver_task

        assert result is False

    @pytest.mark.asyncio
    async def test_allow_session_returns_true(self) -> None:
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

        async def _resolve_session() -> None:
            for _ in range(50):
                if pending:
                    break
                await asyncio.sleep(0.02)
            request_id = next(iter(pending))
            response = type(
                "StubResponse",
                (),
                {"decision": "allow_session", "request_id": request_id},
            )()
            pending[request_id].set_result(response)

        bridge_call_task = asyncio.create_task(
            asyncio.to_thread(
                bridge,
                _StubEntry(name="x"),
                _StubVersion(version="1.0"),
                _build_manifest(layer=1),
            )
        )
        resolver_task = asyncio.create_task(_resolve_session())
        result = await bridge_call_task
        await resolver_task

        assert result is True

    @pytest.mark.asyncio
    async def test_timeout_returns_false_failclosed(self) -> None:
        sink = _FrameSink()
        pending: dict[str, asyncio.Future[Any]] = {}
        loop = asyncio.get_running_loop()

        bridge = IPCConsentBridge(
            write_frame=sink.write,
            pending_perms=pending,
            session_id="test",
            timeout_seconds=0.3,  # Short timeout for the test
            loop=loop,
        )

        # Never resolve the future — timeout path
        result = await asyncio.to_thread(
            bridge,
            _StubEntry(name="x"),
            _StubVersion(version="1.0"),
            _build_manifest(layer=1),
        )

        assert result is False
        # pending_perms is cleaned up after timeout
        assert pending == {}


# ---------------------------------------------------------------------------
# PII / Layer attribute tests
# ---------------------------------------------------------------------------


class TestPermissionRequestFramePopulation:
    """Verify the emitted PermissionRequestFrame carries manifest metadata."""

    @pytest.mark.asyncio
    async def test_pii_includes_acknowledgment_sha256(self) -> None:
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

        async def _resolve() -> None:
            for _ in range(50):
                if pending:
                    break
                await asyncio.sleep(0.02)
            request_id = next(iter(pending))
            response = type(
                "StubResponse",
                (),
                {"decision": "allow_once", "request_id": request_id},
            )()
            pending[request_id].set_result(response)

        manifest = _build_manifest(layer=2, pii=True, trustee="국민건강보험공단")

        bridge_task = asyncio.create_task(
            asyncio.to_thread(
                bridge,
                _StubEntry(name="x"),
                _StubVersion(version="1.0"),
                manifest,
            )
        )
        await asyncio.create_task(_resolve())
        result = await bridge_task

        assert result is True
        request_frames = [f for f in sink.frames if isinstance(f, PermissionRequestFrame)]
        assert len(request_frames) == 1
        # Korean description includes the trustee org name + ack hash prefix
        assert "국민건강보험공단" in request_frames[0].description_ko
        assert "ack-sha256" in request_frames[0].description_ko

    @pytest.mark.asyncio
    async def test_layer_3_renders_high_risk_level(self) -> None:
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

        async def _resolve() -> None:
            for _ in range(50):
                if pending:
                    break
                await asyncio.sleep(0.02)
            request_id = next(iter(pending))
            response = type(
                "StubResponse",
                (),
                {"decision": "allow_once", "request_id": request_id},
            )()
            pending[request_id].set_result(response)

        manifest = _build_manifest(layer=3)

        bridge_task = asyncio.create_task(
            asyncio.to_thread(
                bridge,
                _StubEntry(name="x"),
                _StubVersion(version="1.0"),
                manifest,
            )
        )
        await asyncio.create_task(_resolve())
        result = await bridge_task

        assert result is True
        request_frames = [f for f in sink.frames if isinstance(f, PermissionRequestFrame)]
        assert len(request_frames) == 1
        assert request_frames[0].risk_level == "high"
        assert "Layer 3" in request_frames[0].description_ko
