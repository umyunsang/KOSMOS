# SPDX-License-Identifier: Apache-2.0
"""Micro-compact engine for KOSMOS Context Assembly layer.

MicroCompact performs *surgical*, per-turn token reclamation without
discarding any conversation turns.  It applies three strategies in order:

1. **Tool result truncation** — tool-result messages whose content exceeds
   ``config.micro_compact_budget`` are replaced with a truncated summary.
2. **Repeated content dedup** — when assistant messages echo information
   already present in an older assistant message, the duplicate is stripped
   to a short marker.
3. **System message dedup** — duplicate system instructions injected across
   multiple turns are collapsed to the first occurrence only.

The ``preserve_recent_turns`` guard ensures the N most recent human+assistant
exchange pairs are never touched.  Turn boundaries are counted as pairs of
consecutive (user, assistant) messages.

Reference: Claude Code ``microCompact.ts`` — content-clear path (cold-cache
variant).  KOSMOS v1 uses only the simpler content-clear approach.
"""

from __future__ import annotations

import logging
from typing import Final

from kosmos.context.compact_models import CompactionConfig, CompactionResult
from kosmos.engine.tokens import estimate_tokens
from kosmos.llm.models import ChatMessage

logger = logging.getLogger(__name__)

# Marker inserted in place of truncated tool-result content (mirrors
# Claude Code's TIME_BASED_MC_CLEARED_MESSAGE constant).
_TOOL_RESULT_CLEARED: Final[str] = "[Tool result truncated by micro-compact]"

# Marker used when an assistant turn is deduplicated.
_ASSISTANT_DEDUP_MARKER: Final[str] = "[Assistant message deduplicated — see earlier turn]"

# Minimum character overlap fraction to consider two assistant messages
# as containing redundant information.
_DEDUP_SIMILARITY_THRESHOLD: Final[float] = 0.75

# Minimum content length (chars) before dedup is attempted.  Very short
# assistant messages (e.g. "OK", "Done") are never deduplicated.
_DEDUP_MIN_LENGTH: Final[int] = 80


def _count_total_tokens(messages: list[ChatMessage]) -> int:
    """Estimate total token count across all messages."""
    total = 0
    for msg in messages:
        if msg.content:
            total += estimate_tokens(msg.content)
        if msg.tool_calls:
            for tc in msg.tool_calls:
                total += estimate_tokens(tc.function.arguments)
    return total


def _protected_slice_start(messages: list[ChatMessage], preserve_turns: int) -> int:
    """Return the index from which the protected (recent) slice begins.

    We walk from the end of the list, counting completed user+assistant
    turn pairs.  Once ``preserve_turns`` pairs have been counted, the next
    index is returned as the protection boundary.  Messages at or beyond
    this index must not be modified.

    Args:
        messages: Full conversation history in chronological order.
        preserve_turns: Number of tail turn-pairs to protect.

    Returns:
        Index i such that messages[i:] must never be compacted.
        Returns 0 when all messages are protected.
    """
    if preserve_turns <= 0:
        return len(messages)

    pairs_found = 0
    idx = len(messages) - 1
    while idx >= 0:
        role = messages[idx].role
        # A completed turn pair ends at an assistant message preceded by user.
        if role == "assistant" and idx > 0 and messages[idx - 1].role == "user":
            pairs_found += 1
            if pairs_found >= preserve_turns:
                # Protect from the user message of this pair onwards.
                return idx - 1
            idx -= 2
        else:
            idx -= 1

    # All messages fall within the protected window.
    return 0


def _truncate_tool_result(msg: ChatMessage, budget: int) -> ChatMessage:
    """Return a copy of *msg* with content truncated to within *budget* tokens.

    Only messages with ``role='tool'`` are truncated.  The result is a new
    frozen ``ChatMessage`` with the same ``tool_call_id`` and a truncated
    content string.

    If the message content is already within budget, the original is returned
    unchanged (same object, no copy overhead).
    """
    if msg.role != "tool" or not msg.content:
        return msg

    current_tokens = estimate_tokens(msg.content)
    if current_tokens <= budget:
        return msg

    # Keep as many characters as the budget allows.  Use 4 chars/token as a
    # conservative English estimate (tokens.py uses the same heuristic for
    # non-Korean text).
    char_budget = budget * 4
    truncated_content = msg.content[:char_budget]
    suffix = f"\n{_TOOL_RESULT_CLEARED}"
    truncated_content = truncated_content[: char_budget - len(suffix)] + suffix

    logger.debug(
        "micro_compact: truncated tool-result (call_id=%s) from %d to %d tokens",
        msg.tool_call_id,
        current_tokens,
        estimate_tokens(truncated_content),
    )

    return ChatMessage(
        role="tool",
        content=truncated_content,
        tool_call_id=msg.tool_call_id,
    )


def _is_similar_content(a: str, b: str) -> bool:
    """Return True when *b* is largely redundant with respect to *a*.

    Uses a simple word-overlap heuristic: if more than
    ``_DEDUP_SIMILARITY_THRESHOLD`` of the words in *b* also appear in *a*,
    the content is considered a duplicate.

    This is intentionally conservative — only obvious verbatim repetition is
    flagged.  Semantic similarity requires an LLM and is out of scope for v1.
    """
    if len(b) < _DEDUP_MIN_LENGTH:
        return False
    words_a = set(a.lower().split())
    words_b = b.lower().split()
    if not words_b:
        return False
    overlap = sum(1 for w in words_b if w in words_a) / len(words_b)
    return overlap >= _DEDUP_SIMILARITY_THRESHOLD


def _dedup_assistant_messages(
    messages: list[ChatMessage],
    protect_from: int,
) -> tuple[list[ChatMessage], int]:
    """Replace redundant assistant messages (before *protect_from*) with a marker.

    Iterates forward.  For each assistant message, checks whether its content
    is substantially similar to any *later* assistant message in the protected
    window.  If so, the older message is replaced with ``_ASSISTANT_DEDUP_MARKER``.

    Args:
        messages: Full conversation list (will not be mutated).
        protect_from: Index of the first protected message.

    Returns:
        Tuple of (new message list, number of messages deduplicated).
    """
    # Build a combined reference corpus from the protected assistant messages.
    reference_corpus = " ".join(
        msg.content for msg in messages[protect_from:] if msg.role == "assistant" and msg.content
    )

    if not reference_corpus:
        return messages, 0

    result: list[ChatMessage] = []
    dedup_count = 0

    for i, msg in enumerate(messages):
        if i >= protect_from or msg.role != "assistant" or not msg.content:
            result.append(msg)
            continue

        if _is_similar_content(reference_corpus, msg.content):
            dedup_count += 1
            logger.debug("micro_compact: deduped assistant message at index %d", i)
            result.append(ChatMessage(role="assistant", content=_ASSISTANT_DEDUP_MARKER))
        else:
            result.append(msg)

    return result, dedup_count


def _dedup_system_messages(
    messages: list[ChatMessage],
    protect_from: int,
) -> tuple[list[ChatMessage], int]:
    """Collapse duplicate system messages, keeping only the first occurrence.

    In KOSMOS the system message is the very first element in the list.
    Per-turn attachment messages injected as user-role messages are *not*
    affected here.  Only additional ``role='system'`` messages that may have
    been injected as context refreshers are deduplicated.

    Args:
        messages: Full conversation list (will not be mutated).
        protect_from: Index of the first protected message.

    Returns:
        Tuple of (new message list, number of system messages removed).
    """
    seen_system_contents: set[str] = set()
    result: list[ChatMessage] = []
    removed = 0

    for i, msg in enumerate(messages):
        if msg.role != "system":
            result.append(msg)
            continue

        content = msg.content or ""
        if content not in seen_system_contents:
            seen_system_contents.add(content)
            result.append(msg)
        elif i < protect_from:
            # Duplicate system message outside protected window — drop it.
            removed += 1
            logger.debug("micro_compact: removed duplicate system message at index %d", i)
        else:
            # Even in the protected window, keep the message.
            result.append(msg)

    return result, removed


def micro_compact(
    messages: list[ChatMessage],
    config: CompactionConfig | None = None,
) -> tuple[list[ChatMessage], CompactionResult]:
    """Apply micro-compaction to *messages* and return the reduced list.

    Strategies applied in order:
    1. Tool result truncation (all tool-result messages outside protected zone).
    2. Assistant message deduplication.
    3. System message deduplication.

    The last ``config.preserve_recent_turns`` turn-pairs are never modified.

    Args:
        messages: Conversation history (chronological order, immutable input).
        config: Compaction configuration; defaults to ``CompactionConfig()``.

    Returns:
        Tuple of (compacted message list, CompactionResult).
    """
    cfg = config or CompactionConfig()

    if not messages:
        return messages, CompactionResult(
            original_tokens=0,
            compacted_tokens=0,
            tokens_saved=0,
            strategy_used="micro",
            turns_removed=0,
        )

    original_tokens = _count_total_tokens(messages)
    protect_from = _protected_slice_start(messages, cfg.preserve_recent_turns)

    logger.debug(
        "micro_compact: %d messages, protect_from=%d, original_tokens=%d",
        len(messages),
        protect_from,
        original_tokens,
    )

    # --- Strategy 1: Tool result truncation ---
    step1: list[ChatMessage] = [
        _truncate_tool_result(msg, cfg.micro_compact_budget) if i < protect_from else msg
        for i, msg in enumerate(messages)
    ]

    # --- Strategy 2: Assistant message dedup ---
    step2, _dedup_count = _dedup_assistant_messages(step1, protect_from)

    # --- Strategy 3: System message dedup ---
    step3, _sys_removed = _dedup_system_messages(step2, protect_from)

    compacted_tokens = _count_total_tokens(step3)
    tokens_saved = max(0, original_tokens - compacted_tokens)

    result = CompactionResult(
        original_tokens=original_tokens,
        compacted_tokens=compacted_tokens,
        tokens_saved=tokens_saved,
        strategy_used="micro",
        turns_removed=0,  # micro-compact never removes full turns
    )

    logger.info(
        "micro_compact: %d → %d tokens saved (%d tokens), dedup=%d, sys_removed=%d",
        original_tokens,
        compacted_tokens,
        tokens_saved,
        _dedup_count,
        _sys_removed,
    )

    return step3, result
