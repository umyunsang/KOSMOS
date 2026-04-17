# SPDX-License-Identifier: Apache-2.0
"""Equivalence regression test: session_compact() output vs pre-refactor golden.

T014 — Phase 3.2 RED test.

After ``prompts/compact_v1.md`` and the ``PromptLoader``-backed
``_build_summary_text`` refactor land (T028 / T031), the refactored
``session_compact()`` must produce output that is byte-identical to the
pre-refactor golden fixture captured in T004.

This test is intentionally RED until that refactor is complete:
the test file itself is the contract that ensures equivalence and
prevents drift between the two implementations.

WHY BYTES:
  The golden fixture was captured from the exact inline ``_SUMMARY_HEADER``
  + section-scaffold code path.  Any whitespace, newline, or header change
  introduced by the refactor would silently break the API contract.
  Byte-level comparison catches every such deviation.

TRANSCRIPT RECONSTRUCTION:
  The fixture was produced from a 13-message input:
    [0]  system  — canonical system prompt
    [1]  user    — "서울 강남구 응급실 알려줘"    (compacted)
    [2]  assistant (tool_calls only, no content) — nmc_emergency_search Seoul (compacted)
    [3]  tool    call_1 — Seoul ER search result  (compacted)
    [4]  assistant content "<20 chars, below _extract threshold>" (compacted)
    [5]  user    — "그럼 부산 쪽은?"              (compacted)
    [6]  assistant (tool_calls only, no content) — nmc_emergency_search Busan (compacted)
    [7]  tool    call_2 — Busan ER search result  (compacted)
    [8]  assistant content "<20 chars, below _extract threshold>" (compacted)
    [9]  user    — protected turn 1 opener
    [10] assistant — protected turn 1 reply
    [11] user    — protected turn 2 opener
    [12] assistant — protected turn 2 reply

  With preserve_recent_turns=2, _protected_slice_start walks backward and
  finds pairs (11,12) then (9,10), returning protect_from=9.
  messages[1:9] are compacted; messages[9:] are preserved.

CONFIG:
  CompactionConfig(
      max_context_tokens=500,
      compact_trigger_ratio=0.5,
      micro_compact_budget=100,
      summary_max_tokens=2000,
      preserve_recent_turns=2,
  )
"""

from __future__ import annotations

import pathlib

import pytest

from kosmos.context.compact_models import CompactionConfig
from kosmos.context.session_compact import session_compact
from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall

# ---------------------------------------------------------------------------
# Prompt-file precondition
# ---------------------------------------------------------------------------

# T014 RED precondition: compact_v1.md must exist before the refactored path
# (T031) can load section labels from it.  The test module-level assert below
# enforces that — it deliberately fails RED until T028 authors the file and
# T031 wires it into session_compact() via PromptLoader.
_COMPACT_PROMPT_PATH = pathlib.Path(__file__).parent.parent.parent / "prompts" / "compact_v1.md"

# Raise at collection time so the test runner shows a clear RED error.
if not _COMPACT_PROMPT_PATH.exists():
    pytest.fail(
        f"RED (T014 precondition): prompts/compact_v1.md not found at "
        f"{_COMPACT_PROMPT_PATH}. "
        "Author this file in T028 and wire it into session_compact() in T031 "
        "before this test can go GREEN.",
        pytrace=False,
    )

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

_FIXTURE_PATH = pathlib.Path(__file__).parent / "fixtures" / "session_compact_pre_refactor.txt"

# ---------------------------------------------------------------------------
# Transcript reconstruction
# ---------------------------------------------------------------------------

_CONFIG = CompactionConfig(
    max_context_tokens=500,
    compact_trigger_ratio=0.5,
    micro_compact_budget=100,
    summary_max_tokens=2000,
    preserve_recent_turns=2,
)


def _build_transcript() -> list[ChatMessage]:
    """Reconstruct the exact 13-message transcript that produced the golden fixture.

    Korean strings in the user/tool content are domain data (NFR-05 exception).
    All test code identifiers and docstrings are in English.
    """
    return [
        # [0] canonical system prompt — preserved at index 0, not compacted
        ChatMessage(role="system", content="You are KOSMOS, a Korean public-service assistant."),
        # [1] first user turn — goes into compacted window
        ChatMessage(role="user", content="서울 강남구 응급실 알려줘"),
        # [2] assistant issues tool call, no text content — compacted
        ChatMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_1",
                    type="function",
                    function=FunctionCall(
                        name="nmc_emergency_search",
                        arguments='{"region":"서울"}',
                    ),
                )
            ],
        ),
        # [3] tool result for call_1 — compacted
        ChatMessage(
            role="tool",
            content="서울대병원 응급실, 연세세브란스 응급실 검색 결과",
            tool_call_id="call_1",
        ),
        # [4] assistant short reply (< 40 chars) — below decision threshold, compacted
        ChatMessage(role="assistant", content="확인했어요."),
        # [5] second user turn — compacted
        ChatMessage(role="user", content="그럼 부산 쪽은?"),
        # [6] assistant issues second tool call, no text content — compacted
        ChatMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_2",
                    type="function",
                    function=FunctionCall(
                        name="nmc_emergency_search",
                        arguments='{"region":"부산"}',
                    ),
                )
            ],
        ),
        # [7] tool result for call_2 — compacted
        ChatMessage(
            role="tool",
            content="부산대병원 응급실 검색 결과",
            tool_call_id="call_2",
        ),
        # [8] assistant short reply — below threshold, compacted
        ChatMessage(role="assistant", content="알겠습니다."),
        # [9–10] protected turn 1 (preserve_recent_turns=2 keeps this pair)
        ChatMessage(role="user", content="감사합니다."),
        ChatMessage(role="assistant", content="도움이 되어 기쁩니다."),
        # [11–12] protected turn 2
        ChatMessage(role="user", content="다른 지역도 알려줘."),
        ChatMessage(role="assistant", content="네, 알려드리겠습니다."),
    ]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_session_compact_matches_golden_after_refactor() -> None:
    """Byte-identical equivalence between refactored and pre-refactor session_compact output.

    FAILS RED until ``prompts/compact_v1.md`` + ``PromptLoader`` refactor land
    (T028 / T031).  Once those tasks are complete, this test must go GREEN
    without any modification — proving that the refactored summary assembly
    is semantically and byte-exactly equivalent to the original inline path.

    Assertion:
        The ``summary_generated`` field of the CompactionResult returned by
        ``session_compact()`` must equal (UTF-8 bytes) the contents of
        ``tests/context/fixtures/session_compact_pre_refactor.txt``.
    """
    assert _FIXTURE_PATH.exists(), (
        f"Pre-refactor golden fixture not found: {_FIXTURE_PATH}\n"
        "Run T004 fixture capture step first."
    )

    golden_bytes: bytes = _FIXTURE_PATH.read_bytes()

    transcript = _build_transcript()
    _new_messages, result = session_compact(messages=transcript, config=_CONFIG)

    assert result.summary_generated is not None, (
        "session_compact() returned no summary_generated — "
        "compaction may not have fired or the transcript reconstruction is wrong."
    )

    actual_bytes: bytes = result.summary_generated.encode("utf-8")

    assert actual_bytes == golden_bytes, (
        "session_compact() summary does not match pre-refactor golden fixture.\n"
        f"Fixture path : {_FIXTURE_PATH}\n"
        f"Fixture bytes: {len(golden_bytes)}\n"
        f"Actual bytes : {len(actual_bytes)}\n\n"
        "--- Expected (golden) ---\n"
        f"{golden_bytes.decode('utf-8', errors='replace')}\n"
        "--- Actual ---\n"
        f"{result.summary_generated}"
    )
