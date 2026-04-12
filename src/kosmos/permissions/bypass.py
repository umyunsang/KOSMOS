# SPDX-License-Identifier: Apache-2.0
"""Bypass-immune permission rules that cannot be overridden.

These rules enforce PIPA compliance regardless of any bypass flags.
The BYPASS_IMMUNE_RULES frozenset is a module-level constant — not configurable.
"""

from __future__ import annotations

import json
import logging

from kosmos.permissions.models import (
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)

logger = logging.getLogger(__name__)

# Frozenset of bypass-immune rule names — not configurable at runtime
BYPASS_IMMUNE_RULES: frozenset[str] = frozenset(
    {
        "personal_data_citizen_mismatch",
    }
)


def check_bypass_immune(request: PermissionCheckRequest) -> PermissionStepResult | None:
    """Check bypass-immune rules that apply even when is_bypass_mode=True.

    Returns a deny result if any rule fires. Returns None if all rules pass.

    If is_bypass_mode=True, a WARNING is logged before checking.

    Args:
        request: The permission check request.

    Returns:
        PermissionStepResult with deny if a rule fires, or None if all pass.
    """
    if request.is_bypass_mode:
        logger.warning(
            "Bypass mode active for tool %s — bypass-immune rules still enforced",
            request.tool_id,
        )

    # Rule: personal_data_citizen_mismatch
    if request.is_personal_data and request.session_context.citizen_id is not None:
        try:
            args = json.loads(request.arguments_json)
            args_citizen_id = args.get("citizen_id")
            if (
                args_citizen_id is not None
                and args_citizen_id != request.session_context.citizen_id
            ):
                logger.warning(
                    "Bypass-immune deny: citizen_id mismatch for tool %s (session=%s, args=%s)",
                    request.tool_id,
                    request.session_context.citizen_id,
                    "<redacted>",
                )
                return PermissionStepResult(
                    decision=PermissionDecision.deny,
                    step=0,  # Step 0 = pre-pipeline bypass-immune
                    reason="personal_data_citizen_mismatch",
                )
        except (json.JSONDecodeError, TypeError):
            # If arguments_json can't be parsed, fail closed
            logger.error("Failed to parse arguments_json for bypass-immune check")
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=0,
                reason="internal_error",
            )

    return None
