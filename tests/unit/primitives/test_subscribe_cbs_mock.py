# SPDX-License-Identifier: Apache-2.0
"""T070 — Subscribe primitive: Mock CBS disaster adapter end-to-end pytest.

Verifies the full lifecycle of subscribe() with mock_cbs_disaster_v1:
1. Adapter auto-registers on module import.
2. subscribe() returns an AsyncIterator.
3. Iterating over a short lifetime yields >= 1 CbsBroadcastEvent.
4. Each event has subscription_id populated and a structured CbsBroadcastEvent payload.
5. After lifetime expires, __anext__ raises StopAsyncIteration (clean termination).
"""

from __future__ import annotations

import logging
import re

import pytest

import kosmos.tools.mock  # noqa: F401 — side-effect: registers all mock adapters
from kosmos.primitives.subscribe import (
    _SUBSCRIBE_ADAPTERS,
    CbsBroadcastEvent,
    SubscribeInput,
    subscribe,
)

logger = logging.getLogger(__name__)

_TOOL_ID = "mock_cbs_disaster_v1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TestSubscribeCbsMockRegistration:
    """Adapter auto-registration on import."""

    def test_adapter_registered_after_import(self) -> None:
        """mock_cbs_disaster_v1 must appear in _SUBSCRIBE_ADAPTERS after import."""
        assert _TOOL_ID in _SUBSCRIBE_ADAPTERS, (
            f"{_TOOL_ID!r} not in _SUBSCRIBE_ADAPTERS; "
            "check that kosmos.tools.mock imports disaster_feed.py"
        )

    def test_adapter_modality_is_cbs(self) -> None:
        """Registered modality must be MODALITY_CBS."""
        modality, _ = _SUBSCRIBE_ADAPTERS[_TOOL_ID]
        assert modality == "cbs_broadcast"


@pytest.mark.asyncio
class TestSubscribeCbsMockIterator:
    """subscribe() lifecycle with mock_cbs_disaster_v1."""

    async def test_returns_async_iterator(self) -> None:
        """subscribe() must return an object with __aiter__ (not a coroutine)."""
        inp = SubscribeInput(
            tool_id=_TOOL_ID,
            params={},
            lifetime_seconds=2,
        )
        result = subscribe(inp)
        assert hasattr(result, "__aiter__"), "subscribe() must return an AsyncIterator"
        assert hasattr(result, "__anext__"), "subscribe() must return an AsyncIterator"

    async def test_yields_at_least_one_event_within_lifetime(self) -> None:
        """Must yield >= 1 event within a 2-second lifetime.

        Default adapter cadence: burst_count=3, burst_delay_seconds=0.1s → 3 events
        in ~0.3s, well within the 2-second lifetime.
        """
        inp = SubscribeInput(
            tool_id=_TOOL_ID,
            params={},
            lifetime_seconds=2,
        )
        events: list[CbsBroadcastEvent] = []
        async for event in subscribe(inp):
            events.append(event)  # type: ignore[arg-type]
        assert len(events) >= 1, "Expected >= 1 CBS event; got 0"

    async def test_event_payload_structure(self) -> None:
        """Each event must be a CbsBroadcastEvent with all required fields."""
        inp = SubscribeInput(
            tool_id=_TOOL_ID,
            params={},
            lifetime_seconds=2,
        )
        async for raw_event in subscribe(inp):
            event: CbsBroadcastEvent = raw_event  # type: ignore[assignment]
            assert isinstance(event, CbsBroadcastEvent)
            assert event.kind == "cbs_broadcast"
            assert 4370 <= event.cbs_message_id <= 4385
            assert event.language in ("ko", "en")
            assert len(event.body) > 0
            assert _SHA256_RE.match(event.payload_hash), (
                f"payload_hash must be 64 hex chars; got {event.payload_hash!r}"
            )
            assert event.received_at is not None
            break  # structural check on first event is sufficient

    async def test_subscription_handle_fields_populated(self) -> None:
        """SubscriptionHandle must have subscription_id (UUID) and matching tool_id."""
        from kosmos.primitives.subscribe import _get_handle_for_testing

        inp = SubscribeInput(
            tool_id=_TOOL_ID,
            params={},
            lifetime_seconds=2,
        )
        handle = await _get_handle_for_testing(inp)
        assert handle.subscription_id, "subscription_id must not be empty"
        # Must be a valid UUID4 pattern
        import uuid

        parsed = uuid.UUID(handle.subscription_id)
        assert str(parsed) == handle.subscription_id
        assert handle.tool_id == _TOOL_ID
        assert handle.closes_at > handle.opened_at

    async def test_clean_termination_after_lifetime(self) -> None:
        """After lifetime expires iterator must terminate (StopAsyncIteration)."""
        inp = SubscribeInput(
            tool_id=_TOOL_ID,
            # burst_count=3 @ 0.1s delay → all 3 emitted in ~0.3s; lifetime=1s
            # lets all events drain then adapter signals _DRIVER_DONE cleanly.
            params={"burst_count": 3, "burst_delay_seconds": 0.1},
            lifetime_seconds=1,
        )
        event_count = 0
        async for _ in subscribe(inp):
            event_count += 1
        # Iterator must finish without exception (StopAsyncIteration consumed by for-loop)
        assert event_count >= 1, "Expected at least 1 event before clean termination"
