# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ``kosmos.plugins.manifest_schema``.

Covers data-model.md § 1 + § 2 invariants:

* Positive baseline ``PluginManifest`` round-trips.
* Eight negative cases — one for each of the 5 cross-field validators
  (``_v_mock_source``, ``_v_pipa_required``, ``_v_pipa_hash``,
  ``_v_otel_attribute``, ``_v_namespace``) plus 3 schema-level
  invariants (``frozen``, ``extra=forbid``, regex/length on
  ``plugin_id``).
* Acknowledgment hash module integration — verifies the canonical
  SHA-256 constant exposed by :mod:`kosmos.plugins.canonical_acknowledgment`
  matches the hash a fresh re-extraction would produce (T005 + T006
  coupling).

All cases use Pydantic v2 ``ValidationError`` + the validator's
expected error fragment so test failures point at the broken validator.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from kosmos.plugins import (
    CANONICAL_ACKNOWLEDGMENT_SHA256,
    CANONICAL_ACKNOWLEDGMENT_TEXT,
    PIPATrusteeAcknowledgment,
    PluginManifest,
)
from kosmos.plugins import canonical_acknowledgment as _canon
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
)

# ---------------------------------------------------------------------------
# Builders — keep test setup tight + readable.
# ---------------------------------------------------------------------------


def _make_adapter(
    *,
    tool_id: str = "plugin.demo_plugin.lookup",
    primitive: AdapterPrimitive = AdapterPrimitive.lookup,
    pipa_class: str = "personal_standard",
) -> AdapterRegistration:
    """Build a baseline AdapterRegistration that satisfies the v1.2 GA backstop."""

    return AdapterRegistration(
        tool_id=tool_id,
        primitive=primitive,
        module_path="example.demo_plugin.adapter",
        input_model_ref="example.demo_plugin.schema:DemoLookup",
        source_mode=AdapterSourceMode.OPENAPI,
        published_tier_minimum="digital_onepass_level1_aal1",
        nist_aal_hint="AAL1",
        auth_type="api_key",
        auth_level="AAL1",
        pipa_class=pipa_class,
    )


def _make_pipa_ack(
    *,
    sha256: str | None = None,
) -> PIPATrusteeAcknowledgment:
    return PIPATrusteeAcknowledgment(
        trustee_org_name="KOSMOS Plugin Authors",
        trustee_contact="plugins@example.com",
        pii_fields_handled=["phone_number"],
        legal_basis="PIPA §15-1-2",
        acknowledgment_sha256=sha256 or CANONICAL_ACKNOWLEDGMENT_SHA256,
    )


def _make_manifest_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "plugin_id": "demo_plugin",
        "version": "1.0.0",
        "adapter": _make_adapter(),
        "tier": "live",
        "mock_source_spec": None,
        "processes_pii": True,
        "pipa_trustee_acknowledgment": _make_pipa_ack(),
        "slsa_provenance_url": (
            "https://github.com/kosmos-plugin-store/kosmos-plugin-demo/"
            "releases/download/v1.0.0/demo.intoto.jsonl"
        ),
        "otel_attributes": {"kosmos.plugin.id": "demo_plugin"},
        "search_hint_ko": "데모 플러그인 조회",
        "search_hint_en": "demo plugin lookup",
        "permission_layer": 1,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Positive baseline.
# ---------------------------------------------------------------------------


class TestPluginManifestPositive:
    def test_baseline_construction_round_trips(self) -> None:
        m = PluginManifest(**_make_manifest_kwargs())
        assert m.plugin_id == "demo_plugin"
        assert m.version == "1.0.0"
        assert m.tier == "live"
        assert m.processes_pii is True
        assert m.adapter.tool_id == "plugin.demo_plugin.lookup"
        assert m.otel_attributes["kosmos.plugin.id"] == m.plugin_id

    def test_mock_tier_with_source_spec_passes(self) -> None:
        m = PluginManifest(
            **_make_manifest_kwargs(
                tier="mock",
                mock_source_spec="https://www.nts.go.kr/openapi/spec/1.0",
                processes_pii=False,
                pipa_trustee_acknowledgment=None,
            )
        )
        assert m.tier == "mock"
        assert m.mock_source_spec == "https://www.nts.go.kr/openapi/spec/1.0"

    def test_no_pii_with_no_ack_passes(self) -> None:
        m = PluginManifest(
            **_make_manifest_kwargs(
                processes_pii=False,
                pipa_trustee_acknowledgment=None,
                adapter=_make_adapter(pipa_class="non_personal"),
            )
        )
        assert m.processes_pii is False
        assert m.pipa_trustee_acknowledgment is None


# ---------------------------------------------------------------------------
# Cross-field validator negative cases (5 — one per validator).
# ---------------------------------------------------------------------------


class TestCrossFieldValidators:
    def test_v_mock_source_missing_when_tier_mock(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    tier="mock",
                    mock_source_spec=None,
                    processes_pii=False,
                    pipa_trustee_acknowledgment=None,
                )
            )
        assert "mock_source_spec is required" in str(exc.value)

    def test_v_mock_source_set_when_tier_live(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    tier="live",
                    mock_source_spec="https://accidentally-set.example.com",
                )
            )
        assert "mock_source_spec must be None when tier='live'" in str(exc.value)

    def test_v_pipa_required_when_processes_pii_true(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    processes_pii=True,
                    pipa_trustee_acknowledgment=None,
                )
            )
        assert "pipa_trustee_acknowledgment required" in str(exc.value)

    def test_v_pipa_required_must_be_none_when_processes_pii_false(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    processes_pii=False,
                )
            )
        assert "pipa_trustee_acknowledgment must be None" in str(exc.value)

    def test_v_pipa_hash_mismatch(self) -> None:
        # 64-char lowercase hex but NOT the canonical hash.
        bogus = "0" * 64
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    pipa_trustee_acknowledgment=_make_pipa_ack(sha256=bogus),
                )
            )
        msg = str(exc.value)
        assert "acknowledgment_sha256 mismatch" in msg
        assert CANONICAL_ACKNOWLEDGMENT_SHA256 in msg
        assert bogus in msg

    def test_v_otel_attribute_value_must_match_plugin_id(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    otel_attributes={"kosmos.plugin.id": "wrong_id"},
                )
            )
        assert 'otel_attributes["kosmos.plugin.id"] must equal plugin_id' in str(exc.value)

    def test_v_otel_attribute_required_key_present(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    otel_attributes={"some.other.key": "x"},
                )
            )
        assert "kosmos.plugin.id" in str(exc.value)

    def test_v_namespace_prefix_mismatch(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(
                    adapter=_make_adapter(tool_id="plugin.other_id.lookup"),
                )
            )
        assert "adapter.tool_id must start with 'plugin.demo_plugin.'" in str(exc.value)

    def test_v_namespace_verb_resolve_location_rejected(self) -> None:
        """Post review-eval C3: AdapterRegistration regex rejects
        ``plugin.<id>.resolve_location`` directly — no drift between
        the adapter layer and PluginManifest._v_namespace.
        """
        with pytest.raises(ValidationError) as exc:
            _make_adapter(
                tool_id="plugin.demo_plugin.resolve_location",
                primitive=AdapterPrimitive.resolve_location,
            )
        assert "resolve_location" in str(exc.value)


# ---------------------------------------------------------------------------
# Schema-level invariants (3) — frozen, extra=forbid, plugin_id regex.
# ---------------------------------------------------------------------------


class TestSchemaInvariants:
    def test_manifest_is_frozen(self) -> None:
        m = PluginManifest(**_make_manifest_kwargs())
        with pytest.raises(ValidationError) as exc:
            m.plugin_id = "mutated"  # type: ignore[misc]
        assert "frozen" in str(exc.value).lower() or "instance" in str(exc.value).lower()

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_make_manifest_kwargs(),
                unexpected_field="oops",  # type: ignore[arg-type]
            )
        msg = str(exc.value).lower()
        assert "extra" in msg or "not permitted" in msg or "forbidden" in msg

    def test_plugin_id_regex_rejected(self) -> None:
        # Capital letters + hyphens are not allowed; only [a-z][a-z0-9_]*.
        with pytest.raises(ValidationError) as exc:
            PluginManifest(**_make_manifest_kwargs(plugin_id="Demo-Plugin"))
        msg = str(exc.value)
        assert "plugin_id" in msg
        assert "pattern" in msg.lower() or "string should match pattern" in msg.lower()


# ---------------------------------------------------------------------------
# Canonical acknowledgment hash module integration (T005 + T006 coupling).
# ---------------------------------------------------------------------------


class TestCanonicalAcknowledgmentHash:
    def test_constant_matches_fresh_recomputation(self) -> None:
        """Re-extracting + hashing the markdown must reproduce the constant.

        Guards against accidental drift between the import-time computation
        and a fresh read (e.g. someone editing the markers without updating
        downstream test fixtures).
        """
        text = _canon._extract_canonical_text(_canon._load_security_review_md())
        digest = _canon._compute_canonical_hash(text)
        assert digest == CANONICAL_ACKNOWLEDGMENT_SHA256

    def test_canonical_text_normalised(self) -> None:
        # Normalisation invariants the loader promises: no leading / trailing
        # whitespace, LF line endings only.
        assert CANONICAL_ACKNOWLEDGMENT_TEXT.strip() == CANONICAL_ACKNOWLEDGMENT_TEXT
        assert "\r\n" not in CANONICAL_ACKNOWLEDGMENT_TEXT

    def test_constant_shape(self) -> None:
        # 64 lowercase hex chars; matches ack regex on the model.
        assert len(CANONICAL_ACKNOWLEDGMENT_SHA256) == 64
        assert all(c in "0123456789abcdef" for c in CANONICAL_ACKNOWLEDGMENT_SHA256)

    def test_extracted_text_is_actual_canonical_block_not_prose(self) -> None:
        """C5 regression: prose mentions of the markers in backticks must not
        contaminate extraction. The actual canonical text is 540 chars of
        the 7 PIPA §26 trustee duties — not the 5-char ` ↔ ` separator
        between two prose marker mentions on the same line.
        """
        assert len(CANONICAL_ACKNOWLEDGMENT_TEXT) > 200, (
            f"canonical text suspiciously short ({len(CANONICAL_ACKNOWLEDGMENT_TEXT)} chars) — "
            "extraction probably captured a prose mention instead of the actual block"
        )
        # The actual canonical block opens with this exact phrase.
        assert "본 플러그인의 기여 조직" in CANONICAL_ACKNOWLEDGMENT_TEXT
        # And contains the 7 numbered duties.
        for n in range(1, 8):
            assert f"{n}. " in CANONICAL_ACKNOWLEDGMENT_TEXT, (
                f"duty {n} missing — extraction did not capture the full block"
            )

    def test_extracted_hash_matches_documented_hash(self) -> None:
        """C5 + D1 regression: the hash printed in docs/plugins/security-review.md
        must equal the runtime constant. Catches drift in either direction."""
        from pathlib import Path

        md = Path(_canon._SECURITY_REVIEW_PATH).read_text(encoding="utf-8")
        # The hash table row literally contains the 64-char hex digest.
        assert CANONICAL_ACKNOWLEDGMENT_SHA256 in md, (
            "docs/plugins/security-review.md does not display the runtime "
            f"hash {CANONICAL_ACKNOWLEDGMENT_SHA256} — citizens copying the "
            "documented value into manifest.yaml will fail Q6-PIPA-HASH"
        )
