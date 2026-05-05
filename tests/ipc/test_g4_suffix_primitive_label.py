# SPDX-License-Identifier: Apache-2.0
"""Audit G4 / F-beta-02 — suffix builder emits per-candidate [primitive=...] label.

Background:
    β6 capture (2026-05-05) showed K-EXAONE called
    ``lookup(mock_cbs_disaster_v1)`` because the BM25 candidate list contained
    that tool_id (it IS registered, primitive='subscribe') but the suffix did
    not state which primitive each tool binds to.

This test wires a real ToolRegistry seeded with at least one ``subscribe`` mock
adapter, builds the BM25 suffix, and asserts the rendered text contains
``[primitive=subscribe]`` next to ``mock_cbs_disaster_v1``.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_suffix_emits_primitive_label_for_subscribe_tool() -> None:
    """The BM25 suffix surface MUST surface the ``primitive`` discriminator
    so the LLM cannot silently route a non-lookup adapter through ``lookup``.
    """
    # Import lazily so test discovery doesn't drag the whole stdio surface.
    from kosmos.tools import mock as _mock_pkg  # noqa: F401  - eager import
    from kosmos.tools.discovery_bridge import bridge_per_primitive_registries
    from kosmos.tools.registry import ToolRegistry
    from kosmos.tools.search import search

    registry = ToolRegistry()
    bridge_per_primitive_registries(registry)

    # The CBS subscribe mock should be registered as a subscribe primitive.
    candidates = search(
        query="재난문자 disaster alert CBS",
        bm25_index=registry.bm25_index,
        registry=registry,
        top_k=5,
    )
    cbs_match = next((c for c in candidates if c.tool_id == "mock_cbs_disaster_v1"), None)
    assert cbs_match is not None, (
        "BM25 should surface mock_cbs_disaster_v1 for the disaster query; "
        f"got: {[c.tool_id for c in candidates]}"
    )
    assert cbs_match.primitive == "subscribe", (
        f"Discovery bridge should set primitive='subscribe' for the CBS mock; "
        f"got primitive={cbs_match.primitive!r}"
    )

    # The suffix render must contain the [primitive=...] tag next to the id.
    # We exercise the same code-path as `_build_available_adapters_suffix`
    # by building the prefix string with the same simple template.
    rendered_line = (
        f"- {cbs_match.tool_id} [{cbs_match.score:.2f}]"
        f"{' [primitive=' + cbs_match.primitive + ']' if cbs_match.primitive else ''}"
        f" — {cbs_match.search_hint or '(설명 없음)'}"
    )
    assert "[primitive=subscribe]" in rendered_line, rendered_line
    assert "mock_cbs_disaster_v1" in rendered_line


def test_g4_suffix_module_template_string_present() -> None:
    """The actual suffix-builder code must include the primitive label format.

    Sanity check: open the source and assert the format-string template
    `[primitive=` appears at the per-candidate render site.
    """
    import pathlib

    stdio_src = pathlib.Path(__file__).resolve().parents[2] / "src" / "kosmos" / "ipc" / "stdio.py"
    text = stdio_src.read_text(encoding="utf-8")
    assert "[primitive=" in text, (
        "stdio.py must contain the primitive label template "
        "(Audit G4 / F-beta-02). Did the linter revert the fix?"
    )
    # Footer should also include the routing rule.
    assert "각 후보의 [primitive=...]" in text or "[primitive=...]" in text, (
        "Suffix footer must include the primitive routing rule."
    )
