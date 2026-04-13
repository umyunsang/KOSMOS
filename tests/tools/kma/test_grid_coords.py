# SPDX-License-Identifier: Apache-2.0
"""Unit tests for KMA grid coordinate lookup utilities."""

from __future__ import annotations

import pytest

from kosmos.tools.kma.grid_coords import REGION_TO_GRID, lookup_grid


class TestRegionToGrid:
    def test_has_at_least_17_metro_cities(self) -> None:
        """REGION_TO_GRID must contain at least 17 metropolitan city centroids."""
        metro_cities = [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "경기",
            "강원",
            "충북",
            "충남",
            "전북",
            "전남",
            "경북",
            "경남",
            "제주",
        ]
        for city in metro_cities:
            assert city in REGION_TO_GRID, f"REGION_TO_GRID missing key: {city!r}"

    def test_all_values_are_int_tuples(self) -> None:
        for key, coords in REGION_TO_GRID.items():
            assert isinstance(coords, tuple), f"Value for {key!r} must be a tuple"
            assert len(coords) == 2, f"Value for {key!r} must have 2 elements"
            nx, ny = coords
            assert isinstance(nx, int), f"nx for {key!r} must be int"
            assert isinstance(ny, int), f"ny for {key!r} must be int"

    def test_grid_values_in_kma_range(self) -> None:
        """All grid coordinates must be within KMA grid bounds (1..149 x 1..253)."""
        for key, (nx, ny) in REGION_TO_GRID.items():
            assert 1 <= nx <= 149, f"nx={nx} for {key!r} out of range"
            assert 1 <= ny <= 253, f"ny={ny} for {key!r} out of range"


class TestLookupGrid:
    def test_seoul_korean(self) -> None:
        assert lookup_grid("서울") == (61, 126)

    def test_seoul_romanized(self) -> None:
        assert lookup_grid("Seoul") == (61, 126)

    def test_busan_korean(self) -> None:
        assert lookup_grid("부산") == (98, 76)

    def test_busan_romanized(self) -> None:
        assert lookup_grid("Busan") == (98, 76)

    def test_gangnam_gu(self) -> None:
        nx, ny = lookup_grid("강남구")
        assert isinstance(nx, int)
        assert isinstance(ny, int)

    def test_all_metro_cities_resolvable(self) -> None:
        metro_cities = [
            "서울",
            "부산",
            "대구",
            "인천",
            "광주",
            "대전",
            "울산",
            "세종",
            "경기",
            "강원",
            "충북",
            "충남",
            "전북",
            "전남",
            "경북",
            "경남",
            "제주",
        ]
        for city in metro_cities:
            coords = lookup_grid(city)
            assert len(coords) == 2

    def test_unknown_region_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown region"):
            lookup_grid("NonExistentRegion123")

    def test_unknown_region_error_message_contains_name(self) -> None:
        region = "샌프란시스코"
        with pytest.raises(ValueError, match=region):
            lookup_grid(region)

    def test_case_sensitive_mismatch(self) -> None:
        """Lookup is case-sensitive; 'seoul' != 'Seoul'."""
        with pytest.raises(ValueError):
            lookup_grid("seoul")  # lowercase 's' not in table

    def test_returns_tuple_type(self) -> None:
        result = lookup_grid("서울")
        assert isinstance(result, tuple)
        assert len(result) == 2
