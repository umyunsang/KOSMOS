# SPDX-License-Identifier: Apache-2.0
"""Shared types + driver for the 50-item plugin validation checklist.

The driver is intentionally minimal — every check is a pure function
of (manifest, plugin_root) returning a structured outcome, and the
workflow YAML iterates a YAML manifest of row → dotted-path mappings
to invoke each check. There is no per-check workflow YAML branch;
adding a new check is two-step: append a row to
``checklist_manifest.yaml``, and write the function the row points
at.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from kosmos.plugins.manifest_schema import PluginManifest


@dataclass(frozen=True, slots=True)
class CheckContext:
    """Inputs every check function receives.

    ``manifest`` is None when the row is exercised against a manifest
    YAML that fails ``PluginManifest.model_validate`` — the Q1
    schema checks themselves run in that case (e.g. Q1-MANIFEST-VALID
    returns failure).

    ``plugin_root`` is the directory holding ``manifest.yaml``,
    ``plugin_<id>/``, and ``tests/`` — the same shape produced by
    ``kosmos plugin init`` and the install-time bundle extractor.
    """

    plugin_root: Path
    manifest: PluginManifest | None
    raw_manifest: dict[str, Any]


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    """Result of one check run."""

    passed: bool
    failure_message_ko: str | None = None
    failure_message_en: str | None = None


def passed() -> CheckOutcome:
    """Helper: pass with no message."""
    return CheckOutcome(passed=True)


def failed(*, ko: str, en: str) -> CheckOutcome:
    """Helper: fail with bilingual messages."""
    return CheckOutcome(passed=False, failure_message_ko=ko, failure_message_en=en)


CheckFn = Callable[[CheckContext], CheckOutcome]


class ChecklistRow(BaseModel):
    """One row in ``checklist_manifest.yaml`` (mirrors data-model.md § 3)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^Q\d{1,2}-[A-Z][A-Z0-9-]*$")
    description_ko: str = Field(min_length=1)
    description_en: str = Field(min_length=1)
    source_rule: str = Field(min_length=1)
    check_type: str = Field(pattern=r"^(static|unit|workflow)$")
    check_implementation: str = Field(
        min_length=1,
        description="Dotted path 'kosmos.plugins.checks.q1_schema:check_pyv2'.",
    )
    failure_message_ko: str = Field(min_length=1)
    failure_message_en: str = Field(min_length=1)


def resolve_check(dotted_path: str) -> CheckFn:
    """Resolve a ``module.path:function_name`` reference to a callable."""
    if ":" not in dotted_path:
        raise ValueError(
            f"check_implementation must be 'module.path:function' (got {dotted_path!r})"
        )
    module_name, fn_name = dotted_path.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, fn_name, None)
    if fn is None or not callable(fn):
        raise AttributeError(
            f"check function {fn_name!r} not found in {module_name!r}"
        )
    return fn  # type: ignore[return-value]


def load_checklist_rows(yaml_path: Path) -> list[ChecklistRow]:
    """Load + validate every row in the canonical YAML manifest."""
    raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError(
            f"checklist YAML must decode to a list (got {type(raw).__name__})"
        )
    return [ChecklistRow.model_validate(r) for r in raw]


def _make_context(plugin_root: Path) -> CheckContext:
    manifest_path = plugin_root / "manifest.yaml"
    raw: dict[str, Any] = {}
    if manifest_path.is_file():
        loaded = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            raw = loaded
    manifest: PluginManifest | None = None
    try:
        manifest = PluginManifest.model_validate(raw) if raw else None
    except Exception:
        manifest = None
    return CheckContext(plugin_root=plugin_root, manifest=manifest, raw_manifest=raw)


def run_all_checks(
    plugin_root: Path,
    *,
    yaml_path: Path,
) -> list[tuple[ChecklistRow, CheckOutcome]]:
    """Run every checklist row against ``plugin_root``.

    Returns row + outcome pairs in YAML order so callers can render a
    deterministic summary report.
    """
    rows = load_checklist_rows(yaml_path)
    ctx = _make_context(plugin_root)
    results: list[tuple[ChecklistRow, CheckOutcome]] = []
    for row in rows:
        try:
            fn = resolve_check(row.check_implementation)
            outcome = fn(ctx)
        except Exception as exc:
            outcome = failed(
                ko=f"{row.id} 검증 중 예외: {exc}",
                en=f"{row.id} threw exception: {exc}",
            )
        results.append((row, outcome))
    return results


__all__ = [
    "CheckContext",
    "CheckFn",
    "CheckOutcome",
    "ChecklistRow",
    "failed",
    "load_checklist_rows",
    "passed",
    "resolve_check",
    "run_all_checks",
]
