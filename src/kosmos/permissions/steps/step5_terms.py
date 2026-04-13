# SPDX-License-Identifier: Apache-2.0
"""Step 5: Ministry Terms-of-Use (ToS) consent enforcement.

Checks whether the caller has accepted the terms-of-use published by the tool's
data provider (government ministry / agency).  Consent is tracked in-memory for
the duration of the process; it is not persisted across restarts.

Design decisions:
- Consent is keyed by (session_id, provider).  Consent granted in one session
  does not automatically carry over to another session.
- The ``SessionContext.consented_providers`` tuple is also honoured — if the
  query engine records consent there, step 5 recognises it without requiring a
  separate ``grant_consent()`` call.
- ``grant_consent()`` is the programmatic API for granting consent at runtime
  (e.g., after the user confirms a ToS dialog in the TUI layer).
- ``revoke_consent()`` is provided for testing and session teardown.

Provider extraction:
- The provider string comes from the tool ID using a simple convention:
  the prefix before the first underscore is the provider.
  e.g., ``koroad_accident_search`` → provider ``koroad``.
  Tools with no underscore use their full ID as the provider.

All exceptions cause a fail-closed deny.
"""

from __future__ import annotations

import logging
import threading

from kosmos.permissions.models import (
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)

logger = logging.getLogger(__name__)

_STEP = 5

# ---------------------------------------------------------------------------
# In-memory consent registry
# ---------------------------------------------------------------------------

# Structure: {(session_id, provider): True}
# Thread-safe via _consent_lock.
_consent_registry: dict[tuple[str, str], bool] = {}
_consent_lock = threading.Lock()


def grant_consent(session_id: str, provider: str) -> None:
    """Record that *session_id* has accepted the ToS for *provider*.

    Args:
        session_id: The session that accepted the terms.
        provider: Provider identifier (e.g. ``"koroad"``, ``"weather"``).
    """
    with _consent_lock:
        _consent_registry[(session_id, provider)] = True
    logger.info(
        "Step %d: ToS consent granted for provider=%s session=%s",
        _STEP,
        provider,
        session_id,
    )


def revoke_consent(session_id: str, provider: str) -> None:
    """Remove ToS consent for *provider* in *session_id*.

    No-op if consent was not recorded.  Intended for testing and session
    teardown.

    Args:
        session_id: The session whose consent is being revoked.
        provider: Provider identifier.
    """
    with _consent_lock:
        _consent_registry.pop((session_id, provider), None)


def clear_all_consent() -> None:
    """Wipe the entire in-memory consent registry.

    Intended for testing only.
    """
    with _consent_lock:
        _consent_registry.clear()


def _has_consent(session_id: str, provider: str) -> bool:
    """Return True if consent has been recorded for (session_id, provider)."""
    with _consent_lock:
        return _consent_registry.get((session_id, provider), False)


def _extract_provider(tool_id: str) -> str:
    """Derive the provider prefix from a tool identifier.

    Convention: the substring before the first ``_`` is the provider.
    If no ``_`` is present, the full tool_id is used as the provider.

    Examples::

        "koroad_accident_search" → "koroad"
        "weather_forecast_daily" → "weather"
        "publicdata"             → "publicdata"
    """
    return tool_id.split("_", maxsplit=1)[0]


# ---------------------------------------------------------------------------
# Main step function
# ---------------------------------------------------------------------------


def check_terms(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 5: Verify the caller has accepted the provider's terms of use.

    Args:
        request: The permission check request.

    Returns:
        PermissionStepResult allow if consent recorded, deny otherwise.
    """
    try:
        session_id = request.session_context.session_id
        provider = _extract_provider(request.tool_id)

        # Accept consent recorded either in the session_context tuple
        # (written by the query engine) or via grant_consent() (written by
        # the TUI/consent dialog layer).
        session_consented = provider in request.session_context.consented_providers
        registry_consented = _has_consent(session_id, provider)

        if session_consented or registry_consented:
            logger.debug(
                "Step %d: ToS consent confirmed for provider=%s tool=%s",
                _STEP,
                provider,
                request.tool_id,
            )
            return PermissionStepResult(decision=PermissionDecision.allow, step=_STEP)

        logger.warning(
            "Step %d: ToS consent missing for provider=%s tool=%s session=%s",
            _STEP,
            provider,
            request.tool_id,
            session_id,
        )
        return PermissionStepResult(
            decision=PermissionDecision.deny,
            step=_STEP,
            reason=f"terms_not_accepted:{provider}",
        )

    except Exception as exc:
        logger.exception(
            "Step %d: unexpected exception during terms check for tool %s: %s",
            _STEP,
            request.tool_id,
            exc,
        )
        return PermissionStepResult(
            decision=PermissionDecision.deny,
            step=_STEP,
            reason="internal_error",
        )
