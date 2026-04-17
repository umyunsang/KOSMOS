# SPDX-License-Identifier: Apache-2.0
"""Session summary compaction for KOSMOS Context Assembly layer.

When micro-compaction is insufficient, ``session_compact`` replaces older
conversation turns with a deterministic rule-based summary.  The summary
is inserted as a ``role='system'`` message at position 0 (or immediately
after the canonical system prompt if one is present).

Design:
- No LLM calls — all extraction is rule-based (v1 constraint).
- Idempotent: calling it twice with the same input produces the same output.
- Preserves the last ``config.preserve_recent_turns`` turn-pairs untouched.
- The summary encodes: tool calls made, tool results obtained, and any
  assistant decisions visible from the message text.

Reference: Claude Code ``sessionMemoryCompact.ts`` — session-memory path.
KOSMOS v1 uses deterministic extraction rather than a background summary agent.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Final

import yaml

from kosmos.context.compact_models import CompactionConfig, CompactionResult
from kosmos.context.prompt_loader import PromptLoader
from kosmos.engine.tokens import estimate_tokens
from kosmos.llm.models import ChatMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level: load compact_v1 template via PromptLoader at import time.
# The manifest is resolved relative to the project root (4 levels above this
# file: context/ → kosmos/ → src/ → project root).
# ---------------------------------------------------------------------------

_MANIFEST_PATH: Final[Path] = (
    Path(__file__).parent.parent.parent.parent / "prompts" / "manifest.yaml"
)

_loader = PromptLoader(manifest_path=_MANIFEST_PATH)
_compact_raw: str = _loader.load("compact_v1")

# Parse YAML frontmatter.  The frontmatter is delimited by "---" lines at the
# top of the file; yaml.safe_load of the block between the first two "---"
# markers gives us the template dict.
_fm_text = _compact_raw.split("---")[1]  # block between first and second "---"
_COMPACT_TEMPLATE: dict[str, Any] = yaml.safe_load(_fm_text)

# ---------------------------------------------------------------------------
# Text constants sourced from compact_v1.md frontmatter.
# ---------------------------------------------------------------------------

# Marker prefixed to summaries so downstream code can detect injected summaries.
_SUMMARY_ROLE: Final[str] = "system"
_SUMMARY_HEADER: str = _COMPACT_TEMPLATE["summary_header"]

_SECTION_LABELS: dict[str, str] = _COMPACT_TEMPLATE["section_labels"]
_EMPTY_STATE: str = _COMPACT_TEMPLATE["empty_state"]
_TRUNCATION_MARKER: str = _COMPACT_TEMPLATE["truncation_marker"]
_LINE_PREFIX: str = _COMPACT_TEMPLATE["line_prefix"]
_FORMATTERS: dict[str, str] = _COMPACT_TEMPLATE["formatters"]

# ---------------------------------------------------------------------------
# Algorithmic constants — intentionally NOT externalised (FR-X02).
# ---------------------------------------------------------------------------

# Maximum characters extracted from a single tool-result for the summary.
_MAX_RESULT_EXCERPT_CHARS: Final[int] = 200

# Maximum characters extracted from a single assistant message for the summary.
_MAX_ASSISTANT_EXCERPT_CHARS: Final[int] = 300


def _protected_slice_start(messages: list[ChatMessage], preserve_turns: int) -> int:
    """Return the first index belonging to the protected (recent) turn window.

    Walks backward counting completed (user, assistant) pairs.  Once
    ``preserve_turns`` pairs are found, returns the index of the user message
    that opened the oldest protected pair.

    Returns 0 when all messages are within the protected window.
    """
    if preserve_turns <= 0:
        return len(messages)

    pairs_found = 0
    idx = len(messages) - 1
    while idx >= 0:
        if messages[idx].role == "assistant" and idx > 0 and messages[idx - 1].role == "user":
            pairs_found += 1
            if pairs_found >= preserve_turns:
                return idx - 1
            idx -= 2
        else:
            idx -= 1
    return 0


def _extract_tool_calls(messages: list[ChatMessage]) -> list[str]:
    """Extract a brief description of each tool call from assistant messages."""
    results: list[str] = []
    fmt = _FORMATTERS["tool_call"]
    for msg in messages:
        if msg.role != "assistant" or not msg.tool_calls:
            continue
        for tc in msg.tool_calls:
            # Include the function name and first 80 chars of arguments.
            args_excerpt = (tc.function.arguments or "")[:80]
            if len(tc.function.arguments or "") > 80:
                args_excerpt += "…"
            results.append(fmt.format(name=tc.function.name, args_excerpt=args_excerpt))
    return results


def _extract_tool_results(messages: list[ChatMessage]) -> list[str]:
    """Extract brief excerpts from tool-result messages."""
    results: list[str] = []
    fmt = _FORMATTERS["tool_result"]
    for msg in messages:
        if msg.role != "tool" or not msg.content:
            continue
        excerpt = msg.content[:_MAX_RESULT_EXCERPT_CHARS]
        if len(msg.content) > _MAX_RESULT_EXCERPT_CHARS:
            excerpt += "…"
        call_id = msg.tool_call_id or "unknown"
        results.append(fmt.format(call_id=call_id, excerpt=excerpt))
    return results


def _extract_assistant_decisions(messages: list[ChatMessage]) -> list[str]:
    """Extract non-trivial assistant message excerpts as decision records."""
    results: list[str] = []
    fmt = _FORMATTERS["assistant"]
    for msg in messages:
        if msg.role != "assistant" or not msg.content:
            continue
        content = msg.content.strip()
        # Skip dedup markers and very short messages.
        if len(content) < 40:
            continue
        if "[Assistant message deduplicated" in content:
            continue
        excerpt = content[:_MAX_ASSISTANT_EXCERPT_CHARS]
        if len(content) > _MAX_ASSISTANT_EXCERPT_CHARS:
            excerpt += "…"
        results.append(fmt.format(excerpt=excerpt))
    return results


def _extract_user_intents(messages: list[ChatMessage]) -> list[str]:
    """Extract user messages as intent records."""
    results: list[str] = []
    fmt = _FORMATTERS["user"]
    for msg in messages:
        if msg.role != "user" or not msg.content:
            continue
        content = msg.content.strip()
        # Skip injected attachment markers (prefixed with '[').
        if content.startswith("["):
            continue
        excerpt = content[:200]
        if len(content) > 200:
            excerpt += "…"
        results.append(fmt.format(excerpt=excerpt))
    return results


def _build_summary_text(
    compacted_messages: list[ChatMessage],
    config: CompactionConfig,
) -> str:
    """Build the deterministic summary string from messages to be removed.

    Sections included (only when non-empty):
    - User intents
    - Tool calls made
    - Tool results obtained
    - Assistant decisions

    The summary is truncated to fit within ``config.summary_max_tokens``.

    Args:
        compacted_messages: The messages that are about to be removed.
        config: Compaction configuration controlling summary_max_tokens.

    Returns:
        A non-empty summary string.
    """
    sections: list[str] = [_SUMMARY_HEADER]

    user_intents = _extract_user_intents(compacted_messages)
    if user_intents:
        sections.append(_SECTION_LABELS["user_requests"])
        sections.extend(f"{_LINE_PREFIX}{line}" for line in user_intents)

    tool_calls = _extract_tool_calls(compacted_messages)
    if tool_calls:
        sections.append(_SECTION_LABELS["tool_calls"])
        sections.extend(f"{_LINE_PREFIX}{line}" for line in tool_calls)

    tool_results = _extract_tool_results(compacted_messages)
    if tool_results:
        sections.append(_SECTION_LABELS["tool_results"])
        sections.extend(f"{_LINE_PREFIX}{line}" for line in tool_results)

    decisions = _extract_assistant_decisions(compacted_messages)
    if decisions:
        sections.append(_SECTION_LABELS["assistant_responses"])
        sections.extend(f"{_LINE_PREFIX}{line}" for line in decisions)

    if len(sections) == 1:
        # Nothing extracted — produce a minimal placeholder.
        sections.append(_EMPTY_STATE)

    full_text = "\n".join(sections)

    # Truncate to summary_max_tokens budget (crude character-based).
    char_budget = config.summary_max_tokens * 4
    if len(full_text) > char_budget:
        full_text = full_text[:char_budget] + f"\n{_TRUNCATION_MARKER}"

    return full_text


def session_compact(
    messages: list[ChatMessage],
    config: CompactionConfig | None = None,
) -> tuple[list[ChatMessage], CompactionResult]:
    """Replace older conversation turns with a rule-based session summary.

    The oldest turns (beyond the protected tail window) are extracted, a
    plain-text summary is generated from them, and that summary is inserted
    as a ``role='system'`` message.  The canonical system prompt (if present
    at index 0) is preserved as-is; the summary is injected immediately after.

    Args:
        messages: Conversation history in chronological order.
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
            strategy_used="session_summary",
            turns_removed=0,
        )

    original_tokens = _count_total_tokens(messages)
    protect_from = _protected_slice_start(messages, cfg.preserve_recent_turns)

    logger.debug(
        "session_compact: %d messages, protect_from=%d, original_tokens=%d",
        len(messages),
        protect_from,
        original_tokens,
    )

    # Identify the canonical system prompt at index 0 (if any).
    has_system_prefix = messages and messages[0].role == "system"
    compaction_start = 1 if has_system_prefix else 0

    # Nothing to compact if everything is protected.
    if compaction_start >= protect_from:
        return messages, CompactionResult(
            original_tokens=original_tokens,
            compacted_tokens=original_tokens,
            tokens_saved=0,
            strategy_used="session_summary",
            turns_removed=0,
        )

    # The slice to be replaced by the summary.
    to_compress = messages[compaction_start:protect_from]
    turns_removed = (
        sum(1 for m in to_compress if m.role in ("user", "assistant")) // 2
    )  # Count complete pairs

    summary_text = _build_summary_text(to_compress, cfg)
    summary_message = ChatMessage(role="system", content=summary_text)

    # Construct the new message list:
    #   [system_prompt (if any)] + [summary] + [protected recent turns]
    prefix: list[ChatMessage] = []
    if has_system_prefix:
        prefix = [messages[0]]

    new_messages: list[ChatMessage] = prefix + [summary_message] + list(messages[protect_from:])

    compacted_tokens = _count_total_tokens(new_messages)
    tokens_saved = max(0, original_tokens - compacted_tokens)

    result = CompactionResult(
        original_tokens=original_tokens,
        compacted_tokens=compacted_tokens,
        tokens_saved=tokens_saved,
        strategy_used="session_summary",
        turns_removed=turns_removed,
        summary_generated=summary_text,
    )

    logger.info(
        "session_compact: %d → %d tokens (%d saved), %d turns removed",
        original_tokens,
        compacted_tokens,
        tokens_saved,
        turns_removed,
    )

    return new_messages, result


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
