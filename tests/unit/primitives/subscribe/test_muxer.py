# SPDX-License-Identifier: Apache-2.0
"""T046 [P] — Muxer test: events from 3 modalities flow through one iterator.

Registers mock_cbs_disaster_v1, mock_rest_pull_tick_v1, mock_rss_public_notices_v1,
and asserts that events from all 3 modalities surface through the same
AsyncIterator with discriminated ``kind`` field.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest

from kosmos.primitives.subscribe import (
    CbsBroadcastEvent,
    RestPullTickEvent,
    RssItemEvent,
    SubscribeInput,
    SubscriptionHandle,
    subscribe,
)
from kosmos.tools.mock.cbs.disaster_feed import MOCK_CBS_DISASTER_TOOL
from kosmos.tools.mock.data_go_kr.rest_pull_tick import MOCK_REST_PULL_TICK_TOOL
from kosmos.tools.mock.data_go_kr.rss_notices import MOCK_RSS_PUBLIC_NOTICES_TOOL


@pytest.mark.asyncio
class TestMuxer:
    """T046 — All 3 modalities flow through a single AsyncIterator[SubscriptionEvent]."""

    async def test_cbs_events_have_kind_cbs_broadcast(self):
        """CBS mock adapter emits events with kind='cbs_broadcast'."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        events = []
        async for event in subscribe(inp):
            events.append(event)
            if len(events) >= 2:
                break
        assert len(events) >= 1
        for ev in events:
            assert ev.kind == "cbs_broadcast"
            assert isinstance(ev, CbsBroadcastEvent)

    async def test_rest_pull_events_have_kind_rest_pull_tick(self):
        """REST pull mock adapter emits events with kind='rest_pull_tick'."""
        inp = SubscribeInput(
            tool_id=MOCK_REST_PULL_TICK_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        events = []
        async for event in subscribe(inp):
            events.append(event)
            if len(events) >= 1:
                break
        assert len(events) >= 1
        for ev in events:
            assert ev.kind == "rest_pull_tick"
            assert isinstance(ev, RestPullTickEvent)

    async def test_rss_events_have_kind_rss_item(self):
        """RSS mock adapter emits events with kind='rss_item'."""
        inp = SubscribeInput(
            tool_id=MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        events = []
        async for event in subscribe(inp):
            events.append(event)
            if len(events) >= 2:
                break
        assert len(events) >= 1
        for ev in events:
            assert ev.kind == "rss_item"
            assert isinstance(ev, RssItemEvent)

    async def test_each_event_has_discriminated_kind_field(self):
        """Every event yielded from subscribe() must have a ``kind`` field."""
        for tool in [MOCK_CBS_DISASTER_TOOL, MOCK_REST_PULL_TICK_TOOL, MOCK_RSS_PUBLIC_NOTICES_TOOL]:
            inp = SubscribeInput(
                tool_id=tool.tool_id,
                params={},
                lifetime_seconds=5,
            )
            async for event in subscribe(inp):
                assert hasattr(event, "kind"), f"Event from {tool.tool_id} missing 'kind'"
                assert isinstance(event.kind, str)
                assert event.kind in {"cbs_broadcast", "rest_pull_tick", "rss_item", "subscription_backpressure_drop"}
                break  # Only need 1 event per modality

    async def test_subscribe_returns_async_iterator(self):
        """subscribe() must return an AsyncIterator (not a coroutine)."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        result = subscribe(inp)
        assert hasattr(result, "__aiter__"), "subscribe() must return an AsyncIterator"
