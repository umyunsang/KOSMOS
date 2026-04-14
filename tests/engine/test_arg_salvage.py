# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the K-EXAONE whitespace-argument salvage helper.

Covers the degenerate argument patterns observed during Phase 1 live
validation (spec 019) where FriendliAI Serverless + vLLM Hermes tool parser
emits whitespace-only Korean tool arguments (upstream bug
vllm-project/vllm#10979). The salvage helper rewrites geocoding tool_call
arguments using the most recent user message as the verbatim ``address``.
"""

from __future__ import annotations

import json

import pytest

from kosmos.engine.query import (
    _args_need_salvage,
    _latest_user_text,
    _salvage_address_args,
)
from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall


def _make_call(name: str, arguments: str) -> ToolCall:
    return ToolCall(id="call_1", function=FunctionCall(name=name, arguments=arguments))


@pytest.mark.parametrize(
    "arguments",
    [
        "",
        "{}",
        '{"address":  }',
        '{"address": ""}',
        '{"address": "   "}',
        '{"address": null}',
        "not-json-at-all",
    ],
)
def test_args_need_salvage_detects_degenerate(arguments: str) -> None:
    assert _args_need_salvage(arguments) is True


@pytest.mark.parametrize(
    "arguments",
    [
        '{"address": "강남역"}',
        '{"address": "서울시 강남구"}',
    ],
)
def test_args_need_salvage_leaves_valid_alone(arguments: str) -> None:
    assert _args_need_salvage(arguments) is False


def test_latest_user_text_returns_most_recent() -> None:
    snapshot = [
        ChatMessage(role="system", content="You are KOSMOS."),
        ChatMessage(role="user", content="first"),
        ChatMessage(role="assistant", content="ack"),
        ChatMessage(role="user", content="강남역 근처 사고 정보 알려줘"),
    ]
    assert _latest_user_text(snapshot) == "강남역 근처 사고 정보 알려줘"


def test_latest_user_text_strips_whitespace() -> None:
    snapshot = [ChatMessage(role="user", content="  서울시 강남구  ")]
    assert _latest_user_text(snapshot) == "서울시 강남구"


def test_latest_user_text_returns_empty_when_absent() -> None:
    snapshot = [ChatMessage(role="system", content="only system")]
    assert _latest_user_text(snapshot) == ""


def test_salvage_repairs_whitespace_arguments_for_address_to_region() -> None:
    snapshot = [ChatMessage(role="user", content="강남역 근처 사고 정보 알려줘")]
    calls = [_make_call("address_to_region", '{"address":  }')]

    repaired = _salvage_address_args(calls, snapshot)

    assert len(repaired) == 1
    args = json.loads(repaired[0].function.arguments)
    assert args == {"address": "강남역 근처 사고 정보 알려줘"}


def test_salvage_repairs_address_to_grid_with_empty_string() -> None:
    snapshot = [ChatMessage(role="user", content="강남역 근처 날씨")]
    calls = [_make_call("address_to_grid", '{"address": ""}')]

    repaired = _salvage_address_args(calls, snapshot)

    args = json.loads(repaired[0].function.arguments)
    assert args == {"address": "강남역 근처 날씨"}


def test_salvage_leaves_non_geocoding_tools_alone() -> None:
    snapshot = [ChatMessage(role="user", content="hello")]
    calls = [_make_call("koroad_accident_search", '{"si_do": 11, "gu_gun": 680}')]

    repaired = _salvage_address_args(calls, snapshot)

    assert repaired[0].function.arguments == '{"si_do": 11, "gu_gun": 680}'


def test_salvage_leaves_valid_geocoding_args_alone() -> None:
    snapshot = [ChatMessage(role="user", content="should be ignored")]
    calls = [_make_call("address_to_region", '{"address": "강남역"}')]

    repaired = _salvage_address_args(calls, snapshot)

    args = json.loads(repaired[0].function.arguments)
    assert args == {"address": "강남역"}


def test_salvage_no_user_message_returns_original_list() -> None:
    snapshot = [ChatMessage(role="system", content="no user yet")]
    calls = [_make_call("address_to_region", '{"address":  }')]

    repaired = _salvage_address_args(calls, snapshot)

    assert repaired is calls
    assert repaired[0].function.arguments == '{"address":  }'


def test_salvage_preserves_tool_call_id_and_name() -> None:
    snapshot = [ChatMessage(role="user", content="서귀포시")]
    calls = [
        ToolCall(
            id="call_xyz",
            function=FunctionCall(name="address_to_region", arguments="{}"),
        )
    ]

    repaired = _salvage_address_args(calls, snapshot)

    assert repaired[0].id == "call_xyz"
    assert repaired[0].function.name == "address_to_region"
    assert json.loads(repaired[0].function.arguments) == {"address": "서귀포시"}
