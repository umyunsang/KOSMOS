# SPDX-License-Identifier: Apache-2.0
"""Tests for the XML-tag structural invariant of prompts/system_v1.md (SC-2).

Epic #2152 R1 — the static prompt MUST present four XML-tagged sections:
``<role>``, ``<core_rules>``, ``<tool_usage>``, ``<output_style>``. This test
asserts presence at the PromptLoader boundary so any future rewrite that
loses a section fails CI before reaching production.

Contract: ``specs/2152-system-prompt-redesign/contracts/prompt-assembler.md``
invariant I-A4. Spec: SC-2.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from kosmos.context.prompt_loader import PromptLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "prompts" / "manifest.yaml"

REQUIRED_TAG_PAIRS = [
    ("<role>", "</role>"),
    ("<core_rules>", "</core_rules>"),
    ("<tool_usage>", "</tool_usage>"),
    ("<output_style>", "</output_style>"),
]


@pytest.fixture(scope="module")
def system_prompt_text() -> str:
    loader = PromptLoader(manifest_path=MANIFEST)
    return loader.load("system_v1")


@pytest.mark.parametrize("opening, closing", REQUIRED_TAG_PAIRS)
def test_required_xml_tag_pair_present(system_prompt_text: str, opening: str, closing: str) -> None:
    """Each of the four required XML tags appears exactly once, in order."""
    assert opening in system_prompt_text, (
        f"system_v1.md missing required opening tag {opening!r} (SC-2)"
    )
    assert closing in system_prompt_text, (
        f"system_v1.md missing required closing tag {closing!r} (SC-2)"
    )
    assert system_prompt_text.count(opening) == 1, (
        f"system_v1.md has duplicate {opening!r} — must appear exactly once"
    )
    assert system_prompt_text.index(opening) < system_prompt_text.index(closing), (
        f"system_v1.md has {closing!r} before {opening!r} — order violation"
    )


def test_xml_tags_appear_in_canonical_order(system_prompt_text: str) -> None:
    """Tags appear in the canonical order role → core_rules → tool_usage → output_style."""
    indices = [system_prompt_text.index(opening) for opening, _ in REQUIRED_TAG_PAIRS]
    assert indices == sorted(indices), (
        "XML sections out of canonical order (role, core_rules, tool_usage, output_style)"
    )


def test_template_placeholders_are_documented(system_prompt_text: str) -> None:
    """The ``{platform_name}`` placeholder is a legitimate runtime override hook
    consumed by ``SystemPromptAssembler._format_if_templated``. Verify it lives
    inside ``<role>`` (the only section where it makes semantic sense) so future
    rewrites do not accidentally drop the override path."""
    role_open = system_prompt_text.index("<role>")
    role_close = system_prompt_text.index("</role>")
    role_body = system_prompt_text[role_open:role_close]
    # platform_name placeholder MUST live inside <role>; nowhere else
    assert "{platform_name}" in role_body, (
        "{platform_name} override hook must remain inside <role> — "
        "see SystemPromptAssembler._format_if_templated"
    )
    other_sections = system_prompt_text[role_close:]
    assert "{platform_name}" not in other_sections, (
        "{platform_name} placeholder must appear only inside <role>"
    )


def test_korean_role_prose_present(system_prompt_text: str) -> None:
    """The role section frames the assistant as a Korean public-services
    intermediary — verify Korean anchor words are present."""
    role_open = system_prompt_text.index("<role>")
    role_close = system_prompt_text.index("</role>")
    role_body = system_prompt_text[role_open:role_close]
    assert "공공" in role_body and "시민" in role_body, (
        "role section must frame the assistant as a Korean public-services intermediary"
    )
