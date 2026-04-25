# SPDX-License-Identifier: Apache-2.0
"""End-to-end install timing + OTEL emission verification (T058-T060).

Goals (from spec.md success criteria):

* SC-005 — cold install ≤ 30 seconds wall-clock.
* SC-004 — newly-installed plugin surfaces in BM25 search ≤ 5 seconds.
* SC-007 — every plugin invocation emits a span with kosmos.plugin.id.
* SC-010 — auto-discovery boot cost < 200ms per installed plugin.

The integration test installs the in-tree template staging into a
temporary memdir via install_plugin (file:// catalog + bundle), then
asserts the timing + OTEL contract.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import textwrap
import time
from pathlib import Path
from typing import Any

import pytest

from kosmos.plugins.installer import (
    CatalogEntry,
    CatalogIndex,
    CatalogVersion,
    install_plugin,
)
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Bundle builder — same shape as test_installer_integration.py.
# ---------------------------------------------------------------------------


_ADAPTER_SOURCE = textwrap.dedent(
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
        echo: str = Field(description="Echo of the input.")


    TOOL = GovAPITool(
        id="plugin.timing_demo.lookup",
        name_ko="타이밍 데모 플러그인",
        ministry="OTHER",
        category=["demo"],
        endpoint="https://example.com/timing-demo",
        auth_type="api_key",
        input_schema=DemoLookupInput,
        output_schema=DemoLookupOutput,
        search_hint="타이밍 데모 timing 공공 demo",
        auth_level="AAL1",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        is_personal_data=False,
        primitive="lookup",
        published_tier_minimum="digital_onepass_level1_aal1",
        nist_aal_hint="AAL1",
    )


    async def adapter(payload: Any) -> dict[str, Any]:
        return {"echo": payload.query}
    """
).strip() + "\n"


def _manifest_dict() -> dict[str, Any]:
    return {
        "plugin_id": "timing_demo",
        "version": "1.0.0",
        "adapter": {
            "tool_id": "plugin.timing_demo.lookup",
            "primitive": "lookup",
            "module_path": "adapter",
            "input_model_ref": "adapter:DemoLookupInput",
            "source_mode": "OPENAPI",
            "published_tier_minimum": "digital_onepass_level1_aal1",
            "nist_aal_hint": "AAL1",
            "auth_type": "api_key",
            "auth_level": "AAL1",
            "pipa_class": "non_personal",
        },
        "tier": "live",
        "mock_source_spec": None,
        "processes_pii": False,
        "pipa_trustee_acknowledgment": None,
        "slsa_provenance_url": (
            "https://github.com/kosmos-plugin-store/kosmos-plugin-timing-demo/"
            "releases/download/v1.0.0/timing.intoto.jsonl"
        ),
        "otel_attributes": {"kosmos.plugin.id": "timing_demo"},
        "search_hint_ko": "타이밍 데모 공공 데이터 조회",
        "search_hint_en": "timing demo public data lookup",
        "permission_layer": 1,
    }


def _build_bundle(tmp_path: Path) -> tuple[Path, str, Path]:
    src = tmp_path / "_bundle_src"
    src.mkdir()
    (src / "adapter.py").write_text(_ADAPTER_SOURCE, encoding="utf-8")
    import yaml  # noqa: PLC0415

    (src / "manifest.yaml").write_text(
        yaml.safe_dump(_manifest_dict(), allow_unicode=True),
        encoding="utf-8",
    )
    bundle = tmp_path / "timing.tar.gz"
    with tarfile.open(bundle, "w:gz") as tf:
        for entry in sorted(src.iterdir()):
            tf.add(entry, arcname=entry.name)
    sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
    provenance = tmp_path / "timing.intoto.jsonl"
    provenance.write_bytes(b"{}")
    return bundle, sha, provenance


def _write_catalog(
    tmp_path: Path, bundle: Path, sha: str, provenance: Path
) -> Path:
    catalog = CatalogIndex(
        schema_version="1.0.0",
        generated_iso="2026-04-26T00:00:00Z",
        entries=[
            CatalogEntry(
                name="timing-demo",
                plugin_id="timing_demo",
                latest_version="1.0.0",
                versions=[
                    CatalogVersion(
                        version="1.0.0",
                        bundle_url=f"file://{bundle}",
                        provenance_url=f"file://{provenance}",
                        bundle_sha256=sha,
                        published_iso="2026-04-26T00:00:00Z",
                    )
                ],
                tier="live",
                permission_layer=1,
                processes_pii=False,
                trustee_org_name=None,
                last_published_iso="2026-04-26T00:00:00Z",
            )
        ],
    )
    out = tmp_path / "index.json"
    out.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
    return out


@pytest.fixture
def isolated_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
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
# SC-005 — install ≤ 30 seconds.
# ---------------------------------------------------------------------------


class TestInstallTimingSC005:
    def test_cold_install_under_30_seconds(
        self, tmp_path: Path, isolated_settings: Path
    ) -> None:
        bundle, sha, provenance = _build_bundle(tmp_path)
        catalog = _write_catalog(tmp_path, bundle, sha, provenance)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        start = time.perf_counter()
        result = install_plugin(
            "timing-demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        elapsed = time.perf_counter() - start

        assert result.exit_code == 0, result
        # SC-005 budget: 30s. We measure cold path with file:// I/O so
        # this is a deterministic floor — generous margin protects against
        # CI runner variance.
        assert elapsed < 30.0, f"install took {elapsed:.2f}s (SC-005 budget 30s)"
        # In practice the file:// path completes in well under 1s.
        assert elapsed < 5.0, f"install took {elapsed:.2f}s — unexpectedly slow"


# ---------------------------------------------------------------------------
# SC-004 — BM25 surface ≤ 5 seconds after install.
# ---------------------------------------------------------------------------


class TestBm25SurfaceSC004:
    def test_lookup_surfaces_new_plugin_under_5_seconds(
        self, tmp_path: Path, isolated_settings: Path
    ) -> None:
        bundle, sha, provenance = _build_bundle(tmp_path)
        catalog = _write_catalog(tmp_path, bundle, sha, provenance)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "timing-demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        assert result.exit_code == 0

        # The registry's BM25 index was rebuilt by ToolRegistry.register()
        # during install. Search for the Korean hint and assert the new
        # plugin's tool_id surfaces — within the 5s SC-004 budget.
        start = time.perf_counter()
        results = registry.search("타이밍 데모", max_results=5)
        elapsed = time.perf_counter() - start

        assert elapsed < 5.0, f"BM25 search took {elapsed:.2f}s (SC-004 budget 5s)"
        tool_ids = {r.tool.id for r in results}
        assert "plugin.timing_demo.lookup" in tool_ids


# ---------------------------------------------------------------------------
# SC-007 — kosmos.plugin.id span attribute.
# ---------------------------------------------------------------------------


class TestOtelEmissionSC007:
    def test_install_span_carries_plugin_id(
        self, tmp_path: Path, isolated_settings: Path
    ) -> None:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        bundle, sha, provenance = _build_bundle(tmp_path)
        catalog = _write_catalog(tmp_path, bundle, sha, provenance)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        # Install our own provider for the duration of the install so the
        # in-memory exporter captures the install span. Restore on teardown.
        exporter = InMemorySpanExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        previous = trace.get_tracer_provider()
        trace.set_tracer_provider(provider)
        try:
            result = install_plugin(
                "timing-demo",
                registry=registry,
                executor=executor,
                catalog_url=f"file://{catalog}",
                yes=True,
            )
            provider.force_flush()
        finally:
            trace.set_tracer_provider(previous)

        assert result.exit_code == 0
        spans = list(exporter.get_finished_spans())
        install_spans = [s for s in spans if s.name == "kosmos.plugin.install"]
        assert install_spans, f"no kosmos.plugin.install span emitted; got {[s.name for s in spans]}"
        attrs = dict(install_spans[-1].attributes or {})
        assert attrs.get("kosmos.plugin.id") == "timing_demo"
        assert attrs.get("kosmos.plugin.version") == "1.0.0"
        assert attrs.get("kosmos.plugin.tier") == "live"


# ---------------------------------------------------------------------------
# SC-010 — auto_discover boot cost < 200ms per plugin.
# ---------------------------------------------------------------------------


class TestSlsaSkipL3Refusal:
    """Review eval C6 — Layer-3 plugins cannot use the dev SLSA-skip path."""

    def test_layer_3_with_slsa_skip_returns_exit_3(
        self, tmp_path: Path, isolated_settings: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Build a manifest with permission_layer=3 + is_irreversible=True
        # (Spec 024 V4 requires AAL2 for irreversible).
        manifest = _manifest_dict()
        manifest["permission_layer"] = 3
        manifest["adapter"]["is_irreversible"] = True
        manifest["adapter"]["auth_level"] = "AAL2"

        bundle, sha, provenance = _build_bundle_with_manifest(tmp_path, manifest)
        catalog = _write_catalog(
            tmp_path, bundle, sha, provenance, layer=3, plugin_id=manifest["plugin_id"]
        )
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "timing-demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        assert result.exit_code == 3, f"L3 + SLSA-skip should refuse with exit 3, got {result}"
        assert result.error_kind == "slsa_skip_layer_3_forbidden"

    def test_production_env_refuses_slsa_skip(
        self, tmp_path: Path, isolated_settings: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("KOSMOS_ENV", "production")
        bundle, sha, provenance = _build_bundle(tmp_path)
        catalog = _write_catalog(tmp_path, bundle, sha, provenance)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        result = install_plugin(
            "timing-demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        assert result.exit_code == 3
        assert result.error_kind == "slsa_skip_in_production"


def _build_bundle_with_manifest(
    tmp_path: Path, manifest: dict[str, Any]
) -> tuple[Path, str, Path]:
    """Build a tarball with a custom manifest (used for L3 + irreversible test)."""
    src = tmp_path / "_bundle_src_l3"
    src.mkdir()
    (src / "adapter.py").write_text(_ADAPTER_SOURCE, encoding="utf-8")
    import yaml as _yaml

    (src / "manifest.yaml").write_text(
        _yaml.safe_dump(manifest, allow_unicode=True), encoding="utf-8"
    )
    bundle = tmp_path / "l3_demo.tar.gz"
    with tarfile.open(bundle, "w:gz") as tf:
        for entry in sorted(src.iterdir()):
            tf.add(entry, arcname=entry.name)
    sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
    provenance = tmp_path / "l3_demo.intoto.jsonl"
    provenance.write_bytes(b"{}")
    return bundle, sha, provenance


def _write_catalog(
    tmp_path: Path,
    bundle: Path,
    sha: str,
    provenance: Path,
    *,
    layer: int = 1,
    plugin_id: str = "timing_demo",
) -> Path:
    """Write a catalog index with overridable layer + plugin_id (review eval C6)."""
    catalog = CatalogIndex(
        schema_version="1.0.0",
        generated_iso="2026-04-26T00:00:00Z",
        entries=[
            CatalogEntry(
                name="timing-demo",
                plugin_id=plugin_id,
                latest_version="1.0.0",
                versions=[
                    CatalogVersion(
                        version="1.0.0",
                        bundle_url=f"file://{bundle}",
                        provenance_url=f"file://{provenance}",
                        bundle_sha256=sha,
                        published_iso="2026-04-26T00:00:00Z",
                    )
                ],
                tier="live",
                permission_layer=layer,
                processes_pii=False,
                trustee_org_name=None,
                last_published_iso="2026-04-26T00:00:00Z",
            )
        ],
    )
    out = tmp_path / "index.json"
    out.write_text(catalog.model_dump_json(indent=2), encoding="utf-8")
    return out


class TestAutoDiscoverBootCostSC010:
    def test_auto_discover_under_200ms_per_plugin(
        self, tmp_path: Path, isolated_settings: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from kosmos.plugins.registry import auto_discover

        bundle, sha, provenance = _build_bundle(tmp_path)
        catalog = _write_catalog(tmp_path, bundle, sha, provenance)
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        # Install once so the install_root contains a plugin.
        install_result = install_plugin(
            "timing-demo",
            registry=registry,
            executor=executor,
            catalog_url=f"file://{catalog}",
            yes=True,
        )
        assert install_result.exit_code == 0

        # Now simulate a boot: build a fresh registry and call auto_discover
        # against the install_root. This is the cost per plugin on every TUI
        # cold start.
        boot_registry = ToolRegistry()
        boot_executor = ToolExecutor(boot_registry)
        start = time.perf_counter()
        registered = auto_discover(
            registry=boot_registry,
            executor=boot_executor,
            install_root=isolated_settings / "install",
        )
        elapsed = time.perf_counter() - start

        assert len(registered) == 1
        per_plugin_ms = (elapsed * 1000) / max(len(registered), 1)
        assert per_plugin_ms < 200.0, (
            f"auto_discover took {per_plugin_ms:.1f}ms/plugin (SC-010 budget 200ms)"
        )
