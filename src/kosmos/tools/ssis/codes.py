# SPDX-License-Identifier: Apache-2.0
"""SSIS (한국사회보장정보원) code-table enums.

Shared across the MOHW adapter and all future SSIS adapters (spec 029 §9.2).
Source: 지자체복지서비스_코드표(v1.0).doc + 활용가이드_중앙부처복지서비스(v2.2).doc
"""

from __future__ import annotations

from enum import StrEnum


class SrchKeyCode(StrEnum):
    """Service-list keyword search field code (SSIS 검색분류)."""

    name = "001"  # 서비스명
    summary = "002"  # 서비스내용
    all_fields = "003"  # 서비스명 + 서비스내용


class CallType(StrEnum):
    """SSIS callTp — 호출페이지 타입."""

    list_ = "L"  # 목록 (list)
    detail = "D"  # 상세 (detail) — reserved for NationalWelfaredetailedV001


class OrderBy(StrEnum):
    """SSIS orderBy — 정렬순서."""

    date = "date"  # 등록순
    popular = "popular"  # 인기순 (조회 수 기준)


class LifeArrayCode(StrEnum):
    """Life-stage code (생애주기). Source: 지자체복지서비스_코드표(v1.0).doc."""

    infant = "001"  # 영유아
    child = "002"  # 아동
    teen = "003"  # 청소년
    young_adult = "004"  # 청년
    middle_aged = "005"  # 중장년
    elderly = "006"  # 노년
    pregnancy_birth = "007"  # 임신·출산


class TrgterIndvdlCode(StrEnum):
    """Target-individual / household-type code (가구상황)."""

    multicultural = "010"  # 다문화·탈북민
    multichild = "020"  # 다자녀
    veteran = "030"  # 보훈대상자
    disabled = "040"  # 장애인
    low_income = "050"  # 저소득
    single_parent = "060"  # 한부모·조손


class IntrsThemaCode(StrEnum):
    """Interest-theme code (관심주제)."""

    physical_health = "010"  # 신체건강
    mental_health = "020"  # 정신건강
    livelihood = "030"  # 생활지원
    housing = "040"  # 주거
    employment = "050"  # 일자리
    culture_leisure = "060"  # 문화·여가
    safety_crisis = "070"  # 안전·위기
    pregnancy_birth = "080"  # 임신·출산
    childcare = "090"  # 보육
    education = "100"  # 교육
    adoption_foster = "110"  # 입양·위탁
    care_support = "120"  # 보호·돌봄
    small_finance = "130"  # 서민금융
    legal = "140"  # 법률


__all__ = [
    "CallType",
    "IntrsThemaCode",
    "LifeArrayCode",
    "OrderBy",
    "SrchKeyCode",
    "TrgterIndvdlCode",
]
