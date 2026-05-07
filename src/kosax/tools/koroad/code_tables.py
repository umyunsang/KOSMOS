# SPDX-License-Identifier: Apache-2.0
"""KOROAD API code tables: enums and validation dictionaries.

Source: research/data/_converted/koroad_AccidentHazard_CodeList.md
  - Sheet: Sido 요청값
  - Sheet: Gugun 요청값
  - Sheet: serachYearCd 요청값
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class SidoCode(IntEnum):
    """Province/city codes for KOROAD accident data API (siDo parameter).

    Codes 42 (Gangwon-do) and 45 (Jeonbuk) are legacy codes valid only for
    pre-2023 datasets. Use 51 (강원특별자치도) and 52 (전북특별자치도) for 2023+.
    """

    SEOUL = 11  # 서울특별시
    BUSAN = 26  # 부산광역시
    DAEGU = 27  # 대구광역시
    INCHEON = 28  # 인천광역시
    GWANGJU = 29  # 광주광역시
    DAEJEON = 30  # 대전광역시
    ULSAN = 31  # 울산광역시
    SEJONG = 36  # 세종특별자치시
    GYEONGGI = 41  # 경기도
    GANGWON_LEGACY = 42  # 강원도 (pre-2023 datasets only)
    CHUNGBUK = 43  # 충청북도
    CHUNGNAM = 44  # 충청남도
    JEONBUK_LEGACY = 45  # 전라북도 (pre-2023 datasets only)
    JEONNAM = 46  # 전라남도
    GYEONGBUK = 47  # 경상북도
    GYEONGNAM = 48  # 경상남도
    JEJU = 50  # 제주특별자치도
    GANGWON = 51  # 강원특별자치도 (2023+ datasets)
    JEONBUK = 52  # 전북특별자치도 (2023+ datasets)


class SearchYearCd(StrEnum):
    """Year/category codes for KOROAD accident dataset queries (searchYearCd parameter).

    The numeric string values are the official API parameter values.
    Source: koroad_AccidentHazard_CodeList.md § serachYearCd 요청값
    """

    # 지자체별 (General municipality)
    GENERAL_2024 = "2025119"  # 24년 지자체별
    GENERAL_2023 = "2024056"  # 23년 지자체별
    GENERAL_2022 = "2023026"  # 22년 지자체별
    GENERAL_2021 = "2022046"  # 21년 지자체별

    # 결빙 (Ice)
    ICE_2024 = "2025113"  # 20-24년 결빙
    ICE_2023 = "2024055"  # 19-23년 결빙

    # 어린이보호구역내 어린이 (Child zone)
    CHILD_ZONE_2024 = "2025066"
    CHILD_ZONE_2023 = "2024041"

    # 보행어린이 (Pedestrian child)
    PEDESTRIAN_CHILD_2024 = "2025108"
    PEDESTRIAN_CHILD_2023 = "2024042"

    # 보행노인 (Pedestrian elderly)
    PEDESTRIAN_ELDERLY_2024 = "2025076"
    PEDESTRIAN_ELDERLY_2023 = "2024044"

    # 자전거 (Bicycle)
    BICYCLE_2024 = "2025081"
    BICYCLE_2023 = "2024046"

    # 법규위반별 (Law violation)
    LAW_SIGNAL_2024 = "2025111"  # 신호위반
    LAW_CENTER_2024 = "2025110"  # 중앙선침범

    # 연휴기간별 (Holiday)
    HOLIDAY_2024 = "2025112"  # 22-24년 연휴기간별

    # 이륜차 (Motorcycle)
    MOTORCYCLE_2024 = "2025091"  # 22-24년 이륜차

    # 보행자 (Pedestrian general)
    PEDESTRIAN_2024 = "2025083"  # 22-24년 보행자

    # 음주운전 (Drunk driving)
    DRUNK_DRIVING_2024 = "2025085"  # 22-24년 음주운전

    # 화물차 (Freight)
    FREIGHT_2024 = "2025089"  # 22-24년 화물차

    @property
    def year(self) -> int:
        """Extract the data year from the code name (e.g. GENERAL_2024 → 2024)."""
        # Name format: CATEGORY_YYYY
        parts = self.name.split("_")
        return int(parts[-1])


class HazardType(StrEnum):
    """Hazard category types mapping to default SearchYearCd values.

    Used in RoadRiskScoreInput to derive the appropriate dataset year code
    when search_year_cd is not explicitly provided.
    """

    GENERAL = "general"
    ICE = "ice"
    PEDESTRIAN_CHILD = "pedestrian_child"
    CHILD_ZONE = "child_zone"
    PEDESTRIAN_ELDERLY = "pedestrian_elderly"
    BICYCLE = "bicycle"
    LAW_VIOLATION = "law_violation"
    HOLIDAY = "holiday"
    MOTORCYCLE = "motorcycle"
    PEDESTRIAN = "pedestrian"
    DRUNK_DRIVING = "drunk_driving"
    FREIGHT = "freight"

    def default_year_cd(self) -> SearchYearCd:
        """Return the default SearchYearCd for this hazard type."""
        year_cd_map: dict[str, SearchYearCd] = {
            "general": SearchYearCd.GENERAL_2024,
            "ice": SearchYearCd.ICE_2024,
            "pedestrian_child": SearchYearCd.PEDESTRIAN_CHILD_2024,
            "child_zone": SearchYearCd.CHILD_ZONE_2024,
            "pedestrian_elderly": SearchYearCd.PEDESTRIAN_ELDERLY_2024,
            "bicycle": SearchYearCd.BICYCLE_2024,
            "law_violation": SearchYearCd.LAW_SIGNAL_2024,
            "holiday": SearchYearCd.HOLIDAY_2024,
            "motorcycle": SearchYearCd.MOTORCYCLE_2024,
            "pedestrian": SearchYearCd.PEDESTRIAN_2024,
            "drunk_driving": SearchYearCd.DRUNK_DRIVING_2024,
            "freight": SearchYearCd.FREIGHT_2024,
        }
        return year_cd_map[self.value]


class GugunCode(IntEnum):
    """District (gu/gun) codes for KOROAD accident data API (guGun parameter).

    Because district code integers overlap across sido (multiple sido use code 110
    for their Jung-gu), member names are qualified with the sido prefix.

    Source: koroad_AccidentHazard_CodeList.md § Gugun 요청값
    """

    # Seoul (시도코드 11)
    SEOUL_JONGNO = 110  # 서울 종로구
    SEOUL_JUNGGU = 140  # 서울 중구
    SEOUL_YONGSAN = 170  # 서울 용산구
    SEOUL_SEONGDONG = 200  # 서울 성동구
    SEOUL_GWANGJIN = 215  # 서울 광진구
    SEOUL_DONGDAEMUN = 230  # 서울 동대문구
    SEOUL_JUNGRANG = 260  # 서울 중랑구
    SEOUL_SEONGBUK = 290  # 서울 성북구
    SEOUL_GANGBUK = 305  # 서울 강북구
    SEOUL_DOBONG = 320  # 서울 도봉구
    SEOUL_NOWON = 350  # 서울 노원구
    SEOUL_EUNPYEONG = 380  # 서울 은평구
    SEOUL_SEODAEMUN = 410  # 서울 서대문구
    SEOUL_MAPO = 440  # 서울 마포구
    SEOUL_YANGCHEON = 470  # 서울 양천구
    SEOUL_GANGSEO = 500  # 서울 강서구
    SEOUL_GURO = 530  # 서울 구로구
    SEOUL_GEUMCHEON = 545  # 서울 금천구
    SEOUL_YEONGDEUNGPO = 560  # 서울 영등포구
    SEOUL_DONGJAK = 590  # 서울 동작구
    SEOUL_GWANAK = 620  # 서울 관악구
    SEOUL_SEOCHO = 650  # 서울 서초구
    SEOUL_GANGNAM = 680  # 서울 강남구
    SEOUL_SONGPA = 710  # 서울 송파구
    SEOUL_GANGDONG = 740  # 서울 강동구

    # Busan (시도코드 26)
    BUSAN_JUNGGU = 110  # 부산 중구
    BUSAN_SEO = 140  # 부산 서구
    BUSAN_DONG = 170  # 부산 동구
    BUSAN_YEONGDO = 200  # 부산 영도구
    BUSAN_BUSANJIN = 230  # 부산 부산진구
    BUSAN_DONGNAE = 260  # 부산 동래구
    BUSAN_NAM = 290  # 부산 남구
    BUSAN_BUK = 320  # 부산 북구
    BUSAN_HAEUNDAE = 350  # 부산 해운대구
    BUSAN_SAHA = 380  # 부산 사하구
    BUSAN_GEUMJEONG = 410  # 부산 금정구
    BUSAN_GANGSEO = 440  # 부산 강서구
    BUSAN_YEONJE = 470  # 부산 연제구
    BUSAN_SUYEONG = 500  # 부산 수영구
    BUSAN_SASANG = 530  # 부산 사상구
    BUSAN_GIJANG = 710  # 부산 기장군

    # Daegu (시도코드 27)
    DAEGU_JUNGGU = 110  # 대구 중구
    DAEGU_DONG = 140  # 대구 동구
    DAEGU_SEO = 170  # 대구 서구
    DAEGU_NAM = 200  # 대구 남구
    DAEGU_BUK = 230  # 대구 북구
    DAEGU_SUSEONG = 260  # 대구 수성구
    DAEGU_DALSEO = 290  # 대구 달서구
    DAEGU_DALSEONG = 710  # 대구 달성군

    # Incheon (시도코드 28)
    INCHEON_JUNGGU = 110  # 인천 중구
    INCHEON_DONG = 140  # 인천 동구
    INCHEON_MICHUHOL = 177  # 인천 미추홀구
    INCHEON_YEONSU = 185  # 인천 연수구
    INCHEON_NAM = 200  # 인천 남구 (legacy)
    INCHEON_NAMDONG = 237  # 인천 남동구
    INCHEON_BUPYEONG = 245  # 인천 부평구
    INCHEON_GYEYANG = 259  # 인천 계양구
    INCHEON_SEO = 261  # 인천 서구
    INCHEON_GANGHWA = 710  # 인천 강화군
    INCHEON_ONGJIN = 720  # 인천 옹진군

    # Gwangju (시도코드 29)
    GWANGJU_DONG = 110  # 광주 동구
    GWANGJU_SEO = 140  # 광주 서구
    GWANGJU_NAM = 155  # 광주 남구
    GWANGJU_BUK = 170  # 광주 북구
    GWANGJU_GWANGSAN = 200  # 광주 광산구

    # Daejeon (시도코드 30)
    DAEJEON_DONG = 110  # 대전 동구
    DAEJEON_JUNGGU = 140  # 대전 중구
    DAEJEON_SEO = 170  # 대전 서구
    DAEJEON_YUSEONG = 200  # 대전 유성구
    DAEJEON_DAEDEOK = 230  # 대전 대덕구

    # Ulsan (시도코드 31)
    ULSAN_JUNGGU = 110  # 울산 중구
    ULSAN_NAM = 140  # 울산 남구
    ULSAN_DONG = 170  # 울산 동구
    ULSAN_BUK = 200  # 울산 북구
    ULSAN_ULJU = 710  # 울산 울주군

    # Gyeonggi (시도코드 41)
    GYEONGGI_SUWON_JANGAHN = 111  # 경기 수원시 장안구
    GYEONGGI_SUWON_KWONSUN = 113  # 경기 수원시 권선구
    GYEONGGI_SUWON_PALDAL = 115  # 경기 수원시 팔달구
    GYEONGGI_SUWON_YEONGTONG = 117  # 경기 수원시 영통구
    GYEONGGI_SEONGNAM_SUJONG = 131  # 경기 성남시 수정구
    GYEONGGI_SEONGNAM_JUNGWON = 133  # 경기 성남시 중원구
    GYEONGGI_SEONGNAM_BUNDANG = 135  # 경기 성남시 분당구
    GYEONGGI_UIJEONGBU = 150  # 경기 의정부시
    GYEONGGI_ANYANG_MANAN = 171  # 경기 안양시 만안구
    GYEONGGI_ANYANG_DONGAN = 173  # 경기 안양시 동안구
    GYEONGGI_BUCHEON_WONMI = 191  # 경기 부천시 원미구
    GYEONGGI_BUCHEON_SOSAL = 193  # 경기 부천시 소사구
    GYEONGGI_BUCHEON_OJEONG = 195  # 경기 부천시 오정구
    GYEONGGI_GWANGMYEONG = 210  # 경기 광명시
    GYEONGGI_PYEONGTAEK = 220  # 경기 평택시
    GYEONGGI_DONGDUCHEON = 250  # 경기 동두천시
    GYEONGGI_ANSAN_SANGNOK = 271  # 경기 안산시 상록구
    GYEONGGI_ANSAN_DANWON = 273  # 경기 안산시 단원구
    GYEONGGI_GOYANG_DEOKYANG = 281  # 경기 고양시 덕양구
    GYEONGGI_GOYANG_ILSANDONG = 285  # 경기 고양시 일산동구
    GYEONGGI_GOYANG_ILSANSEO = 287  # 경기 고양시 일산서구
    GYEONGGI_GWACHEON = 290  # 경기 과천시
    GYEONGGI_GUEONGGI_GUMI = 310  # 경기 구미시
    GYEONGGI_UIWANG = 390  # 경기 의왕시
    GYEONGGI_HANAM = 550  # 경기 하남시
    GYEONGGI_YONGIN_CHEOIN = 461  # 경기 용인시 처인구
    GYEONGGI_YONGIN_GIHEUNG = 463  # 경기 용인시 기흥구
    GYEONGGI_YONGIN_SUJI = 465  # 경기 용인시 수지구
    GYEONGGI_PAJU = 480  # 경기 파주시
    GYEONGGI_ICHEON = 500  # 경기 이천시
    GYEONGGI_ANSEONG = 550  # 경기 안성시
    GYEONGGI_GIMPO = 570  # 경기 김포시
    GYEONGGI_HWASEONG = 590  # 경기 화성시
    GYEONGGI_GWANGJU = 610  # 경기 광주시
    GYEONGGI_YANGJU = 630  # 경기 양주시
    GYEONGGI_POCHEON = 680  # 경기 포천시
    GYEONGGI_YEOJU = 670  # 경기 여주시
    GYEONGGI_YANGPYEONG = 820  # 경기 양평군
    GYEONGGI_GAPYEONG = 830  # 경기 가평군
    GYEONGGI_YEONCHEON = 840  # 경기 연천군


# ---------------------------------------------------------------------------
# SIDO_GUGUN_MAP: legal district code sets per province/city
# Used by KoroadAccidentSearchInput cross-validator.
# ---------------------------------------------------------------------------

SIDO_GUGUN_MAP: dict[SidoCode, frozenset[int]] = {
    SidoCode.SEOUL: frozenset(
        {
            110,
            140,
            170,
            200,
            215,
            230,
            260,
            290,
            305,
            320,
            350,
            380,
            410,
            440,
            470,
            500,
            530,
            545,
            560,
            590,
            620,
            650,
            680,
            710,
            740,
        }
    ),
    SidoCode.BUSAN: frozenset(
        {
            110,
            140,
            170,
            200,
            230,
            260,
            290,
            320,
            350,
            380,
            410,
            440,
            470,
            500,
            530,
            710,
        }
    ),
    SidoCode.DAEGU: frozenset(
        {
            110,
            140,
            170,
            200,
            230,
            260,
            290,
            710,
        }
    ),
    SidoCode.INCHEON: frozenset(
        {
            110,
            140,
            177,
            185,
            200,
            237,
            245,
            259,
            261,
            710,
            720,
        }
    ),
    SidoCode.GWANGJU: frozenset({110, 140, 155, 170, 200}),
    SidoCode.DAEJEON: frozenset({110, 140, 170, 200, 230}),
    SidoCode.ULSAN: frozenset({110, 140, 170, 200, 710}),
    SidoCode.SEJONG: frozenset({0}),  # Sejong has no gugun (single municipality)
    SidoCode.GYEONGGI: frozenset(
        {
            111,
            113,
            115,
            117,
            131,
            133,
            135,
            150,
            171,
            173,
            191,
            193,
            195,
            210,
            220,
            250,
            271,
            273,
            281,
            285,
            287,
            290,
            390,
            461,
            463,
            465,
            480,
            500,
            550,
            570,
            590,
            610,
            630,
            670,
            680,
            820,
            830,
            840,
        }
    ),
    SidoCode.GANGWON_LEGACY: frozenset(
        {
            110,
            120,
            130,
            150,
            160,
            170,
            180,
            190,
            210,
            720,
            730,
            750,
            760,
            770,
            780,
            790,
            800,
            810,
            820,
        }
    ),
    SidoCode.CHUNGBUK: frozenset(
        {
            110,
            130,
            140,
            150,
            720,
            730,
            740,
            745,
            750,
            760,
            770,
            780,
        }
    ),
    SidoCode.CHUNGNAM: frozenset(
        {
            110,
            130,
            140,
            150,
            160,
            720,
            725,
            730,
            740,
            745,
            750,
            760,
            770,
            800,
        }
    ),
    SidoCode.JEONBUK_LEGACY: frozenset(
        {
            110,
            130,
            140,
            150,
            720,
            730,
            740,
            750,
            760,
            770,
            780,
            790,
            800,
        }
    ),
    SidoCode.JEONNAM: frozenset(
        {
            110,
            720,
            730,
            740,
            750,
            760,
            770,
            780,
            790,
            800,
            810,
            820,
            830,
            840,
        }
    ),
    SidoCode.GYEONGBUK: frozenset(
        {
            110,
            115,
            130,
            140,
            150,
            720,
            725,
            730,
            740,
            745,
            750,
            755,
            760,
            770,
            780,
            790,
            800,
            810,
            820,
            830,
            840,
        }
    ),
    SidoCode.GYEONGNAM: frozenset(
        {
            110,
            125,
            127,
            129,
            131,
            133,
            720,
            725,
            730,
            740,
            745,
            750,
            760,
            770,
            780,
            790,
            800,
            810,
            820,
            830,
        }
    ),
    SidoCode.JEJU: frozenset({110, 130}),
    SidoCode.GANGWON: frozenset(
        {
            110,
            120,
            130,
            140,
            150,
            155,
            160,
            170,
            180,
            720,
            730,
            750,
            760,
            770,
            780,
            790,
            800,
            810,
            820,
        }
    ),
    SidoCode.JEONBUK: frozenset(
        {
            110,
            113,
            130,
            140,
            150,
            720,
            730,
            740,
            750,
            760,
            770,
            780,
            790,
            800,
        }
    ),
}


# ---------------------------------------------------------------------------
# Legacy code year boundary constants
# ---------------------------------------------------------------------------

#: The first year for which Gangwon should use code 51 (강원특별자치도) instead of 42.
GANGWON_NEW_CODE_YEAR = 2023

#: The first year for which Jeonbuk should use code 52 (전북특별자치도) instead of 45.
JEONBUK_NEW_CODE_YEAR = 2023
