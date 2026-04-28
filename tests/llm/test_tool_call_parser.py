# SPDX-License-Identifier: Apache-2.0
"""Tests for the K-EXAONE textual <tool_call> marker parser (Epic #2152).

The four canonical input formats come from the live Epic #2152 P5 smoke run
(specs/2152-system-prompt-redesign/smoke-stdio-*.jsonl). Every test asserts
both extraction (parsed call) and stripping (cleaned text) so the citizen
never sees the marker.
"""

from __future__ import annotations

from kosmos.llm.tool_call_parser import (
    ParsedToolCall,
    extract_textual_tool_calls,
)


def test_no_markers_returns_text_unchanged() -> None:
    text = "안녕하세요. 무엇을 도와드릴까요?"
    calls, cleaned = extract_textual_tool_calls(text)
    assert calls == []
    assert cleaned == text


def test_format1_openai_shape_json() -> None:
    text = (
        '<tool_call>{"name": "resolve_location", "arguments": {"location": "강남역"}}</tool_call>'
    )
    calls, cleaned = extract_textual_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "resolve_location"
    assert calls[0].arguments == {"location": "강남역"}
    assert "<tool_call>" not in cleaned


def test_format3_single_key_dict_with_name_prefix() -> None:
    text = '<tool_call>{"name_nmc_emergency_search": {"query": "근처 응급실"}}</tool_call>'
    calls, _ = extract_textual_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "nmc_emergency_search"
    assert calls[0].arguments == {"query": "근처 응급실"}


def test_format3_single_key_dict_without_prefix() -> None:
    text = '<tool_call>{"resolve_location": {"location": "강남역"}}</tool_call>'
    calls, _ = extract_textual_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "resolve_location"
    assert calls[0].arguments == {"location": "강남역"}


def test_format2_xml_attr_pseudo_json() -> None:
    text = '<tool_call>{"kma_today" name="kma_today" arguments={"location": "서울"}}</tool_call>'
    calls, cleaned = extract_textual_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "kma_today"
    assert calls[0].arguments == {"location": "서울"}
    assert cleaned.strip() == ""


def test_format4_mixed_xml_body() -> None:
    text = (
        "<tool_call>koroad_accident_hotspot_search\n"
        "<arg_key>location</arg_key><arg_value>어린이 보호구역</arg_value>\n"
        "<arg_key>accident_type</arg_key><arg_value>사고 다발</arg_value>\n"
        "</tool_call>"
    )
    calls, _ = extract_textual_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "koroad_accident_hotspot_search"
    assert calls[0].arguments == {
        "location": "어린이 보호구역",
        "accident_type": "사고 다발",
    }


def test_marker_stripped_from_surrounding_prose() -> None:
    text = (
        "기상청 자료를 확인하겠습니다.\n"
        '<tool_call>{"name": "kma_forecast_fetch", '
        '"arguments": {"region": "서울"}}</tool_call>\n'
        "잠시 기다려 주세요."
    )
    calls, cleaned = extract_textual_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "kma_forecast_fetch"
    # The natural-language portions survive; only the marker is removed.
    assert "기상청 자료를 확인하겠습니다" in cleaned
    assert "잠시 기다려 주세요" in cleaned
    assert "<tool_call>" not in cleaned
    assert "</tool_call>" not in cleaned


def test_multiple_markers_in_one_turn() -> None:
    text = (
        '<tool_call>{"name": "resolve_location", '
        '"arguments": {"location": "강남역"}}</tool_call>'
        " 이어서 "
        '<tool_call>{"name": "kma_forecast_fetch", '
        '"arguments": {"region": "서울"}}</tool_call>'
    )
    calls, cleaned = extract_textual_tool_calls(text)
    assert len(calls) == 2
    assert [c.name for c in calls] == ["resolve_location", "kma_forecast_fetch"]
    assert "<tool_call>" not in cleaned


def test_unparseable_block_logged_and_skipped() -> None:
    """A totally unrecognised body is dropped from the parsed list but
    still stripped from the cleaned text — fail-open so the citizen sees
    at least the prose."""
    text = "<tool_call>completely garbled !@#$%^&*()</tool_call>"
    calls, cleaned = extract_textual_tool_calls(text)
    assert calls == []
    assert "<tool_call>" not in cleaned


def test_parsed_tool_call_is_frozen() -> None:
    """ParsedToolCall is a frozen dataclass — immutable contract."""
    import dataclasses

    import pytest

    call = ParsedToolCall(name="x", arguments={"a": 1})
    with pytest.raises(dataclasses.FrozenInstanceError):
        call.name = "y"  # type: ignore[misc]


def test_extract_returns_text_when_only_garbled_marker() -> None:
    """No markers → cleaned == original (identity preservation)."""
    text = "단순 텍스트만 있고 마커는 없음"
    calls, cleaned = extract_textual_tool_calls(text)
    assert calls == []
    assert cleaned is text  # same object — no copy


def test_xml_attr_with_korean_argument_value() -> None:
    """K-EXAONE pseudo-JSON arguments often hold Korean strings — must
    survive json.loads round-trip without escaping."""
    text = '<tool_call>{"x" name="x" arguments={"city": "부산광역시"}}</tool_call>'
    calls, _ = extract_textual_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].arguments == {"city": "부산광역시"}
