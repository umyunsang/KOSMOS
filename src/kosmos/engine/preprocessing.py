# SPDX-License-Identifier: Apache-2.0
"""Context-window preprocessing pipeline for the KOSMOS Query Engine.

Four stages compress the conversation history before each LLM call to keep
the message list within the model's context window (128K tokens for K-EXAONE).

Stage execution order:
1. ``tool_result_budget``  — truncate oversized individual tool results
2. ``snip``                — remove stale tool results older than N turns
3. ``microcompact``        — strip whitespace in old messages
4. ``collapse``            — merge consecutive same-role messages

Each stage receives a message list and config, returns a new list. The
original list is never mutated.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.tokens import estimate_tokens
from kosmos.llm.models import ChatMessage

logger = logging.getLogger(__name__)

PreprocessStage = Callable[[list[ChatMessage], QueryEngineConfig, int], list[ChatMessage]]
"""Signature for a preprocessing stage function.

Args:
    messages: Current conversation history (must not be mutated).
    config: Engine config with threshold parameters.
    current_turn: The current turn count (for age-based decisions).

Returns:
    Processed message list (may be the same list if no changes needed).
"""


# ---------------------------------------------------------------------------
# Stage 1: tool_result_budget — truncate oversized tool results
# ---------------------------------------------------------------------------


def stage_tool_result_budget(
    messages: list[ChatMessage],
    config: QueryEngineConfig,
    current_turn: int,
) -> list[ChatMessage]:
    """Truncate tool result messages that exceed the per-result token budget.

    Any ``role='tool'`` message whose content exceeds
    ``config.tool_result_budget`` tokens is replaced with a truncated version
    that includes a ``[truncated]`` marker.
    """
    budget = config.tool_result_budget
    result: list[ChatMessage] = []

    for msg in messages:
        if msg.role == "tool" and msg.content:
            tokens = estimate_tokens(msg.content)
            if tokens > budget:
                # Truncate to roughly budget tokens worth of characters.
                # Use the inverse of the heuristic: budget tokens ≈ budget * 3 chars
                # (average of Korean 2 and English 4).
                char_limit = budget * 3
                truncated = msg.content[:char_limit]
                new_content = f"{truncated}\n[truncated: {tokens} -> {budget} tokens]"
                result.append(
                    ChatMessage(
                        role="tool",
                        content=new_content,
                        tool_call_id=msg.tool_call_id,
                    ),
                )
                logger.debug(
                    "Truncated tool result %s: %d -> %d tokens",
                    msg.tool_call_id,
                    tokens,
                    budget,
                )
                continue
        result.append(msg)

    return result


# ---------------------------------------------------------------------------
# Stage 2: snip — remove stale tool results
# ---------------------------------------------------------------------------


def stage_snip(
    messages: list[ChatMessage],
    config: QueryEngineConfig,
    current_turn: int,
) -> list[ChatMessage]:
    """Remove tool result messages older than ``config.snip_turn_age`` turns.

    Only tool results (``role='tool'``) are candidates. System, user, and
    assistant messages are always preserved. A tool result is considered
    "stale" when the turn distance exceeds the configured age threshold.

    Turn distance is approximated by counting user messages seen so far
    (each user message marks a new turn boundary).
    """
    threshold = config.snip_turn_age
    result: list[ChatMessage] = []
    user_turns_seen = 0

    for msg in messages:
        if msg.role == "user":
            user_turns_seen += 1

        if msg.role == "tool":
            turn_age = current_turn - user_turns_seen
            if turn_age >= threshold:
                logger.debug(
                    "Snipped stale tool result %s (age=%d, threshold=%d)",
                    msg.tool_call_id,
                    turn_age,
                    threshold,
                )
                continue
        result.append(msg)

    return result


# ---------------------------------------------------------------------------
# Stage 3: microcompact — strip whitespace in old messages
# ---------------------------------------------------------------------------

_WHITESPACE_RUN = re.compile(r"\s+")


def stage_microcompact(
    messages: list[ChatMessage],
    config: QueryEngineConfig,
    current_turn: int,
) -> list[ChatMessage]:
    """Compress whitespace in messages older than ``config.microcompact_turn_age``.

    Replaces runs of whitespace with single spaces and strips leading/trailing
    whitespace. Only applies to non-system messages whose turn age exceeds the
    threshold.
    """
    threshold = config.microcompact_turn_age
    result: list[ChatMessage] = []
    user_turns_seen = 0

    for msg in messages:
        if msg.role == "user":
            user_turns_seen += 1

        turn_age = current_turn - user_turns_seen

        if msg.role != "system" and msg.content and turn_age >= threshold:
            compacted = _WHITESPACE_RUN.sub(" ", msg.content).strip()
            if compacted != msg.content:
                result.append(
                    ChatMessage(
                        role=msg.role,
                        content=compacted,
                        name=msg.name,
                        tool_calls=msg.tool_calls,
                        tool_call_id=msg.tool_call_id,
                    ),
                )
                continue
        result.append(msg)

    return result


# ---------------------------------------------------------------------------
# Stage 4: collapse — merge consecutive same-role messages
# ---------------------------------------------------------------------------


def stage_collapse(
    messages: list[ChatMessage],
    config: QueryEngineConfig,
    current_turn: int,
) -> list[ChatMessage]:
    """Merge consecutive messages with the same role into a single message.

    Only merges messages where both have content and neither has tool_calls
    or tool_call_id (to avoid breaking tool-call correlation). System messages
    are never merged.
    """
    if not messages:
        return []

    result: list[ChatMessage] = [messages[0]]

    for msg in messages[1:]:
        prev = result[-1]

        can_merge = (
            msg.role == prev.role
            and msg.role not in ("system", "tool")
            and msg.content is not None
            and prev.content is not None
            and msg.tool_calls is None
            and prev.tool_calls is None
            and msg.tool_call_id is None
            and prev.tool_call_id is None
            and msg.name == prev.name
        )

        if can_merge:
            merged_content = f"{prev.content}\n{msg.content}"
            result[-1] = ChatMessage(
                role=msg.role,
                content=merged_content,
                name=msg.name,
            )
            logger.debug("Collapsed consecutive %s messages", msg.role)
        else:
            result.append(msg)

    return result


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------

_DEFAULT_STAGES: list[PreprocessStage] = [
    stage_tool_result_budget,
    stage_snip,
    stage_microcompact,
    stage_collapse,
]


class PreprocessingPipeline:
    """Ordered pipeline of context compression stages.

    Each stage receives a copy of the message list and config, returning a
    new list. The original list is never modified.

    Args:
        stages: Optional custom stage list. Defaults to the standard 4-stage
                pipeline (tool_result_budget → snip → microcompact → collapse).
    """

    def __init__(self, stages: list[PreprocessStage] | None = None) -> None:
        self._stages = stages if stages is not None else list(_DEFAULT_STAGES)

    def run(
        self,
        messages: list[ChatMessage],
        config: QueryEngineConfig,
        current_turn: int = 0,
    ) -> list[ChatMessage]:
        """Apply all stages sequentially to the message list.

        Each stage receives the output of the previous stage. The original
        input list is not modified.

        Args:
            messages: Current conversation history.
            config: Engine config with threshold parameters.
            current_turn: Current turn count for age-based decisions.

        Returns:
            Processed message list ready for LLM snapshot.
        """
        # Start with a shallow copy to avoid mutating the original
        current = list(messages)

        for stage in self._stages:
            current = stage(current, config, current_turn)

        return current
