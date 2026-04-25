# SPDX-License-Identifier: Apache-2.0
"""Plugin adapter registration + auto-discovery.

Wires a validated :class:`~kosmos.plugins.manifest_schema.PluginManifest`
into the existing Spec 022 :class:`~kosmos.tools.registry.ToolRegistry`
+ Spec 1634 :class:`~kosmos.tools.executor.ToolExecutor`. The plugin
module convention mirrors the in-tree adapter contract:

* ``manifest.adapter.module_path`` resolves to a Python module that
  exports two symbols.
* ``TOOL: GovAPITool`` — the registry-bound tool definition. Its
  ``id`` MUST equal ``manifest.adapter.tool_id``; the V1-V6 invariant
  chain on ``GovAPITool`` is therefore re-enforced at
  ``ToolRegistry.register()`` time.
* ``adapter`` (or ``ADAPTER``) — an async callable accepting the
  validated input model instance and returning a dict matching the
  output schema.

Every successful registration emits an OTEL span
``kosmos.plugin.install`` carrying the ``kosmos.plugin.id`` attribute
(Spec 021 KOSMOS extension; Migration tree § L1-A A7). A failure
emits the same span with ``status=ERROR`` so the local Langfuse can
graph install attempts even when nothing lands in the registry.

Auto-discovery walks ``KOSMOS_PLUGIN_INSTALL_ROOT`` (Spec 035
sibling) and registers every manifest it finds in lexicographic order
of ``plugin_id`` (deterministic boot ordering — needed for prompt
cache stability per Spec 026).
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from kosmos.plugins.exceptions import (
    ManifestValidationError,
    PluginRegistrationError,
)
from kosmos.plugins.manifest_schema import PluginManifest
from kosmos.settings import settings
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)


# Plugin module symbol contract — see module docstring.
_TOOL_SYMBOL = "TOOL"
_ADAPTER_SYMBOL_PRIMARY = "adapter"
_ADAPTER_SYMBOL_SECONDARY = "ADAPTER"

AdapterFn = Callable[[Any], Awaitable[dict[str, Any]]]
"""Async adapter function signature (mirrors ``ToolExecutor.AdapterFn``)."""


def _import_adapter_module(module_path: str, *, plugin_root: Path | None) -> ModuleType:
    """Import the plugin's adapter module.

    Two resolution strategies:

    1. ``plugin_root`` provided → load from
       ``<plugin_root>/<module_path-leaf>.py`` via
       :func:`importlib.util.spec_from_file_location` so plugins
       installed under ``~/.kosmos/memdir/user/plugins/<id>/`` work
       without polluting ``sys.path``.
    2. ``plugin_root`` is ``None`` → use the standard
       :func:`importlib.import_module` resolution; the contributor's
       package must already be on the import path (e.g. installed via
       ``pip install -e`` for local development).
    """

    if plugin_root is not None:
        # Resolve dotted `module_path` (e.g. "plugin_my_plugin.adapter")
        # to a filesystem path under `plugin_root`. Codex review: the
        # earlier `leaf = module_path.split(".")[-1]` only probed the
        # final segment, which broke installed bundles that ship the
        # adapter inside a Python package (the default scaffold layout
        # `plugin_<id>/adapter.py`). Convert each `.` to a path
        # separator and probe the full relative location.
        relative_path = Path(*module_path.split("."))
        candidate = plugin_root / relative_path.with_suffix(".py")
        if not candidate.is_file():
            raise PluginRegistrationError(
                f"plugin adapter module not found at {candidate} "
                f"(module_path={module_path!r}, plugin_root={plugin_root})"
            )
        spec_name = f"_kosmos_plugin_{plugin_root.name}_{module_path.replace('.', '_')}"
        spec = importlib.util.spec_from_file_location(spec_name, candidate)
        if spec is None or spec.loader is None:
            raise PluginRegistrationError(f"failed to build import spec for {candidate}")
        module = importlib.util.module_from_spec(spec)
        # H2 (review eval): pop any stale entry from a previous failed
        # install so a re-install gets a fresh module rather than the
        # leaked one. Also stamp the spec_name BEFORE exec so the
        # plugin's own intra-package references resolve.
        sys.modules.pop(spec_name, None)
        sys.modules[spec_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            sys.modules.pop(spec_name, None)
            raise PluginRegistrationError(f"plugin adapter module failed to import: {exc}") from exc
        # NB: post-exec failures (resolve_tool_and_adapter, registry.register)
        # also pop this entry — see register_plugin_adapter's except blocks.
        return module

    try:
        return importlib.import_module(module_path)
    except ImportError as exc:
        raise PluginRegistrationError(
            f"could not import adapter module {module_path!r}: {exc}"
        ) from exc


def _resolve_tool_and_adapter(
    module: ModuleType, *, expected_tool_id: str
) -> tuple[GovAPITool, AdapterFn]:
    tool = getattr(module, _TOOL_SYMBOL, None)
    if tool is None:
        raise PluginRegistrationError(
            f"plugin module {module.__name__!r} missing required "
            f"symbol {_TOOL_SYMBOL!r} (expected GovAPITool instance)"
        )
    if not isinstance(tool, GovAPITool):
        raise PluginRegistrationError(
            f"plugin module {module.__name__!r}.{_TOOL_SYMBOL} must be a "
            f"GovAPITool instance; got {type(tool).__name__}"
        )
    if tool.id != expected_tool_id:
        raise PluginRegistrationError(
            f"plugin tool.id {tool.id!r} does not match manifest "
            f"adapter.tool_id {expected_tool_id!r}"
        )

    fn = getattr(module, _ADAPTER_SYMBOL_PRIMARY, None) or getattr(
        module, _ADAPTER_SYMBOL_SECONDARY, None
    )
    if fn is None or not callable(fn):
        raise PluginRegistrationError(
            f"plugin module {module.__name__!r} missing async callable "
            f"{_ADAPTER_SYMBOL_PRIMARY!r} or {_ADAPTER_SYMBOL_SECONDARY!r}"
        )
    return tool, fn


def _rebuild_bm25_index_for(registry: ToolRegistry, tool_id: str) -> None:
    """Force-rebuild the registry's retriever for a specific plugin adapter.

    The existing :meth:`ToolRegistry.register` already rebuilds the BM25
    corpus over every registered tool — this helper exists as the spec-named
    seam (data-model.md § Entity relationships) so callers (and tests) can
    request a targeted re-index without touching the private retriever.

    Implementation note: BM25 over the in-process corpus is fast; we
    intentionally do not maintain incremental ``add_or_update`` state.
    The helper just verifies the tool is present then re-runs the same
    full rebuild path the registry uses internally.
    """
    if tool_id not in registry:
        raise PluginRegistrationError(
            f"cannot rebuild BM25 index for unregistered tool {tool_id!r}"
        )
    corpus = {tid: t.search_hint for tid, t in registry._tools.items()}  # noqa: SLF001
    registry._retriever.rebuild(corpus)  # noqa: SLF001
    logger.debug("Rebuilt BM25 index for plugin tool %s", tool_id)


def register_plugin_adapter(
    manifest: PluginManifest,
    *,
    registry: ToolRegistry,
    executor: ToolExecutor,
    plugin_root: Path | None = None,
    slsa_verification: str = "passed",
) -> GovAPITool:
    """Register a plugin's adapter with the running registry + executor.

    The manifest must already be a validated :class:`PluginManifest`
    instance (callers are expected to round-trip through
    ``PluginManifest.model_validate``). All five cross-field invariants
    have therefore already run — this function focuses on *plumbing*:
    importing the adapter module, binding the executor, calling
    ``ToolRegistry.register``, emitting OTEL.

    Args:
        manifest: Validated plugin manifest.
        registry: The central :class:`ToolRegistry`.
        executor: The :class:`ToolExecutor` to bind the async adapter to.
        plugin_root: Optional filesystem path to load ``adapter.py`` from
            (used by :func:`auto_discover` for installed bundles). When
            ``None``, ``manifest.adapter.module_path`` is resolved via
            the standard import system.

    Returns:
        The registered :class:`GovAPITool`.

    Raises:
        PluginRegistrationError: If the adapter module is missing
            required symbols, the tool.id does not match the manifest
            namespace, or registration triggers a Spec 022/024/025/031
            invariant violation. The OTEL span is closed with
            ``StatusCode.ERROR`` before the exception propagates.
    """
    if not isinstance(manifest, PluginManifest):
        raise PluginRegistrationError(
            "register_plugin_adapter requires a validated PluginManifest "
            f"instance; got {type(manifest).__name__}"
        )

    # C2 backstop (review eval): the five PluginManifest cross-field
    # validators run at __init__ but are skipped if the caller bypassed
    # validation via model_construct(). Mirror Spec 025's V6 pattern by
    # re-running the invariant checks directly against field values, so a
    # tampered manifest cannot reach the registry. We re-validate the
    # whole instance — this catches drift on any of the five validators
    # without enumerating them here.
    try:
        PluginManifest.model_validate(manifest.model_dump())
    except Exception as exc:  # noqa: BLE001 — Pydantic ValidationError fan-out.
        raise PluginRegistrationError(
            "PluginManifest invariant violation at register_plugin_adapter "
            "(model_construct bypass detected): "
            f"{exc}"
        ) from exc

    plugin_id = manifest.plugin_id
    expected_tool_id = manifest.adapter.tool_id

    with _tracer.start_as_current_span("kosmos.plugin.install") as span:
        span.set_attribute("kosmos.plugin.id", plugin_id)
        span.set_attribute("kosmos.plugin.version", manifest.version)
        span.set_attribute("kosmos.plugin.tier", manifest.tier)
        span.set_attribute("kosmos.plugin.tool_id", expected_tool_id)
        span.set_attribute("kosmos.plugin.permission_layer", manifest.permission_layer)
        # C6 (review eval): emit the SLSA verification state on every
        # install so OTEL collectors can graph skip-frequency + alert
        # on production environments seeing 'skipped'.
        span.set_attribute("kosmos.plugin.slsa_verification", slsa_verification)

        module = None
        try:
            module = _import_adapter_module(manifest.adapter.module_path, plugin_root=plugin_root)
            tool, adapter_fn = _resolve_tool_and_adapter(module, expected_tool_id=expected_tool_id)
            registry.register(tool)
            executor.register_adapter(tool.id, adapter_fn)
        except PluginRegistrationError:
            # H2 (review eval): a post-exec failure (symbol resolution /
            # tool.id mismatch / V1-V6 invariant) leaves the module in
            # sys.modules. Pop it so a retry isn't poisoned.
            if module is not None and module.__name__ in sys.modules:
                sys.modules.pop(module.__name__, None)
            span.set_status(Status(StatusCode.ERROR))
            raise
        except Exception as exc:
            if module is not None and module.__name__ in sys.modules:
                sys.modules.pop(module.__name__, None)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise PluginRegistrationError(
                f"plugin {plugin_id!r} registration failed: {exc}"
            ) from exc

        logger.info(
            "Registered plugin %s v%s (tier=%s, tool_id=%s)",
            plugin_id,
            manifest.version,
            manifest.tier,
            expected_tool_id,
        )
        return tool


def _load_manifest_from_yaml(path: Path) -> PluginManifest:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ManifestValidationError(f"could not read manifest at {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestValidationError(
            f"manifest at {path} must decode to a mapping; got {type(raw).__name__}"
        )
    try:
        return PluginManifest.model_validate(raw)
    except Exception as exc:
        raise ManifestValidationError(f"manifest at {path} failed validation: {exc}") from exc


def auto_discover(
    *,
    registry: ToolRegistry,
    executor: ToolExecutor,
    install_root: Path | None = None,
    strict: bool = False,
) -> list[GovAPITool]:
    """Walk the install root and register every plugin found.

    Iterates ``<install_root>/<plugin_id>/manifest.yaml`` in
    lexicographic ``plugin_id`` order so registration is deterministic
    boot-to-boot (prompt-cache stability per Spec 026).

    Args:
        registry: Central :class:`ToolRegistry`.
        executor: :class:`ToolExecutor` for adapter binding.
        install_root: Override the configured install root (tests).
        strict: When True, raise on the first registration failure.
            When False (default), log + skip failed plugins so a single
            broken bundle does not block boot. The skipped failure is
            still surfaced via OTEL ``kosmos.plugin.install`` span with
            ``status=ERROR``.

    Returns:
        List of registered :class:`GovAPITool` instances in
        registration order.
    """
    root = install_root or settings.plugin_install_root
    registered: list[GovAPITool] = []

    if not root.is_dir():
        logger.debug("plugin install root %s missing — skipping auto-discover", root)
        return registered

    for plugin_dir in sorted(root.iterdir(), key=lambda p: p.name):
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "manifest.yaml"
        if not manifest_path.is_file():
            logger.debug("no manifest.yaml in %s — skipping", plugin_dir)
            continue

        try:
            manifest = _load_manifest_from_yaml(manifest_path)
            tool = register_plugin_adapter(
                manifest,
                registry=registry,
                executor=executor,
                plugin_root=plugin_dir,
            )
            registered.append(tool)
        except (ManifestValidationError, PluginRegistrationError) as exc:
            logger.error("plugin auto-discover failed for %s: %s", plugin_dir.name, exc)
            if strict:
                raise

    return registered


__all__ = [
    "auto_discover",
    "register_plugin_adapter",
    "_rebuild_bm25_index_for",
]
