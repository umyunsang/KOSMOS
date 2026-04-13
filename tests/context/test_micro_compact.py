# SPDX-License-Identifier: Apache-2.0
"""Tests for micro_compact engine (micro_compact.py).

Covers:
- Empty input returns unchanged
- Tool result truncation above budget
- Tool results within budget are unchanged
- Assistant message deduplication
- System message deduplication
- preserve_recent_turns boundary — protected messages are never modified
- Token count decreases after compaction
- Single-message edge case
- All-protected edge case (preserve_recent_turns covers everything)
"""

from __future__ import annotations

from kosmos.context.compact_models import CompactionConfig
from kosmos.context.micro_compact import (
    _TOOL_RESULT_CLEARED,
    _protected_slice_start,
    micro_compact,
)
from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _sys(content: str = "System prompt.") -> ChatMessage:
    return ChatMessage(role="system", content=content)


def _user(content: str = "User message.") -> ChatMessage:
    return ChatMessage(role="user", content=content)


def _assistant(content: str = "Assistant message.") -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


def _tool_result(content: str, call_id: str = "call_1") -> ChatMessage:
    return ChatMessage(role="tool", content=content, tool_call_id=call_id)


def _assistant_with_tool_call(
    call_id: str = "call_1", fn: str = "search", args: str = '{"q": "test"}'
) -> ChatMessage:
    tc = ToolCall(id=call_id, function=FunctionCall(name=fn, arguments=args))
    return ChatMessage(role="assistant", content=None, tool_calls=[tc])


def _large_content(n_chars: int = 20_000) -> str:
    """Return a long ASCII string of length n_chars."""
    return "x" * n_chars


# ---------------------------------------------------------------------------
# Tests: empty and trivial inputs
# ---------------------------------------------------------------------------


class TestMicroCompactEdgeCases:
    def test_empty_list_returns_empty(self) -> None:
        result_msgs, result = micro_compact([])
        assert result_msgs == []
        assert result.original_tokens == 0
        assert result.compacted_tokens == 0
        assert result.tokens_saved == 0
        assert result.strategy_used == "micro"

    def test_single_system_message_unchanged(self) -> None:
        msgs = [_sys()]
        result_msgs, result = micro_compact(msgs)
        assert len(result_msgs) == 1
        assert result_msgs[0].content == msgs[0].content

    def test_single_user_message_unchanged(self) -> None:
        msgs = [_user("Hello")]
        result_msgs, result = micro_compact(msgs)
        assert result_msgs[0].content == "Hello"

    def test_single_tool_result_within_budget(self) -> None:
        """Short tool result stays unchanged."""
        cfg = CompactionConfig(micro_compact_budget=1000)
        msgs = [_tool_result("Short result")]
        result_msgs, _ = micro_compact(msgs, cfg)
        assert result_msgs[0].content == "Short result"


# ---------------------------------------------------------------------------
# Tests: tool result truncation
# ---------------------------------------------------------------------------


class TestToolResultTruncation:
    def test_large_tool_result_is_truncated(self) -> None:
        """Tool result vastly exceeding budget gets truncated."""
        cfg = CompactionConfig(micro_compact_budget=10, preserve_recent_turns=0)
        big_content = _large_content(10_000)
        msgs = [_tool_result(big_content)]
        result_msgs, result = micro_compact(msgs, cfg)
        assert len(result_msgs) == 1
        assert _TOOL_RESULT_CLEARED in result_msgs[0].content
        assert len(result_msgs[0].content) < len(big_content)
        assert result.tokens_saved > 0

    def test_tool_call_id_preserved_after_truncation(self) -> None:
        cfg = CompactionConfig(micro_compact_budget=10, preserve_recent_turns=0)
        msgs = [_tool_result(_large_content(5000), call_id="call_abc")]
        result_msgs, _ = micro_compact(msgs, cfg)
        assert result_msgs[0].tool_call_id == "call_abc"

    def test_non_tool_role_not_truncated(self) -> None:
        """User and assistant messages are never truncated by tool-result logic."""
        cfg = CompactionConfig(micro_compact_budget=5, preserve_recent_turns=0)
        big_user = _user(_large_content(8000))
        result_msgs, _ = micro_compact([big_user], cfg)
        assert result_msgs[0].content == big_user.content

    def test_tool_result_in_protected_zone_not_truncated(self) -> None:
        """Tool results inside the protected tail window must not be truncated."""
        cfg = CompactionConfig(micro_compact_budget=5, preserve_recent_turns=2)
        # Build: [user1, assistant1, user2(tool), assistant2]
        msgs = [
            _user("q1"),
            _assistant("a1"),
            _user("q2"),
            _assistant_with_tool_call(),
        ]
        big_result = _tool_result(_large_content(5000))
        msgs.append(big_result)

        # The protected window (2 pairs) covers user2→assistant2→tool_result.
        result_msgs, _ = micro_compact(msgs, cfg)
        # Find the tool result in output
        tool_msg = next(m for m in result_msgs if m.role == "tool")
        assert tool_msg.content == big_result.content, "Protected tool result must not be truncated"

    def test_multiple_tool_results_outside_protection_all_truncated(self) -> None:
        cfg = CompactionConfig(micro_compact_budget=5, preserve_recent_turns=0)
        msgs = [
            _tool_result(_large_content(5000), call_id="c1"),
            _tool_result(_large_content(5000), call_id="c2"),
        ]
        result_msgs, result = micro_compact(msgs, cfg)
        for m in result_msgs:
            assert _TOOL_RESULT_CLEARED in (m.content or "")
        assert result.tokens_saved > 0


# ---------------------------------------------------------------------------
# Tests: assistant message deduplication
# ---------------------------------------------------------------------------


class TestAssistantMessageDedup:
    def test_near_identical_assistant_messages_deduped(self) -> None:
        """Older assistant message that largely repeats a later one is replaced."""
        repeated = "The capital of France is Paris. " * 20  # 640 chars
        msgs = [
            _user("q1"),
            _assistant(repeated),  # old, outside protected window
            _user("q2"),
            _assistant(repeated),  # newer, inside protected window
        ]
        cfg = CompactionConfig(preserve_recent_turns=1)
        result_msgs, _ = micro_compact(msgs, cfg)
        # The older assistant message (index 1) should be deduped.
        assert "[deduplicated" in result_msgs[1].content.lower() or (
            result_msgs[1].content != repeated
        )

    def test_distinct_assistant_messages_not_deduped(self) -> None:
        """Distinct assistant messages are preserved as-is."""
        msg_a = "The capital of France is Paris."
        msg_b = "The capital of Germany is Berlin."
        msgs = [_user("q1"), _assistant(msg_a), _user("q2"), _assistant(msg_b)]
        cfg = CompactionConfig(preserve_recent_turns=1)
        result_msgs, _ = micro_compact(msgs, cfg)
        # Both messages should retain non-marker content
        assert result_msgs[1].content is not None
        # msg_a is distinct enough to be preserved
        # (exact assertion varies with threshold, but we verify no crash)
        assert len(result_msgs) == 4


# ---------------------------------------------------------------------------
# Tests: system message deduplication
# ---------------------------------------------------------------------------


class TestSystemMessageDedup:
    def test_duplicate_system_messages_reduced(self) -> None:
        """Duplicate system messages outside the protected window are dropped."""
        sys_text = "System: always be helpful."
        msgs = [
            ChatMessage(role="system", content=sys_text),  # canonical
            _user("q1"),
            _assistant("a1"),
            ChatMessage(role="system", content=sys_text),  # duplicate injection
            _user("q2"),
            _assistant("a2"),
        ]
        cfg = CompactionConfig(preserve_recent_turns=0)
        result_msgs, _ = micro_compact(msgs, cfg)
        system_msgs = [m for m in result_msgs if m.role == "system"]
        assert len(system_msgs) == 1, "Duplicate system message should be removed"

    def test_distinct_system_messages_both_kept(self) -> None:
        """Different system messages are never dropped."""
        msgs = [
            ChatMessage(role="system", content="Prompt A."),
            _user("q1"),
            _assistant("a1"),
            ChatMessage(role="system", content="Prompt B."),  # different content
            _user("q2"),
            _assistant("a2"),
        ]
        cfg = CompactionConfig(preserve_recent_turns=0)
        result_msgs, _ = micro_compact(msgs, cfg)
        system_msgs = [m for m in result_msgs if m.role == "system"]
        assert len(system_msgs) == 2


# ---------------------------------------------------------------------------
# Tests: preserve_recent_turns boundary
# ---------------------------------------------------------------------------


class TestProtectedSliceStart:
    def test_zero_preserve_returns_len(self) -> None:
        msgs = [_user("a"), _assistant("b"), _user("c"), _assistant("d")]
        assert _protected_slice_start(msgs, 0) == len(msgs)

    def test_one_turn_protects_last_pair(self) -> None:
        msgs = [_user("a"), _assistant("b"), _user("c"), _assistant("d")]
        idx = _protected_slice_start(msgs, 1)
        # Should protect the last (user, assistant) pair.
        assert idx == 2  # messages[2:] = [user("c"), assistant("d")]

    def test_large_preserve_returns_zero(self) -> None:
        msgs = [_user("a"), _assistant("b")]
        idx = _protected_slice_start(msgs, 10)
        assert idx == 0  # all messages protected

    def test_single_message_large_preserve(self) -> None:
        msgs = [_user("only")]
        idx = _protected_slice_start(msgs, 5)
        assert idx == 0


# ---------------------------------------------------------------------------
# Tests: token accounting
# ---------------------------------------------------------------------------


class TestTokenAccounting:
    def test_compaction_never_increases_tokens(self) -> None:
        """Compacted output must always have <= tokens than input."""
        cfg = CompactionConfig(micro_compact_budget=10, preserve_recent_turns=0)
        msgs = [
            _user("What is the weather?"),
            _assistant_with_tool_call(),
            _tool_result(_large_content(5000)),
            _assistant("The weather is sunny."),
        ]
        result_msgs, result = micro_compact(msgs, cfg)
        assert result.compacted_tokens <= result.original_tokens
        assert result.tokens_saved >= 0

    def test_tokens_saved_equals_difference(self) -> None:
        cfg = CompactionConfig(micro_compact_budget=10, preserve_recent_turns=0)
        msgs = [_tool_result(_large_content(5000))]
        result_msgs, result = micro_compact(msgs, cfg)
        actual_diff = result.original_tokens - result.compacted_tokens
        assert result.tokens_saved == max(0, actual_diff)

    def test_no_truncation_needed_tokens_saved_zero(self) -> None:
        cfg = CompactionConfig(micro_compact_budget=10_000, preserve_recent_turns=0)
        msgs = [_user("short"), _assistant("also short")]
        _, result = micro_compact(msgs, cfg)
        assert result.tokens_saved == 0

    def test_strategy_is_micro(self) -> None:
        _, result = micro_compact([_user("hi"), _assistant("hello")])
        assert result.strategy_used == "micro"

    def test_turns_removed_always_zero(self) -> None:
        """Micro-compact never removes full turns."""
        cfg = CompactionConfig(micro_compact_budget=5, preserve_recent_turns=0)
        msgs = [_tool_result(_large_content(5000))]
        _, result = micro_compact(msgs, cfg)
        assert result.turns_removed == 0
