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
# Region-2 depth (구군) lookup table
# ---------------------------------------------------------------------------

# Maps district name strings to GugunCode members.
# Key: Kakao API region_2depth_name value (usually the official Korean name).
# Value: GugunCode member.  Returns None for unrecognized districts;
#        callers should use GugunCode.SEOUL_JONGNO (0) or similar safe fallback.
_REGION2_TO_GUGUN: dict[str, GugunCode] = {
    # --- Seoul (시도코드 11) ---
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
    # --- Busan (시도코드 26) ---
    "해운대구": GugunCode.BUSAN_HAEUNDAE,
    "부산진구": GugunCode.BUSAN_BUSANJIN,
    "동래구": GugunCode.BUSAN_DONGNAE,
    "남구": GugunCode.BUSAN_NAM,
    "북구": GugunCode.BUSAN_BUK,
    "사상구": GugunCode.BUSAN_SASANG,
    "사하구": GugunCode.BUSAN_SAHA,
    "연제구": GugunCode.BUSAN_YEONJE,
    "영도구": GugunCode.BUSAN_YEONGDO,
    "수영구": GugunCode.BUSAN_SUYEONG,
    "금정구": GugunCode.BUSAN_GEUMJEONG,
    "기장군": GugunCode.BUSAN_GIJANG,
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
        logger.warning("region1_to_sido: no match for %r", normalized)
    return result


def region2_to_gugun(region2: str) -> GugunCode | None:
    """Map a Kakao ``region_2depth_name`` string to a :class:`GugunCode`.

    Args:
        region2: District name as returned by the Kakao Local API.
            Leading/trailing whitespace is stripped before lookup.

    Returns:
        The matching :class:`GugunCode`, or ``None`` if no match is found.
        Returns ``None`` for districts not yet in the lookup table —
        callers should use a sido-appropriate default (e.g. the first
        district code for that sido) as a fallback.
    """
    normalized = region2.strip()
    result = _REGION2_TO_GUGUN.get(normalized)
    if result is None:
        logger.debug("region2_to_gugun: no exact match for %r, returning None", normalized)
    return result
