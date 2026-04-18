# SPDX-License-Identifier: Apache-2.0
"""T034 — Contract shape test for the verify primitive.

Loads specs/031-five-primitive-harness/contracts/verify.input.schema.json
and verify.output.schema.json, then validates that:

1. VerifyInput correctly validates / rejects against the input schema shape.
2. All 6 AuthContext family variants round-trip through VerifyOutput.
3. VerifyMismatchError round-trips correctly.
4. Invalid discriminator values are rejected.

No network calls; all pure-Python.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from kosmos.primitives.verify import (
    DigitalOnepassContext,
    GanpyeonInjeungContext,
    GeumyungInjeungseoContext,
    GongdongInjeungseoContext,
    MobileIdContext,
    MyDataContext,
    VerifyInput,
    VerifyMismatchError,
    VerifyOutput,
)

# Locate contract files relative to this file's ancestry (worktree root).
_REPO_ROOT = Path(__file__).parents[4]
_CONTRACTS_DIR = _REPO_ROOT / "specs" / "031-five-primitive-harness" / "contracts"

_VERIFIED_AT = "2026-04-19T09:00:00Z"

# ---------------------------------------------------------------------------
# Helpers — build minimal valid payloads per family
# ---------------------------------------------------------------------------

_FAMILY_CONTEXTS: list[dict[str, object]] = [
    {
        "family": "gongdong_injeungseo",
        "published_tier": "gongdong_injeungseo_personal_aal3",
        "nist_aal_hint": "AAL3",
        "verified_at": _VERIFIED_AT,
        "external_session_ref": "ref-gongdong",
        "certificate_issuer": "KICA",
    },
    {
        "family": "geumyung_injeungseo",
        "published_tier": "geumyung_injeungseo_personal_aal2",
        "nist_aal_hint": "AAL2",
        "verified_at": _VERIFIED_AT,
        "external_session_ref": "ref-geumyung",
        "bank_cluster": "kftc",
    },
    {
        "family": "ganpyeon_injeung",
        "published_tier": "ganpyeon_injeung_kakao_aal2",
        "nist_aal_hint": "AAL2",
        "verified_at": _VERIFIED_AT,
        "external_session_ref": None,
        "provider": "kakao",
    },
    {
        "family": "digital_onepass",
        "published_tier": "digital_onepass_level2_aal2",
        "nist_aal_hint": "AAL2",
        "verified_at": _VERIFIED_AT,
        "external_session_ref": None,
        "level": 2,
    },
    {
        "family": "mobile_id",
        "published_tier": "mobile_id_mdl_aal2",
        "nist_aal_hint": "AAL2",
        "verified_at": _VERIFIED_AT,
        "external_session_ref": None,
        "id_type": "mdl",
    },
    {
        "family": "mydata",
        "published_tier": "mydata_individual_aal2",
        "nist_aal_hint": "AAL2",
        "verified_at": _VERIFIED_AT,
        "external_session_ref": None,
        "provider_id": "TEST_001",
    },
]

_EXPECTED_TYPES = [
    GongdongInjeungseoContext,
    GeumyungInjeungseoContext,
    GanpyeonInjeungContext,
    DigitalOnepassContext,
    MobileIdContext,
    MyDataContext,
]


# ---------------------------------------------------------------------------
# T034a — contract files exist and are valid JSON
# ---------------------------------------------------------------------------


class TestContractFilesExist:
    def test_input_schema_exists(self) -> None:
        path = _CONTRACTS_DIR / "verify.input.schema.json"
        assert path.exists(), f"Contract file not found: {path}"

    def test_output_schema_exists(self) -> None:
        path = _CONTRACTS_DIR / "verify.output.schema.json"
        assert path.exists(), f"Contract file not found: {path}"

    def test_input_schema_is_valid_json(self) -> None:
        path = _CONTRACTS_DIR / "verify.input.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert schema["title"] == "VerifyInput"
        assert "family_hint" in schema["properties"]

    def test_output_schema_is_valid_json(self) -> None:
        path = _CONTRACTS_DIR / "verify.output.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        assert "VerifyMismatchError" in schema["$defs"]
        for family_cls in [
            "GongdongInjeungseoContext",
            "GeumyungInjeungseoContext",
            "GanpyeonInjeungContext",
            "DigitalOnepassContext",
            "MobileIdContext",
            "MyDataContext",
        ]:
            assert family_cls in schema["$defs"], f"Missing {family_cls} in output schema"


# ---------------------------------------------------------------------------
# T034b — VerifyInput round-trips
# ---------------------------------------------------------------------------


class TestVerifyInputShape:
    @pytest.mark.parametrize(
        "family",
        [
            "gongdong_injeungseo",
            "geumyung_injeungseo",
            "ganpyeon_injeung",
            "digital_onepass",
            "mobile_id",
            "mydata",
        ],
    )
    def test_valid_family_hint(self, family: str) -> None:
        vi = VerifyInput(family_hint=family, session_context={})  # type: ignore[arg-type]
        assert vi.family_hint == family

    def test_unknown_family_hint_rejected(self) -> None:
        with pytest.raises(ValidationError):
            VerifyInput(family_hint="alien_cert", session_context={})  # type: ignore[arg-type]

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            VerifyInput(family_hint="mydata", session_context={}, surprise="oops")  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        vi = VerifyInput(family_hint="mydata", session_context={})
        with pytest.raises(ValidationError):
            vi.family_hint = "mobile_id"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T034c — 6 AuthContext family variants round-trip through VerifyOutput
# ---------------------------------------------------------------------------


_OUTPUT_ADAPTER: TypeAdapter[VerifyOutput] = TypeAdapter(VerifyOutput)


@pytest.mark.parametrize(
    "payload, expected_type",
    list(zip(_FAMILY_CONTEXTS, _EXPECTED_TYPES)),
)
def test_verify_output_roundtrip(
    payload: dict[str, object], expected_type: type
) -> None:
    output = VerifyOutput(result=payload)  # type: ignore[arg-type]
    assert isinstance(output.result, expected_type)
    assert output.result.family == payload["family"]


def test_verify_output_json_roundtrip_gongdong() -> None:
    payload = _FAMILY_CONTEXTS[0]
    output = VerifyOutput(result=payload)  # type: ignore[arg-type]
    serialised = output.model_dump_json()
    restored = VerifyOutput.model_validate_json(serialised)
    assert isinstance(restored.result, GongdongInjeungseoContext)
    assert restored.result.certificate_issuer == "KICA"


# ---------------------------------------------------------------------------
# T034d — VerifyMismatchError round-trips through VerifyOutput
# ---------------------------------------------------------------------------


def test_verify_mismatch_error_in_output() -> None:
    mismatch = {
        "family": "mismatch_error",
        "reason": "family_mismatch",
        "expected_family": "mobile_id",
        "observed_family": "gongdong_injeungseo",
        "message": "Caller expected mobile_id but adapter returned gongdong_injeungseo.",
    }
    output = VerifyOutput(result=mismatch)  # type: ignore[arg-type]
    assert isinstance(output.result, VerifyMismatchError)
    assert output.result.reason == "family_mismatch"
    assert output.result.family == "mismatch_error"


def test_verify_mismatch_error_json_roundtrip() -> None:
    mismatch = VerifyMismatchError(
        family="mismatch_error",
        reason="family_mismatch",
        expected_family="mydata",
        observed_family="mobile_id",
        message="test mismatch",
    )
    output = VerifyOutput(result=mismatch)
    serialised = output.model_dump_json()
    restored = VerifyOutput.model_validate_json(serialised)
    assert isinstance(restored.result, VerifyMismatchError)


# ---------------------------------------------------------------------------
# T034e — unknown discriminator value rejected
# ---------------------------------------------------------------------------


def test_unknown_discriminator_rejected() -> None:
    payload = {
        "family": "alien_cert",
        "published_tier": "whatever",
        "nist_aal_hint": "AAL1",
        "verified_at": _VERIFIED_AT,
    }
    with pytest.raises(ValidationError):
        VerifyOutput(result=payload)  # type: ignore[arg-type]
