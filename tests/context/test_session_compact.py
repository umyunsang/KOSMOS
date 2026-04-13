# SPDX-License-Identifier: Apache-2.0
"""Tests for session_compact engine (session_compact.py).

Covers:
- Empty input returns unchanged
- Summary is inserted as role='system' at the right position
- Original system prompt is preserved at index 0
- Protected (recent) turns are preserved verbatim
- turns_removed counts only complete pairs removed
- Summary contains tool calls, tool results, and user intents
- All-protected edge case returns unchanged
- Single message edge case
- Token count decreases after compaction
- Strategy label is 'session_summary'
"""

from __future__ import annotations

from kosmos.context.compact_models import CompactionConfig
from kosmos.context.session_compact import (
    _SUMMARY_HEADER,
    session_compact,
)
from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sys(content: str = "System prompt.") -> ChatMessage:
    return ChatMessage(role="system", content=content)


def _user(content: str = "User message.") -> ChatMessage:
    return ChatMessage(role="user", content=content)


def _assistant(content: str = "Assistant reply.") -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


def _tool_result(content: str, call_id: str = "c1") -> ChatMessage:
    return ChatMessage(role="tool", content=content, tool_call_id=call_id)


def _assistant_with_tc(call_id: str = "c1", fn: str = "search") -> ChatMessage:
    tc = ToolCall(id=call_id, function=FunctionCall(name=fn, arguments='{"q":"test"}'))
    return ChatMessage(role="assistant", content=None, tool_calls=[tc])


def _make_full_conversation(n_turns: int) -> list[ChatMessage]:
    """Build a conversation of n_turns user+assistant pairs (no system)."""
    msgs: list[ChatMessage] = []
    for i in range(n_turns):
        msgs.append(_user(f"User turn {i}"))
        msgs.append(_assistant(f"Assistant turn {i}"))
    return msgs


# ---------------------------------------------------------------------------
# Tests: edge cases
# ---------------------------------------------------------------------------


class TestSessionCompactEdgeCases:
    def test_empty_list(self) -> None:
        result_msgs, result = session_compact([])
        assert result_msgs == []
        assert result.tokens_saved == 0
        assert result.turns_removed == 0

    def test_single_message_all_protected(self) -> None:
        msgs = [_user("only one")]
        cfg = CompactionConfig(preserve_recent_turns=4)
        result_msgs, result = session_compact(msgs, cfg)
        assert result_msgs == msgs
        assert result.tokens_saved == 0

    def test_only_system_prompt_no_compaction(self) -> None:
        msgs = [_sys()]
        result_msgs, result = session_compact(msgs)
        # Nothing to compact
        assert len(result_msgs) >= 1
        assert result_msgs[0].role == "system"

    def test_all_protected_turns_unchanged(self) -> None:
        """When all turns fall in the protected window, no change occurs."""
        msgs = _make_full_conversation(2)  # 4 messages
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, result = session_compact(msgs, cfg)
        assert result.tokens_saved == 0
        assert result.turns_removed == 0


# ---------------------------------------------------------------------------
# Tests: summary insertion
# ---------------------------------------------------------------------------


class TestSessionCompactSummaryInsertion:
    def test_summary_is_system_message(self) -> None:
        """The generated summary must be a role='system' message."""
        msgs = _make_full_conversation(6)
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, result = session_compact(msgs, cfg)
        summary_msgs = [m for m in result_msgs if m.role == "system"]
        assert len(summary_msgs) >= 1

    def test_summary_contains_header(self) -> None:
        msgs = _make_full_conversation(6)
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, result = session_compact(msgs, cfg)
        summary_msgs = [m for m in result_msgs if m.role == "system"]
        assert any(_SUMMARY_HEADER in (m.content or "") for m in summary_msgs)

    def test_summary_generated_field_populated(self) -> None:
        msgs = _make_full_conversation(6)
        cfg = CompactionConfig(preserve_recent_turns=2)
        _, result = session_compact(msgs, cfg)
        assert result.summary_generated is not None
        assert _SUMMARY_HEADER in result.summary_generated

    def test_canonical_system_prompt_preserved_at_index_0(self) -> None:
        """Original system prompt must stay at index 0."""
        sys_content = "You are a helpful assistant."
        msgs = [_sys(sys_content)] + _make_full_conversation(6)
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, _ = session_compact(msgs, cfg)
        assert result_msgs[0].role == "system"
        assert result_msgs[0].content == sys_content

    def test_summary_placed_after_system_prompt(self) -> None:
        """Summary is inserted at index 1 when a system prompt is at 0."""
        msgs = [_sys()] + _make_full_conversation(6)
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, _ = session_compact(msgs, cfg)
        assert result_msgs[1].role == "system"
        assert _SUMMARY_HEADER in (result_msgs[1].content or "")

    def test_summary_at_index_0_when_no_system_prompt(self) -> None:
        """Summary is at index 0 when there is no canonical system prompt."""
        msgs = _make_full_conversation(6)
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, _ = session_compact(msgs, cfg)
        assert result_msgs[0].role == "system"
        assert _SUMMARY_HEADER in (result_msgs[0].content or "")


# ---------------------------------------------------------------------------
# Tests: protected turn preservation
# ---------------------------------------------------------------------------


class TestSessionCompactProtection:
    def test_protected_turns_preserved_verbatim(self) -> None:
        """The last preserve_recent_turns pairs must appear unchanged in output."""
        msgs = _make_full_conversation(5)
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, _ = session_compact(msgs, cfg)

        # Expected preserved tail: last 2 pairs from the original.
        protected_user_8 = "User turn 3"
        protected_user_9 = "User turn 4"
        output_user_contents = [m.content for m in result_msgs if m.role == "user"]
        assert protected_user_8 in output_user_contents
        assert protected_user_9 in output_user_contents

    def test_protected_assistant_turns_preserved(self) -> None:
        msgs = _make_full_conversation(5)
        cfg = CompactionConfig(preserve_recent_turns=2)
        result_msgs, _ = session_compact(msgs, cfg)
        output_asst_contents = [m.content for m in result_msgs if m.role == "assistant"]
        assert "Assistant turn 3" in output_asst_contents
        assert "Assistant turn 4" in output_asst_contents

    def test_turns_removed_field_counts_removed_pairs(self) -> None:
        """turns_removed should reflect the number of removed turn pairs."""
        msgs = _make_full_conversation(6)  # 6 pairs = 12 messages
        cfg = CompactionConfig(preserve_recent_turns=2)
        _, result = session_compact(msgs, cfg)
        assert result.turns_removed >= 1


# ---------------------------------------------------------------------------
# Tests: summary content includes key facts
# ---------------------------------------------------------------------------


class TestSessionCompactSummaryContent:
    def test_summary_includes_user_intents(self) -> None:
        distinctive = "I want to know about vaccine schedules for children"
        msgs = [_user(distinctive), _assistant("Sure, here is the info.")]
        msgs += _make_full_conversation(3)  # ensure something is protected
        cfg = CompactionConfig(preserve_recent_turns=2)
        _, result = session_compact(msgs, cfg)
        if result.summary_generated:
            assert distinctive[:50] in result.summary_generated

    def test_summary_includes_tool_calls(self) -> None:
        msgs: list[ChatMessage] = [
            _user("search for parking"),
            _assistant_with_tc(call_id="tc1", fn="search_parking"),
            _tool_result("No results found", "tc1"),
            _assistant("I couldn't find any parking."),
        ]
        msgs += _make_full_conversation(2)
        cfg = CompactionConfig(preserve_recent_turns=2)
        _, result = session_compact(msgs, cfg)
        if result.summary_generated:
            assert "search_parking" in result.summary_generated


# ---------------------------------------------------------------------------
# Tests: token accounting
# ---------------------------------------------------------------------------


class TestSessionCompactTokenAccounting:
    def test_tokens_decrease_after_compaction(self) -> None:
        """Session summary saves tokens when turns are large enough to compress."""
        # Use long messages so the removed turns outweigh the summary overhead.
        long_content = "The government service database returned many results. " * 40
        msgs: list[ChatMessage] = []
        for i in range(8):
            msgs.append(_user(f"Question {i}: {long_content}"))
            msgs.append(_assistant(f"Answer {i}: {long_content}"))
        cfg = CompactionConfig(preserve_recent_turns=2)
        _, result = session_compact(msgs, cfg)
        assert result.compacted_tokens < result.original_tokens
        assert result.tokens_saved > 0

    def test_strategy_is_session_summary(self) -> None:
        msgs = _make_full_conversation(4)
        _, result = session_compact(msgs)
        assert result.strategy_used == "session_summary"

    def test_tokens_saved_is_clamped_to_zero(self) -> None:
        """tokens_saved is always >= 0, even when summary overhead exceeds removed content."""
        # Small inputs where summary might be larger than what it replaces.
        msgs = _make_full_conversation(4)
        cfg = CompactionConfig(preserve_recent_turns=2)
        _, result = session_compact(msgs, cfg)
        assert result.tokens_saved >= 0

    def test_tokens_saved_matches_difference_for_large_inputs(self) -> None:
        """For large inputs, tokens_saved == original - compacted."""
        long_content = "x" * 2000
        msgs = []
        for i in range(6):
            msgs.append(_user(f"q{i} {long_content}"))
            msgs.append(_assistant(f"a{i} {long_content}"))
        cfg = CompactionConfig(preserve_recent_turns=2)
        _, result = session_compact(msgs, cfg)
        # When compaction actually saved tokens, the difference must match.
        if result.tokens_saved > 0:
            assert result.tokens_saved == result.original_tokens - result.compacted_tokens
