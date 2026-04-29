# SPDX-License-Identifier: Apache-2.0
"""End-to-end integration tests for ``kosmos.plugins.installer.install_plugin``.

Exercises the 8-phase install flow against a synthetic plugin bundle
and a local file:// catalog. The autouse network-block fixture in
``conftest.py`` guarantees no test reaches a real URL — file:// is the
only protocol exercised.

Tests cover happy path + 4 negative paths from
``contracts/plugin-install.cli.md``:

* exit 0 — install succeeds, registry receives the adapter, BM25 index
  rebuilt, consent receipt written.
* exit 1 — catalog miss.
* exit 2 — bundle SHA mismatch.
* exit 4 — manifest invalid (catalog plugin_id ↔ manifest plugin_id
  drift).
* exit 5 — citizen rejects consent.

A dry-run test confirms phase 6/7 are skipped when ``dry_run=True``.

The synthetic plugin (``demo_plugin``) is built per-test so each test
controls its own manifest/adapter/tarball without touching the real
``~/.kosmos`` filesystem (``KOSMOS_PLUGIN_*`` env vars + monkeypatched
``settings`` paths confine all I/O to ``tmp_path``).
"""

from __future__ import annotations

import hashlib
import json
import tarfile
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from kosmos.plugins.installer import (
    CatalogEntry,
    CatalogIndex,
    CatalogVersion,
    install_plugin,
)
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Synthetic plugin generator
# ---------------------------------------------------------------------------


_ADAPTER_SOURCE = (
    textwrap.dedent(
        """
    from __future__ import annotations
    from typing import Any
    from pydantic import BaseModel, ConfigDict, Field

    from kosmos.tools.models import GovAPITool


    class DemoLookupInput(BaseModel):
        model_config = ConfigDict(frozen=True, extra="forbid")
        query: str = Field(min_length=1, description="Demo query.")


    class DemoLookupOutput(BaseModel):
        model_config = ConfigDict(frozen=True, extra="allow")
        echo: str


    # Epic δ #2295 Path B: auth_level / pipa_class / is_irreversible /
    # dpa_reference / is_personal_data removed — replaced by policy block.
    from datetime import datetime, timezone
    from kosmos.tools.models import AdapterRealDomainPolicy

    _POLICY = AdapterRealDomainPolicy(
        real_classification_url="https://www.data.go.kr/policy",
        real_classification_text="공공데이터포털 이용약관 (조회 전용)",
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
    )

    TOOL = GovAPITool(
        id="plugin.demo_plugin.lookup",
        name_ko="데모 플러그인",
        ministry="OTHER",
        category=["demo"],
        endpoint="https://example.com/demo",
        auth_type="api_key",
        input_schema=DemoLookupInput,
        output_schema=DemoLookupOutput,
        search_hint="데모 demo plugin",
        policy=_POLICY,
        primitive="lookup",
        published_tier_minimum="digital_onepass_level1_aal1",
        nist_aal_hint="AAL1",
    )


    async def adapter(payload: Any) -> dict[str, Any]:
        return {"echo": payload.query}
    """
    ).strip()
    + "\n"
)


def _manifest_dict(*, plugin_id: str = "demo_plugin", tier: str = "live") -> dict[str, Any]:
    # Epic δ #2295 Path B: auth_level / pipa_class removed from adapter block;
    # replaced by policy block with citizen_facing_gate. dpa_reference added
    # as top-level manifest field.
    return {
        "plugin_id": plugin_id,
        "version": "1.0.0",
        "adapter": {
            "tool_id": f"plugin.{plugin_id}.lookup",
            "primitive": "lookup",
            "module_path": "adapter",
            "input_model_ref": "adapter:DemoLookupInput",
            "source_mode": "OPENAPI",
            "published_tier_minimum": "digital_onepass_level1_aal1",
            "nist_aal_hint": "AAL1",
            "auth_type": "api_key",
            "policy": {
                "real_classification_url": "https://www.data.go.kr/policy",
                "real_classification_text": "공공데이터포털 이용약관 (조회 전용)",
                "citizen_facing_gate": "read-only",
                "last_verified": "2026-04-29T00:00:00Z",
            },
        },
        "tier": tier,
        "mock_source_spec": ("https://example.com/spec" if tier == "mock" else None),
        "processes_pii": False,
        "pipa_trustee_acknowledgment": None,
        "dpa_reference": None,
        "slsa_provenance_url": (
            "https://github.com/kosmos-plugin-store/kosmos-plugin-demo/"
            "releases/download/v1.0.0/demo.intoto.jsonl"
        ),
        "otel_attributes": {"kosmos.plugin.id": plugin_id},
        "search_hint_ko": "데모 플러그인 조회",
        "search_hint_en": "demo plugin lookup",
        "permission_layer": 1,
    }


def _build_bundle(
    tmp_path: Path,
    *,
    manifest: dict[str, Any] | None = None,
) -> tuple[Path, str]:
    """Build a synthetic tar.gz bundle and return (path, sha256)."""
    bundle_dir = tmp_path / "_bundle_src"
    bundle_dir.mkdir()
    (bundle_dir / "adapter.py").write_text(_ADAPTER_SOURCE, encoding="utf-8")
    (bundle_dir / "manifest.yaml").write_text(
        yaml.safe_dump(manifest or _manifest_dict(), allow_unicode=True),
        encoding="utf-8",
    )
    bundle = tmp_path / "demo.tar.gz"
    with tarfile.open(bundle, "w:gz") as tf:
        for entry in sorted(bundle_dir.iterdir()):
            tf.add(entry, arcname=entry.name)
    sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
    return bundle, sha


def _build_catalog(tmp_path: Path, *, bundle: Path, sha: str) -> Path:
    bundle_url = f"file://{bundle}"
    provenance = tmp_path / "demo.intoto.jsonl"
    provenance.write_bytes(b"{}")
    catalog = CatalogIndex(
        schema_version="1.0.0",
        generated_iso="2026-04-25T00:00:00Z",
        entries=[
            CatalogEntry(
                name="demo",
                plugin_id="demo_plugin",
                latest_version="1.0.0",
                versions=[
                    CatalogVersion(
                        version="1.0.0",
                        bundle_url=bundle_url,
                        provenance_url=f"file://{provenance}",
                        bundle_sha256=sha,
                        published_iso="2026-04-25T00:00:00Z",
                    )
                ],
                tier="live",
                permission_layer=1,
                processes_pii=False,
                trustee_org_name=None,
                last_published_iso="2026-04-25T00:00:00Z",
            )
        ],
    )
    catalog_file = tmp_path / "index.json"
    catalog_file.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
    return catalog_file


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Confine plugin filesystem state to tmp_path + bypass SLSA."""
    install_root = tmp_path / "install"
    bundle_cache = tmp_path / "cache"
    user_memdir = tmp_path / "memdir" / "user"
    monkeypatch.setattr("kosmos.plugins.installer.settings.plugin_install_root", install_root)
    monkeypatch.setattr("kosmos.plugins.installer.settings.plugin_bundle_cache", bundle_cache)
    monkeypatch.setattr("kosmos.plugins.installer.settings.plugin_slsa_skip", True)
    monkeypatch.setattr(
        "kosmos.plugins.installer.settings.user_memdir_root",
        user_memdir,
    )
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInstallHappyPath:
    def test_install_succeeds(self, tmp_path: Path, isolated_settings: Path) -> None:
        bundle, sha = _build_bundle(tmp_path)
        catalog = _build_catalog(tmp_path, bundle=bundle, sha=sha)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )

        assert result.exit_code == 0, result
        assert result.plugin_id == "demo_plugin"
        assert result.plugin_version == "1.0.0"
        assert result.receipt_id is not None
        assert result.receipt_id.startswith("rcpt-")
        # Plugin is now in the registry + index rebuilt.
        assert "plugin.demo_plugin.lookup" in registry
        # Bundle was extracted to install_root.
        install_dir = isolated_settings / "install" / "demo_plugin"
        assert (install_dir / "manifest.yaml").is_file()
        assert (install_dir / "adapter.py").is_file()
        # Receipt written.
        receipt_files = list(
            (isolated_settings / "memdir" / "user" / "consent").glob("rcpt-*.json")
        )
        assert len(receipt_files) == 1
        receipt_payload = json.loads(receipt_files[0].read_text(encoding="utf-8"))
        assert receipt_payload["plugin_id"] == "demo_plugin"
        assert receipt_payload["slsa_verification"] == "skipped"


class TestInstallNegativePaths:
    def test_catalog_miss(self, tmp_path: Path, isolated_settings: Path) -> None:
        bundle, sha = _build_bundle(tmp_path)
        catalog = _build_catalog(tmp_path, bundle=bundle, sha=sha)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "nonexistent-plugin",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        assert result.exit_code == 1
        assert result.error_kind == "catalog_miss"

    def test_bundle_sha_mismatch(self, tmp_path: Path, isolated_settings: Path) -> None:
        bundle, _ = _build_bundle(tmp_path)
        # Catalog claims a different SHA — bundle on disk now mismatches.
        wrong_sha = "0" * 64
        catalog = _build_catalog(tmp_path, bundle=bundle, sha=wrong_sha)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        assert result.exit_code == 2
        assert result.error_kind == "bundle_sha_mismatch"
        # Bundle retained for forensic inspection.
        cache_dir = isolated_settings / "cache"
        assert any(cache_dir.glob("*.tar.gz"))

    def test_manifest_plugin_id_mismatch(self, tmp_path: Path, isolated_settings: Path) -> None:
        # Build a bundle whose manifest declares a different plugin_id than
        # the catalog entry — installer must reject in phase 4.
        bad_manifest = _manifest_dict(plugin_id="other_id")
        bundle, sha = _build_bundle(tmp_path, manifest=bad_manifest)
        catalog = _build_catalog(tmp_path, bundle=bundle, sha=sha)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        assert result.exit_code == 4
        assert result.error_kind == "manifest_plugin_id_mismatch"

    def test_consent_rejected(self, tmp_path: Path, isolated_settings: Path) -> None:
        bundle, sha = _build_bundle(tmp_path)
        catalog = _build_catalog(tmp_path, bundle=bundle, sha=sha)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            consent_prompt=lambda *_args: False,
        )
        assert result.exit_code == 5
        assert result.error_kind == "consent_rejected"
        # No install dir, no receipt.
        install_dir = isolated_settings / "install" / "demo_plugin"
        assert not install_dir.exists()
        receipt_dir = isolated_settings / "memdir" / "user" / "consent"
        assert not receipt_dir.exists() or not list(receipt_dir.glob("*.json"))


class TestInstallDryRun:
    def test_dry_run_skips_phase_6_and_7(self, tmp_path: Path, isolated_settings: Path) -> None:
        bundle, sha = _build_bundle(tmp_path)
        catalog = _build_catalog(tmp_path, bundle=bundle, sha=sha)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            dry_run=True,
        )
        assert result.exit_code == 0
        assert result.receipt_id is None
        assert "plugin.demo_plugin.lookup" not in registry
        install_dir = isolated_settings / "install" / "demo_plugin"
        assert not install_dir.exists()
        receipt_dir = isolated_settings / "memdir" / "user" / "consent"
        assert not receipt_dir.exists() or not list(receipt_dir.glob("*.json"))
