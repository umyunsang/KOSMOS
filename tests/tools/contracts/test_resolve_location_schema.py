# SPDX-License-Identifier: Apache-2.0
"""Contract tests for ResolveLocationOutput discriminated union — T017.

Round-trips each of the 6 output variants through model_validate_json() to
verify that the Pydantic v2 schema matches the frozen contract in
specs/022-mvp-main-tool/contracts/resolve_location.output.schema.json.

All tests are pure-Python; no network calls.
"""

from __future__ import annotations

import json

import pytest
from pydantic import TypeAdapter, ValidationError

from ummaya.tools.models import (
    AddressResult,
    AdmCodeResult,
    CoordResult,
    POIResult,
    RegionResult,
    ResolveBundle,
    ResolveError,
    ResolveLocationOutputUnion,  # type: ignore[attr-defined]
)

_ADAPTER: TypeAdapter[object] = TypeAdapter(ResolveLocationOutputUnion)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Happy-path round-trips for each variant
# ---------------------------------------------------------------------------


class TestCoordResultRoundTrip:
    def test_high_confidence(self):
        raw = json.dumps(
            {
                "kind": "coords",
                "lat": 37.5665,
                "lon": 126.9780,
                "confidence": "high",
                "source": "kakao",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, CoordResult)
        assert result.kind == "coords"
        assert result.lat == pytest.approx(37.5665)
        assert result.confidence == "high"
        assert result.source == "kakao"

    def test_low_confidence_sgis_source(self):
        raw = json.dumps(
            {
                "kind": "coords",
                "lat": 35.1796,
                "lon": 129.0756,
                "confidence": "low",
                "source": "sgis",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, CoordResult)
        assert result.source == "sgis"


class TestAdmCodeResultRoundTrip:
    def test_eupmyeondong_level(self):
        raw = json.dumps(
            {
                "kind": "adm_cd",
                "code": "1168000000",
                "name": "서울특별시 강남구",
                "level": "eupmyeondong",
                "source": "juso",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, AdmCodeResult)
        assert result.code == "1168000000"
        assert len(result.code) == 10
        assert result.level == "eupmyeondong"
        assert result.source == "juso"

    def test_sido_level_sgis(self):
        raw = json.dumps(
            {
                "kind": "adm_cd",
                "code": "1100000000",
                "name": "서울특별시",
                "level": "sido",
                "source": "sgis",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, AdmCodeResult)
        assert result.level == "sido"

    def test_invalid_code_pattern_raises(self):
        raw = json.dumps(
            {
                "kind": "adm_cd",
                "code": "ABCDE12345",  # must be 10 digits
                "name": "invalid",
                "level": "sido",
                "source": "juso",
            }
        )
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)

    def test_invalid_source_raises(self):
        # Spec 2522 T047 — "kakao" 가 AdmCodeResult.source 에 추가 (Kakao
        # b_code fallback). 이전에는 ["sgis", "juso"] 만 valid 였으나 v4 에서
        # ["sgis", "juso", "kakao"] 로 확장. invalid 검증은 명백한 미허용 값으로.
        raw = json.dumps(
            {
                "kind": "adm_cd",
                "code": "1168000000",
                "name": "강남구",
                "level": "sigungu",
                "source": "vworld",  # not in allow-list
            }
        )
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)


class TestAddressResultRoundTrip:
    def test_full_address(self):
        raw = json.dumps(
            {
                "kind": "address",
                "road_address": "서울특별시 강남구 테헤란로 152",
                "jibun_address": "서울특별시 강남구 역삼동 737-1",
                "postal_code": "06236",
                "source": "kakao",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, AddressResult)
        assert result.kind == "address"
        assert result.postal_code == "06236"

    def test_null_fields_allowed(self):
        raw = json.dumps(
            {
                "kind": "address",
                "road_address": None,
                "jibun_address": None,
                "postal_code": None,
                "source": "juso",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, AddressResult)
        assert result.road_address is None


class TestPOIResultRoundTrip:
    def test_full_poi(self):
        raw = json.dumps(
            {
                "kind": "poi",
                "name": "강남역",
                "category": "지하철역",
                "lat": 37.4979,
                "lon": 127.0276,
                "source": "kakao",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, POIResult)
        assert result.name == "강남역"
        assert result.source == "kakao"

    def test_invalid_poi_source_raises(self):
        raw = json.dumps(
            {
                "kind": "poi",
                "name": "강남역",
                "category": "역",
                "lat": 37.4979,
                "lon": 127.0276,
                "source": "juso",  # not allowed for poi
            }
        )
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)


class TestRegionResultRoundTrip:
    def test_region_result(self):
        raw = json.dumps(
            {
                "kind": "region",
                "region_type": "B",
                "address_name": "부산광역시 사하구 하단동",
                "region_1depth_name": "부산광역시",
                "region_2depth_name": "사하구",
                "region_3depth_name": "하단동",
                "region_4depth_name": "",
                "code": "2638010300",
                "x": 128.96044110450242,
                "y": 35.11437276296668,
                "source": "kakao",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, RegionResult)
        assert result.region_2depth_name == "사하구"


class TestResolveBundleRoundTrip:
    def test_full_bundle(self):
        raw = json.dumps(
            {
                "kind": "bundle",
                "source": "bundle",
                "coords": {
                    "kind": "coords",
                    "lat": 37.5665,
                    "lon": 126.9780,
                    "confidence": "high",
                    "source": "kakao",
                },
                "adm_cd": {
                    "kind": "adm_cd",
                    "code": "1168000000",
                    "name": "강남구",
                    "level": "sigungu",
                    "source": "juso",
                },
                "address": None,
                "poi": None,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, ResolveBundle)
        assert result.coords is not None
        assert result.adm_cd is not None

    def test_minimal_bundle_all_none(self):
        """Bundle with all sub-results None is valid (partial resolution)."""
        raw = json.dumps(
            {
                "kind": "bundle",
                "source": "bundle",
                "coords": None,
                "adm_cd": None,
                "address": None,
                "poi": None,
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, ResolveBundle)


class TestResolveErrorRoundTrip:
    def test_not_found_error(self):
        raw = json.dumps(
            {
                "kind": "error",
                "reason": "not_found",
                "message": "Could not resolve coordinates for query '존재하지않는장소'.",
                "candidates": [],
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, ResolveError)
        assert result.reason == "not_found"
        assert result.candidates == []

    def test_invalid_reason_raises(self):
        raw = json.dumps(
            {
                "kind": "error",
                "reason": "unknown_reason",  # not in the enum
                "message": "test",
            }
        )
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)

    def test_empty_query_error(self):
        raw = json.dumps(
            {
                "kind": "error",
                "reason": "empty_query",
                "message": "Query must not be empty.",
            }
        )
        result = _ADAPTER.validate_json(raw)
        assert isinstance(result, ResolveError)


# ---------------------------------------------------------------------------
# Discriminator rejection tests
# ---------------------------------------------------------------------------


class TestDiscriminatorRejection:
    def test_unknown_kind_raises(self):
        raw = json.dumps({"kind": "unknown_variant", "data": "x"})
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)

    def test_missing_kind_raises(self):
        raw = json.dumps({"lat": 37.5665, "lon": 126.9780})
        with pytest.raises(ValidationError):
            _ADAPTER.validate_json(raw)
