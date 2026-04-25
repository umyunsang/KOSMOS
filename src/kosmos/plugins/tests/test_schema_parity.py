# SPDX-License-Identifier: Apache-2.0
"""Drift gate for ``contracts/manifest.schema.json``.

The on-disk JSON Schema at
``specs/1636-plugin-dx-5tier/contracts/manifest.schema.json`` is the
contract external plugin authors and downstream tooling read. The live
source-of-truth is :class:`kosmos.plugins.manifest_schema.PluginManifest`
exported via ``model_json_schema()``. This test fails when the two
diverge so a contributor can never quietly mutate the contract by
editing one side only.

Regeneration recipe (when the diff is intended):

    uv run python -c "
    import json, pathlib
    from kosmos.plugins import PluginManifest
    s = PluginManifest.model_json_schema()
    s['\\$schema'] = 'https://json-schema.org/draft/2020-12/schema'
    s['\\$id'] = 'https://kosmos.dev/schemas/plugin-manifest/1.0.0.json'
    pathlib.Path('specs/1636-plugin-dx-5tier/contracts/manifest.schema.json').write_text(
        json.dumps(s, indent=2, ensure_ascii=False) + '\\n', encoding='utf-8'
    )
    "

If your change adds a new validator, also touch a fixture row in
``test_manifest_schema.py`` so the regen and the runtime invariant move
together.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from kosmos.plugins import PluginManifest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_CONTRACT_PATH = (
    _REPO_ROOT / "specs" / "1636-plugin-dx-5tier" / "contracts" / "manifest.schema.json"
)


def _load_disk_schema() -> dict[str, Any]:
    if not _CONTRACT_PATH.is_file():
        pytest.fail(f"contract schema missing: {_CONTRACT_PATH} — regenerate per module docstring.")
    return json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))


def _live_schema() -> dict[str, Any]:
    schema = PluginManifest.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://kosmos.dev/schemas/plugin-manifest/1.0.0.json"
    return schema


class TestManifestSchemaParity:
    def test_disk_schema_equals_pydantic_export(self) -> None:
        """Byte-equivalent JSON Schema between disk + live model."""
        disk = _load_disk_schema()
        live = _live_schema()
        # json.dumps with sorted keys + ensure_ascii=False normalises any
        # ordering differences while keeping diagnostic output readable.
        disk_canon = json.dumps(disk, indent=2, ensure_ascii=False, sort_keys=True)
        live_canon = json.dumps(live, indent=2, ensure_ascii=False, sort_keys=True)
        assert disk_canon == live_canon, (
            "JSON Schema drift detected between disk contract and Pydantic "
            "export. Regenerate per the module docstring once the change is "
            "intentional."
        )

    def test_schema_pins_canonical_id_and_dialect(self) -> None:
        disk = _load_disk_schema()
        assert disk.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
        assert disk.get("$id") == ("https://kosmos.dev/schemas/plugin-manifest/1.0.0.json")

    def test_schema_carries_all_required_top_level_fields(self) -> None:
        disk = _load_disk_schema()
        required = set(disk.get("required", []))
        # Spot-check the load-bearing fields per data-model.md § 1. The full
        # parity test above guarantees byte equivalence; this guard catches
        # regressions where a field becomes Optional in the model without an
        # accompanying spec change.
        for field in (
            "plugin_id",
            "version",
            "adapter",
            "tier",
            "slsa_provenance_url",
            "otel_attributes",
            "search_hint_ko",
            "search_hint_en",
            "permission_layer",
        ):
            assert field in required, f"required field {field!r} missing from contract"
