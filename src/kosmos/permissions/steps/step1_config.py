# SPDX-License-Identifier: Apache-2.0
"""Step 1: Configuration-based access tier enforcement.

Checks the tool's declared AccessTier against the current environment:
- public → allow unconditionally
- api_key → allow iff the credential for the tool's *specific* provider is
  configured (Kakao tools require ``KOSMOS_KAKAO_API_KEY``; data.go.kr
  tools require ``KOSMOS_DATA_GO_KR_API_KEY``). A tool-specific override
  ``KOSMOS_<TOOL_ID>_API_KEY`` or the legacy global ``KOSMOS_API_KEY``
  also satisfies the check. Resolution is delegated to
  :mod:`kosmos.permissions.credentials`.
- authenticated → deny (not implemented in v1)
- restricted → deny (not implemented in v1)
"""

from __future__ import annotations

import logging

from kosmos.permissions.credentials import candidate_env_vars, has_credential
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
        if not has_credential(request.tool_id):
            logger.warning(
                "Step %d: api_key tier denied for tool %s — no credential configured (checked %s)",
                _STEP,
                request.tool_id,
                ", ".join(candidate_env_vars(request.tool_id)),
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
