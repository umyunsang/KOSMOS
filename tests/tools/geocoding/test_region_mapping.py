# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.tools.geocoding.region_mapping."""

from __future__ import annotations

from kosmos.tools.geocoding.region_mapping import region1_to_sido, region2_to_gugun
from kosmos.tools.koroad.code_tables import GugunCode, SidoCode


class TestRegion1ToSido:
    """region1_to_sido() covers all 17 sido including post-2023 autonomy names."""

    # --- Basic metro cities ---
    def test_seoul_short(self):
        assert region1_to_sido("서울") == SidoCode.SEOUL

    def test_seoul_official(self):
        assert region1_to_sido("서울특별시") == SidoCode.SEOUL

    def test_busan_short(self):
        assert region1_to_sido("부산") == SidoCode.BUSAN

    def test_busan_official(self):
        assert region1_to_sido("부산광역시") == SidoCode.BUSAN

    def test_daegu(self):
        assert region1_to_sido("대구광역시") == SidoCode.DAEGU

    def test_incheon(self):
        assert region1_to_sido("인천광역시") == SidoCode.INCHEON

    def test_gwangju(self):
        assert region1_to_sido("광주광역시") == SidoCode.GWANGJU

    def test_daejeon(self):
        assert region1_to_sido("대전광역시") == SidoCode.DAEJEON

    def test_ulsan(self):
        assert region1_to_sido("울산광역시") == SidoCode.ULSAN

    def test_sejong_short(self):
        assert region1_to_sido("세종") == SidoCode.SEJONG

    def test_sejong_official(self):
        assert region1_to_sido("세종특별자치시") == SidoCode.SEJONG

    def test_gyeonggi_short(self):
        assert region1_to_sido("경기") == SidoCode.GYEONGGI

    def test_gyeonggi_official(self):
        assert region1_to_sido("경기도") == SidoCode.GYEONGGI

    # --- Post-2023 special autonomy names ---
    def test_gangwon_legacy_name(self):
        """Old name 강원도 maps to new GANGWON code (51) for 2023+ compatibility."""
        assert region1_to_sido("강원도") == SidoCode.GANGWON

    def test_gangwon_new_name(self):
        assert region1_to_sido("강원특별자치도") == SidoCode.GANGWON

    def test_gangwon_short(self):
        assert region1_to_sido("강원") == SidoCode.GANGWON

    def test_jeonbuk_legacy_name(self):
        """Old name 전라북도 maps to new JEONBUK code (52) for 2023+ compatibility."""
        assert region1_to_sido("전라북도") == SidoCode.JEONBUK

    def test_jeonbuk_new_name(self):
        assert region1_to_sido("전북특별자치도") == SidoCode.JEONBUK

    def test_jeonbuk_short(self):
        assert region1_to_sido("전북") == SidoCode.JEONBUK

    # --- Other provinces ---
    def test_chungbuk(self):
        assert region1_to_sido("충청북도") == SidoCode.CHUNGBUK

    def test_chungnam(self):
        assert region1_to_sido("충청남도") == SidoCode.CHUNGNAM

    def test_jeonnam(self):
        assert region1_to_sido("전라남도") == SidoCode.JEONNAM

    def test_gyeongbuk(self):
        assert region1_to_sido("경상북도") == SidoCode.GYEONGBUK

    def test_gyeongnam(self):
        assert region1_to_sido("경상남도") == SidoCode.GYEONGNAM

    def test_jeju_short(self):
        assert region1_to_sido("제주") == SidoCode.JEJU

    def test_jeju_official(self):
        assert region1_to_sido("제주특별자치도") == SidoCode.JEJU

    # --- Whitespace handling ---
    def test_strips_whitespace(self):
        assert region1_to_sido("  서울특별시  ") == SidoCode.SEOUL

    # --- Unknown name ---
    def test_unknown_returns_none(self):
        assert region1_to_sido("알수없는도시") is None

    def test_empty_string_returns_none(self):
        assert region1_to_sido("") is None

    # --- Enum codes ---
    def test_gangwon_code_is_51(self):
        sido = region1_to_sido("강원특별자치도")
        assert sido is not None
        assert int(sido) == 51

    def test_jeonbuk_code_is_52(self):
        sido = region1_to_sido("전북특별자치도")
        assert sido is not None
        assert int(sido) == 52


class TestRegion2ToGugun:
    """region2_to_gugun() is province-aware and disambiguates duplicate names."""

    # --- Basic unambiguous names within each sido ---
    def test_seoul_gangnam(self):
        assert region2_to_gugun("강남구", SidoCode.SEOUL) == GugunCode.SEOUL_GANGNAM

    def test_seoul_seocho(self):
        assert region2_to_gugun("서초구", SidoCode.SEOUL) == GugunCode.SEOUL_SEOCHO

    def test_seoul_jongno(self):
        assert region2_to_gugun("종로구", SidoCode.SEOUL) == GugunCode.SEOUL_JONGNO

    def test_busan_haeundae(self):
        assert region2_to_gugun("해운대구", SidoCode.BUSAN) == GugunCode.BUSAN_HAEUNDAE

    def test_strips_whitespace(self):
        assert region2_to_gugun("  강남구  ", SidoCode.SEOUL) == GugunCode.SEOUL_GANGNAM

    def test_unknown_returns_none(self):
        assert region2_to_gugun("알수없는구", SidoCode.SEOUL) is None

    def test_empty_returns_none(self):
        assert region2_to_gugun("", SidoCode.SEOUL) is None

    # --- Fail-closed on missing sido ---
    def test_none_sido_returns_none(self):
        """Without a resolved sido, ambiguous names must fail closed."""
        assert region2_to_gugun("중구", None) is None

    def test_none_sido_returns_none_even_for_unique_name(self):
        """Even unambiguous names return None without a sido (API contract)."""
        assert region2_to_gugun("강남구", None) is None

    # --- Ambiguous "중구" across six metropolitan cities ---
    def test_junggu_seoul(self):
        assert region2_to_gugun("중구", SidoCode.SEOUL) == GugunCode.SEOUL_JUNGGU

    def test_junggu_busan(self):
        assert region2_to_gugun("중구", SidoCode.BUSAN) == GugunCode.BUSAN_JUNGGU

    def test_junggu_daegu(self):
        """Regression: 대구 중구 must not return SEOUL_JUNGGU or BUSAN_JUNGGU."""
        assert region2_to_gugun("중구", SidoCode.DAEGU) == GugunCode.DAEGU_JUNGGU

    def test_junggu_incheon(self):
        assert region2_to_gugun("중구", SidoCode.INCHEON) == GugunCode.INCHEON_JUNGGU

    def test_junggu_daejeon(self):
        assert region2_to_gugun("중구", SidoCode.DAEJEON) == GugunCode.DAEJEON_JUNGGU

    def test_junggu_ulsan(self):
        assert region2_to_gugun("중구", SidoCode.ULSAN) == GugunCode.ULSAN_JUNGGU

    # --- Ambiguous "남구" regressions ---
    def test_namgu_busan(self):
        """Regression: 부산 남구 → BUSAN_NAM (code 290), not Seoul/Incheon."""
        assert region2_to_gugun("남구", SidoCode.BUSAN) == GugunCode.BUSAN_NAM

    def test_namgu_ulsan(self):
        """Regression: 울산 남구 → ULSAN_NAM (code 140)."""
        result = region2_to_gugun("남구", SidoCode.ULSAN)
        assert result == GugunCode.ULSAN_NAM
        assert int(result) == 140

    def test_namgu_daegu(self):
        assert region2_to_gugun("남구", SidoCode.DAEGU) == GugunCode.DAEGU_NAM

    def test_namgu_gwangju(self):
        assert region2_to_gugun("남구", SidoCode.GWANGJU) == GugunCode.GWANGJU_NAM

    # --- Ambiguous "북구" regressions ---
    def test_bukgu_gwangju(self):
        """Regression: 광주 북구 → GWANGJU_BUK (code 170), not Busan/Daegu/Ulsan."""
        result = region2_to_gugun("북구", SidoCode.GWANGJU)
        assert result == GugunCode.GWANGJU_BUK
        assert int(result) == 170

    def test_bukgu_busan(self):
        assert region2_to_gugun("북구", SidoCode.BUSAN) == GugunCode.BUSAN_BUK

    def test_bukgu_daegu(self):
        assert region2_to_gugun("북구", SidoCode.DAEGU) == GugunCode.DAEGU_BUK

    def test_bukgu_ulsan(self):
        assert region2_to_gugun("북구", SidoCode.ULSAN) == GugunCode.ULSAN_BUK

    # --- Ambiguous "동구" regressions ---
    def test_donggu_incheon(self):
        """Regression: 인천 동구 → INCHEON_DONG (code 140)."""
        result = region2_to_gugun("동구", SidoCode.INCHEON)
        assert result == GugunCode.INCHEON_DONG
        assert int(result) == 140

    def test_donggu_busan(self):
        assert region2_to_gugun("동구", SidoCode.BUSAN) == GugunCode.BUSAN_DONG

    def test_donggu_daegu(self):
        assert region2_to_gugun("동구", SidoCode.DAEGU) == GugunCode.DAEGU_DONG

    def test_donggu_gwangju(self):
        assert region2_to_gugun("동구", SidoCode.GWANGJU) == GugunCode.GWANGJU_DONG

    def test_donggu_daejeon(self):
        assert region2_to_gugun("동구", SidoCode.DAEJEON) == GugunCode.DAEJEON_DONG

    def test_donggu_ulsan(self):
        assert region2_to_gugun("동구", SidoCode.ULSAN) == GugunCode.ULSAN_DONG

    # --- Ambiguous "서구" regressions ---
    def test_seogu_busan(self):
        assert region2_to_gugun("서구", SidoCode.BUSAN) == GugunCode.BUSAN_SEO

    def test_seogu_daegu(self):
        assert region2_to_gugun("서구", SidoCode.DAEGU) == GugunCode.DAEGU_SEO

    def test_seogu_incheon(self):
        assert region2_to_gugun("서구", SidoCode.INCHEON) == GugunCode.INCHEON_SEO

    def test_seogu_gwangju(self):
        assert region2_to_gugun("서구", SidoCode.GWANGJU) == GugunCode.GWANGJU_SEO

    def test_seogu_daejeon(self):
        assert region2_to_gugun("서구", SidoCode.DAEJEON) == GugunCode.DAEJEON_SEO

    # --- Regression: specific integer codes from the review brief ---
    # NOTE: GugunCode is an IntEnum whose integer codes repeat across sido
    # (e.g. multiple sido use 110/140/170 for different districts), so the
    # authoritative check is the integer value, not the enum member identity.
    def test_daegu_junggu_code_110(self):
        """대구 중구 → integer code 110 (not Seoul 중구's 140)."""
        result = region2_to_gugun("중구", SidoCode.DAEGU)
        assert result is not None
        assert int(result) == 110
        assert int(result) != int(GugunCode.SEOUL_JUNGGU)

    def test_busan_namgu_code_290(self):
        """부산 남구 → integer code 290."""
        result = region2_to_gugun("남구", SidoCode.BUSAN)
        assert result is not None
        assert int(result) == 290

    def test_ulsan_namgu_code_140(self):
        """울산 남구 → integer code 140 (distinct from Busan 남구 at 290)."""
        result = region2_to_gugun("남구", SidoCode.ULSAN)
        assert result is not None
        assert int(result) == 140
        assert int(result) != int(GugunCode.BUSAN_NAM)

    def test_gwangju_bukgu_code_170(self):
        """광주 북구 → integer code 170 (distinct from Busan 북구 at 320)."""
        result = region2_to_gugun("북구", SidoCode.GWANGJU)
        assert result is not None
        assert int(result) == 170
        assert int(result) != int(GugunCode.BUSAN_BUK)

    def test_incheon_donggu_code_140(self):
        """인천 동구 → integer code 140 (distinct from Daegu 동구 alias)."""
        result = region2_to_gugun("동구", SidoCode.INCHEON)
        assert result is not None
        assert int(result) == 140

    # --- Province without a mapped district table ---
    def test_sido_without_table_returns_none(self):
        """Provinces without a detailed table (e.g. GYEONGGI, JEJU) return None.

        This is intentional fail-closed behaviour: the Kakao region_2depth_name
        for those provinces is typically the 시 name, which does not map
        one-to-one to a KOROAD gugun code.
        """
        assert region2_to_gugun("수원시", SidoCode.GYEONGGI) is None

    # --- Gwangju 동구 (110) vs Daegu 동구 (140) produce different integer codes ---
    def test_donggu_codes_differ_by_province(self):
        daegu_dong = region2_to_gugun("동구", SidoCode.DAEGU)
        gwangju_dong = region2_to_gugun("동구", SidoCode.GWANGJU)
        assert daegu_dong is not None and gwangju_dong is not None
        assert int(daegu_dong) == 140
        assert int(gwangju_dong) == 110
        assert int(daegu_dong) != int(gwangju_dong)
