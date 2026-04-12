# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the KOSMOS Query Engine preprocessing pipeline.

Tests cover all four stages individually and the PreprocessingPipeline
orchestrator.  No live API calls; all inputs are constructed inline.
"""

from __future__ import annotations

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.preprocessing import (
    PreprocessingPipeline,
    stage_collapse,
    stage_microcompact,
    stage_snip,
    stage_tool_result_budget,
)
from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tool_msg(content: str, call_id: str = "call_1") -> ChatMessage:
    """Build a minimal role='tool' message."""
    return ChatMessage(role="tool", content=content, tool_call_id=call_id)


def _user_msg(content: str) -> ChatMessage:
    return ChatMessage(role="user", content=content)


def _assistant_msg(content: str) -> ChatMessage:
    return ChatMessage(role="assistant", content=content)


def _system_msg(content: str) -> ChatMessage:
    return ChatMessage(role="system", content=content)


def _assistant_with_tool_calls(call_id: str = "call_tc") -> ChatMessage:
    """Build an assistant message carrying tool_calls."""
    tc = ToolCall(
        id=call_id,
        type="function",
        function=FunctionCall(name="some_tool", arguments="{}"),
    )
    return ChatMessage(role="assistant", content=None, tool_calls=[tc])


# ---------------------------------------------------------------------------
# Stage 1: stage_tool_result_budget
# ---------------------------------------------------------------------------


def test_tool_result_budget_unchanged_when_under_budget() -> None:
    """Tool result under the token budget is returned unmodified."""
    config = QueryEngineConfig(tool_result_budget=2000)
    short_content = "Short result."
    msgs = [_tool_msg(short_content)]

    result = stage_tool_result_budget(msgs, config, current_turn=1)

    assert len(result) == 1
    assert result[0].content == short_content


def test_tool_result_budget_truncates_oversized() -> None:
    """Tool result exceeding the budget is truncated with a [truncated] marker."""
    # budget = 5 tokens, inverse heuristic: char_limit = 5 * 3 = 15 chars
    config = QueryEngineConfig(tool_result_budget=5)
    long_content = "A" * 200  # 200 chars / 4 chars-per-token = 50 tokens >> 5
    msgs = [_tool_msg(long_content)]

    result = stage_tool_result_budget(msgs, config, current_turn=1)

    assert len(result) == 1
    assert "[truncated:" in result[0].content
    assert result[0].tool_call_id == "call_1"
    # Must be shorter than original
    assert len(result[0].content) < len(long_content) + 40  # marker is small


def test_tool_result_budget_preserves_tool_call_id() -> None:
    """Truncated tool message retains its original tool_call_id."""
    config = QueryEngineConfig(tool_result_budget=5)
    long_content = "B" * 200
    msgs = [_tool_msg(long_content, call_id="call_xyz")]

    result = stage_tool_result_budget(msgs, config, current_turn=0)

    assert result[0].tool_call_id == "call_xyz"


def test_tool_result_budget_non_tool_never_modified() -> None:
    """User, assistant, and system messages are never touched."""
    config = QueryEngineConfig(tool_result_budget=5)
    msgs = [
        _system_msg("You are KOSMOS."),
        _user_msg("Hello " * 200),  # very long user content
        _assistant_msg("Response " * 200),
    ]
    original_contents = [m.content for m in msgs]

    result = stage_tool_result_budget(msgs, config, current_turn=1)

    assert [m.content for m in result] == original_contents


def test_tool_result_budget_empty_content_unchanged() -> None:
    """A tool message with empty string content is left unchanged."""
    config = QueryEngineConfig(tool_result_budget=10)
    # ChatMessage role='tool' requires tool_call_id; content may be None or ''
    # The stage checks `msg.content` truthiness, so empty string passes through
    msgs = [ChatMessage(role="tool", content="", tool_call_id="call_empty")]

    result = stage_tool_result_budget(msgs, config, current_turn=0)

    assert result[0].content == ""


def test_tool_result_budget_only_oversized_messages_truncated() -> None:
    """With mixed tool results, only the oversized one is truncated."""
    config = QueryEngineConfig(tool_result_budget=5)
    small_content = "tiny"  # 4 chars / 4 = 1 token — under budget
    large_content = "X" * 400  # 400 / 4 = 100 tokens — over budget

    msgs = [
        _tool_msg(small_content, call_id="call_a"),
        _tool_msg(large_content, call_id="call_b"),
    ]
    result = stage_tool_result_budget(msgs, config, current_turn=2)

    assert result[0].content == small_content
    assert "[truncated:" in result[1].content


# ---------------------------------------------------------------------------
# Stage 2: stage_snip
# ---------------------------------------------------------------------------


def test_stage_snip_fresh_tool_result_preserved() -> None:
    """Tool results within the snip_turn_age threshold are kept."""
    config = QueryEngineConfig(snip_turn_age=5)
    # current_turn=1, user_turns_seen=1 → age = 1 - 1 = 0 < 5
    msgs = [
        _user_msg("query"),
        _tool_msg("fresh result"),
    ]

    result = stage_snip(msgs, config, current_turn=1)

    assert any(m.role == "tool" for m in result)


def test_stage_snip_stale_tool_result_removed() -> None:
    """Tool result with turn_age >= threshold is removed."""
    config = QueryEngineConfig(snip_turn_age=5)
    # user_turns_seen=1 after the user message; current_turn=10 → age=9 >= 5
    msgs = [
        _user_msg("old query"),
        _tool_msg("stale result"),
    ]

    result = stage_snip(msgs, config, current_turn=10)

    assert not any(m.role == "tool" for m in result)


def test_stage_snip_non_tool_messages_always_preserved() -> None:
    """System, user, and assistant messages are never snipped."""
    config = QueryEngineConfig(snip_turn_age=1)
    msgs = [
        _system_msg("system prompt"),
        _user_msg("user message"),
        _assistant_msg("assistant response"),
    ]

    result = stage_snip(msgs, config, current_turn=100)

    assert len(result) == 3
    assert result[0].role == "system"
    assert result[1].role == "user"
    assert result[2].role == "assistant"


def test_stage_snip_exactly_at_threshold_is_removed() -> None:
    """Edge case: turn_age exactly equal to threshold → removed."""
    config = QueryEngineConfig(snip_turn_age=5)
    # user_turns_seen=1, current_turn=6 → age = 6 - 1 = 5 == threshold
    msgs = [
        _user_msg("query at boundary"),
        _tool_msg("boundary result"),
    ]

    result = stage_snip(msgs, config, current_turn=6)

    assert not any(m.role == "tool" for m in result)


def test_stage_snip_multiple_turns_correct_age_accounting() -> None:
    """Later tool results (closer to current_turn) survive; earlier ones are snipped."""
    config = QueryEngineConfig(snip_turn_age=3)
    # Turn 1: user + tool (age = 5 - 1 = 4 → snipped)
    # Turn 2: user + tool (age = 5 - 2 = 3 → snipped, exactly at threshold)
    # Turn 3: user + tool (age = 5 - 3 = 2 → preserved)
    msgs = [
        _user_msg("q1"),
        _tool_msg("result_t1", call_id="c1"),
        _user_msg("q2"),
        _tool_msg("result_t2", call_id="c2"),
        _user_msg("q3"),
        _tool_msg("result_t3", call_id="c3"),
    ]

    result = stage_snip(msgs, config, current_turn=5)

    tool_messages = [m for m in result if m.role == "tool"]
    tool_ids = [m.tool_call_id for m in tool_messages]
    assert "c3" in tool_ids
    assert "c1" not in tool_ids
    assert "c2" not in tool_ids


# ---------------------------------------------------------------------------
# Stage 3: stage_microcompact
# ---------------------------------------------------------------------------


def test_stage_microcompact_compresses_old_message_whitespace() -> None:
    """Messages older than threshold have their whitespace compressed."""
    config = QueryEngineConfig(microcompact_turn_age=3)
    # user_turns_seen=1, current_turn=10 → age=9 >= 3
    msgs = [
        _user_msg("Hello   World\n\twith   extra  spaces"),
    ]

    result = stage_microcompact(msgs, config, current_turn=10)

    assert result[0].content == "Hello World with extra spaces"


def test_stage_microcompact_recent_message_unchanged() -> None:
    """Messages younger than threshold keep their original whitespace."""
    config = QueryEngineConfig(microcompact_turn_age=3)
    original = "Hello   World\n\nwith   spaces"
    # user_turns_seen=1, current_turn=2 → age=1 < 3
    msgs = [_user_msg(original)]

    result = stage_microcompact(msgs, config, current_turn=2)

    assert result[0].content == original


def test_stage_microcompact_system_messages_never_modified() -> None:
    """System messages are skipped unconditionally."""
    config = QueryEngineConfig(microcompact_turn_age=1)
    original = "You are   KOSMOS  assistant."
    msgs = [_system_msg(original)]

    result = stage_microcompact(msgs, config, current_turn=100)

    assert result[0].content == original


def test_stage_microcompact_already_compact_returns_same_object() -> None:
    """A message already without extra whitespace is not replaced."""
    config = QueryEngineConfig(microcompact_turn_age=1)
    content = "Already compact text."
    msg = _user_msg(content)
    msgs = [msg]

    result = stage_microcompact(msgs, config, current_turn=10)

    # Same object identity — no unnecessary copy
    assert result[0] is msg


def test_stage_microcompact_strips_leading_trailing_whitespace() -> None:
    """Leading and trailing whitespace are stripped from old messages."""
    config = QueryEngineConfig(microcompact_turn_age=1)
    msgs = [_user_msg("  spaces around  ")]

    result = stage_microcompact(msgs, config, current_turn=5)

    assert result[0].content == "spaces around"


def test_stage_microcompact_assistant_message_old_is_compressed() -> None:
    """Old assistant messages (not system) also get whitespace compressed."""
    config = QueryEngineConfig(microcompact_turn_age=2)
    original = "Result   is   here."
    # After the user message, user_turns_seen=1; current_turn=5 → age=4 >= 2
    msgs = [
        _user_msg("q"),
        _assistant_msg(original),
    ]

    result = stage_microcompact(msgs, config, current_turn=5)

    assert result[1].content == "Result is here."


# ---------------------------------------------------------------------------
# Stage 4: stage_collapse
# ---------------------------------------------------------------------------


def test_stage_collapse_merges_consecutive_user_messages() -> None:
    """Two consecutive user messages without tool fields are merged."""
    config = QueryEngineConfig()
    msgs = [
        _user_msg("first"),
        _user_msg("second"),
    ]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 1
    assert result[0].role == "user"
    assert result[0].content == "first\nsecond"


def test_stage_collapse_merges_consecutive_assistant_messages() -> None:
    """Two consecutive assistant messages without tool fields are merged."""
    config = QueryEngineConfig()
    msgs = [
        _assistant_msg("part one"),
        _assistant_msg("part two"),
    ]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 1
    assert result[0].content == "part one\npart two"


def test_stage_collapse_different_roles_not_merged() -> None:
    """Alternating roles are never merged."""
    config = QueryEngineConfig()
    msgs = [
        _user_msg("hello"),
        _assistant_msg("world"),
    ]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 2


def test_stage_collapse_system_messages_never_merged() -> None:
    """Two consecutive system messages must NOT be collapsed."""
    config = QueryEngineConfig()
    msgs = [
        _system_msg("instruction A"),
        _system_msg("instruction B"),
    ]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 2


def test_stage_collapse_tool_messages_never_merged() -> None:
    """Two consecutive tool messages are never collapsed."""
    config = QueryEngineConfig()
    msgs = [
        _tool_msg("result A", call_id="c1"),
        _tool_msg("result B", call_id="c2"),
    ]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 2


def test_stage_collapse_message_with_tool_calls_not_merged() -> None:
    """Assistant message carrying tool_calls is not collapsed with its neighbor."""
    config = QueryEngineConfig()
    msgs = [
        _assistant_with_tool_calls("tc_1"),
        _assistant_msg("plain text"),
    ]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 2


def test_stage_collapse_message_with_tool_call_id_not_merged() -> None:
    """A tool message is not merged even when surrounded by identical-role messages."""
    config = QueryEngineConfig()
    msgs = [
        _tool_msg("r1", call_id="c1"),
        _tool_msg("r2", call_id="c2"),
        _tool_msg("r3", call_id="c3"),
    ]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 3


def test_stage_collapse_empty_list_returns_empty() -> None:
    """Empty input produces empty output."""
    config = QueryEngineConfig()
    result = stage_collapse([], config, current_turn=0)
    assert result == []


def test_stage_collapse_single_message_unchanged() -> None:
    """A single message is returned as-is."""
    config = QueryEngineConfig()
    msgs = [_user_msg("only message")]
    result = stage_collapse(msgs, config, current_turn=0)
    assert len(result) == 1
    assert result[0].content == "only message"


def test_stage_collapse_three_consecutive_user_messages_fully_merged() -> None:
    """Three consecutive user messages collapse into one."""
    config = QueryEngineConfig()
    msgs = [_user_msg("a"), _user_msg("b"), _user_msg("c")]

    result = stage_collapse(msgs, config, current_turn=0)

    assert len(result) == 1
    assert result[0].content == "a\nb\nc"


# ---------------------------------------------------------------------------
# PreprocessingPipeline
# ---------------------------------------------------------------------------


def test_pipeline_default_stages_applied_in_order() -> None:
    """Default pipeline runs all four stages and produces a valid result."""
    config = QueryEngineConfig(
        tool_result_budget=5,  # small budget so truncation fires
        snip_turn_age=2,
        microcompact_turn_age=1,
    )
    # Build a history that exercises all four stages:
    # - oversized tool result (stage 1)
    # - stale tool result (stage 2)
    # - whitespace in old user message (stage 3)
    # - two consecutive user messages (stage 4)
    msgs = [
        _user_msg("old   query"),  # turn 1
        _tool_msg("X" * 500, "c_stale"),  # stale after stage 2
        _user_msg("recent query"),  # turn 2 / recent
        _user_msg("also recent"),  # consecutive → collapse
    ]

    pipeline = PreprocessingPipeline()
    result = pipeline.run(msgs, config, current_turn=5)

    # The stale tool result should be gone
    assert not any(m.role == "tool" for m in result)
    # Old user message should be whitespace-compressed
    old_user = next((m for m in result if m.role == "user" and "old" in (m.content or "")), None)
    if old_user:
        assert "   " not in old_user.content
    # Result list is non-empty
    assert len(result) >= 1


def test_pipeline_does_not_mutate_input_list() -> None:
    """The pipeline must not modify the original messages list."""
    config = QueryEngineConfig()
    msgs = [
        _system_msg("prompt"),
        _user_msg("hello"),
        _assistant_msg("hi"),
    ]
    original_ids = [id(m) for m in msgs]

    pipeline = PreprocessingPipeline()
    pipeline.run(msgs, config, current_turn=1)

    # Original list unchanged in length and object identity
    assert [id(m) for m in msgs] == original_ids
    assert len(msgs) == 3


def test_pipeline_custom_stages_list() -> None:
    """A pipeline with a custom stage list applies only those stages."""
    config = QueryEngineConfig()
    call_log: list[str] = []

    def stage_a(
        messages: list[ChatMessage],
        config: QueryEngineConfig,
        current_turn: int,
    ) -> list[ChatMessage]:
        call_log.append("A")
        return messages

    def stage_b(
        messages: list[ChatMessage],
        config: QueryEngineConfig,
        current_turn: int,
    ) -> list[ChatMessage]:
        call_log.append("B")
        return messages

    msgs = [_user_msg("test")]
    pipeline = PreprocessingPipeline(stages=[stage_a, stage_b])
    pipeline.run(msgs, config, current_turn=0)

    assert call_log == ["A", "B"]


def test_pipeline_empty_stages_returns_copy() -> None:
    """A pipeline with no stages returns a copy of the input list."""
    config = QueryEngineConfig()
    msgs = [_user_msg("hello")]
    pipeline = PreprocessingPipeline(stages=[])
    result = pipeline.run(msgs, config, current_turn=0)

    assert result == msgs
    assert result is not msgs  # shallow copy, not the same list


def test_pipeline_combined_four_stages_no_tool_calls_in_result() -> None:
    """Full pipeline with stale tools: no tool messages remain after snip."""
    config = QueryEngineConfig(
        tool_result_budget=100,
        snip_turn_age=2,
        microcompact_turn_age=10,
    )
    msgs = [
        _user_msg("first turn"),  # turn 1
        _tool_msg("tool result 1", "c1"),  # age will be high
        _user_msg("second turn"),  # turn 2
        _tool_msg("tool result 2", "c2"),  # age will be high
        _user_msg("current"),  # turn 3
    ]

    pipeline = PreprocessingPipeline()
    result = pipeline.run(msgs, config, current_turn=10)

    # All tool results should be snipped (age >= 2)
    assert not any(m.role == "tool" for m in result)
    # Non-tool messages survive
    assert any(m.role == "user" for m in result)
