# SPDX-License-Identifier: Apache-2.0
"""T060 [P] — Mock RSS 2.0 public notices adapter for data.go.kr surface.

tool_id = "mock_rss_public_notices_v1"
Modality: MODALITY_RSS.

Emits RssItemEvent with guid de-duplication via RssGuidTracker (per-handle).
The RSS 2.0 spec guid edge case (research.md §4):
- Duplicate guids within a handle are suppressed.
- reset_guids param can force the tracker to reset (simulating publisher reuse).

Fixture items are drawn from a static feed simulating a Korean government
public notices RSS 2.0 feed (data.go.kr RSS format).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from kosmos.primitives.subscribe import (
    MODALITY_RSS,
    RssGuidTracker,
    RssItemEvent,
    SubscribeInput,
    SubscriptionHandle,
    register_subscribe_adapter,
)
from kosmos.tools.transparency import stamp_mock_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transparency constants — Epic ε #2296 retrofit (FR-005 / FR-025)
# contracts/mock-adapter-response-shape.md § 4 "EXISTING (retrofitted)" row
# ---------------------------------------------------------------------------

_REFERENCE_IMPL: Final = "ax-infrastructure-callable-channel"
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/subscribe/data_go_kr/rss-notices"
_SECURITY_WRAPPING: Final = "RSS 2.0 over HTTPS + data.go.kr API key"
_POLICY_AUTHORITY: Final = "https://www.data.go.kr/ugs/selectPublicDataPageList.do"
_INTERNATIONAL_REF: Final = "(generic RSS feed)"


def get_transparency_metadata() -> dict[str, Any]:
    """Return the six transparency fields for this subscribe adapter.

    Used by the registry-wide transparency scan (FR-006) to verify
    that subscribe adapters declare their transparency metadata even though
    they yield events rather than returning a response dict.
    """
    return stamp_mock_response(
        {"tool_id": "mock_rss_public_notices_v1", "adapter_type": "subscribe"},
        reference_implementation=_REFERENCE_IMPL,
        actual_endpoint_when_live=_ACTUAL_ENDPOINT,
        security_wrapping_pattern=_SECURITY_WRAPPING,
        policy_authority=_POLICY_AUTHORITY,
        international_reference=_INTERNATIONAL_REF,
    )

# Static RSS 2.0 fixture items (simulating a public notices feed)
_RSS_FIXTURES = [
    {
        "guid": "notice-2026-001",
        "title": "국토교통부 공고 제2026-001호 — 도시개발구역 지정",
        "link": "https://www.data.go.kr/notices/2026-001",
        "published_at": "2026-04-19T09:00:00+09:00",
        "description": "서울시 강남구 일원 도시개발구역 지정 공고입니다.",
    },
    {
        "guid": "notice-2026-002",
        "title": "보건복지부 공고 제2026-002호 — 의료기관 인증 기준 개정",
        "link": "https://www.data.go.kr/notices/2026-002",
        "published_at": "2026-04-19T10:00:00+09:00",
        "description": "의료기관 인증 평가 기준 개정 사항 안내.",
    },
    {
        "guid": "notice-2026-003",
        "title": "행정안전부 공고 제2026-003호 — 재난 안전 관리 계획",
        "link": "https://www.data.go.kr/notices/2026-003",
        "published_at": "2026-04-19T11:00:00+09:00",
        "description": "2026년 재난 및 안전관리 기본 계획 수립 완료.",
    },
    {
        "guid": "notice-2026-004",
        "title": "환경부 공고 제2026-004호 — 대기질 관리 특별 대책",
        "link": "https://www.data.go.kr/notices/2026-004",
        "published_at": "2026-04-19T12:00:00+09:00",
        "description": "수도권 미세먼지 특별 대책 강화 방안 공고.",
    },
]


def _parse_rfc3339(dt_str: str) -> datetime:
    """Parse RFC 3339 string to datetime with timezone."""
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return datetime.now(UTC)


async def _rss_notices_generator(
    inp: SubscribeInput,
    handle: SubscriptionHandle,
) -> AsyncIterator[RssItemEvent]:
    """Async generator producing RSS 2.0 public notice events with guid de-dup.

    Parameters from inp.params:
    - item_delay_seconds (float): Delay between items (default 0.05s).
    - reset_guids (bool): If True, tracker is reset after first pass (Edge Case test).
    - repeat_count (int): How many full passes over the fixture (default 1).
      With reset_guids=True and repeat_count=2, the second pass re-delivers all items.
    """
    params = inp.params
    item_delay = float(params.get("item_delay_seconds", 0.05))  # type: ignore[arg-type]
    reset_guids = bool(params.get("reset_guids", False))
    repeat_count = int(params.get("repeat_count", 1))  # type: ignore[call-overload]

    # Per-subscription guid tracker (stateful within this handle)
    tracker = RssGuidTracker()

    for pass_num in range(repeat_count):
        if pass_num > 0 and reset_guids:
            # Simulate publisher resetting guids — Edge Case from research.md §4
            tracker.reset()

        for fixture in _RSS_FIXTURES:
            # Check lifetime
            if datetime.now(UTC).timestamp() > handle.closes_at.timestamp():
                return

            guid = fixture["guid"]
            if not tracker.is_new(guid):
                # Duplicate guid suppressed
                continue

            event = RssItemEvent(
                feed_tool_id=inp.tool_id,
                guid=guid,
                published_at=_parse_rfc3339(fixture["published_at"]),
                title=fixture["title"],
                link=fixture.get("link"),
                description=fixture.get("description"),
            )
            yield event

            if item_delay > 0:
                await asyncio.sleep(item_delay)
            else:
                await asyncio.sleep(0)


@dataclass
class _MockRssPublicNoticesTool:
    """Lightweight tool descriptor for the RSS public notices mock adapter."""

    tool_id: str = "mock_rss_public_notices_v1"
    modality: str = MODALITY_RSS


MOCK_RSS_PUBLIC_NOTICES_TOOL = _MockRssPublicNoticesTool()

# Register with the subscribe primitive's adapter registry
register_subscribe_adapter(
    tool_id=MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id,
    modality=MODALITY_RSS,
    adapter_fn=_rss_notices_generator,
)

logger.debug("Registered mock RSS public notices adapter: %r", MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id)

__all__ = ["MOCK_RSS_PUBLIC_NOTICES_TOOL", "get_transparency_metadata"]
