# SPDX-License-Identifier: Apache-2.0
"""T030 + T031 — resolve_location envelope byte-identity and re-export signature contract.

Proves two guarantees introduced by Spec 031 Phase 2:

1. FR-017 (byte-identity): ``kosmos.primitives.resolve_location`` is the *same
   coroutine* as ``kosmos.tools.resolve_location.resolve_location`` — no wrapper
   that alters input/output schema shapes.  Tests load Spec 022 contract JSON
   schemas and validate fixture payloads through both import paths identically.

2. T031 (re-export contract): ``kosmos.primitives.__init__`` does NOT introduce
   any attribute change on the re-exported symbol.  ``__signature__``,
   ``__doc__``, ``__module__``, and ``__name__`` must be identical to the
   canonical Spec 022 source.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from kosmos.tools.models import (
    AddressResult,
    AdmCodeResult,
    CoordResult,
    POIResult,
    ResolveBundle,
    ResolveError,
    ResolveLocationInput,
)

# ---------------------------------------------------------------------------
# Import both paths and assert identity
# ---------------------------------------------------------------------------

import kosmos.primitives as _primitives_module
from kosmos.tools.resolve_location import resolve_location as _canonical_rl

_primitives_rl = _primitives_module.resolve_location

# Path to Spec 022 JSON Schema contracts (relative to project root).
_CONTRACTS_DIR = (
    Path(__file__).resolve().parents[3]
    / "specs"
    / "022-mvp-main-tool"
    / "contracts"
)
_INPUT_SCHEMA_PATH = _CONTRACTS_DIR / "resolve_location.input.schema.json"
_OUTPUT_SCHEMA_PATH = _CONTRACTS_DIR / "resolve_location.output.schema.json"


# ---------------------------------------------------------------------------
# T031 — re-export attribute contract (no separate file required per spec)
# ---------------------------------------------------------------------------


def test_primitives_resolve_location_is_same_object_as_canonical() -> None:
    """FR-017: primitives.resolve_location IS the spec-022 coroutine."""
    assert _primitives_rl is _canonical_rl, (
        "kosmos.primitives.resolve_location must be the identical object to "
        "kosmos.tools.resolve_location.resolve_location — any wrapping would "
        "break byte-identity."
    )


def test_primitives_resolve_location_preserves_dunder_name() -> None:
    """T031: __name__ is unchanged by the re-export."""
    assert _primitives_rl.__name__ == _canonical_rl.__name__


def test_primitives_resolve_location_preserves_dunder_module() -> None:
    """T031: __module__ still points to the Spec 022 source module."""
    assert _primitives_rl.__module__ == _canonical_rl.__module__
    assert "kosmos.tools.resolve_location" in _primitives_rl.__module__


def test_primitives_resolve_location_preserves_dunder_doc() -> None:
    """T031: __doc__ is identical between canonical and re-exported symbol."""
    assert _primitives_rl.__doc__ == _canonical_rl.__doc__


def test_primitives_resolve_location_preserves_signature() -> None:
    """T031: __signature__ is identical — no extra/removed parameters."""
    canonical_sig = inspect.signature(_canonical_rl)
    primitives_sig = inspect.signature(_primitives_rl)
    assert canonical_sig == primitives_sig, (
        f"Signature mismatch.\n"
        f"  canonical : {canonical_sig}\n"
        f"  primitives: {primitives_sig}"
    )


# ---------------------------------------------------------------------------
# Contract schema files exist
# ---------------------------------------------------------------------------


def test_spec022_input_schema_file_exists() -> None:
    """Spec 022 resolve_location.input.schema.json must be present."""
    assert _INPUT_SCHEMA_PATH.is_file(), (
        f"Spec 022 contract file missing: {_INPUT_SCHEMA_PATH}"
    )


def test_spec022_output_schema_file_exists() -> None:
    """Spec 022 resolve_location.output.schema.json must be present."""
    assert _OUTPUT_SCHEMA_PATH.is_file(), (
        f"Spec 022 contract file missing: {_OUTPUT_SCHEMA_PATH}"
    )


# ---------------------------------------------------------------------------
# FR-017 — schema shape byte-identity
# ---------------------------------------------------------------------------


class TestResolveLocationInputShape:
    """Validate ResolveLocationInput matches the Spec 022 contract."""

    def test_minimal_input_valid(self) -> None:
        ta = TypeAdapter(ResolveLocationInput)
        parsed = ta.validate_python({"query": "서울 강남구"})
        assert parsed.query == "서울 강남구"
        # Default want value from contract
        assert parsed.want == "coords_and_admcd"

    def test_all_want_values_accepted(self) -> None:
        ta = TypeAdapter(ResolveLocationInput)
        valid_wants = [
            "coords",
            "adm_cd",
            "coords_and_admcd",
            "road_address",
            "jibun_address",
            "poi",
            "all",
        ]
        for want in valid_wants:
            parsed = ta.validate_python({"query": "강남역", "want": want})
            assert parsed.want == want

    def test_invalid_want_rejected(self) -> None:
        from pydantic import ValidationError

        ta = TypeAdapter(ResolveLocationInput)
        with pytest.raises(ValidationError):
            ta.validate_python({"query": "강남역", "want": "full_bundle"})

    def test_empty_query_rejected(self) -> None:
        from pydantic import ValidationError

        ta = TypeAdapter(ResolveLocationInput)
        with pytest.raises(ValidationError):
            ta.validate_python({"query": ""})

    def test_near_anchor_accepted(self) -> None:
        ta = TypeAdapter(ResolveLocationInput)
        parsed = ta.validate_python(
            {"query": "강남", "want": "coords", "near": [37.5172, 127.0473]}
        )
        assert parsed.near is not None

    def test_contract_schema_is_valid_json(self) -> None:
        schema = json.loads(_INPUT_SCHEMA_PATH.read_text())
        assert schema.get("title") == "ResolveLocationInput"
        assert schema.get("type") == "object"


class TestResolveLocationOutputShape:
    """Validate ResolveLocationOutput variants match the Spec 022 output contract."""

    def test_coord_result_shape(self) -> None:
        result = CoordResult(
            kind="coords",
            lat=37.5172,
            lon=127.0473,
            confidence="high",
            source="kakao",
        )
        data = result.model_dump()
        assert data["kind"] == "coords"
        assert "lat" in data and "lon" in data
        assert "confidence" in data
        assert "source" in data

    def test_adm_code_result_shape(self) -> None:
        result = AdmCodeResult(
            kind="adm_cd",
            code="1168010500",
            name="서울특별시 강남구 개포동",
            level="eupmyeondong",
            source="juso",
        )
        data = result.model_dump()
        assert data["kind"] == "adm_cd"
        assert len(data["code"]) == 10
        assert data["level"] == "eupmyeondong"

    def test_adm_code_pattern_enforced(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AdmCodeResult(
                kind="adm_cd",
                code="short",  # not 10 digits
                name="서울",
                level="sido",
                source="juso",
            )

    def test_address_result_shape(self) -> None:
        result = AddressResult(
            kind="address",
            road_address="서울특별시 강남구 개포로 617",
            jibun_address=None,
            postal_code="06313",
            source="kakao",
        )
        data = result.model_dump()
        assert data["kind"] == "address"
        assert "road_address" in data
        assert "postal_code" in data

    def test_poi_result_shape(self) -> None:
        result = POIResult(
            kind="poi",
            name="강남역",
            category="REGION_ADDR",
            lat=37.4979,
            lon=127.0276,
            source="kakao",
        )
        data = result.model_dump()
        assert data["kind"] == "poi"
        assert data["source"] == "kakao"

    def test_resolve_bundle_shape(self) -> None:
        coord = CoordResult(
            kind="coords", lat=37.5172, lon=127.0473, confidence="high", source="kakao"
        )
        bundle = ResolveBundle(kind="bundle", source="bundle", coords=coord)
        data = bundle.model_dump()
        assert data["kind"] == "bundle"
        assert data["source"] == "bundle"
        assert data["coords"] is not None

    def test_resolve_error_shape(self) -> None:
        err = ResolveError(
            kind="error",
            reason="not_found",
            message="Could not resolve query.",
        )
        data = err.model_dump()
        assert data["kind"] == "error"
        assert data["reason"] == "not_found"

    def test_invalid_error_reason_rejected(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResolveError(
                kind="error",
                reason="bad_reason",  # not in enum
                message="test",
            )

    def test_contract_schema_is_valid_json(self) -> None:
        schema = json.loads(_OUTPUT_SCHEMA_PATH.read_text())
        assert schema.get("title") == "ResolveLocationOutput"
        assert "oneOf" in schema
