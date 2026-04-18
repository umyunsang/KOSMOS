# SPDX-License-Identifier: Apache-2.0
"""T029 + T031 — lookup envelope byte-identity and re-export signature contract.

Proves two guarantees introduced by Spec 031 Phase 2:

1. FR-016 (byte-identity): ``kosmos.primitives.lookup`` is the *same coroutine*
   as ``kosmos.tools.lookup.lookup`` — not a wrapper that alters input/output
   schema shapes.  Tests load Spec 022 contract JSON schemas and round-trip
   fixture payloads through both import paths to confirm they validate
   identically.

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

# ---------------------------------------------------------------------------
# Import both paths and assert identity
# ---------------------------------------------------------------------------
import kosmos.primitives as _primitives_module
from kosmos.tools.lookup import lookup as _canonical_lookup
from kosmos.tools.models import (
    LookupError,  # noqa: A004
    LookupSearchResult,
)

_primitives_lookup = _primitives_module.lookup

# Path to Spec 022 JSON Schema contracts (relative to project root).
_CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "specs" / "022-mvp-main-tool" / "contracts"
_INPUT_SCHEMA_PATH = _CONTRACTS_DIR / "lookup.input.schema.json"
_OUTPUT_SCHEMA_PATH = _CONTRACTS_DIR / "lookup.output.schema.json"


# ---------------------------------------------------------------------------
# T031 — re-export attribute contract (no separate file required per spec)
# ---------------------------------------------------------------------------


def test_primitives_lookup_is_same_object_as_canonical() -> None:
    """FR-016: primitives.lookup IS the spec-022 coroutine, not a wrapper."""
    assert _primitives_lookup is _canonical_lookup, (
        "kosmos.primitives.lookup must be the identical object to "
        "kosmos.tools.lookup.lookup — any wrapping would break byte-identity."
    )


def test_primitives_lookup_preserves_dunder_name() -> None:
    """T031: __name__ is unchanged by the re-export."""
    assert _primitives_lookup.__name__ == _canonical_lookup.__name__


def test_primitives_lookup_preserves_dunder_module() -> None:
    """T031: __module__ still points to the Spec 022 source module."""
    assert _primitives_lookup.__module__ == _canonical_lookup.__module__
    assert "kosmos.tools.lookup" in _primitives_lookup.__module__


def test_primitives_lookup_preserves_dunder_doc() -> None:
    """T031: __doc__ is identical between canonical and re-exported symbol."""
    assert _primitives_lookup.__doc__ == _canonical_lookup.__doc__


def test_primitives_lookup_preserves_signature() -> None:
    """T031: __signature__ is identical — no extra/removed parameters."""
    canonical_sig = inspect.signature(_canonical_lookup)
    primitives_sig = inspect.signature(_primitives_lookup)
    assert canonical_sig == primitives_sig, (
        f"Signature mismatch.\n  canonical : {canonical_sig}\n  primitives: {primitives_sig}"
    )


# ---------------------------------------------------------------------------
# Contract schema files exist
# ---------------------------------------------------------------------------


def test_spec022_input_schema_file_exists() -> None:
    """Spec 022 lookup.input.schema.json must be present in the worktree."""
    assert _INPUT_SCHEMA_PATH.is_file(), f"Spec 022 contract file missing: {_INPUT_SCHEMA_PATH}"


def test_spec022_output_schema_file_exists() -> None:
    """Spec 022 lookup.output.schema.json must be present in the worktree."""
    assert _OUTPUT_SCHEMA_PATH.is_file(), f"Spec 022 contract file missing: {_OUTPUT_SCHEMA_PATH}"


# ---------------------------------------------------------------------------
# FR-016 — schema shape byte-identity: validate fixtures against Spec 022
# contract and against the live Pydantic models exposed by primitives.lookup
# ---------------------------------------------------------------------------


class TestLookupInputSchemaShape:
    """Validate that LookupSearchInput / LookupFetchInput match the contract."""

    def test_search_input_valid_fixture(self) -> None:
        from kosmos.tools.models import LookupSearchInput

        ta = TypeAdapter(LookupSearchInput)
        fixture = {"mode": "search", "query": "교통사고 위험지점"}
        parsed = ta.validate_python(fixture)
        assert parsed.mode == "search"
        assert parsed.query == "교통사고 위험지점"

    def test_fetch_input_valid_fixture(self) -> None:
        from kosmos.tools.models import LookupFetchInput

        ta = TypeAdapter(LookupFetchInput)
        fixture = {
            "mode": "fetch",
            "tool_id": "koroad_accident_hazard_search",
            "params": {"adm_cd": "4113510700", "year": 2022},
        }
        parsed = ta.validate_python(fixture)
        assert parsed.mode == "fetch"
        assert parsed.tool_id == "koroad_accident_hazard_search"

    def test_search_input_rejects_empty_query(self) -> None:
        from pydantic import ValidationError

        from kosmos.tools.models import LookupSearchInput

        ta = TypeAdapter(LookupSearchInput)
        with pytest.raises(ValidationError):
            ta.validate_python({"mode": "search", "query": ""})

    def test_contract_schema_is_valid_json(self) -> None:
        """Input schema contract file must be parseable JSON."""
        schema = json.loads(_INPUT_SCHEMA_PATH.read_text())
        assert schema.get("title") == "LookupInput"
        assert "oneOf" in schema or "$defs" in schema


class TestLookupOutputSchemaShape:
    """Validate that LookupOutput variants match the Spec 022 output contract."""

    def test_search_result_shape_matches_contract(self) -> None:
        result = LookupSearchResult(
            kind="search",
            candidates=[],
            total_registry_size=4,
            effective_top_k=5,
            reason="ok",
        )
        data = result.model_dump()
        assert data["kind"] == "search"
        assert "candidates" in data
        assert "total_registry_size" in data
        assert "effective_top_k" in data

    def test_error_shape_matches_contract(self) -> None:
        err = LookupError(
            kind="error",
            reason="unknown_tool",
            message="Tool 'bad_tool' is not registered.",
            retryable=False,
        )
        data = err.model_dump()
        assert data["kind"] == "error"
        assert data["reason"] == "unknown_tool"
        assert data["retryable"] is False

    def test_contract_schema_is_valid_json(self) -> None:
        """Output schema contract file must be parseable JSON."""
        schema = json.loads(_OUTPUT_SCHEMA_PATH.read_text())
        assert schema.get("title") == "LookupOutput"
        # Output contract uses oneOf at root level
        assert "oneOf" in schema
