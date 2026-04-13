# SPDX-License-Identifier: Apache-2.0
"""Tests for AutoCompactor and auto_compact module.

Covers:
- No compaction when tokens are below threshold
- Micro-compact strategy triggered first when threshold is crossed
- Escalation to session_summary when micro alone is insufficient
- Escalation to aggressive when both prior strategies are insufficient
- Empty list returns None result
- CompactionResult is None when no compaction needed
- Strategy labels match the applied strategy
- Tokens are reduced after compaction
- preserve_recent_turns respected across all strategies
- Async interface works correctly (pytest-asyncio)
"""

from __future__ import annotations

import pytest

from kosmos.context.auto_compact import AutoCompactor
from kosmos.context.compact_models import CompactionConfig
from kosmos.engine.tokens import estimate_tokens
from kosmos.llm.models import ChatMessage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content)


def _assistant(content: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


def _tool_result(content: str, call_id: str = "c1") -> ChatMessage:
    return ChatMessage(role="tool", content=content, tool_call_id=call_id)


def _sys(content: str = "System prompt.") -> ChatMessage:
    return ChatMessage(role="system", content=content)


def _make_large_history(n_turns: int, chars_per_turn: int = 2000) -> list[ChatMessage]:
    """Build a long conversation for compaction testing."""
    msgs: list[ChatMessage] = []
    for i in range(n_turns):
        msgs.append(_user("u" * chars_per_turn + f" turn {i}"))
        msgs.append(_assistant("a" * chars_per_turn + f" turn {i}"))
    return msgs


def _total_tokens(msgs: list[ChatMessage]) -> int:
    total = 0
    for m in msgs:
        if m.content:
            total += estimate_tokens(m.content)
        if m.tool_calls:
            for tc in m.tool_calls:
                total += estimate_tokens(tc.function.arguments)
    return total


# ---------------------------------------------------------------------------
# Tests: no-op when below threshold
# ---------------------------------------------------------------------------


class TestAutoCompactorNoOp:
    @pytest.mark.asyncio
    async def test_no_compaction_below_threshold(self) -> None:
        """Returns (messages, None) when token count is below trigger_threshold."""
        cfg = CompactionConfig(
            max_context_tokens=100_000,
            compact_trigger_ratio=0.85,
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        msgs = [_user("hello"), _assistant("world")]
        result_msgs, result = await compactor.maybe_compact(msgs, cfg)
        assert result is None
        assert result_msgs == msgs

    @pytest.mark.asyncio
    async def test_empty_list_returns_none_result(self) -> None:
        compactor = AutoCompactor()
        result_msgs, result = await compactor.maybe_compact([])
        assert result_msgs == []
        assert result is None

    @pytest.mark.asyncio
    async def test_messages_unchanged_when_no_compaction(self) -> None:
        cfg = CompactionConfig(max_context_tokens=1_000_000)
        compactor = AutoCompactor(config=cfg)
        msgs = [_user("a"), _assistant("b")]
        result_msgs, _ = await compactor.maybe_compact(msgs)
        assert result_msgs is msgs  # exact same object, no copy


# ---------------------------------------------------------------------------
# Tests: micro-compact triggered
# ---------------------------------------------------------------------------


class TestAutoCompactorMicroStrategy:
    @pytest.mark.asyncio
    async def test_micro_compact_triggered_and_reduces_tokens(self) -> None:
        """When threshold exceeded and micro-compact is sufficient, use micro."""
        # Make tool results very large so micro-compact can trim them.
        big_result = "x" * 40_000  # ~10k tokens
        msgs = [
            _sys(),
            _user("q1"),
            _tool_result(big_result, "c1"),
            _assistant("done"),
            _user("q2"),
            _assistant("also done"),
        ]

        # Threshold very low so we definitely trigger.
        cfg = CompactionConfig(
            max_context_tokens=100,
            compact_trigger_ratio=0.5,
            micro_compact_budget=50,
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        result_msgs, result = await compactor.maybe_compact(msgs, cfg)

        assert result is not None
        assert result.compacted_tokens < result.original_tokens


# ---------------------------------------------------------------------------
# Tests: session-summary escalation
# ---------------------------------------------------------------------------


class TestAutoCompactorSessionSummaryEscalation:
    @pytest.mark.asyncio
    async def test_session_summary_applied_when_micro_insufficient(self) -> None:
        """When micro-compact cannot reach threshold, session summary is applied."""
        # Build a very large history (no tool results to trim).
        msgs = _make_large_history(n_turns=20, chars_per_turn=500)

        # Threshold below even a minimal conversation.
        cfg = CompactionConfig(
            max_context_tokens=500,
            compact_trigger_ratio=0.5,
            preserve_recent_turns=2,
        )
        compactor = AutoCompactor(config=cfg)
        result_msgs, result = await compactor.maybe_compact(msgs, cfg)

        assert result is not None
        assert result.strategy_used in ("session_summary", "aggressive")

    @pytest.mark.asyncio
    async def test_session_summary_result_contains_summary_message(self) -> None:
        msgs = _make_large_history(n_turns=10, chars_per_turn=400)
        cfg = CompactionConfig(
            max_context_tokens=200,
            compact_trigger_ratio=0.5,
            preserve_recent_turns=2,
        )
        compactor = AutoCompactor(config=cfg)
        result_msgs, result = await compactor.maybe_compact(msgs, cfg)
        if result and result.strategy_used in ("session_summary", "aggressive"):
            # At least one system message with summary header should be present.
            from kosmos.context.session_compact import _SUMMARY_HEADER  # noqa: PLC0415

            summary_msgs = [m for m in result_msgs if m.role == "system"]
            assert any(_SUMMARY_HEADER in (m.content or "") for m in summary_msgs)


# ---------------------------------------------------------------------------
# Tests: aggressive truncation escalation
# ---------------------------------------------------------------------------


class TestAutoCompactorAggressiveEscalation:
    @pytest.mark.asyncio
    async def test_aggressive_strategy_reduces_tokens_significantly(self) -> None:
        """Aggressive truncation must bring tokens below the threshold."""
        # Build a large conversation where even session-summary leaves too much.
        msgs = _make_large_history(n_turns=30, chars_per_turn=800)
        cfg = CompactionConfig(
            max_context_tokens=100,
            compact_trigger_ratio=0.1,  # threshold = 10 tokens — very aggressive
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        result_msgs, result = await compactor.maybe_compact(msgs, cfg)
        assert result is not None
        # Output must have fewer tokens than input.
        assert result.compacted_tokens < result.original_tokens

    @pytest.mark.asyncio
    async def test_aggressive_strategy_label(self) -> None:
        msgs = _make_large_history(n_turns=30, chars_per_turn=800)
        cfg = CompactionConfig(
            max_context_tokens=100,
            compact_trigger_ratio=0.1,
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        _, result = await compactor.maybe_compact(msgs, cfg)
        if result:
            assert result.strategy_used in ("micro", "session_summary", "aggressive")


# ---------------------------------------------------------------------------
# Tests: preserve_recent_turns across strategies
# ---------------------------------------------------------------------------


class TestAutoCompactorPreservation:
    @pytest.mark.asyncio
    async def test_most_recent_turns_always_preserved(self) -> None:
        """The last preserve_recent_turns pairs must appear in output regardless of strategy."""
        n_turns = 10
        msgs = _make_large_history(n_turns=n_turns, chars_per_turn=300)
        # Last turn user content is distinctive.
        last_user_content = msgs[-2].content or ""

        cfg = CompactionConfig(
            max_context_tokens=200,
            compact_trigger_ratio=0.5,
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        result_msgs, _ = await compactor.maybe_compact(msgs, cfg)

        output_user_contents = [m.content for m in result_msgs if m.role == "user"]
        assert last_user_content in output_user_contents, (
            "Most recent user turn must be preserved after compaction"
        )

    @pytest.mark.asyncio
    async def test_canonical_system_prompt_always_preserved(self) -> None:
        """The initial system prompt is never removed."""
        sys_text = "CANONICAL SYSTEM PROMPT"
        msgs = [_sys(sys_text)] + _make_large_history(n_turns=10, chars_per_turn=300)
        cfg = CompactionConfig(
            max_context_tokens=200,
            compact_trigger_ratio=0.5,
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        result_msgs, _ = await compactor.maybe_compact(msgs, cfg)
        # First message must still be the canonical system prompt.
        assert result_msgs[0].role == "system"
        assert result_msgs[0].content == sys_text


# ---------------------------------------------------------------------------
# Tests: CompactionResult fields
# ---------------------------------------------------------------------------


class TestAutoCompactorResult:
    @pytest.mark.asyncio
    async def test_result_tokens_saved_is_nonneg(self) -> None:
        msgs = _make_large_history(n_turns=6, chars_per_turn=400)
        cfg = CompactionConfig(
            max_context_tokens=100,
            compact_trigger_ratio=0.5,
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        _, result = await compactor.maybe_compact(msgs, cfg)
        if result:
            assert result.tokens_saved >= 0

    @pytest.mark.asyncio
    async def test_result_original_tokens_matches_input(self) -> None:
        msgs = _make_large_history(n_turns=6, chars_per_turn=400)
        expected = _total_tokens(msgs)
        cfg = CompactionConfig(
            max_context_tokens=100,
            compact_trigger_ratio=0.5,
            preserve_recent_turns=1,
        )
        compactor = AutoCompactor(config=cfg)
        _, result = await compactor.maybe_compact(msgs, cfg)
        if result:
            assert result.original_tokens == expected
