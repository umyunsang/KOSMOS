# SPDX-License-Identifier: Apache-2.0
"""Korean administrative region name → KOROAD SidoCode / GugunCode mapping.

Converts the ``region_1depth_name`` and ``region_2depth_name`` strings
returned by the Kakao Local API into the integer codes expected by the
KOROAD accident search API.

Coverage:
  - All 17 sido (시도) values defined in :class:`~kosmos.tools.koroad.code_tables.SidoCode`,
    including post-2023 special autonomy designations:
    강원특별자치도 (code 51) and 전북특별자치도 (code 52).
  - Shortened forms: "서울" → SEOUL, "경기" → GYEONGGI, etc.
  - Official long forms: "서울특별시" → SEOUL, "경기도" → GYEONGGI.

District lookup is **province-aware**: ambiguous names such as "중구", "남구",
"북구", "동구", and "서구" appear in multiple metropolitan cities, so
``region2_to_gugun`` requires the resolved :class:`SidoCode` to disambiguate.
Callers that only have a district name but not a province must treat the
lookup as unresolved (fail-closed) rather than guessing.
"""

from __future__ import annotations

import logging

from kosmos.tools.koroad.code_tables import GugunCode, SidoCode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Region-1 depth (시도) lookup table
# ---------------------------------------------------------------------------

# Maps all known Korean province/city name forms to SidoCode.
# Handles: short forms, official long forms, post-2023 autonomy names.
_REGION1_TO_SIDO: dict[str, SidoCode] = {
    # --- Seoul ---
    "서울": SidoCode.SEOUL,
    "서울시": SidoCode.SEOUL,
    "서울특별시": SidoCode.SEOUL,
    # --- Busan ---
    "부산": SidoCode.BUSAN,
    "부산시": SidoCode.BUSAN,
    "부산광역시": SidoCode.BUSAN,
    # --- Daegu ---
    "대구": SidoCode.DAEGU,
    "대구시": SidoCode.DAEGU,
    "대구광역시": SidoCode.DAEGU,
    # --- Incheon ---
    "인천": SidoCode.INCHEON,
    "인천시": SidoCode.INCHEON,
    "인천광역시": SidoCode.INCHEON,
    # --- Gwangju ---
    "광주": SidoCode.GWANGJU,
    "광주시": SidoCode.GWANGJU,
    "광주광역시": SidoCode.GWANGJU,
    # --- Daejeon ---
    "대전": SidoCode.DAEJEON,
    "대전시": SidoCode.DAEJEON,
    "대전광역시": SidoCode.DAEJEON,
    # --- Ulsan ---
    "울산": SidoCode.ULSAN,
    "울산시": SidoCode.ULSAN,
    "울산광역시": SidoCode.ULSAN,
    # --- Sejong ---
    "세종": SidoCode.SEJONG,
    "세종시": SidoCode.SEJONG,
    "세종특별자치시": SidoCode.SEJONG,
    # --- Gyeonggi ---
    "경기": SidoCode.GYEONGGI,
    "경기도": SidoCode.GYEONGGI,
    # --- Gangwon (post-2023: 강원특별자치도, code 51) ---
    "강원": SidoCode.GANGWON,
    "강원도": SidoCode.GANGWON,
    "강원특별자치도": SidoCode.GANGWON,
    # Legacy composite name intentionally maps to new code for 2023+ datasets
    "강원도(강원특별자치도)": SidoCode.GANGWON,
    # --- Chungbuk ---
    "충북": SidoCode.CHUNGBUK,
    "충청북도": SidoCode.CHUNGBUK,
    # --- Chungnam ---
    "충남": SidoCode.CHUNGNAM,
    "충청남도": SidoCode.CHUNGNAM,
    # --- Jeonbuk (post-2023: 전북특별자치도, code 52) ---
    "전북": SidoCode.JEONBUK,
    "전북도": SidoCode.JEONBUK,
    "전라북도": SidoCode.JEONBUK,
    "전북특별자치도": SidoCode.JEONBUK,
    # Legacy composite name intentionally maps to new code for 2023+ datasets
    "전라북도(전북특별자치도)": SidoCode.JEONBUK,
    # --- Jeonnam ---
    "전남": SidoCode.JEONNAM,
    "전라남도": SidoCode.JEONNAM,
    # --- Gyeongbuk ---
    "경북": SidoCode.GYEONGBUK,
    "경상북도": SidoCode.GYEONGBUK,
    # --- Gyeongnam ---
    "경남": SidoCode.GYEONGNAM,
    "경상남도": SidoCode.GYEONGNAM,
    # --- Jeju ---
    "제주": SidoCode.JEJU,
    "제주도": SidoCode.JEJU,
    "제주특별자치도": SidoCode.JEJU,
}

# ---------------------------------------------------------------------------
# Region-2 depth (구군) lookup table — province-aware
# ---------------------------------------------------------------------------
#
# Structured as a nested mapping ``{SidoCode: {district_name: GugunCode}}`` so
# that ambiguous names (중구/남구/북구/동구/서구 all recur across metro cities)
# resolve to the correct code for the caller's resolved province.
#
# Only the seven metropolitan cities plus the Special City (Seoul) are
# modelled here.  For 도-level provinces the Kakao API typically returns a
# 시 name (e.g. "수원시") at ``region_2depth_name``, which does not map 1-to-1
# to a KOROAD gugun code — those cases intentionally fall through and return
# ``None`` so the caller can fail closed rather than guess.

_REGION2_TO_GUGUN_BY_SIDO: dict[SidoCode, dict[str, GugunCode]] = {
    # --- Seoul (시도코드 11) ---
    SidoCode.SEOUL: {
        "종로구": GugunCode.SEOUL_JONGNO,
        "중구": GugunCode.SEOUL_JUNGGU,
        "용산구": GugunCode.SEOUL_YONGSAN,
        "성동구": GugunCode.SEOUL_SEONGDONG,
        "광진구": GugunCode.SEOUL_GWANGJIN,
        "동대문구": GugunCode.SEOUL_DONGDAEMUN,
        "중랑구": GugunCode.SEOUL_JUNGRANG,
        "성북구": GugunCode.SEOUL_SEONGBUK,
        "강북구": GugunCode.SEOUL_GANGBUK,
        "도봉구": GugunCode.SEOUL_DOBONG,
        "노원구": GugunCode.SEOUL_NOWON,
        "은평구": GugunCode.SEOUL_EUNPYEONG,
        "서대문구": GugunCode.SEOUL_SEODAEMUN,
        "마포구": GugunCode.SEOUL_MAPO,
        "양천구": GugunCode.SEOUL_YANGCHEON,
        "강서구": GugunCode.SEOUL_GANGSEO,
        "구로구": GugunCode.SEOUL_GURO,
        "금천구": GugunCode.SEOUL_GEUMCHEON,
        "영등포구": GugunCode.SEOUL_YEONGDEUNGPO,
        "동작구": GugunCode.SEOUL_DONGJAK,
        "관악구": GugunCode.SEOUL_GWANAK,
        "서초구": GugunCode.SEOUL_SEOCHO,
        "강남구": GugunCode.SEOUL_GANGNAM,
        "송파구": GugunCode.SEOUL_SONGPA,
        "강동구": GugunCode.SEOUL_GANGDONG,
    },
    # --- Busan (시도코드 26) ---
    SidoCode.BUSAN: {
        "중구": GugunCode.BUSAN_JUNGGU,
        "서구": GugunCode.BUSAN_SEO,
        "동구": GugunCode.BUSAN_DONG,
        "영도구": GugunCode.BUSAN_YEONGDO,
        "부산진구": GugunCode.BUSAN_BUSANJIN,
        "동래구": GugunCode.BUSAN_DONGNAE,
        "남구": GugunCode.BUSAN_NAM,
        "북구": GugunCode.BUSAN_BUK,
        "해운대구": GugunCode.BUSAN_HAEUNDAE,
        "사하구": GugunCode.BUSAN_SAHA,
        "금정구": GugunCode.BUSAN_GEUMJEONG,
        "강서구": GugunCode.BUSAN_GANGSEO,
        "연제구": GugunCode.BUSAN_YEONJE,
        "수영구": GugunCode.BUSAN_SUYEONG,
        "사상구": GugunCode.BUSAN_SASANG,
        "기장군": GugunCode.BUSAN_GIJANG,
    },
    # --- Daegu (시도코드 27) ---
    SidoCode.DAEGU: {
        "중구": GugunCode.DAEGU_JUNGGU,
        "동구": GugunCode.DAEGU_DONG,
        "서구": GugunCode.DAEGU_SEO,
        "남구": GugunCode.DAEGU_NAM,
        "북구": GugunCode.DAEGU_BUK,
        "수성구": GugunCode.DAEGU_SUSEONG,
        "달서구": GugunCode.DAEGU_DALSEO,
        "달성군": GugunCode.DAEGU_DALSEONG,
    },
    # --- Incheon (시도코드 28) ---
    SidoCode.INCHEON: {
        "중구": GugunCode.INCHEON_JUNGGU,
        "동구": GugunCode.INCHEON_DONG,
        "미추홀구": GugunCode.INCHEON_MICHUHOL,
        "연수구": GugunCode.INCHEON_YEONSU,
        # "남구" is a legacy name (now 미추홀구); retained for completeness but
        # modern Kakao results will emit "미추홀구".
        "남구": GugunCode.INCHEON_NAM,
        "남동구": GugunCode.INCHEON_NAMDONG,
        "부평구": GugunCode.INCHEON_BUPYEONG,
        "계양구": GugunCode.INCHEON_GYEYANG,
        "서구": GugunCode.INCHEON_SEO,
        "강화군": GugunCode.INCHEON_GANGHWA,
        "옹진군": GugunCode.INCHEON_ONGJIN,
    },
    # --- Gwangju (시도코드 29) ---
    SidoCode.GWANGJU: {
        "동구": GugunCode.GWANGJU_DONG,
        "서구": GugunCode.GWANGJU_SEO,
        "남구": GugunCode.GWANGJU_NAM,
        "북구": GugunCode.GWANGJU_BUK,
        "광산구": GugunCode.GWANGJU_GWANGSAN,
    },
    # --- Daejeon (시도코드 30) ---
    SidoCode.DAEJEON: {
        "동구": GugunCode.DAEJEON_DONG,
        "중구": GugunCode.DAEJEON_JUNGGU,
        "서구": GugunCode.DAEJEON_SEO,
        "유성구": GugunCode.DAEJEON_YUSEONG,
        "대덕구": GugunCode.DAEJEON_DAEDEOK,
    },
    # --- Ulsan (시도코드 31) ---
    SidoCode.ULSAN: {
        "중구": GugunCode.ULSAN_JUNGGU,
        "남구": GugunCode.ULSAN_NAM,
        "동구": GugunCode.ULSAN_DONG,
        "북구": GugunCode.ULSAN_BUK,
        "울주군": GugunCode.ULSAN_ULJU,
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def region1_to_sido(region1: str) -> SidoCode | None:
    """Map a Kakao ``region_1depth_name`` string to a :class:`SidoCode`.

    Handles shortened forms ("서울"), official long forms ("서울특별시"),
    and post-2023 special autonomy names ("강원특별자치도", "전북특별자치도").

    Args:
        region1: Province/city name as returned by the Kakao Local API.
            Leading/trailing whitespace is stripped before lookup.

    Returns:
        The matching :class:`SidoCode`, or ``None`` if no match is found.
    """
    normalized = region1.strip()
    result = _REGION1_TO_SIDO.get(normalized)
    if result is None:
        logger.debug("region1_to_sido: no match for %r", normalized)
    return result


def region2_to_gugun(region2: str, sido: SidoCode | None) -> GugunCode | None:
    """Map a Kakao ``region_2depth_name`` string to a :class:`GugunCode`.

    The lookup is **province-aware**: the same district name (e.g. "중구",
    "남구") is used by multiple metropolitan cities but resolves to
    different KOROAD codes.  The caller must supply the already-resolved
    :class:`SidoCode` so the correct code is returned.

    Args:
        region2: District name as returned by the Kakao Local API.
            Leading/trailing whitespace is stripped before lookup.
        sido: Resolved :class:`SidoCode` for the address's province.  When
            ``None`` the lookup is considered unresolved and ``None`` is
            returned (fail-closed) rather than guessing a code.

    Returns:
        The matching :class:`GugunCode`, or ``None`` if ``sido`` is ``None``,
        the province is not modelled here, or the district name is not
        recognised for that province.  Callers must handle the ``None`` case
        explicitly (e.g. raise an error) rather than guessing a default code.
    """
    normalized = region2.strip()

    if sido is None:
        logger.debug(
            "region2_to_gugun: cannot resolve %r without a sido — returning None",
            normalized,
        )
        return None

    province_table = _REGION2_TO_GUGUN_BY_SIDO.get(sido)
    if province_table is None:
        logger.debug(
            "region2_to_gugun: sido %s has no district table — returning None",
            sido.name,
        )
        return None

    result = province_table.get(normalized)
    if result is None:
        logger.debug(
            "region2_to_gugun: no match for %r in sido %s — returning None",
            normalized,
            sido.name,
        )
    return result
