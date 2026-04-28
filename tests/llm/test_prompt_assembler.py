# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.llm.prompt_assembler (Epic #2152 R2 + R4).

Contract: ``specs/2152-system-prompt-redesign/contracts/prompt-assembler.md``
invariants I-A1..I-A7.
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from kosmos.context.prompt_loader import PromptLoader
from kosmos.llm.prompt_assembler import (
    DYNAMIC_BOUNDARY_MARKER,
    PromptAssembler,
    PromptAssemblyContext,
    PromptAssemblyError,
    SystemPromptManifest,
    system_prompt,
)

# Pydantic v2 wraps ``raise PromptAssemblyError`` from inside a
# ``@model_validator`` into a ``ValidationError`` whose first cause is the
# original exception. Tests assert against either: direct ``PromptAssemblyError``
# from ``PromptAssembler.register`` (raised at the registry level, pre-validator)
# vs ``ValidationError`` from model construction with a bad payload.
_INVARIANT_ERRORS = (PromptAssemblyError, ValidationError)


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "prompts" / "manifest.yaml"


@pytest.fixture
def assembler() -> PromptAssembler:
    return PromptAssembler(static_prefix_source=PromptLoader(manifest_path=MANIFEST))


def _ctx(**overrides: object) -> PromptAssemblyContext:
    base: dict[str, object] = {
        "session_id": "0193f3c9-9eaf-7000-a000-000000000001",
        "session_started_at": datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC),
        "tool_inventory": ("lookup", "resolve_location"),
        "dynamic_inputs": {},
    }
    base.update(overrides)
    return PromptAssemblyContext(**base)  # type: ignore[arg-type]


# I-A1 — static-prefix byte stability across dynamic_inputs ----------------


def test_static_prefix_byte_stable_across_dynamic_inputs(
    assembler: PromptAssembler,
) -> None:
    a = assembler.build(_ctx(dynamic_inputs={}))
    b = assembler.build(_ctx(dynamic_inputs={"ministry_scope": "kma"}))
    c = assembler.build(_ctx(dynamic_inputs={"ministry_scope": "kma,hira"}))
    assert a.static_prefix == b.static_prefix == c.static_prefix


# I-A2 — prefix_hash matches sha256(static_prefix) -------------------------


def test_prefix_hash_matches_static_prefix(assembler: PromptAssembler) -> None:
    manifest = assembler.build(_ctx())
    expected = hashlib.sha256(manifest.static_prefix.encode("utf-8")).hexdigest()
    assert manifest.prefix_hash == expected


# I-A3 — boundary marker terminates the static prefix ----------------------


def test_boundary_marker_present(assembler: PromptAssembler) -> None:
    manifest = assembler.build(_ctx())
    assert manifest.static_prefix.endswith(DYNAMIC_BOUNDARY_MARKER)


# I-A4 — all four XML tag pairs visible in the static prefix --------------


def test_xml_tag_presence(assembler: PromptAssembler) -> None:
    manifest = assembler.build(_ctx())
    for opening, closing in (
        ("<role>", "</role>"),
        ("<core_rules>", "</core_rules>"),
        ("<tool_usage>", "</tool_usage>"),
        ("<output_style>", "</output_style>"),
    ):
        assert opening in manifest.static_prefix
        assert closing in manifest.static_prefix


# I-A5 — None-returning injector is omitted without a stray newline -------


def test_none_return_is_omitted(assembler: PromptAssembler) -> None:
    @system_prompt(assembler, name="quiet_injector")
    def _inj(ctx: PromptAssemblyContext) -> str | None:
        return None

    @system_prompt(assembler, name="loud_injector")
    def _loud(ctx: PromptAssemblyContext) -> str | None:
        return "<loud/>"

    manifest = assembler.build(_ctx())
    # Only the loud injector contributes; suffix is exactly its body.
    assert manifest.dynamic_suffix == "<loud/>"


# I-A6 — build() is idempotent for the same context -----------------------


def test_build_idempotent_for_same_context(assembler: PromptAssembler) -> None:
    ctx = _ctx()
    a = assembler.build(ctx)
    b = assembler.build(ctx)
    assert a.static_prefix == b.static_prefix
    assert a.prefix_hash == b.prefix_hash


# I-A7 — register dup-name handling ---------------------------------------


def test_register_dup_name(assembler: PromptAssembler) -> None:
    def _fn(ctx: PromptAssemblyContext) -> str | None:
        return None

    assembler.register("foo", _fn)
    # Same (name, fn) pair → idempotent re-registration is allowed.
    assembler.register("foo", _fn)
    # Different fn under same name → must raise.
    def _other(ctx: PromptAssemblyContext) -> str | None:
        return "x"

    with pytest.raises(PromptAssemblyError):
        assembler.register("foo", _other)


# Additional sanity tests --------------------------------------------------


def test_decorator_name_must_be_snake_case(assembler: PromptAssembler) -> None:
    with pytest.raises(PromptAssemblyError):
        @system_prompt(assembler, name="BadCaseName")
        def _bad(ctx: PromptAssemblyContext) -> str | None:  # pragma: no cover
            return None


def test_dynamic_inputs_keys_must_be_snake_case() -> None:
    with pytest.raises(_INVARIANT_ERRORS):
        PromptAssemblyContext(
            session_id="0193f3c9-9eaf-7000-a000-000000000001",
            session_started_at=datetime(2026, 4, 28, 12, 0, 0, tzinfo=UTC),
            tool_inventory=(),
            dynamic_inputs={"BadKey": "v"},
        )


def test_manifest_rejects_missing_marker() -> None:
    """SystemPromptManifest validator catches malformed inputs early."""
    with pytest.raises(_INVARIANT_ERRORS):
        SystemPromptManifest(
            static_prefix="<role>x</role>\n",  # no marker
            dynamic_suffix="",
            prefix_hash="0" * 64,
        )


def test_manifest_rejects_hash_drift() -> None:
    """SystemPromptManifest validator catches hash/prefix mismatch."""
    static_prefix = "<role>x</role>" + DYNAMIC_BOUNDARY_MARKER
    with pytest.raises(_INVARIANT_ERRORS):
        SystemPromptManifest(
            static_prefix=static_prefix,
            dynamic_suffix="",
            prefix_hash="f" * 64,  # not actually the sha256 of static_prefix
        )


def test_construction_fails_when_prompt_missing_xml_tag() -> None:
    """Fail-closed — assembler refuses to construct from an incomplete prompt."""

    class _BadLoader:
        def load(self, _id: str) -> str:
            return "<role>only role</role>"  # missing 3 tag pairs

    with pytest.raises(PromptAssemblyError):
        PromptAssembler(static_prefix_source=_BadLoader())  # type: ignore[arg-type]
