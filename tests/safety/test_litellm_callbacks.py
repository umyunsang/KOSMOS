# SPDX-License-Identifier: Apache-2.0
"""T028 + T032 — Tests for kosmos.safety._litellm_callbacks.

Covers:
  - test_block_returns_block_decision: block fixtures → ModerationBlockError
  - test_self_harm_substitutes_crisis_hotline: self-harm block → 1393 + 1366
  - test_pass_returns_allow: pass fixtures → unchanged kwargs (no exception)
  - test_moderation_outage_fail_open: TransportError → allow + ModerationWarnedEvent
  - test_post_call_output_moderation: post_call blocks flagged completion text
  - test_emit_safety_event_called_once_on_block: emit_safety_event called exactly once
  - test_emit_safety_event_called_once_on_outage_warn: emit called once on outage
  - test_emit_safety_event_not_called_on_allow: emit NOT called on allow path
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from pydantic import SecretStr

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "safety"

# ---------------------------------------------------------------------------
# Helpers to build minimal OpenAI moderation JSON responses
# ---------------------------------------------------------------------------

_ALL_CATS = [
    "harassment",
    "harassment/threatening",
    "hate",
    "hate/threatening",
    "illicit",
    "illicit/violent",
    "self-harm",
    "self-harm/instructions",
    "self-harm/intent",
    "sexual",
    "sexual/minors",
    "violence",
    "violence/graphic",
]


def _make_moderation_response(flagged_keys: list[str]) -> dict[str, Any]:
    """Return a minimal OpenAI moderation JSON response dict.

    Args:
        flagged_keys: JSON key strings (e.g. ``["hate"]`` or ``["self-harm"]``)
            to mark as True.  All others default to False.
    """
    cats = {k: (k in flagged_keys) for k in _ALL_CATS}
    scores = {k: (1.0 if k in flagged_keys else 0.0) for k in _ALL_CATS}
    applied = {k: ["text"] for k in _ALL_CATS}
    return {
        "id": "modr-test",
        "model": "omni-moderation-latest",
        "results": [
            {
                "flagged": bool(flagged_keys),
                "categories": cats,
                "category_applied_input_types": applied,
                "category_scores": scores,
            }
        ],
    }


def _block_flags_for_category(category: str) -> list[str]:
    """Map a fixture ``category`` field to the JSON key(s) to flag."""
    mapping: dict[str, list[str]] = {
        "hate": ["hate"],
        "violence": ["violence"],
        "self-harm": ["self-harm"],
        "sexual/minors": ["sexual/minors"],
        "weapons": ["illicit/violent"],
    }
    return mapping[category]


def _make_kwargs(content: str) -> dict[str, Any]:
    return {
        "model": "kosmos-test",
        "messages": [{"role": "user", "content": content}],
    }


# ---------------------------------------------------------------------------
# Fixtures loader
# ---------------------------------------------------------------------------


def _load_block_fixtures() -> list[dict[str, Any]]:
    path = FIXTURES_DIR / "moderation_block_samples.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _load_pass_fixtures() -> list[dict[str, Any]]:
    path = FIXTURES_DIR / "moderation_pass_samples.json"
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Context manager: enable moderation with a fake key via monkeypatch
# ---------------------------------------------------------------------------


def _patch_moderation_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch settings.safety so moderation_enabled=True with a fake key."""
    from unittest.mock import MagicMock

    fake_safety = MagicMock()
    fake_safety.moderation_enabled = True
    fake_safety.openai_moderation_api_key = SecretStr("sk-test-fake")

    import kosmos.settings as _settings_mod

    monkeypatch.setattr(_settings_mod.settings, "safety", fake_safety)


# ---------------------------------------------------------------------------
# T028 — test_block_returns_block_decision
# ---------------------------------------------------------------------------


_block_fixtures = _load_block_fixtures()


@pytest.mark.parametrize("fixture", _block_fixtures, ids=[f["id"] for f in _block_fixtures])
def test_block_returns_block_decision(
    fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each block fixture causes pre_call to raise ModerationBlockError."""
    _patch_moderation_enabled(monkeypatch)
    flagged_keys = _block_flags_for_category(fixture["category"])
    mock_response = _make_moderation_response(flagged_keys)

    from kosmos.safety._litellm_callbacks import ModerationBlockError, pre_call

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        kwargs = _make_kwargs(fixture["input_text"])
        with pytest.raises(ModerationBlockError) as exc_info:
            pre_call(kwargs)

    err = exc_info.value
    assert len(err.categories) >= 1, "ModerationBlockError must carry at least one category"


# ---------------------------------------------------------------------------
# T028 — test_self_harm_substitutes_crisis_hotline
# ---------------------------------------------------------------------------


def test_self_harm_substitutes_crisis_hotline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Self-harm block → ModerationBlockError.substitution contains 1393 and 1366."""
    _patch_moderation_enabled(monkeypatch)

    block_fixtures = _load_block_fixtures()
    self_harm_fixture = next(f for f in block_fixtures if f["category"] == "self-harm")
    mock_response = _make_moderation_response(["self-harm"])

    from kosmos.safety._litellm_callbacks import ModerationBlockError, pre_call

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        kwargs = _make_kwargs(self_harm_fixture["input_text"])
        with pytest.raises(ModerationBlockError) as exc_info:
            pre_call(kwargs)

    err = exc_info.value
    assert err.substitution is not None, "Self-harm block must have a substitution body"
    assert "1393" in err.substitution, "Crisis-hotline body must include 1393 (중앙자살예방센터)"
    assert "1366" in err.substitution, "Crisis-hotline body must include 1366 (여성긴급전화)"


# ---------------------------------------------------------------------------
# T028 — test_pass_returns_allow
# ---------------------------------------------------------------------------


_pass_fixtures = _load_pass_fixtures()


@pytest.mark.parametrize("fixture", _pass_fixtures, ids=[f["id"] for f in _pass_fixtures])
def test_pass_returns_allow(
    fixture: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pass fixtures → pre_call returns unchanged kwargs without raising."""
    _patch_moderation_enabled(monkeypatch)
    mock_response = _make_moderation_response([])  # all False

    from kosmos.safety._litellm_callbacks import pre_call

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        kwargs = _make_kwargs(fixture["input_text"])
        result = pre_call(kwargs)

    assert result is kwargs, "pre_call must return kwargs unchanged on allow"


# ---------------------------------------------------------------------------
# T028 — test_moderation_outage_fail_open
# ---------------------------------------------------------------------------


def test_moderation_outage_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TransportError → fail-open: pre_call returns kwargs unchanged + warn event emitted."""
    _patch_moderation_enabled(monkeypatch)

    # Track emit_safety_event calls
    emitted_events: list[Any] = []

    import kosmos.safety._litellm_callbacks as _cb_mod

    monkeypatch.setattr(_cb_mod, "emit_safety_event", lambda evt: emitted_events.append(evt))

    from kosmos.safety._litellm_callbacks import pre_call
    from kosmos.safety._models import ModerationWarnedEvent

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(side_effect=httpx.TransportError("simulated outage"))
        kwargs = _make_kwargs("테스트 입력")
        result = pre_call(kwargs)

    assert result is kwargs, "Fail-open: pre_call must return kwargs on outage"
    assert len(emitted_events) == 1, "Exactly one event must be emitted on outage"
    event = emitted_events[0]
    assert isinstance(event, ModerationWarnedEvent), "Emitted event must be ModerationWarnedEvent"
    assert event.detail == "outage", "ModerationWarnedEvent.detail must be 'outage'"


# ---------------------------------------------------------------------------
# T028 — test_post_call_output_moderation
# ---------------------------------------------------------------------------


def test_post_call_output_moderation_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """post_call raises ModerationBlockError for a flagged LLM completion."""
    _patch_moderation_enabled(monkeypatch)
    mock_response = _make_moderation_response(["hate"])

    from kosmos.safety._litellm_callbacks import ModerationBlockError, post_call

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        kwargs = _make_kwargs("irrelevant")
        with pytest.raises(ModerationBlockError):
            post_call(kwargs, "혐오 발언이 포함된 응답 텍스트")


def test_post_call_output_moderation_allow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """post_call returns response unchanged when all categories are False."""
    _patch_moderation_enabled(monkeypatch)
    mock_response = _make_moderation_response([])

    from kosmos.safety._litellm_callbacks import post_call

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        kwargs = _make_kwargs("irrelevant")
        clean_response = "안전한 공공서비스 응답입니다."
        result = post_call(kwargs, clean_response)

    assert result is clean_response, "post_call must return response unchanged on allow"


def test_post_call_outage_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """post_call: TransportError → fail-open, returns response unchanged + warn event."""
    _patch_moderation_enabled(monkeypatch)

    emitted_events: list[Any] = []
    import kosmos.safety._litellm_callbacks as _cb_mod

    monkeypatch.setattr(_cb_mod, "emit_safety_event", lambda evt: emitted_events.append(evt))

    from kosmos.safety._litellm_callbacks import post_call
    from kosmos.safety._models import ModerationWarnedEvent

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(side_effect=httpx.TransportError("simulated outage"))
        kwargs = _make_kwargs("irrelevant")
        clean_response = "정상 응답"
        result = post_call(kwargs, clean_response)

    assert result is clean_response
    assert len(emitted_events) == 1
    assert isinstance(emitted_events[0], ModerationWarnedEvent)
    assert emitted_events[0].detail == "outage"


# ---------------------------------------------------------------------------
# T032 — Span-emission contract: emit_safety_event call counts
# ---------------------------------------------------------------------------


def test_emit_safety_event_called_once_on_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pre_call emits emit_safety_event exactly once on a block path."""
    _patch_moderation_enabled(monkeypatch)

    emitted_events: list[Any] = []
    import kosmos.safety._litellm_callbacks as _cb_mod

    monkeypatch.setattr(_cb_mod, "emit_safety_event", lambda evt: emitted_events.append(evt))

    from kosmos.safety._litellm_callbacks import ModerationBlockError, pre_call
    from kosmos.safety._models import ModerationBlockedEvent

    mock_response = _make_moderation_response(["violence"])

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        with pytest.raises(ModerationBlockError):
            pre_call(_make_kwargs("폭력적인 내용"))

    assert len(emitted_events) == 1, "Exactly one event emitted per block pre_call"
    assert isinstance(emitted_events[0], ModerationBlockedEvent)


def test_emit_safety_event_called_once_on_outage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pre_call emits emit_safety_event exactly once on outage (warn) path."""
    _patch_moderation_enabled(monkeypatch)

    emitted_events: list[Any] = []
    import kosmos.safety._litellm_callbacks as _cb_mod

    monkeypatch.setattr(_cb_mod, "emit_safety_event", lambda evt: emitted_events.append(evt))

    from kosmos.safety._litellm_callbacks import pre_call

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(side_effect=httpx.TransportError("outage"))
        pre_call(_make_kwargs("테스트"))

    assert len(emitted_events) == 1, "Exactly one event emitted per outage pre_call"


def test_emit_safety_event_not_called_on_allow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pre_call emits zero events on the allow path."""
    _patch_moderation_enabled(monkeypatch)

    emitted_events: list[Any] = []
    import kosmos.safety._litellm_callbacks as _cb_mod

    monkeypatch.setattr(_cb_mod, "emit_safety_event", lambda evt: emitted_events.append(evt))

    from kosmos.safety._litellm_callbacks import pre_call

    mock_response = _make_moderation_response([])

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        pre_call(_make_kwargs("자살 예방 상담 전화"))

    assert len(emitted_events) == 0, "No events emitted on allow path"


def test_post_call_emit_once_on_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """post_call emits emit_safety_event exactly once on block."""
    _patch_moderation_enabled(monkeypatch)

    emitted_events: list[Any] = []
    import kosmos.safety._litellm_callbacks as _cb_mod

    monkeypatch.setattr(_cb_mod, "emit_safety_event", lambda evt: emitted_events.append(evt))

    from kosmos.safety._litellm_callbacks import ModerationBlockError, post_call
    from kosmos.safety._models import ModerationBlockedEvent

    mock_response = _make_moderation_response(["sexual/minors"])

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        with pytest.raises(ModerationBlockError):
            post_call(_make_kwargs("irrelevant"), "flagged completion text")

    assert len(emitted_events) == 1
    assert isinstance(emitted_events[0], ModerationBlockedEvent)


def test_post_call_emit_zero_on_allow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """post_call emits zero events on allow path."""
    _patch_moderation_enabled(monkeypatch)

    emitted_events: list[Any] = []
    import kosmos.safety._litellm_callbacks as _cb_mod

    monkeypatch.setattr(_cb_mod, "emit_safety_event", lambda evt: emitted_events.append(evt))

    from kosmos.safety._litellm_callbacks import post_call

    mock_response = _make_moderation_response([])

    with respx.mock(base_url="https://api.openai.com") as mock:
        mock.post("/v1/moderations").mock(return_value=httpx.Response(200, json=mock_response))
        post_call(_make_kwargs("irrelevant"), "clean response text")

    assert len(emitted_events) == 0


# ---------------------------------------------------------------------------
# T028 — moderation disabled → no-op (no HTTP call)
# ---------------------------------------------------------------------------


def test_pre_call_noop_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """When moderation_enabled=False, pre_call returns kwargs without any HTTP call."""
    from unittest.mock import MagicMock

    fake_safety = MagicMock()
    fake_safety.moderation_enabled = False

    import kosmos.settings as _settings_mod

    monkeypatch.setattr(_settings_mod.settings, "safety", fake_safety)

    from kosmos.safety._litellm_callbacks import pre_call

    kwargs = _make_kwargs("anything")
    # No respx mock — if an HTTP call is made, it will error
    result = pre_call(kwargs)
    assert result is kwargs
