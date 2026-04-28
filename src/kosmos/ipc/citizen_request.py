# SPDX-License-Identifier: Apache-2.0
"""Citizen utterance envelope (Epic #2152 R3).

Wraps citizen-pasted text in ``<citizen_request>...</citizen_request>`` XML tags
at the chat-request boundary so any instruction-shaped citizen content cannot be
mistaken for system instructions.

Contract: ``specs/2152-system-prompt-redesign/contracts/chat-request-envelope.md``
invariants I-C3, I-C4, I-C6.
"""

from __future__ import annotations


_OPEN_TAG = "<citizen_request>\n"
_CLOSE_TAG = "\n</citizen_request>"


def wrap_citizen_request(text: str) -> str:
    """Return ``text`` wrapped in ``<citizen_request>`` XML tags.

    Empty input returns the empty string unchanged so the no-op path stays
    byte-stable (FR-015 spirit). The function is pure: no I/O, no logging,
    no whitespace normalisation. Whatever citizen bytes come in are preserved
    verbatim between the tags.

    Caller obligation: invoke only on messages whose role is ``"user"``. The
    wrap is structural — it gives the model an unambiguous boundary between
    citizen-pasted content and the system instruction surface (Anthropic
    prompt-engineering guide §8.2 XML tags).

    Args:
        text: The citizen-supplied user message body.

    Returns:
        ``text`` unchanged when empty; otherwise the wrapped string.
    """
    if not text:
        return text
    return f"{_OPEN_TAG}{text}{_CLOSE_TAG}"
