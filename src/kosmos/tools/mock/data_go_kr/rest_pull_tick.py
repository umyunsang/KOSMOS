# SPDX-License-Identifier: Apache-2.0
"""T059 [P] — Mock REST-pull tick adapter for data.go.kr byte-mirror surface.

tool_id = "mock_rest_pull_tick_v1"
Modality: MODALITY_REST_PULL.

Emits RestPullTickEvent on each polling tick.

The harness enforces a minimum 10s polling interval (research.md §4, T054).
The adapter declares its preferred polling_interval via params; the harness
clamps it to max(10, adapter_declared).

For test purposes, the mock ignores the polling interval and emits a single
tick immediately (or N ticks if tick_count param is set).

Adapter-declared polling_interval default: 30s (per AGENTS.md decision,
documented below in DECISIONS).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Final

from kosmos.primitives.subscribe import (
    _MIN_POLLING_INTERVAL_SECONDS,
    MODALITY_REST_PULL,
    RestPullTickEvent,
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
_ACTUAL_ENDPOINT: Final = "https://api.gateway.kosmos.gov.kr/v1/subscribe/data_go_kr/rest-poll"
_SECURITY_WRAPPING: Final = "data.go.kr REST API key + 행정안전부 open API gateway"
_POLICY_AUTHORITY: Final = "https://www.data.go.kr/ugs/selectPublicDataPageList.do"
_INTERNATIONAL_REF: Final = "(generic REST polling)"


def get_transparency_metadata() -> dict[str, Any]:
    """Return the six transparency fields for this subscribe adapter.

    Used by the registry-wide transparency scan (FR-006) to verify
    that subscribe adapters declare their transparency metadata even though
    they yield events rather than returning a response dict.
    """
    return stamp_mock_response(
        {"tool_id": "mock_rest_pull_tick_v1", "adapter_type": "subscribe"},
        reference_implementation=_REFERENCE_IMPL,
        actual_endpoint_when_live=_ACTUAL_ENDPOINT,
        security_wrapping_pattern=_SECURITY_WRAPPING,
        policy_authority=_POLICY_AUTHORITY,
        international_reference=_INTERNATIONAL_REF,
    )

# DECISION: Default polling_interval = 30s.
# Rationale: data.go.kr free tier allows 1000 calls/day per service key
# (~12s minimum between calls). 30s provides comfortable headroom without
# being so infrequent that near-realtime alerts are missed.
# The harness enforces floor=10s regardless; adapters may set higher values.
_DEFAULT_POLLING_INTERVAL_SECONDS: float = 30.0

# Mock payload simulating a data.go.kr REST response for public notices
_MOCK_PAYLOAD: dict[str, object] = {
    "response": {
        "header": {
            "resultCode": "00",
            "resultMsg": "NORMAL_SERVICE",
        },
        "body": {
            "items": {
                "item": [
                    {
                        "noticeNo": "20260419-001",
                        "title": "2026년도 국토교통부 공고 제001호",
                        "pubDate": "2026-04-19T09:00:00+09:00",
                        "category": "국토교통",
                    }
                ]
            },
            "numOfRows": 1,
            "pageNo": 1,
            "totalCount": 1,
        },
    }
}


def _make_response_hash(payload: dict[str, object]) -> str:
    """SHA-256 of the JSON-serialized response payload."""
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def _rest_pull_tick_generator(
    inp: SubscribeInput,
    handle: SubscriptionHandle,
) -> AsyncIterator[RestPullTickEvent]:
    """Async generator producing REST-pull tick events.

    Parameters from inp.params:
    - polling_interval_seconds (float): Override; harness clamps to >= 10s.
    - tick_count (int): Total ticks to emit (default 1 for most tests).
    - tick_delay_seconds (float): Delay between ticks (default = clamped interval).
    """
    params = inp.params
    raw_interval = float(
        params.get("polling_interval_seconds", _DEFAULT_POLLING_INTERVAL_SECONDS)  # type: ignore[arg-type]
    )
    # Harness enforces minimum interval (FR-REST-pull, research §4)
    polling_interval = max(raw_interval, _MIN_POLLING_INTERVAL_SECONDS)

    tick_count = int(params.get("tick_count", 1))  # type: ignore[call-overload]
    # For test convenience, allow override of actual sleep time
    tick_delay = float(params.get("tick_delay_seconds", polling_interval))  # type: ignore[arg-type]
    # But still enforce minimum in production path
    tick_delay = max(tick_delay, _MIN_POLLING_INTERVAL_SECONDS)

    emitted = 0
    while emitted < tick_count:
        # Check lifetime before emitting
        now = datetime.now(UTC)
        if now.timestamp() > handle.closes_at.timestamp():
            break

        payload = dict(_MOCK_PAYLOAD)  # shallow copy for determinism
        response_hash = _make_response_hash(payload)
        tick_at = datetime.now(UTC)

        event = RestPullTickEvent(
            tool_id=inp.tool_id,
            tick_at=tick_at,
            response_hash=response_hash,
            payload=payload,
        )
        yield event
        emitted += 1

        if emitted < tick_count:
            await asyncio.sleep(tick_delay)


@dataclass
class _MockRestPullTickTool:
    """Lightweight tool descriptor for the REST-pull tick mock adapter."""

    tool_id: str = "mock_rest_pull_tick_v1"
    modality: str = MODALITY_REST_PULL
    polling_interval_seconds: float = _DEFAULT_POLLING_INTERVAL_SECONDS


MOCK_REST_PULL_TICK_TOOL = _MockRestPullTickTool()

# Register with the subscribe primitive's adapter registry
register_subscribe_adapter(
    tool_id=MOCK_REST_PULL_TICK_TOOL.tool_id,
    modality=MODALITY_REST_PULL,
    adapter_fn=_rest_pull_tick_generator,
)

logger.debug("Registered mock REST-pull tick adapter: %r", MOCK_REST_PULL_TICK_TOOL.tool_id)

__all__ = ["MOCK_REST_PULL_TICK_TOOL", "get_transparency_metadata"]
