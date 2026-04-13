# SPDX-License-Identifier: Apache-2.0
"""Step 6: Sandboxed execution context.

Executes the tool adapter in an isolated environment where only the credentials
relevant to the tool's access tier are visible. Catches all exceptions and
converts them to deny results.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
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

# Regex patterns for env vars allowed per access tier.
# Using patterns instead of a hardcoded list allows any KOSMOS_*_API_KEY
# variable (e.g. KOSMOS_KOROAD_API_KEY, KOSMOS_DATA_GO_KR_API_KEY) to be
# visible inside the sandbox for tiers that require API key credentials.
_TIER_ALLOWED_PATTERNS: dict[AccessTier, list[re.Pattern[str]]] = {
    AccessTier.public: [],
    AccessTier.api_key: [re.compile(r"^KOSMOS_.*_API_KEY$")],
    AccessTier.authenticated: [re.compile(r"^KOSMOS_.*_API_KEY$")],
    AccessTier.restricted: [re.compile(r"^KOSMOS_.*_API_KEY$")],
}

# Serialize env-mutation sections so concurrent coroutines cannot observe a
# partially-filtered environment.
_sandbox_lock = asyncio.Lock()


def _is_allowed(key: str, patterns: list[re.Pattern[str]]) -> bool:
    """Return True if *key* matches any of the given compiled patterns."""
    return any(p.match(key) for p in patterns)


async def execute_sandboxed(
    request: PermissionCheckRequest,
    adapter_fn: Any,  # Callable[[BaseModel], Awaitable[dict]]
    validated_input: Any,  # BaseModel
) -> tuple[PermissionStepResult, ToolResult | None]:
    """Execute the tool adapter in an isolated sandbox.

    Temporarily removes KOSMOS_* env vars not matched by the tool's access-tier
    patterns, executes the adapter, then restores all env vars.

    A module-level asyncio.Lock serializes the env-mutation window so that
    concurrent coroutines cannot observe a partially-filtered environment.

    Args:
        request: The permission check request.
        adapter_fn: The async adapter callable.
        validated_input: The validated Pydantic input model instance.

    Returns:
        Tuple of (PermissionStepResult, ToolResult or None).
        On success: (allow result, ToolResult) — built from the adapter output.
        On exception: (deny result, None).
    """
    allowed_patterns = _TIER_ALLOWED_PATTERNS.get(request.access_tier, [])

    async with _sandbox_lock:
        # Snapshot and temporarily remove non-allowed KOSMOS_ vars
        saved_vars: dict[str, str] = {}

        for key, value in list(os.environ.items()):
            if key.startswith("KOSMOS_") and not _is_allowed(key, allowed_patterns):
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
