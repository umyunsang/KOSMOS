# SPDX-License-Identifier: Apache-2.0
"""Unit tests for KOROAD code table enums and SIDO_GUGUN_MAP validation dict."""

from __future__ import annotations

from kosmos.tools.koroad.code_tables import (
    GANGWON_NEW_CODE_YEAR,
    JEONBUK_NEW_CODE_YEAR,
    SIDO_GUGUN_MAP,
    GugunCode,
    HazardType,
    SearchYearCd,
    SidoCode,
)

# ---------------------------------------------------------------------------
# SidoCode enum membership tests
# ---------------------------------------------------------------------------


class TestSidoCode:
    def test_all_expected_members_exist(self) -> None:
        expected = {
            "SEOUL": 11,
            "BUSAN": 26,
            "DAEGU": 27,
            "INCHEON": 28,
            "GWANGJU": 29,
            "DAEJEON": 30,
            "ULSAN": 31,
            "SEJONG": 36,
            "GYEONGGI": 41,
            "GANGWON_LEGACY": 42,
            "CHUNGBUK": 43,
            "CHUNGNAM": 44,
            "JEONBUK_LEGACY": 45,
            "JEONNAM": 46,
            "GYEONGBUK": 47,
            "GYEONGNAM": 48,
            "JEJU": 50,
            "GANGWON": 51,
            "JEONBUK": 52,
        }
        for name, value in expected.items():
            assert SidoCode[name] == value, f"SidoCode.{name} should equal {value}"

    def test_total_count(self) -> None:
        assert len(SidoCode) == 19

    def test_legacy_codes_present(self) -> None:
        assert SidoCode.GANGWON_LEGACY == 42
        assert SidoCode.JEONBUK_LEGACY == 45

    def test_new_codes_present(self) -> None:
        assert SidoCode.GANGWON == 51
        assert SidoCode.JEONBUK == 52

    def test_int_comparison(self) -> None:
        # IntEnum should compare equal to plain int
        assert SidoCode.SEOUL == 11
        assert SidoCode.BUSAN == 26


# ---------------------------------------------------------------------------
# SearchYearCd enum tests
# ---------------------------------------------------------------------------


class TestSearchYearCd:
    def test_general_2024_value(self) -> None:
        assert SearchYearCd.GENERAL_2024.value == "2025119"

    def test_general_2023_value(self) -> None:
        assert SearchYearCd.GENERAL_2023.value == "2024056"

    def test_ice_2024_value(self) -> None:
        assert SearchYearCd.ICE_2024.value == "2025113"

    def test_child_zone_2024_value(self) -> None:
        assert SearchYearCd.CHILD_ZONE_2024.value == "2025066"

    def test_year_property_general_2024(self) -> None:
        assert SearchYearCd.GENERAL_2024.year == 2024

    def test_year_property_general_2023(self) -> None:
        assert SearchYearCd.GENERAL_2023.year == 2023

    def test_year_property_ice_2024(self) -> None:
        assert SearchYearCd.ICE_2024.year == 2024

    def test_all_members_have_string_values(self) -> None:
        for member in SearchYearCd:
            assert isinstance(member.value, str), f"{member.name} value should be str"
            assert member.value.isdigit(), f"{member.name} value should be all digits"

    def test_all_members_parseable_year(self) -> None:
        for member in SearchYearCd:
            assert member.year >= 2021, f"{member.name}.year should be >= 2021"
            assert member.year <= 2030, f"{member.name}.year should be <= 2030"


# ---------------------------------------------------------------------------
# HazardType enum tests
# ---------------------------------------------------------------------------


class TestHazardType:
    def test_all_expected_members(self) -> None:
        expected_values = {
            "general",
            "ice",
            "pedestrian_child",
            "child_zone",
            "pedestrian_elderly",
            "bicycle",
            "law_violation",
            "holiday",
            "motorcycle",
            "pedestrian",
            "drunk_driving",
            "freight",
        }
        actual_values = {m.value for m in HazardType}
        assert actual_values == expected_values

    def test_member_count(self) -> None:
        assert len(HazardType) == 12

    def test_general_maps_to_general_2024(self) -> None:
        assert HazardType.GENERAL.default_year_cd() == SearchYearCd.GENERAL_2024

    def test_ice_maps_to_ice_2024(self) -> None:
        assert HazardType.ICE.default_year_cd() == SearchYearCd.ICE_2024

    def test_child_zone_maps_to_child_zone_2024(self) -> None:
        assert HazardType.CHILD_ZONE.default_year_cd() == SearchYearCd.CHILD_ZONE_2024

    def test_all_hazard_types_have_default_year_cd(self) -> None:
        for ht in HazardType:
            ycd = ht.default_year_cd()
            assert isinstance(ycd, SearchYearCd), (
                f"{ht.name}.default_year_cd() must return SearchYearCd"
            )


# ---------------------------------------------------------------------------
# GugunCode enum tests
# ---------------------------------------------------------------------------


class TestGugunCode:
    def test_seoul_gangnam(self) -> None:
        assert GugunCode.SEOUL_GANGNAM == 680

    def test_seoul_jongno(self) -> None:
        assert GugunCode.SEOUL_JONGNO == 110

    def test_seoul_seocho(self) -> None:
        assert GugunCode.SEOUL_SEOCHO == 650

    def test_busan_junggu(self) -> None:
        assert GugunCode.BUSAN_JUNGGU == 110

    def test_overlapping_integer_values_are_aliases(self) -> None:
        # Both Seoul Jongno and Busan Junggu have integer value 110.
        # In Python IntEnum, duplicate values become aliases for the first member.
        # The important contract is that the integer value 110 is accessible via both names.
        assert GugunCode.SEOUL_JONGNO == 110
        assert GugunCode.BUSAN_JUNGGU == 110
        # Both resolve to the canonical first member (SEOUL_JONGNO)
        assert GugunCode(110) == 110


# ---------------------------------------------------------------------------
# SIDO_GUGUN_MAP tests
# ---------------------------------------------------------------------------


class TestSidoGugunMap:
    def test_all_sido_codes_present(self) -> None:
        for sido in SidoCode:
            assert sido in SIDO_GUGUN_MAP, f"SIDO_GUGUN_MAP missing entry for {sido.name}"

    def test_seoul_has_25_gu(self) -> None:
        assert len(SIDO_GUGUN_MAP[SidoCode.SEOUL]) == 25

    def test_seoul_gangnam_in_map(self) -> None:
        assert 680 in SIDO_GUGUN_MAP[SidoCode.SEOUL]

    def test_seoul_jongno_in_map(self) -> None:
        assert 110 in SIDO_GUGUN_MAP[SidoCode.SEOUL]

    def test_busan_has_expected_gu(self) -> None:
        assert 110 in SIDO_GUGUN_MAP[SidoCode.BUSAN]  # Busan Junggu
        assert 710 in SIDO_GUGUN_MAP[SidoCode.BUSAN]  # Busan Gijang-gun

    def test_jeju_has_two_entities(self) -> None:
        assert len(SIDO_GUGUN_MAP[SidoCode.JEJU]) == 2

    def test_all_map_values_are_frozensets(self) -> None:
        for sido, gugun_set in SIDO_GUGUN_MAP.items():
            assert isinstance(gugun_set, frozenset), f"{sido.name} map value must be frozenset"

    def test_map_values_are_integers(self) -> None:
        for sido, gugun_set in SIDO_GUGUN_MAP.items():
            for code in gugun_set:
                assert isinstance(code, int), f"{sido.name} gugun code {code!r} must be int"


# ---------------------------------------------------------------------------
# Legacy boundary constants
# ---------------------------------------------------------------------------


def test_gangwon_new_code_year() -> None:
    assert GANGWON_NEW_CODE_YEAR == 2023


def test_jeonbuk_new_code_year() -> None:
    assert JEONBUK_NEW_CODE_YEAR == 2023
