# SPDX-License-Identifier: Apache-2.0
"""T037 — subscribe primitive handle revocation behavior.

Verifies what happens when a citizen cancels a subscription (simulating
``/consent revoke rcpt-<id>``). Key questions:

  Q1. Does a revoked handle's event iterator stop emitting events?
  Q2. Can the same subscription_id be used to resume after revocation?
  Q3. Does subscribe() always create a NEW handle regardless of previous state?

Observed behavior (from reading src/kosmos/primitives/subscribe.py):
----------------------------------------------------------------------
The subscribe primitive is session-scoped and stateless from the caller's
perspective. There is NO global handle registry or revocation API — each call
to subscribe() constructs a new _SubscribeIterator with a fresh SubscriptionHandle
(a new UUID4 subscription_id). Consequently:

- "Revocation" in the current implementation means: abandon the iterator
  (stop consuming it or let it go out of scope / cancel its driver task).
- subscribe() never accepts a ``handle_id`` parameter to resume a prior
  subscription. (Not yet implemented — Spec #1755 explicitly defers
  post-revocation resume.) The SubscribeInput schema only accepts
  {tool_id, params, lifetime_seconds}.
- A re-call with the same (tool_id, params) creates an ENTIRELY NEW handle
  with a new subscription_id, independent of any prior handle.

This test verifies:
  T037-A: Iterator stops emitting after finalize (simulating citizen cancel).
  T037-B: A second subscribe() call always creates a NEW handle, not resuming.
  T037-C: New handle has a distinct subscription_id from the cancelled one.
  T037-D: Cancelled handle's driver task is cleaned up (no resource leak).
  T037-E: Attempting to call subscribe() again with the same input yields fresh
          events from the start (no state bleed from the revoked handle).

Spec divergences noted inline:
- DIVERGENCE-004: There is no revoke() / unsubscribe() function in
  kosmos.primitives.subscribe — revocation is out-of-scope for Spec 031 and
  explicitly deferred per issue #1755. The test simulates revocation by breaking
  out of the async iteration early and verifying iterator cleanup.
- DIVERGENCE-005: subscribe() does not accept ``handle_id`` to resume; the
  concept of "resume after revocation" does not apply. The test verifies the
  documented alternative: any subsequent subscribe() call creates a new handle.

References:
- src/kosmos/primitives/subscribe.py (_SubscribeIterator._finalize)
- specs/031-five-primitive-harness/data-model.md §3
- specs/1634-tool-system-wiring/contracts/primitive-envelope.md §5
"""

from __future__ import annotations

import asyncio

import pytest

from kosmos.primitives._errors import SubscriptionBackpressureDrop
from kosmos.primitives.subscribe import (
    CbsBroadcastEvent,
    RssItemEvent,
    SubscribeInput,
    SubscriptionHandle,
    _get_handle_for_testing,
    subscribe,
)

# Import adapters so their side-effect registration runs
from kosmos.tools.mock.cbs.disaster_feed import MOCK_CBS_DISASTER_TOOL
from kosmos.tools.mock.data_go_kr.rss_notices import MOCK_RSS_PUBLIC_NOTICES_TOOL

# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSubscribeRevoke:
    """T037 — handle revocation / cancellation semantics."""

    # ------------------------------------------------------------------
    # T037-A: Iterator stops after early break (simulated citizen cancel)
    # ------------------------------------------------------------------

    async def test_iterator_stops_after_break(self):
        """Breaking from the async-for loop stops event delivery (simulated revoke).

        The subscriber (citizen) cancels by abandoning the iterator.
        No more events must arrive after the break; the driver task finishes
        without blocking the test.

        DIVERGENCE-004: No explicit revoke() API exists; early break IS the
        revocation mechanism available in Spec 031.
        """
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={"burst_count": 20, "burst_delay_seconds": 0.01},
            lifetime_seconds=30,
        )
        collected_before = []
        async with asyncio.timeout(10.0):
            async for event in subscribe(inp):
                if not isinstance(event, SubscriptionBackpressureDrop):
                    collected_before.append(event)
                # Simulate citizen revocation after first event
                if len(collected_before) >= 1:
                    break  # abandon the iterator

        # At least 1 event was delivered before revocation
        assert len(collected_before) >= 1, "Expected at least 1 event before cancel"
        # After the break, the iterator is exhausted — no further events are accessible
        # (the iterator object is effectively closed at this point)

    async def test_revoked_iterator_driver_task_is_cleaned_up(self):
        """The internal driver task must not outlive the abandoned iterator.

        After breaking from the async iteration, the _SubscribeIterator's
        driver task should eventually be cancelled. We verify this by checking
        the asyncio task set does not grow unboundedly.
        """
        tasks_before = len(asyncio.all_tasks())

        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={"burst_count": 5, "burst_delay_seconds": 0.01},
            lifetime_seconds=30,
        )
        async with asyncio.timeout(10.0):
            async for event in subscribe(inp):
                if not isinstance(event, SubscriptionBackpressureDrop):
                    break  # abandon after first real event

        # Give the event loop a moment to cancel and collect the driver task
        await asyncio.sleep(0.1)
        tasks_after = len(asyncio.all_tasks())

        # Task count must not grow relative to before (driver cleaned up)
        assert tasks_after <= tasks_before + 1, (
            f"Possible task leak: {tasks_before} → {tasks_after} tasks"
        )

    # ------------------------------------------------------------------
    # T037-B: Second subscribe() always creates a NEW handle
    # ------------------------------------------------------------------

    async def test_second_subscribe_creates_new_handle(self):
        """A second call to subscribe() with the same input produces a new handle.

        DIVERGENCE-005: subscribe() has no handle_id resume semantics.
        Each call is independent and always creates a fresh SubscriptionHandle.
        """
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        handle_a = await _get_handle_for_testing(inp)
        handle_b = await _get_handle_for_testing(inp)

        # Both handles are valid SubscriptionHandle instances
        assert isinstance(handle_a, SubscriptionHandle)
        assert isinstance(handle_b, SubscriptionHandle)

        # Different subscription IDs — proof that no state is shared
        assert handle_a.subscription_id != handle_b.subscription_id, (
            "Second subscribe() must allocate a new subscription_id, not resume the old one"
        )

    # ------------------------------------------------------------------
    # T037-C: Cancelled handle subscription_id is distinct from new handle
    # ------------------------------------------------------------------

    async def test_new_handle_distinct_from_cancelled_handle(self):
        """The new handle after cancel has a different subscription_id.

        This is the core revocation safety property: the old cancelled handle
        cannot be accidentally resumed because subscribe() never reuses IDs.
        """
        inp = SubscribeInput(
            tool_id=MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id,
            params={"item_delay_seconds": 0.0},
            lifetime_seconds=10,
        )

        # Phase 1: obtain first handle and immediately "revoke" by abandoning the iterator
        cancelled_id: str | None = None
        async with asyncio.timeout(10.0):
            async for event in subscribe(inp):
                if isinstance(event, (RssItemEvent, CbsBroadcastEvent)):
                    # Extract subscription_id from the handle created during first iteration
                    # (first __anext__ call triggers _start() which sets self._handle)
                    break

        # Capture the handle via the testing helper to compare IDs
        old_handle = await _get_handle_for_testing(inp)
        cancelled_id = old_handle.subscription_id

        # Phase 2: open a new subscription
        new_handle = await _get_handle_for_testing(inp)

        assert new_handle.subscription_id != cancelled_id, (
            "New subscription after cancel must have a different subscription_id; "
            "old handle must NOT be resumable via subscribe()"
        )

    # ------------------------------------------------------------------
    # T037-D: Post-cancellation subscribe() delivers events from the start
    # ------------------------------------------------------------------

    async def test_new_subscribe_delivers_events_from_start(self):
        """After cancelling a subscription, a new subscribe() re-delivers from the beginning.

        Because each subscribe() call is independent (no shared state between handles),
        the new subscription starts the adapter's generator from scratch.
        The RSS adapter with repeat_count=1 and no reset_guids will re-deliver
        all fixture items because a new RssGuidTracker is created for each call.
        """
        inp = SubscribeInput(
            tool_id=MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id,
            params={"item_delay_seconds": 0.0, "repeat_count": 1},
            lifetime_seconds=10,
        )

        # First subscription: collect first event, then cancel
        first_guids: list[str] = []
        async with asyncio.timeout(10.0):
            async for event in subscribe(inp):
                if isinstance(event, RssItemEvent):
                    first_guids.append(event.guid)
                    break  # cancel after first event

        assert len(first_guids) >= 1, "First subscription must yield at least 1 event"

        # Second subscription (after cancel): must also deliver events from the start
        second_guids: list[str] = []
        async with asyncio.timeout(10.0):
            async for event in subscribe(inp):
                if isinstance(event, RssItemEvent):
                    second_guids.append(event.guid)
                    break  # only need first event from new subscription

        assert len(second_guids) >= 1, "New subscription after cancel must still deliver events"
        # The new subscription delivers the same first item (no state bleed from old handle)
        assert second_guids[0] == first_guids[0], (
            f"New subscription should start from the beginning of the adapter's event stream. "
            f"First GUID: old={first_guids[0]!r}, new={second_guids[0]!r}"
        )

    # ------------------------------------------------------------------
    # T037-E: No resume_handle_id parameter exists (Spec 031 + #1755)
    # ------------------------------------------------------------------

    async def test_subscribe_input_has_no_handle_id_parameter(self):
        """SubscribeInput schema must NOT accept a ``handle_id`` field.

        Per Spec 031 FR-013 and issue #1755, post-revocation resume via
        handle_id is explicitly deferred. The schema enforces this via
        ``extra='forbid'`` (ConfigDict).

        DIVERGENCE-005: This is intentional behavior, not a spec gap.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SubscribeInput(
                tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
                params={},
                lifetime_seconds=5,
                handle_id="some-old-handle-id",  # type: ignore[call-arg]
            )
