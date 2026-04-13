# SPDX-License-Identifier: Apache-2.0
"""Step 1: Configuration-based access tier enforcement.

Checks the tool's declared AccessTier against the current environment:
- public → allow unconditionally
- api_key → allow iff at least one KOSMOS_*_API_KEY env var is set and non-empty
- authenticated → deny (not implemented in v1)
- restricted → deny (not implemented in v1)
"""

from __future__ import annotations

import logging
import os

from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)

logger = logging.getLogger(__name__)

_STEP = 1


def check_config(request: PermissionCheckRequest) -> PermissionStepResult:
    """Check configuration-based access tier rules.

    Args:
        request: The permission check request.

    Returns:
        PermissionStepResult with allow, deny, or escalate decision.
    """
    tier = request.access_tier

    if tier == AccessTier.public:
        logger.debug("Step %d: public tier — allow for tool %s", _STEP, request.tool_id)
        return PermissionStepResult(decision=PermissionDecision.allow, step=_STEP)

    if tier == AccessTier.api_key:
        has_key = any(
            v.strip()
            for k, v in os.environ.items()
            if k.startswith("KOSMOS_") and k.endswith("_API_KEY")
        )
        if not has_key:
            logger.warning(
                "Step %d: api_key tier denied for tool %s — no KOSMOS_*_API_KEY env var configured",
                _STEP,
                request.tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="api_key_not_configured",
            )
        logger.debug("Step %d: api_key tier — allow for tool %s", _STEP, request.tool_id)
        return PermissionStepResult(decision=PermissionDecision.allow, step=_STEP)

    if tier == AccessTier.authenticated:
        logger.warning(
            "Step %d: authenticated tier denied for tool %s — not implemented in v1",
            _STEP,
            request.tool_id,
        )
        return PermissionStepResult(
            decision=PermissionDecision.deny,
            step=_STEP,
            reason="citizen_auth_not_implemented",
        )

    if tier == AccessTier.restricted:
        logger.warning(
            "Step %d: restricted tier denied for tool %s — not implemented in v1",
            _STEP,
            request.tool_id,
        )
        return PermissionStepResult(
            decision=PermissionDecision.deny,
            step=_STEP,
            reason="tier_restricted_not_implemented",
        )

    # Unknown tier — fail closed
    logger.error("Step %d: unknown tier %r for tool %s — denying", _STEP, tier, request.tool_id)
    return PermissionStepResult(
        decision=PermissionDecision.deny,
        step=_STEP,
        reason="internal_error",
    )
