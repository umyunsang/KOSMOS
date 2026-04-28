# SPDX-License-Identifier: Apache-2.0
"""Spec 1979 T031 — fixture plugin adapter for E2E PTY scenario.

Returns canned subway arrival data without making any outbound network
call. The fixture stays in sync with the manifest's tool_id =
plugin.seoul_subway.lookup.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from kosmos.tools.models import GovAPITool


class LookupInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    station: str = Field(min_length=1, description="역명 (e.g. 강남)")


class LookupOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    station: str
    arrivals: list[dict[str, Any]]


TOOL = GovAPITool(
    id="plugin.seoul_subway.lookup",
    ministry="OTHER",
    category=["transport"],
    endpoint="https://test.local/seoul-subway/arrivals",
    name_ko="서울 지하철 도착 정보 조회 (fixture)",
    name_en="Seoul subway arrival lookup (fixture)",
    description_ko="서울 지하철 실시간 도착 정보 (E2E fixture; 외부 API 호출 없음)",
    description_en="Seoul subway real-time arrival info (E2E fixture; no outbound calls)",
    search_hint="지하철 도착 시간 강남역 subway arrival station",
    auth_type="public",
    auth_level="public",
    pipa_class="non_personal",
    dpa_reference=None,
    requires_auth=False,
    is_personal_data=False,
    is_concurrency_safe=True,
    cache_ttl_seconds=60,
    rate_limit_per_minute=30,
    is_irreversible=False,
    is_core=True,
    input_schema=LookupInput,
    output_schema=LookupOutput,
)


async def adapter(payload: LookupInput) -> dict[str, Any]:
    """Canned response — no outbound network call."""
    return {
        "station": payload.station,
        "arrivals": [
            {"line": "2", "direction": "성수", "minutes_to_arrival": 5},
            {"line": "2", "direction": "사당", "minutes_to_arrival": 3},
        ],
    }
