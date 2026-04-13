# SPDX-License-Identifier: Apache-2.0
"""401 authentication-refresh helpers for tool adapters.

When a tool adapter receives an HTTP 401, the recovery pipeline can attempt to
refresh credentials before retrying.  For now, credentials are re-read from
environment variables (the simplest, zero-dependency approach).  Future
versions can extend ``attempt_auth_refresh`` for OAuth token rotation or
external secret-manager integration.

Design decisions:
- Stateless: no credential cache is maintained here.  Each call re-reads the
  environment so that operator key rotations are picked up immediately.
- Fail-closed: returns ``False`` (no refresh) if the expected env var is absent
  or empty, rather than raising.
- Naming convention for env vars: ``KOSMOS_<TOOL_ID_UPPER>_API_KEY``
  e.g. ``KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY``.  The fallback
  ``KOSMOS_API_KEY`` is tried when no tool-specific var exists.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# Global fallback env var tried when no tool-specific key is configured.
_GLOBAL_KEY_VAR: str = "KOSMOS_API_KEY"

# Shared data.go.kr key used by KMA and KOROAD adapters.
_DATA_GO_KR_KEY_VAR: str = "KOSMOS_DATA_GO_KR_API_KEY"


def _env_var_name(tool_id: str) -> str:
    """Return the canonical env var name for *tool_id*.

    ``koroad_accident_search`` → ``KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY``
    """
    return f"KOSMOS_{tool_id.upper()}_API_KEY"


async def attempt_auth_refresh(tool_id: str) -> bool:
    """Attempt to refresh credentials for *tool_id* from the environment.

    This function is a coroutine for API consistency (future implementations
    may perform async I/O to a secrets manager).

    The refresh is considered successful when either:
    - A non-empty ``KOSMOS_<TOOL_ID_UPPER>_API_KEY`` variable is present, or
    - A non-empty global ``KOSMOS_API_KEY`` variable is present.

    Args:
        tool_id: Stable snake_case tool identifier.

    Returns:
        ``True`` if a non-empty credential was found in the environment.
        ``False`` if no credential is available (caller should surface a
        ``needs_authentication`` stop reason).
    """
    specific_var = _env_var_name(tool_id)
    specific_value = os.environ.get(specific_var, "").strip()
    if specific_value:
        logger.info(
            "Auth refresh: found credential in %s for tool %s",
            specific_var,
            tool_id,
        )
        return True

    # data.go.kr shared key (used by KMA and KOROAD adapters).
    data_go_kr_value = os.environ.get(_DATA_GO_KR_KEY_VAR, "").strip()
    if data_go_kr_value:
        logger.info(
            "Auth refresh: found credential in %s (data.go.kr shared key) for tool %s",
            _DATA_GO_KR_KEY_VAR,
            tool_id,
        )
        return True

    global_value = os.environ.get(_GLOBAL_KEY_VAR, "").strip()
    if global_value:
        logger.info(
            "Auth refresh: found credential in %s (global fallback) for tool %s",
            _GLOBAL_KEY_VAR,
            tool_id,
        )
        return True

    logger.warning(
        "Auth refresh: no credential found for tool %s (checked %s, %s, and %s)",
        tool_id,
        specific_var,
        _DATA_GO_KR_KEY_VAR,
        _GLOBAL_KEY_VAR,
    )
    return False


def get_credential(tool_id: str) -> str | None:
    """Return the current credential string for *tool_id*, or ``None``.

    Convenience helper for adapter implementations that need to read the
    refreshed key synchronously after ``attempt_auth_refresh`` returns
    ``True``.

    Args:
        tool_id: Stable snake_case tool identifier.

    Returns:
        Non-empty credential string, or ``None`` if not available.
    """
    specific_var = _env_var_name(tool_id)
    value = os.environ.get(specific_var, "").strip()
    if value:
        return value
    data_go_kr_value = os.environ.get(_DATA_GO_KR_KEY_VAR, "").strip()
    if data_go_kr_value:
        return data_go_kr_value
    global_value = os.environ.get(_GLOBAL_KEY_VAR, "").strip()
    return global_value or None
