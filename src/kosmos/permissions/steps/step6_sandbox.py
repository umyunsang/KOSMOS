# SPDX-License-Identifier: Apache-2.0
"""Step 6: Sandboxed execution context.

Executes the tool adapter in an isolated environment where only the credentials
relevant to the tool's access tier are visible. Catches all exceptions and
converts them to deny results.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)
from kosmos.tools.models import ToolResult

logger = logging.getLogger(__name__)

_STEP = 6

# Environment variables allowed per access tier
_TIER_ALLOWED_VARS: dict[AccessTier, list[str]] = {
    AccessTier.public: [],
    AccessTier.api_key: ["KOSMOS_DATA_GO_KR_API_KEY"],
    AccessTier.authenticated: ["KOSMOS_DATA_GO_KR_API_KEY"],
    AccessTier.restricted: ["KOSMOS_DATA_GO_KR_API_KEY"],
}


async def execute_sandboxed(
    request: PermissionCheckRequest,
    adapter_fn: Any,  # Callable[[BaseModel], Awaitable[dict]]
    validated_input: Any,  # BaseModel
) -> tuple[PermissionStepResult, ToolResult | None]:
    """Execute the tool adapter in an isolated sandbox.

    Temporarily removes KOSMOS_* env vars not in the tool's allowed set,
    executes the adapter, then restores all env vars.

    Args:
        request: The permission check request.
        adapter_fn: The async adapter callable.
        validated_input: The validated Pydantic input model instance.

    Returns:
        Tuple of (PermissionStepResult, ToolResult or None).
        On success: (allow result, ToolResult) — built from the adapter output.
        On exception: (deny result, None).
    """
    # Snapshot and temporarily remove non-allowed KOSMOS_ vars
    allowed = set(_TIER_ALLOWED_VARS.get(request.access_tier, []))
    saved_vars: dict[str, str] = {}

    for key, value in list(os.environ.items()):
        if key.startswith("KOSMOS_") and key not in allowed:
            saved_vars[key] = value
            del os.environ[key]

    try:
        result_data = await adapter_fn(validated_input)
        logger.debug("Step %d: sandbox execution succeeded for tool %s", _STEP, request.tool_id)
        return (
            PermissionStepResult(decision=PermissionDecision.allow, step=_STEP),
            ToolResult(
                tool_id=request.tool_id,
                success=True,
                data=result_data,
            ),
        )
    except Exception as exc:
        logger.error(
            "Step %d: sandbox execution failed for tool %s: %s",
            _STEP,
            request.tool_id,
            exc,
        )
        return (
            PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="execution_error",
            ),
            None,
        )
    finally:
        # Restore all removed env vars
        for key, value in saved_vars.items():
            os.environ[key] = value
