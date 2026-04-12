# SPDX-License-Identifier: Apache-2.0
"""Unit tests for kosmos.engine.events — StopReason and QueryEvent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.models import TokenUsage
from kosmos.tools.models import ToolResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_result(*, success: bool = True) -> ToolResult:
    """Return a minimal valid ToolResult."""
    if success:
        return ToolResult(tool_id="test_tool", success=True, data={"key": "value"})
    return ToolResult(
        tool_id="test_tool",
        success=False,
        error="Something went wrong",
        error_type="execution",
    )


def _make_token_usage() -> TokenUsage:
    """Return a minimal valid TokenUsage."""
    return TokenUsage(input_tokens=10, output_tokens=5)


# ===========================================================================
# StopReason
# ===========================================================================


class TestStopReason:
    @pytest.mark.parametrize(
        ("member_name", "expected_value"),
        [
            ("task_complete", "task_complete"),
            ("end_turn", "end_turn"),
            ("needs_citizen_input", "needs_citizen_input"),
            ("needs_authentication", "needs_authentication"),
            ("api_budget_exceeded", "api_budget_exceeded"),
            ("max_iterations_reached", "max_iterations_reached"),
            ("error_unrecoverable", "error_unrecoverable"),
            ("cancelled", "cancelled"),
        ],
    )
    def test_all_enum_values_exist(self, member_name: str, expected_value: str) -> None:
        """All 8 StopReason members must exist with their documented string values."""
        member = StopReason[member_name]
        assert member.value == expected_value

    def test_stop_reason_is_str_enum(self) -> None:
        """StopReason must be a str subclass so it serialises as a plain string."""
        assert isinstance(StopReason.task_complete, str)

    def test_stop_reason_total_count(self) -> None:
        """Exactly 8 StopReason members must be defined."""
        assert len(StopReason) == 8


# ===========================================================================
# QueryEvent — text_delta
# ===========================================================================


class TestQueryEventTextDelta:
    def test_valid_text_delta(self) -> None:
        """A text_delta event with content set must construct without error."""
        event = QueryEvent(type="text_delta", content="Hello world")

        assert event.type == "text_delta"
        assert event.content == "Hello world"

    def test_text_delta_missing_content_raises(self) -> None:
        """A text_delta event without content must raise ValidationError."""
        with pytest.raises(ValidationError, match="content"):
            QueryEvent(type="text_delta")

    def test_text_delta_empty_string_is_valid(self) -> None:
        """An empty string is a valid content value (represents a zero-length delta)."""
        event = QueryEvent(type="text_delta", content="")
        assert event.content == ""


# ===========================================================================
# QueryEvent — tool_use
# ===========================================================================


class TestQueryEventToolUse:
    def test_valid_tool_use_minimal(self) -> None:
        """A tool_use event with tool_name and tool_call_id must construct successfully."""
        event = QueryEvent(
            type="tool_use",
            tool_name="koroad_accident_search",
            tool_call_id="call_abc123",
        )

        assert event.type == "tool_use"
        assert event.tool_name == "koroad_accident_search"
        assert event.tool_call_id == "call_abc123"
        assert event.arguments is None

    def test_valid_tool_use_with_arguments(self) -> None:
        """A tool_use event may include optional JSON-serialized arguments."""
        event = QueryEvent(
            type="tool_use",
            tool_name="koroad_accident_search",
            tool_call_id="call_abc123",
            arguments='{"query": "서울 강남구"}',
        )

        assert event.arguments == '{"query": "서울 강남구"}'

    @pytest.mark.parametrize(
        ("tool_name", "tool_call_id"),
        [
            (None, "call_abc123"),  # tool_name missing
            ("my_tool", None),  # tool_call_id missing
            (None, None),  # both missing
        ],
    )
    def test_tool_use_missing_required_fields_raises(
        self,
        tool_name: str | None,
        tool_call_id: str | None,
    ) -> None:
        """A tool_use event missing tool_name or tool_call_id must raise ValidationError."""
        with pytest.raises(ValidationError):
            QueryEvent(
                type="tool_use",
                tool_name=tool_name,
                tool_call_id=tool_call_id,
            )


# ===========================================================================
# QueryEvent — tool_result
# ===========================================================================


class TestQueryEventToolResult:
    def test_valid_tool_result_success(self) -> None:
        """A tool_result event with a successful ToolResult must construct correctly."""
        tr = _make_tool_result(success=True)
        event = QueryEvent(type="tool_result", tool_result=tr)

        assert event.type == "tool_result"
        assert event.tool_result is tr

    def test_valid_tool_result_failure(self) -> None:
        """A tool_result event wrapping a failed ToolResult must also be valid."""
        tr = _make_tool_result(success=False)
        event = QueryEvent(type="tool_result", tool_result=tr)

        assert event.tool_result.success is False

    def test_tool_result_missing_tool_result_raises(self) -> None:
        """A tool_result event without tool_result set must raise ValidationError."""
        with pytest.raises(ValidationError, match="tool_result"):
            QueryEvent(type="tool_result")


# ===========================================================================
# QueryEvent — usage_update
# ===========================================================================


class TestQueryEventUsageUpdate:
    def test_valid_usage_update(self) -> None:
        """A usage_update event with a TokenUsage must construct without error."""
        usage = _make_token_usage()
        event = QueryEvent(type="usage_update", usage=usage)

        assert event.type == "usage_update"
        assert event.usage is usage
        assert event.usage.input_tokens == 10
        assert event.usage.output_tokens == 5

    def test_usage_update_missing_usage_raises(self) -> None:
        """A usage_update event without usage set must raise ValidationError."""
        with pytest.raises(ValidationError, match="usage"):
            QueryEvent(type="usage_update")


# ===========================================================================
# QueryEvent — stop
# ===========================================================================


class TestQueryEventStop:
    @pytest.mark.parametrize("reason", list(StopReason))
    def test_valid_stop_all_reasons(self, reason: StopReason) -> None:
        """A stop event must be constructable for every StopReason value."""
        event = QueryEvent(type="stop", stop_reason=reason)

        assert event.type == "stop"
        assert event.stop_reason == reason

    def test_stop_missing_stop_reason_raises(self) -> None:
        """A stop event without stop_reason must raise ValidationError."""
        with pytest.raises(ValidationError, match="stop_reason"):
            QueryEvent(type="stop")

    def test_stop_with_optional_message(self) -> None:
        """A stop event may include an optional stop_message string."""
        event = QueryEvent(
            type="stop",
            stop_reason=StopReason.error_unrecoverable,
            stop_message="Upstream API returned HTTP 500 three times.",
        )

        assert event.stop_message == "Upstream API returned HTTP 500 three times."

    def test_stop_without_message_defaults_to_none(self) -> None:
        """When stop_message is omitted it must default to None."""
        event = QueryEvent(type="stop", stop_reason=StopReason.end_turn)

        assert event.stop_message is None


# ===========================================================================
# QueryEvent — immutability (frozen model)
# ===========================================================================


class TestQueryEventFrozen:
    def test_frozen_prevents_attribute_assignment(self) -> None:
        """Assigning to a field after construction must raise an error (frozen model)."""
        event = QueryEvent(type="text_delta", content="immutable text")

        with pytest.raises((TypeError, ValidationError)):
            event.content = "mutated"  # type: ignore[misc]

    def test_frozen_prevents_new_attribute(self) -> None:
        """Setting a new attribute on a frozen model must also raise."""
        event = QueryEvent(type="text_delta", content="some content")

        with pytest.raises((TypeError, ValidationError)):
            event.new_field = "should not work"  # type: ignore[attr-defined]
