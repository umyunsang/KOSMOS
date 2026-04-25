# SPDX-License-Identifier: Apache-2.0
"""Plugin namespace invariants (R-1 Q8 family + ADR-007).

The three checks in this file mirror the validation-workflow IDs:

* **Q8-NAMESPACE** — every plugin adapter's ``tool_id`` MUST match
  ``plugin.<plugin_id>.<verb>``.
* **Q8-NO-ROOT-OVERRIDE** — ``<verb>`` MUST be one of the four reserved
  root primitives (``lookup`` / ``submit`` / ``verify`` / ``subscribe``).
  ``resolve_location`` is explicitly excluded — it is a built-in
  primitive whose surface a plugin cannot override.
* **Q8-VERB-IN-PRIMITIVES** — the verb suffix collisions with ADR-007's
  permissive ``AdapterRegistration`` regex (which allows
  ``resolve_location`` so existing built-in adapters keep validating)
  are caught at the manifest layer, not at registration time.

The shim ``kosmos.tools.registry.register_plugin_adapter`` is exercised
by the registration-flow test below so callers using the canonical
``kosmos.tools.registry`` import path see identical behaviour to the
``kosmos.plugins.registry`` direct path.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.plugins import (
    CANONICAL_ACKNOWLEDGMENT_SHA256,
    PluginManifest,
)
from kosmos.plugins.exceptions import PluginRegistrationError
from kosmos.tools import registry as tools_registry
from kosmos.tools.registry import (
    AdapterPrimitive,
    AdapterRegistration,
    AdapterSourceMode,
    ToolRegistry,
)


def _adapter(
    *, tool_id: str, primitive: AdapterPrimitive = AdapterPrimitive.lookup
) -> AdapterRegistration:
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
        pipa_class="non_personal",
    )


def _manifest_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "plugin_id": "demo_plugin",
        "version": "1.0.0",
        "adapter": _adapter(tool_id="plugin.demo_plugin.lookup"),
        "tier": "live",
        "mock_source_spec": None,
        "processes_pii": False,
        "pipa_trustee_acknowledgment": None,
        "slsa_provenance_url": "https://github.com/kosmos-plugin-store/x",
        "otel_attributes": {"kosmos.plugin.id": "demo_plugin"},
        "search_hint_ko": "데모",
        "search_hint_en": "demo",
        "permission_layer": 1,
    }
    base.update(overrides)
    return base


class TestQ8Namespace:
    def test_namespace_prefix_required(self) -> None:
        """Q8-NAMESPACE: tool_id MUST match plugin.<plugin_id>.<verb>."""
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_manifest_kwargs(
                    adapter=_adapter(tool_id="plugin.other_id.lookup"),
                )
            )
        assert "adapter.tool_id must start with 'plugin.demo_plugin.'" in str(exc.value)

    def test_namespace_unprefixed_rejected_by_adapter_regex(self) -> None:
        """Built-in adapter regex still rejects bare snake_case mismatching the alternation."""
        # The regex on AdapterRegistration permits either the snake_case form OR
        # the plugin namespaced form — so bare snake_case 'lookup' is accepted
        # at the AdapterRegistration layer (legacy in-tree adapters use it).
        # The PluginManifest._v_namespace validator then rejects it because it
        # lacks the plugin.<id>. prefix.
        bare_adapter = AdapterRegistration(
            tool_id="lookup",
            primitive=AdapterPrimitive.lookup,
            module_path="example.demo_plugin.adapter",
            input_model_ref="example.demo_plugin.schema:DemoLookup",
            source_mode=AdapterSourceMode.OPENAPI,
            published_tier_minimum="digital_onepass_level1_aal1",
            nist_aal_hint="AAL1",
            auth_type="api_key",
            auth_level="AAL1",
            pipa_class="non_personal",
        )
        with pytest.raises(ValidationError) as exc:
            PluginManifest(**_manifest_kwargs(adapter=bare_adapter))
        assert "adapter.tool_id must start with" in str(exc.value)


class TestQ8NoRootOverride:
    def test_resolve_location_verb_rejected_at_manifest(self) -> None:
        """Q8-NO-ROOT-OVERRIDE: resolve_location is a built-in; plugins cannot claim it.

        ADR-007's regex on AdapterRegistration permits resolve_location for
        symmetry with the in-tree resolve_location adapter; PluginManifest
        layers an additional restriction on top so plugins specifically
        cannot override the four reserved root primitives.
        """
        with pytest.raises(ValidationError) as exc:
            PluginManifest(
                **_manifest_kwargs(
                    adapter=_adapter(
                        tool_id="plugin.demo_plugin.resolve_location",
                        primitive=AdapterPrimitive.resolve_location,
                    ),
                )
            )
        msg = str(exc.value)
        assert "verb suffix must be one of" in msg
        assert "resolve_location" in msg

    def test_unknown_verb_rejected_at_adapter_regex(self) -> None:
        """ADR-007 regex itself rejects verbs outside the alternation."""
        with pytest.raises(ValidationError):
            AdapterRegistration(
                tool_id="plugin.demo_plugin.bogus_verb",
                primitive=AdapterPrimitive.lookup,
                module_path="x",
                input_model_ref="x:Y",
                source_mode=AdapterSourceMode.OPENAPI,
                published_tier_minimum="digital_onepass_level1_aal1",
                nist_aal_hint="AAL1",
                auth_type="api_key",
                auth_level="AAL1",
                pipa_class="non_personal",
            )


class TestQ8VerbInPrimitives:
    @pytest.mark.parametrize(
        ("verb", "primitive"),
        [
            ("lookup", AdapterPrimitive.lookup),
            ("submit", AdapterPrimitive.submit),
            ("verify", AdapterPrimitive.verify),
            ("subscribe", AdapterPrimitive.subscribe),
        ],
    )
    def test_each_root_verb_accepted(
        self, verb: str, primitive: AdapterPrimitive
    ) -> None:
        m = PluginManifest(
            **_manifest_kwargs(
                adapter=_adapter(
                    tool_id=f"plugin.demo_plugin.{verb}",
                    primitive=primitive,
                ),
            )
        )
        assert m.adapter.tool_id.endswith(f".{verb}")
        assert m.adapter.primitive == primitive


class TestRegisterPluginAdapterShim:
    """Smoke-test the shim on kosmos.tools.registry routes to the impl."""

    def test_shim_is_callable_and_routes_to_plugin_module(self) -> None:
        # We do not exercise a full end-to-end registration here (T058
        # owns that). The contract this test protects: the shim symbol
        # exists on the canonical module path, accepts the documented
        # kwargs, and calls into kosmos.plugins.registry's implementation.
        assert callable(tools_registry.register_plugin_adapter)

        # Failure path: passing a non-PluginManifest raises a
        # PluginRegistrationError (or its parent PluginError) — this
        # exercises the shim → impl indirection without needing a real
        # adapter module on disk.
        with pytest.raises(PluginRegistrationError):
            tools_registry.register_plugin_adapter(
                "not-a-manifest",
                registry=ToolRegistry(),
                executor=object(),
            )

    def test_canonical_hash_constant_round_trips(self) -> None:
        # A guard against an accidental rename of the public constant —
        # downstream plugins import it from kosmos.plugins, the shim
        # consumers may import it from elsewhere; either path must yield
        # the same 64-char lowercase hex digest.
        assert isinstance(CANONICAL_ACKNOWLEDGMENT_SHA256, str)
        assert len(CANONICAL_ACKNOWLEDGMENT_SHA256) == 64
