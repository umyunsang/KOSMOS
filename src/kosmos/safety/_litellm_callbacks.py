# SPDX-License-Identifier: Apache-2.0
"""LiteLLM callback hooks for the KOSMOS content-moderation layer (Layer B).

Exports two LiteLLM-compatible callback functions:

    pre_call(kwargs: dict) -> dict
        Intercepts the user's last message before it is sent to the LLM.
        On a moderation block, raises ModerationBlockError (a LookupError
        subclass), which LiteLLM's callback loop propagates to the caller.
        On a self-harm block, the raised exception carries a crisis-hotline
        substitution body instead.

    post_call(kwargs: dict, response: object) -> object
        Intercepts the LLM's completed response.
        On a flagged completion, raises ModerationBlockError.
        On a self-harm flag, injects the crisis-hotline body into the response
        before raising.

Block signal contract (non-self-harm categories):
    Both hooks raise ``ModerationBlockError``, a ``LookupError`` subclass, so
    LiteLLM's callback loop receives a recognisable exception it can translate
    into a ``LookupError(reason=LookupErrorReason.content_blocked)`` envelope.
    Callers that want to catch only moderation blocks should catch
    ``ModerationBlockError``.

Fail-open deviation (FR-011):
    When the OpenAI Moderation API is unreachable (``httpx.TransportError`` or
    ``openai.APIConnectionError``), the request is **allowed through unchanged**
    and a ``ModerationWarnedEvent(detail="outage")`` is emitted on the active
    span.  This is a deliberate deviation from the general fail-closed posture
    because moderation outages must not bring the entire public-service platform
    offline.  See specs/026-safety-rails/spec.md § Edge Cases.

Reference: specs/026-safety-rails/spec.md FR-008..FR-011, FR-016, FR-022.
"""

from __future__ import annotations

from typing import Any

from kosmos.safety._models import ModerationBlockedEvent, ModerationWarnedEvent
from kosmos.safety._span import emit_safety_event

# ---------------------------------------------------------------------------
# Crisis-hotline substitution text (self-harm blocks only).
# Both numbers are mandatory per T028 / spec § Validation Scenarios.
# ---------------------------------------------------------------------------
_CRISIS_HOTLINE_KO = (
    "도움이 필요하시면 다음 기관에 연락하세요:\n"
    "• 중앙자살예방센터: 1393 (24시간)\n"
    "• 여성긴급전화: 1366"
)

# OpenAI Categories attribute names that map to our canonical category labels.
# Keys are the Python attribute names on openai.types.moderation.Categories;
# values are the human-readable labels we surface in SafetyDecision / events.
_CATEGORY_ATTR_TO_LABEL: dict[str, str] = {
    "hate": "hate",
    "hate_threatening": "hate/threatening",
    "harassment": "harassment",
    "harassment_threatening": "harassment/threatening",
    "illicit": "illicit",
    "illicit_violent": "illicit/violent",
    "self_harm": "self-harm",
    "self_harm_instructions": "self-harm/instructions",
    "self_harm_intent": "self-harm/intent",
    "sexual": "sexual",
    "sexual_minors": "sexual/minors",
    "violence": "violence",
    "violence_graphic": "violence/graphic",
}

# Attribute names that belong to the self-harm family.
_SELF_HARM_ATTRS = frozenset(
    {"self_harm", "self_harm_instructions", "self_harm_intent"}
)


class ModerationBlockError(LookupError):
    """Raised by pre_call / post_call when moderation issues a hard block.

    Attributes:
        categories: Tuple of flagged category label strings.
        substitution: Optional crisis-hotline text (self-harm blocks only).
    """

    def __init__(
        self,
        categories: tuple[str, ...],
        substitution: str | None = None,
    ) -> None:
        super().__init__(f"Content moderation block: {categories!r}")
        self.categories = categories
        self.substitution = substitution


def _build_all_false_categories() -> dict[str, Any]:
    """Return a JSON-serialisable dict with every moderation category set False."""
    return {
        "harassment": False,
        "harassment/threatening": False,
        "hate": False,
        "hate/threatening": False,
        "illicit": False,
        "illicit/violent": False,
        "self-harm": False,
        "self-harm/instructions": False,
        "self-harm/intent": False,
        "sexual": False,
        "sexual/minors": False,
        "violence": False,
        "violence/graphic": False,
    }


def _call_moderation_api(content: str) -> tuple[tuple[str, ...], bool]:
    """Call the OpenAI Moderation API and return (flagged_categories, is_self_harm).

    Imports ``openai`` lazily so that the callback module remains importable even
    when the ``openai`` package is not installed (disabled moderation path).

    Returns:
        A 2-tuple:
          - ``flagged_categories``: tuple of category-label strings that were
            truthy in the API response (may be empty on allow).
          - ``is_self_harm``: True iff any self-harm-family category was flagged.

    Raises:
        openai.APIConnectionError: Propagated to caller; triggers fail-open.
        httpx.TransportError: Propagated to caller; triggers fail-open.
    """
    import openai  # noqa: PLC0415 (lazy import — intentional, see module docstring)

    from kosmos.settings import settings  # noqa: PLC0415 (avoid circular import)

    api_key = settings.safety.openai_moderation_api_key
    assert api_key is not None  # guarded by _ensure_enabled()

    client = openai.OpenAI(api_key=api_key.get_secret_value())
    result = client.moderations.create(
        model="omni-moderation-latest",
        input=content,
    )

    categories_obj = result.results[0].categories
    flagged_labels: list[str] = []
    is_self_harm = False

    for attr, label in _CATEGORY_ATTR_TO_LABEL.items():
        value = getattr(categories_obj, attr, None)
        if value:
            flagged_labels.append(label)
            if attr in _SELF_HARM_ATTRS:
                is_self_harm = True

    return tuple(flagged_labels), is_self_harm


def _ensure_enabled() -> bool:
    """Return True if moderation is enabled in settings, False otherwise."""
    from kosmos.settings import settings  # noqa: PLC0415 (avoid circular at module level)

    return settings.safety.moderation_enabled


def _extract_last_user_content(kwargs: dict[str, Any]) -> str | None:
    """Extract the content string from the last user-role message in kwargs."""
    messages: list[dict[str, Any]] = kwargs.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                return content
    return None


def pre_call(kwargs: dict[str, Any]) -> dict[str, Any]:
    """LiteLLM pre-call hook: moderate the user's last message.

    Args:
        kwargs: LiteLLM call kwargs dict (contains ``model``, ``messages``, etc.).

    Returns:
        The kwargs dict, unchanged when the moderation decision is ``allow`` or
        when moderation is disabled.

    Raises:
        ModerationBlockError: When the moderation decision is ``block``.
            For self-harm blocks, ``error.substitution`` contains the crisis-
            hotline Korean text with both 1393 and 1366.
    """
    if not _ensure_enabled():
        return kwargs

    content = _extract_last_user_content(kwargs)
    if content is None:
        return kwargs

    try:
        flagged_categories, is_self_harm = _call_moderation_api(content)
    except Exception as exc:  # noqa: BLE001
        # FR-011 explicit fail-open deviation: any outage → allow + warn event.
        # See module docstring for the rationale.
        import httpx  # noqa: PLC0415

        try:
            import openai as _openai  # noqa: PLC0415
            _connection_errors = (_openai.APIConnectionError, httpx.TransportError)
        except ImportError:
            _connection_errors = (httpx.TransportError,)  # type: ignore[assignment]

        if isinstance(exc, _connection_errors):
            emit_safety_event(ModerationWarnedEvent(detail="outage"))
            return kwargs
        raise

    if flagged_categories:
        emit_safety_event(ModerationBlockedEvent(categories=flagged_categories))
        substitution = _CRISIS_HOTLINE_KO if is_self_harm else None
        raise ModerationBlockError(
            categories=flagged_categories,
            substitution=substitution,
        )

    return kwargs


def post_call(kwargs: dict[str, Any], response: object) -> object:
    """LiteLLM post-call hook: moderate the LLM's completed response text.

    Args:
        kwargs: The original LiteLLM call kwargs (for context / logging).
        response: The LLM response object as returned by LiteLLM.

    Returns:
        The response object, unchanged when the decision is ``allow`` or when
        moderation is disabled.

    Raises:
        ModerationBlockError: When the moderation decision is ``block``.
            For self-harm blocks, ``error.substitution`` contains the crisis-
            hotline text.
    """
    if not _ensure_enabled():
        return response

    # Extract response text: support both LiteLLM ModelResponse-style objects
    # and plain strings (for testing convenience).
    content: str | None = None
    if isinstance(response, str):
        content = response
    else:
        # Attempt duck-type access for LiteLLM ModelResponse.
        import contextlib  # noqa: PLC0415

        with contextlib.suppress(AttributeError, IndexError):
            content = response.choices[0].message.content  # type: ignore[union-attr]

    if content is None:
        return response

    try:
        flagged_categories, is_self_harm = _call_moderation_api(content)
    except Exception as exc:  # noqa: BLE001
        import httpx  # noqa: PLC0415

        try:
            import openai as _openai  # noqa: PLC0415
            _connection_errors = (_openai.APIConnectionError, httpx.TransportError)
        except ImportError:
            _connection_errors = (httpx.TransportError,)  # type: ignore[assignment]

        if isinstance(exc, _connection_errors):
            emit_safety_event(ModerationWarnedEvent(detail="outage"))
            return response
        raise

    if flagged_categories:
        emit_safety_event(ModerationBlockedEvent(categories=flagged_categories))
        substitution = _CRISIS_HOTLINE_KO if is_self_harm else None
        raise ModerationBlockError(
            categories=flagged_categories,
            substitution=substitution,
        )

    return response
