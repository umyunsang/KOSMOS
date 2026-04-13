# SPDX-License-Identifier: Apache-2.0
"""Auto-compact trigger for KOSMOS Context Assembly layer.

``AutoCompactor.maybe_compact()`` monitors token usage after each turn and
applies the appropriate compaction strategy when the conversation history
exceeds the configured threshold.

Escalation order:
  1. **Micro-compact** — surgical per-turn trimming.  Fast, zero information
     loss.  Attempted first.
  2. **Session summary** — replace older turns with a rule-based summary.
     Applied when micro-compact alone cannot bring the count below threshold.
  3. **Aggressive truncation** — drop the oldest non-summary turns one by
     one until the count is below threshold.  Last resort.

A compaction is skipped entirely (returns ``None``) when the message list
is empty or the current token count is already below the trigger threshold.

Reference: Claude Code ``autoCompact.ts`` — the ``maybeAutoCompact()``
function, tiered escalation pattern.
"""

from __future__ import annotations

import logging

from kosmos.context.compact_models import CompactionConfig, CompactionResult
from kosmos.context.micro_compact import (
    _count_total_tokens,  # noqa: PLC2701
    micro_compact,
)
from kosmos.context.session_compact import session_compact
from kosmos.llm.models import ChatMessage

logger = logging.getLogger(__name__)


def _aggressive_truncate(
    messages: list[ChatMessage],
    threshold: int,
    preserve_recent_turns: int,
) -> tuple[list[ChatMessage], int]:
    """Drop the oldest non-summary, non-system-prompt turns until below threshold.

    The canonical system prompt (index 0 when role='system') and any session
    summary messages are never removed.  The ``preserve_recent_turns`` tail
    window is protected.

    Returns:
        Tuple of (reduced message list, number of turns dropped).
    """
    # Determine the protected tail boundary.
    from kosmos.context.micro_compact import _protected_slice_start  # noqa: PLC0415
    from kosmos.context.session_compact import _SUMMARY_HEADER  # noqa: PLC0415

    turns_dropped = 0
    current = list(messages)

    while _count_total_tokens(current) > threshold:
        protect_from = _protected_slice_start(current, preserve_recent_turns)
        # Find the oldest droppable index (skip system prompt at 0 and summaries).
        drop_idx: int | None = None
        for i, msg in enumerate(current):
            if i == 0 and msg.role == "system":
                continue  # canonical system prompt
            if msg.role == "system" and msg.content and _SUMMARY_HEADER in msg.content:
                continue  # already-generated summary
            if i >= protect_from:
                break  # protected window
            drop_idx = i
            break

        if drop_idx is None:
            # Nothing droppable — cannot reduce further.
            logger.warning(
                "aggressive_truncate: cannot reduce below %d tokens — "
                "all non-protected messages are summaries or system prompts",
                _count_total_tokens(current),
            )
            break

        logger.debug("aggressive_truncate: dropping message at index %d", drop_idx)
        current.pop(drop_idx)
        turns_dropped += 1

    return current, turns_dropped


class AutoCompactor:
    """Stateless compaction orchestrator.

    Instantiate once and call ``maybe_compact()`` after every turn.

    Args:
        config: Compaction configuration; defaults to ``CompactionConfig()``.
    """

    def __init__(self, config: CompactionConfig | None = None) -> None:
        self._config = config or CompactionConfig()

    async def maybe_compact(
        self,
        messages: list[ChatMessage],
        config: CompactionConfig | None = None,
    ) -> tuple[list[ChatMessage], CompactionResult | None]:
        """Inspect token usage and apply compaction when needed.

        This is declared ``async`` so it integrates cleanly with the async
        engine loop.  In v1 all operations are synchronous; no ``await``
        expressions are used internally.

        Args:
            messages: Full conversation history (most recent turn appended).
            config: Optional per-call config override.

        Returns:
            Tuple of:
            - Message list (original if no compaction needed, compacted otherwise).
            - ``CompactionResult`` describing what was done, or ``None`` when
              no compaction was necessary.
        """
        cfg = config or self._config

        if not messages:
            return messages, None

        current_tokens = _count_total_tokens(messages)
        threshold = cfg.trigger_threshold

        if current_tokens < threshold:
            logger.debug(
                "auto_compact: skipped (%d tokens < threshold %d)",
                current_tokens,
                threshold,
            )
            return messages, None

        logger.info(
            "auto_compact: triggered at %d tokens (threshold=%d, max=%d)",
            current_tokens,
            threshold,
            cfg.max_context_tokens,
        )

        # --- Stage 1: Micro-compact ---
        stage1_messages, micro_result = micro_compact(messages, cfg)
        stage1_tokens = _count_total_tokens(stage1_messages)

        if stage1_tokens < threshold:
            logger.info(
                "auto_compact: micro-compact sufficient (%d → %d tokens)",
                current_tokens,
                stage1_tokens,
            )
            return stage1_messages, micro_result

        logger.info(
            "auto_compact: micro-compact insufficient (%d tokens still >= %d), "
            "escalating to session_summary",
            stage1_tokens,
            threshold,
        )

        # --- Stage 2: Session summary compact ---
        stage2_messages, session_result = session_compact(stage1_messages, cfg)
        stage2_tokens = _count_total_tokens(stage2_messages)

        if stage2_tokens < threshold:
            logger.info(
                "auto_compact: session_summary sufficient (%d → %d tokens)",
                stage1_tokens,
                stage2_tokens,
            )
            return stage2_messages, session_result

        logger.warning(
            "auto_compact: session_summary insufficient (%d tokens still >= %d), "
            "escalating to aggressive truncation",
            stage2_tokens,
            threshold,
        )

        # --- Stage 3: Aggressive truncation ---
        stage3_messages, turns_dropped = _aggressive_truncate(
            stage2_messages, threshold, cfg.preserve_recent_turns
        )
        stage3_tokens = _count_total_tokens(stage3_messages)

        aggressive_result = CompactionResult(
            original_tokens=current_tokens,
            compacted_tokens=stage3_tokens,
            tokens_saved=max(0, current_tokens - stage3_tokens),
            strategy_used="aggressive",
            turns_removed=session_result.turns_removed + turns_dropped,
            summary_generated=session_result.summary_generated,
        )

        logger.info(
            "auto_compact: aggressive truncation complete (%d → %d tokens, %d turns dropped)",
            current_tokens,
            stage3_tokens,
            turns_dropped,
        )

        return stage3_messages, aggressive_result
