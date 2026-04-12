# SPDX-License-Identifier: Apache-2.0
"""Steps 2-5: Pass-through stub implementations for v1.

Each stub returns PermissionDecision.allow unconditionally and logs a DEBUG
message recording the pass-through. They have the same function signature as
active steps, so activation in v2+ is a drop-in replacement.
"""

from __future__ import annotations

import logging

from kosmos.permissions.models import (
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)

logger = logging.getLogger(__name__)


def check_intent(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 2 (stub): Intent analysis — pass-through in v1."""
    logger.debug("Step 2 (stub): pass-through for tool %s", request.tool_id)
    return PermissionStepResult(decision=PermissionDecision.allow, step=2)


def check_params(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 3 (stub): Parameter inspection — pass-through in v1."""
    logger.debug("Step 3 (stub): pass-through for tool %s", request.tool_id)
    return PermissionStepResult(decision=PermissionDecision.allow, step=3)


def check_authn(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 4 (stub): Citizen authentication — pass-through in v1."""
    logger.debug("Step 4 (stub): pass-through for tool %s", request.tool_id)
    return PermissionStepResult(decision=PermissionDecision.allow, step=4)


def check_terms(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 5 (stub): Ministry terms-of-use — pass-through in v1."""
    logger.debug("Step 5 (stub): pass-through for tool %s", request.tool_id)
    return PermissionStepResult(decision=PermissionDecision.allow, step=5)
