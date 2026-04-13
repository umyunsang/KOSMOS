# SPDX-License-Identifier: Apache-2.0
"""Step 4: Citizen authentication level enforcement.

Verifies that the caller holds a sufficient authentication level for the tool's
required access tier.  The mapping follows a strict linear ordering:

    anonymous (0) < basic (1) < verified (2)

Access-tier requirements:

    public       → any auth_level (including 0 / anonymous)
    api_key      → any auth_level (key presence is step 1's responsibility)
    authenticated → auth_level >= AUTH_LEVEL_VERIFIED (2)
    restricted    → auth_level >= AUTH_LEVEL_VERIFIED (2) AND citizen_id present

The distinction between ``authenticated`` and ``restricted`` is meaningful
here: a ``restricted`` tool also requires a non-None ``citizen_id`` so that
the audit trail can record an identifiable actor.

All exceptions cause a fail-closed deny.
"""

from __future__ import annotations

import logging

from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)

logger = logging.getLogger(__name__)

_STEP = 4

# ---------------------------------------------------------------------------
# Auth-level constants
# ---------------------------------------------------------------------------

AUTH_LEVEL_ANONYMOUS: int = 0
AUTH_LEVEL_BASIC: int = 1
AUTH_LEVEL_VERIFIED: int = 2


# ---------------------------------------------------------------------------
# Tier → minimum auth level mapping
# ---------------------------------------------------------------------------

_TIER_MIN_AUTH_LEVEL: dict[AccessTier, int] = {
    AccessTier.public: AUTH_LEVEL_ANONYMOUS,
    AccessTier.api_key: AUTH_LEVEL_ANONYMOUS,
    AccessTier.authenticated: AUTH_LEVEL_VERIFIED,
    AccessTier.restricted: AUTH_LEVEL_VERIFIED,
}


# ---------------------------------------------------------------------------
# Main step function
# ---------------------------------------------------------------------------


def check_authn(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 4: Verify caller authentication level matches the tool's tier.

    Args:
        request: The permission check request.

    Returns:
        PermissionStepResult allow if auth level is sufficient, deny otherwise.
    """
    try:
        tier = request.access_tier
        auth_level = request.session_context.auth_level
        citizen_id = request.session_context.citizen_id

        min_level = _TIER_MIN_AUTH_LEVEL.get(tier)
        if min_level is None:
            # Unknown tier — fail closed
            logger.error(
                "Step %d: unknown access tier %r for tool %s — denying",
                _STEP,
                tier,
                request.tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="internal_error",
            )

        if auth_level < min_level:
            logger.warning(
                "Step %d: insufficient auth level for tool %s tier=%s (required>=%d, got %d)",
                _STEP,
                request.tool_id,
                tier,
                min_level,
                auth_level,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="insufficient_auth_level",
            )

        # Restricted tier additionally requires an identified citizen
        if tier == AccessTier.restricted and citizen_id is None:
            logger.warning(
                "Step %d: restricted tier requires citizen_id but none present for tool %s",
                _STEP,
                request.tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="citizen_id_required",
            )

        logger.debug(
            "Step %d: auth check passed for tool %s (tier=%s auth_level=%d)",
            _STEP,
            request.tool_id,
            tier,
            auth_level,
        )
        return PermissionStepResult(decision=PermissionDecision.allow, step=_STEP)

    except Exception as exc:
        logger.exception(
            "Step %d: unexpected exception during authn check for tool %s: %s",
            _STEP,
            request.tool_id,
            exc,
        )
        return PermissionStepResult(
            decision=PermissionDecision.deny,
            step=_STEP,
            reason="internal_error",
        )
