# SPDX-License-Identifier: Apache-2.0
"""T058 [P] — Mock CBS disaster broadcast adapter.

tool_id = "mock_cbs_disaster_v1"
Modality: MODALITY_CBS (3GPP TS 23.041 byte mirror).

Produces CbsBroadcastEvent fixtures covering message IDs 4370–4385
(ATIS-0700007 CMAS categories adopted by the Korean CBS profile).

Supports ``burst_count`` param for back-pressure testing (T049):
- burst_count (int, default 3): How many events to emit total.
- burst_delay_seconds (float, default 0.1): Delay between events.
  Set to 0.0 for back-pressure stress tests.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, TypedDict

from kosmos.primitives.subscribe import (
    MODALITY_CBS,
    CbsBroadcastEvent,
    SubscribeInput,
    SubscriptionHandle,
    register_subscribe_adapter,
)

logger = logging.getLogger(__name__)


class _CbsFixture(TypedDict):
    cbs_message_id: Literal[
        4370,
        4371,
        4372,
        4373,
        4374,
        4375,
        4376,
        4377,
        4378,
        4379,
        4380,
        4381,
        4382,
        4383,
        4384,
        4385,
    ]
    language: Literal["ko", "en"]
    body: str


# CBS message ID fixtures (3GPP TS 23.041 range 4370–4385)
_CBS_FIXTURES: list[_CbsFixture] = [
    {
        "cbs_message_id": 4370,
        "language": "ko",
        "body": "[긴급재난문자] 지진 발생 경보: 규모 4.5, 경상북도 일대. 즉시 대피하십시오.",
    },
    {
        "cbs_message_id": 4371,
        "language": "ko",
        "body": "[긴급재난문자] 호우 경보: 서울 전 지역. 강우량 80mm/h 이상 예상.",
    },
    {
        "cbs_message_id": 4372,
        "language": "en",
        "body": "[EMERGENCY ALERT] Tsunami warning issued for coastal areas. Move to high ground.",
    },
    {
        "cbs_message_id": 4373,
        "language": "ko",
        "body": "[재난문자] 산사태 위험 경보: 강원도 산간 지역. 외출을 자제하십시오.",
    },
    {
        "cbs_message_id": 4374,
        "language": "ko",
        "body": "[재난문자] 폭염 경보: 전국. 낮 최고 기온 39도 예상. 야외 활동 자제.",
    },
    {
        "cbs_message_id": 4375,
        "language": "en",
        "body": "[CIVIL ALERT] Nuclear power plant drill in progress. No action required.",
    },
]


def _make_payload_hash(body: str, received_at: datetime) -> str:
    """SHA-256 of raw bearer payload (body + timestamp ISO string)."""
    raw = f"{body}|{received_at.isoformat()}".encode()
    return hashlib.sha256(raw).hexdigest()


def _build_cbs_events(count: int) -> list[CbsBroadcastEvent]:
    """Build a list of CbsBroadcastEvent objects synchronously (no I/O)."""
    events: list[CbsBroadcastEvent] = []
    for i in range(count):
        fixture = _CBS_FIXTURES[i % len(_CBS_FIXTURES)]
        received_at = datetime.now(UTC)
        payload_hash = _make_payload_hash(fixture["body"], received_at)
        events.append(
            CbsBroadcastEvent(
                cbs_message_id=fixture["cbs_message_id"],
                received_at=received_at,
                payload_hash=payload_hash,
                language=fixture["language"],
                body=fixture["body"],
            )
        )
    return events


async def _cbs_disaster_generator(
    inp: SubscribeInput,
    handle: SubscriptionHandle,
) -> AsyncIterator[CbsBroadcastEvent]:
    """Async generator producing CBS broadcast events.

    Parameters from inp.params:
    - burst_count (int): Total events to emit (default 3).
    - burst_delay_seconds (float): Delay between events (default 0.1s).
      When set to 0.0, all events are yielded in one coroutine step
      (no intermediate awaits) to enable back-pressure testing.
    """
    params = inp.params
    burst_count = int(params.get("burst_count", 3))  # type: ignore[call-overload]
    burst_delay = float(params.get("burst_delay_seconds", 0.1))  # type: ignore[arg-type]

    if burst_delay == 0.0:
        # Burst mode: build all events synchronously and yield them without
        # any await between them so the queue fills up before the consumer
        # has a chance to drain it. This is the back-pressure stress path.
        events = _build_cbs_events(burst_count)
        for event in events:
            if datetime.now(UTC).timestamp() > handle.closes_at.timestamp():
                break
            yield event
        # Single yield at the end so the caller can switch context
        await asyncio.sleep(0)
        return

    # Normal mode: emit with delay between events
    emitted = 0
    fixture_idx = 0
    while emitted < burst_count:
        fixture = _CBS_FIXTURES[fixture_idx % len(_CBS_FIXTURES)]
        received_at = datetime.now(UTC)
        payload_hash = _make_payload_hash(fixture["body"], received_at)

        event = CbsBroadcastEvent(
            cbs_message_id=fixture["cbs_message_id"],
            received_at=received_at,
            payload_hash=payload_hash,
            language=fixture["language"],
            body=fixture["body"],
        )
        yield event
        emitted += 1
        fixture_idx += 1

        await asyncio.sleep(burst_delay)

        # Check lifetime
        if datetime.now(UTC).timestamp() > handle.closes_at.timestamp():
            break


@dataclass
class _MockCbsDisasterTool:
    """Lightweight tool descriptor for the CBS disaster mock adapter."""

    tool_id: str = "mock_cbs_disaster_v1"
    modality: str = MODALITY_CBS


MOCK_CBS_DISASTER_TOOL = _MockCbsDisasterTool()

# Register with the subscribe primitive's adapter registry
register_subscribe_adapter(
    tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
    modality=MODALITY_CBS,
    adapter_fn=_cbs_disaster_generator,
)

logger.debug("Registered mock CBS disaster adapter: %r", MOCK_CBS_DISASTER_TOOL.tool_id)

__all__ = ["MOCK_CBS_DISASTER_TOOL"]
