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
- Credential resolution is centralised in :mod:`kosmos.permissions.credentials`
  so step 1 of the permission pipeline and this module agree on which env vars
  satisfy which tool.  That means Kakao-backed tools (``address_to_region``,
  ``address_to_grid``) correctly discover ``KOSMOS_KAKAO_API_KEY`` here,
  and data.go.kr-backed tools discover ``KOSMOS_DATA_GO_KR_API_KEY``.
"""

from __future__ import annotations

import logging

from kosmos.permissions.credentials import candidate_env_vars, resolve_credential

logger = logging.getLogger(__name__)


async def attempt_auth_refresh(tool_id: str) -> bool:
    """Attempt to refresh credentials for *tool_id* from the environment.

    This function is a coroutine for API consistency (future implementations
    may perform async I/O to a secrets manager).

    Resolution is delegated to
    :func:`kosmos.permissions.credentials.resolve_credential`, which tries
    the per-tool override, the tool's provider-specific env var, and finally
    the legacy global fallback.

    Args:
        tool_id: Stable snake_case tool identifier.

    Returns:
        ``True`` if a non-empty credential was found in the environment.
        ``False`` if no credential is available (caller should surface a
        ``needs_authentication`` stop reason).
    """
    credential = resolve_credential(tool_id)
    if credential is not None:
        logger.info("Auth refresh: credential resolved for tool %s", tool_id)
        return True

    logger.warning(
        "Auth refresh: no credential found for tool %s (checked %s)",
        tool_id,
        ", ".join(candidate_env_vars(tool_id)),
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
    return resolve_credential(tool_id)
