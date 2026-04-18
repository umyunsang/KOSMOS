# SPDX-License-Identifier: Apache-2.0
"""T036 — Per-family published_tier narrowing tests.

For each of the 6 AuthContext family variants, verify that:
1. All allowed published_tier values (data-model.md § 2.1) are accepted.
2. A published_tier from a different family is rejected with ValidationError.
3. An arbitrary out-of-spec string is rejected.

This proves the @model_validator(mode="after") enforcement from T040.
No network calls; all pure-Python.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from kosmos.primitives.verify import (
    DigitalOnepassContext,
    GanpyeonInjeungContext,
    GeumyungInjeungseoContext,
    GongdongInjeungseoContext,
    MobileIdContext,
    MyDataContext,
)

_NOW = datetime(2026, 4, 19, 9, 0, 0, tzinfo=UTC)


def _gongdong(published_tier: str) -> GongdongInjeungseoContext:
    return GongdongInjeungseoContext(
        published_tier=published_tier,  # type: ignore[arg-type]
        nist_aal_hint="AAL3",
        verified_at=_NOW,
        certificate_issuer="KICA",
    )


def _geumyung(published_tier: str) -> GeumyungInjeungseoContext:
    return GeumyungInjeungseoContext(
        published_tier=published_tier,  # type: ignore[arg-type]
        nist_aal_hint="AAL2",
        verified_at=_NOW,
        bank_cluster="kftc",
    )


def _ganpyeon(published_tier: str) -> GanpyeonInjeungContext:
    return GanpyeonInjeungContext(
        published_tier=published_tier,  # type: ignore[arg-type]
        nist_aal_hint="AAL2",
        verified_at=_NOW,
        provider="kakao",
    )


def _onepass(published_tier: str) -> DigitalOnepassContext:
    return DigitalOnepassContext(
        published_tier=published_tier,  # type: ignore[arg-type]
        nist_aal_hint="AAL2",
        verified_at=_NOW,
        level=2,
    )


def _mobile_id(published_tier: str) -> MobileIdContext:
    return MobileIdContext(
        published_tier=published_tier,  # type: ignore[arg-type]
        nist_aal_hint="AAL2",
        verified_at=_NOW,
        id_type="mdl",
    )


def _mydata(published_tier: str) -> MyDataContext:
    return MyDataContext(
        published_tier=published_tier,  # type: ignore[arg-type]
        nist_aal_hint="AAL2",
        verified_at=_NOW,
        provider_id="TEST_001",
    )


# ---------------------------------------------------------------------------
# GongdongInjeungseoContext — 3 allowed tiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tier",
    [
        "gongdong_injeungseo_personal_aal3",
        "gongdong_injeungseo_corporate_aal3",
        "gongdong_injeungseo_bank_only_aal2",
    ],
)
def test_gongdong_accepts_own_tiers(tier: str) -> None:
    ctx = _gongdong(tier)
    assert ctx.published_tier == tier


@pytest.mark.parametrize(
    "foreign_tier",
    [
        "geumyung_injeungseo_personal_aal2",
        "ganpyeon_injeung_kakao_aal2",
        "digital_onepass_level1_aal1",
        "mobile_id_mdl_aal2",
        "mydata_individual_aal2",
    ],
)
def test_gongdong_rejects_foreign_tiers(foreign_tier: str) -> None:
    with pytest.raises(ValidationError):
        _gongdong(foreign_tier)


def test_gongdong_rejects_arbitrary_string() -> None:
    with pytest.raises(ValidationError):
        _gongdong("not_a_real_tier")


# ---------------------------------------------------------------------------
# GeumyungInjeungseoContext — 2 allowed tiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tier",
    [
        "geumyung_injeungseo_personal_aal2",
        "geumyung_injeungseo_business_aal3",
    ],
)
def test_geumyung_accepts_own_tiers(tier: str) -> None:
    ctx = _geumyung(tier)
    assert ctx.published_tier == tier


@pytest.mark.parametrize(
    "foreign_tier",
    [
        "gongdong_injeungseo_personal_aal3",
        "ganpyeon_injeung_toss_aal2",
        "digital_onepass_level3_aal3",
        "mobile_id_resident_aal2",
        "mydata_individual_aal2",
    ],
)
def test_geumyung_rejects_foreign_tiers(foreign_tier: str) -> None:
    with pytest.raises(ValidationError):
        _geumyung(foreign_tier)


# ---------------------------------------------------------------------------
# GanpyeonInjeungContext — 7 allowed tiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tier",
    [
        "ganpyeon_injeung_pass_aal2",
        "ganpyeon_injeung_kakao_aal2",
        "ganpyeon_injeung_naver_aal2",
        "ganpyeon_injeung_toss_aal2",
        "ganpyeon_injeung_bank_aal2",
        "ganpyeon_injeung_samsung_aal2",
        "ganpyeon_injeung_payco_aal2",
    ],
)
def test_ganpyeon_accepts_own_tiers(tier: str) -> None:
    ctx = _ganpyeon(tier)
    assert ctx.published_tier == tier


@pytest.mark.parametrize(
    "foreign_tier",
    [
        "gongdong_injeungseo_bank_only_aal2",
        "geumyung_injeungseo_business_aal3",
        "digital_onepass_level2_aal2",
        "mobile_id_mdl_aal2",
        "mydata_individual_aal2",
    ],
)
def test_ganpyeon_rejects_foreign_tiers(foreign_tier: str) -> None:
    with pytest.raises(ValidationError):
        _ganpyeon(foreign_tier)


# ---------------------------------------------------------------------------
# DigitalOnepassContext — 3 allowed tiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tier",
    [
        "digital_onepass_level1_aal1",
        "digital_onepass_level2_aal2",
        "digital_onepass_level3_aal3",
    ],
)
def test_onepass_accepts_own_tiers(tier: str) -> None:
    ctx = _onepass(tier)
    assert ctx.published_tier == tier


@pytest.mark.parametrize(
    "foreign_tier",
    [
        "gongdong_injeungseo_personal_aal3",
        "geumyung_injeungseo_personal_aal2",
        "ganpyeon_injeung_naver_aal2",
        "mobile_id_resident_aal2",
        "mydata_individual_aal2",
    ],
)
def test_onepass_rejects_foreign_tiers(foreign_tier: str) -> None:
    with pytest.raises(ValidationError):
        _onepass(foreign_tier)


# ---------------------------------------------------------------------------
# MobileIdContext — 2 allowed tiers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tier",
    [
        "mobile_id_mdl_aal2",
        "mobile_id_resident_aal2",
    ],
)
def test_mobile_id_accepts_own_tiers(tier: str) -> None:
    ctx = _mobile_id(tier)
    assert ctx.published_tier == tier


@pytest.mark.parametrize(
    "foreign_tier",
    [
        "gongdong_injeungseo_corporate_aal3",
        "geumyung_injeungseo_business_aal3",
        "ganpyeon_injeung_pass_aal2",
        "digital_onepass_level1_aal1",
        "mydata_individual_aal2",
    ],
)
def test_mobile_id_rejects_foreign_tiers(foreign_tier: str) -> None:
    with pytest.raises(ValidationError):
        _mobile_id(foreign_tier)


# ---------------------------------------------------------------------------
# MyDataContext — 1 allowed tier
# ---------------------------------------------------------------------------


def test_mydata_accepts_own_tier() -> None:
    ctx = _mydata("mydata_individual_aal2")
    assert ctx.published_tier == "mydata_individual_aal2"


@pytest.mark.parametrize(
    "foreign_tier",
    [
        "gongdong_injeungseo_personal_aal3",
        "geumyung_injeungseo_personal_aal2",
        "ganpyeon_injeung_bank_aal2",
        "digital_onepass_level3_aal3",
        "mobile_id_mdl_aal2",
    ],
)
def test_mydata_rejects_foreign_tiers(foreign_tier: str) -> None:
    with pytest.raises(ValidationError):
        _mydata(foreign_tier)


def test_mydata_rejects_arbitrary_string() -> None:
    with pytest.raises(ValidationError):
        _mydata("totally_made_up_tier")
