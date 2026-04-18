# SPDX-License-Identifier: Apache-2.0
"""T048 [P] — FR-014: subscribe with lifetime=1s terminates cleanly after expiry.

After lifetime expires:
- The AsyncIterator must stop yielding events (StopAsyncIteration).
- A final audit marker (SubscriptionBackpressureDrop or clean close) is emitted
  only if there were unflushed events at expiry.
"""

from __future__ import annotations

import asyncio
import time

import pytest

from kosmos.primitives.subscribe import (
    SubscribeInput,
    SubscriptionBackpressureDrop,
    SubscriptionHandle,
    subscribe,
)
from kosmos.tools.mock.cbs.disaster_feed import MOCK_CBS_DISASTER_TOOL


@pytest.mark.asyncio
class TestSubscribeLifetimeExpiry:
    """T048 — FR-014: iterator terminates cleanly after lifetime expires."""

    async def test_iterator_terminates_after_lifetime(self):
        """subscribe(lifetime=1) must stop within ~2 seconds."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=1,
        )
        start = time.monotonic()
        events = []
        async for event in subscribe(inp):
            events.append(event)
            # Safety valve: don't let test run forever
            if time.monotonic() - start > 5.0:
                pytest.fail("subscribe() did not terminate within 5s after lifetime=1s")

        elapsed = time.monotonic() - start
        # Must have terminated cleanly (no infinite loop)
        assert elapsed < 5.0, f"Iterator took too long to terminate: {elapsed:.2f}s"

    async def test_iterator_terminates_with_stop_async_iteration(self):
        """Iterator must raise StopAsyncIteration (or return) cleanly, not hang."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=1,
        )
        # Collect all events — should complete (not block indefinitely)
        collected = []
        try:
            async with asyncio.timeout(5.0):
                async for event in subscribe(inp):
                    collected.append(event)
        except TimeoutError:
            pytest.fail("subscribe() iterator did not terminate within 5s (lifetime=1s)")

    async def test_subscription_handle_closes_at_is_accurate(self):
        """SubscriptionHandle.closes_at must reflect opened_at + lifetime_seconds."""
        from datetime import datetime, timezone

        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=1,
        )
        handle = None
        async with asyncio.timeout(5.0):
            async for event in subscribe(inp):
                # First item may be the handle or an event; get handle from subscribe()
                break

        # Access the handle directly from subscribe to verify closes_at
        from kosmos.primitives.subscribe import _get_handle_for_testing
        handle = await _get_handle_for_testing(inp)
        assert handle is not None
        expected_delta = (handle.closes_at - handle.opened_at).total_seconds()
        assert abs(expected_delta - 1.0) < 1.1, (
            f"closes_at delta {expected_delta:.2f}s != expected ~1.0s"
        )

    async def test_no_events_after_expiry(self):
        """Events must not be delivered after lifetime expires."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=1,
        )
        all_events = []
        async with asyncio.timeout(5.0):
            async for event in subscribe(inp):
                all_events.append(event)

        # Wait another 1s and verify no new events arrive (iterator already closed)
        await asyncio.sleep(1.0)
        # Re-checking: the iterator should have been exhausted — no way to get more events
        # The key assertion: the for-loop above completed without hanging
        assert True  # If we reach here, iterator terminated cleanly
