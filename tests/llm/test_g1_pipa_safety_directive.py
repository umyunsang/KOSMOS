# SPDX-License-Identifier: Apache-2.0
"""Wave-2 G1 fix — F-gamma-07 PIPA §22 chat-input directive in system_v1.md.

The audit finding (γ9): K-EXAONE asked the citizen to type their RRN
(주민등록번호) and a raw ``session_id`` directly into the chat textarea
instead of dispatching the ``verify`` primitive. PIPA §22 invalidates
that consent path because the chat surface persists through the LLM
context window and the session JSONL transcript.

This test asserts the static prompt carries the canonical
``<pipa_safety>`` directive that forbids the failure mode and routes
sensitive credential collection through the verify modal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kosmos.context.prompt_loader import PromptLoader

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "prompts" / "manifest.yaml"


@pytest.fixture(scope="module")
def system_prompt_text() -> str:
    loader = PromptLoader(manifest_path=MANIFEST)
    return loader.load("system_v1")


def test_pipa_safety_section_present(system_prompt_text: str) -> None:
    """The ``<pipa_safety>`` block exists exactly once and carries the
    PIPA §22 channel-appropriateness directive."""
    assert "<pipa_safety>" in system_prompt_text
    assert "</pipa_safety>" in system_prompt_text
    # The opening tag may also appear inside an inline cross-reference
    # (e.g. ``<primitives>`` lines that point at ``<pipa_safety>``).
    # Count the closing tag — that one is unambiguous as a section
    # boundary marker.
    assert system_prompt_text.count("</pipa_safety>") == 1


@pytest.mark.parametrize(
    "forbidden_input_keyword",
    [
        "주민등록번호",
        "외국인등록번호",
        "운전면허번호",
        "여권번호",
        "인증서 비밀번호",
        "OTP",
        "계좌번호",
        "session_id",
    ],
)
def test_pipa_safety_enumerates_sensitive_input(
    system_prompt_text: str, forbidden_input_keyword: str
) -> None:
    """Every sensitive-input class the audit observed is named explicitly
    so K-EXAONE can pattern-match without relying on its own taxonomy."""
    open_idx = system_prompt_text.index("<pipa_safety>")
    close_idx = system_prompt_text.index("</pipa_safety>")
    body = system_prompt_text[open_idx:close_idx]
    assert forbidden_input_keyword in body, (
        f"<pipa_safety> directive must enumerate {forbidden_input_keyword!r} "
        f"so K-EXAONE never solicits it via chat input"
    )


def test_pipa_safety_routes_to_verify_modal(system_prompt_text: str) -> None:
    """The directive must instruct the LLM to invoke ``verify`` (and *only*
    verify) when sensitive credentials would be needed — i.e. the
    secure-input modal owns the channel, not the chat textarea."""
    open_idx = system_prompt_text.index("<pipa_safety>")
    close_idx = system_prompt_text.index("</pipa_safety>")
    body = system_prompt_text[open_idx:close_idx]
    assert "verify" in body
    assert "modal" in body or "secure-input" in body or "secure modal" in body, (
        "Directive must call out the secure modal path explicitly"
    )


def test_pipa_safety_forbids_chat_input_phrasing(system_prompt_text: str) -> None:
    """The directive must include the explicit failure-mode pattern
    seen in the γ9 reproduction so the LLM has a concrete negative
    example to anchor against."""
    open_idx = system_prompt_text.index("<pipa_safety>")
    close_idx = system_prompt_text.index("</pipa_safety>")
    body = system_prompt_text[open_idx:close_idx]
    # γ9 audit reproduction string:
    # "주민등록번호 앞 6자리 알려주세요"
    assert "주민등록번호" in body
    assert "채팅" in body, "Directive must name 채팅(chat) as the forbidden channel"


def test_verify_primitive_description_warns_about_chat_channel(
    system_prompt_text: str,
) -> None:
    """The ``verify(...)`` primitive description in <tool_usage>
    must point readers at <pipa_safety> so the directive cannot be
    missed by a model that only attends to <primitives>."""
    # The description lives inside <primitives>; verify the cross-ref.
    prims_open = system_prompt_text.index("<primitives>")
    prims_close = system_prompt_text.index("</primitives>")
    prims_body = system_prompt_text[prims_open:prims_close]
    assert "verify" in prims_body
    # The verify line must mention modal/secure-input AND PIPA.
    verify_lines = [ln for ln in prims_body.splitlines() if "verify" in ln]
    assert verify_lines, "<primitives> must contain a verify entry"
    joined = "\n".join(verify_lines)
    assert "modal" in joined or "secure" in joined
    assert "PIPA" in joined or "pipa" in joined
