# SPDX-License-Identifier: Apache-2.0
"""Contract tests for LookupOutput discriminated union — T018.

Round-trips each of the 5 output variants through model_validate_json() to
verify that the Pydantic v2 schema matches the frozen contract in
specs/022-mvp-main-tool/contracts/lookup.output.schema.json.

All tests are pure-Python; no network calls.
"""

from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from kosmos.tools.models import (
    LookupCollection,
    LookupError,  # noqa: A004
    LookupOutput,  # type: ignore[attr-defined]
    LookupRecord,
    LookupSearchResult,
    LookupTimeseries,
)

_ADAPTER: TypeAdapter[object] = TypeAdapter(LookupOutput)  # type: ignore[arg-type]

# Shared meta block for fetch variants
_META = {
    "source": "koroad_accident_hazard_search",
    "fetched_at": "2024-01-15T12:00:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "elapsed_ms": 142,
    "rate_limit_remaining": None,
}


# ---------------------------------------------------------------------------
# LookupSearchResult round-trips
# ---------------------------------------------------------------------------


class TestLookupSearchResultRoundTrip:
    def test_empty_candidates(self):
        raw = json.dumps(
            {
                "kind": "search",
                "candidates": [],
                "total_registry_size": 0,
                "effective_top_k": 0,
                "reason": "empty_registry",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupSearchResult)
        assert result.kind == "search"
        assert result.reason == "empty_registry"

    def test_with_candidates(self):
        raw = json.dumps(
            {
                "kind": "search",
                "candidates": [
                    {
                        "tool_id": "koroad_accident_hazard_search",
                        "score": 0.8456,
                        "required_params": ["adm_cd", "year"],
                        "search_hint": "교통사고 위험지점 adm_cd year",
                        "why_matched": "BM25 score 0.8456 on search_hint",
                        "requires_auth": False,
                        "is_personal_data": False,
                    }
                ],
                "total_registry_size": 10,
                "effective_top_k": 5,
                "reason": "ok",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupSearchResult)
        assert len(result.candidates) == 1
        assert result.candidates[0].tool_id == "koroad_accident_hazard_search"
        assert result.candidates[0].score == pytest.approx(0.8456)


# ---------------------------------------------------------------------------
# LookupRecord round-trips
# ---------------------------------------------------------------------------


class TestLookupRecordRoundTrip:
    def test_basic_record(self):
        raw = json.dumps(
            {
                "kind": "record",
                "item": {"temperature": 22.5, "condition": "맑음"},
                "meta": _META,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupRecord)
        assert result.kind == "record"
        assert result.item["condition"] == "맑음"
        assert result.meta.source == "koroad_accident_hazard_search"

    def test_missing_meta_raises(self):
        raw = json.dumps(
            {
                "kind": "record",
                "item": {"key": "value"},
            }
        )
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)


# ---------------------------------------------------------------------------
# LookupCollection round-trips
# ---------------------------------------------------------------------------


class TestLookupCollectionRoundTrip:
    def test_happy_path(self):
        raw = json.dumps(
            {
                "kind": "collection",
                "items": [
                    {"spot_nm": "강남구 개포동 일대", "occrrnc_cnt": 12},
                    {"spot_nm": "강남구 삼성동 일대", "occrrnc_cnt": 9},
                ],
                "total_count": 2,
                "next_cursor": None,
                "meta": _META,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupCollection)
        assert result.kind == "collection"
        assert len(result.items) == 2
        assert result.total_count == 2

    def test_empty_collection(self):
        raw = json.dumps(
            {
                "kind": "collection",
                "items": [],
                "total_count": 0,
                "meta": _META,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupCollection)
        assert result.items == []

    def test_null_total_count_allowed(self):
        raw = json.dumps(
            {
                "kind": "collection",
                "items": [{"x": 1}],
                "total_count": None,
                "meta": _META,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupCollection)
        assert result.total_count is None


# ---------------------------------------------------------------------------
# LookupTimeseries round-trips
# ---------------------------------------------------------------------------


class TestLookupTimeseriesRoundTrip:
    def test_hourly_timeseries(self):
        raw = json.dumps(
            {
                "kind": "timeseries",
                "points": [
                    {"ts": "2024-01-15T10:00:00Z", "value": 5},
                    {"ts": "2024-01-15T11:00:00Z", "value": 7},
                ],
                "interval": "hour",
                "meta": _META,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupTimeseries)
        assert result.interval == "hour"
        assert len(result.points) == 2

    def test_invalid_interval_raises(self):
        raw = json.dumps(
            {
                "kind": "timeseries",
                "points": [],
                "interval": "week",  # not in enum
                "meta": _META,
            }
        )
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)


# ---------------------------------------------------------------------------
# LookupError round-trips
# ---------------------------------------------------------------------------


class TestLookupErrorRoundTrip:
    def test_auth_required_no_meta(self):
        raw = json.dumps(
            {
                "kind": "error",
                "reason": "auth_required",
                "message": "Tool requires authentication.",
                "retryable": False,
                "meta": None,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupError)
        assert result.reason == "auth_required"
        assert result.meta is None

    def test_unknown_tool_with_meta(self):
        raw = json.dumps(
            {
                "kind": "error",
                "reason": "unknown_tool",
                "message": "Tool 'nonexistent_tool' is not registered.",
                "retryable": False,
                "meta": _META,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupError)
        assert result.reason == "unknown_tool"
        assert result.meta is not None

    def test_retryable_timeout(self):
        raw = json.dumps(
            {
                "kind": "error",
                "reason": "timeout",
                "message": "Upstream API timed out after 30s.",
                "retryable": True,
                "upstream_code": "504",
                "upstream_message": "Gateway Timeout",
                "meta": _META,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, LookupError)
        assert result.retryable is True
        assert result.upstream_code == "504"

    def test_invalid_reason_raises(self):
        raw = json.dumps(
            {
                "kind": "error",
                "reason": "bad_credentials",  # not in enum
                "message": "test",
            }
        )
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)


# ---------------------------------------------------------------------------
# Discriminator rejection
# ---------------------------------------------------------------------------


class TestLookupDiscriminatorRejection:
    def test_unknown_kind_raises(self):
        raw = json.dumps({"kind": "unknown", "data": "x"})
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)

    def test_missing_kind_raises(self):
        raw = json.dumps({"items": [], "total_count": 0})
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)
