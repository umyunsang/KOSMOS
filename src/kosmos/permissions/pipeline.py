# SPDX-License-Identifier: Apache-2.0
"""PermissionPipeline — 7-step permission gauntlet orchestrator.

Single entry point for Layer 1 (QueryEngine) to check permissions before
tool execution. Assembles the full pipeline: bypass-immune check → steps 1-5
(pre-execution) → step 6 (sandboxed execution) → step 7 (audit).
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable

from pydantic import ValidationError

from kosmos.permissions.bypass import check_bypass_immune
from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
    SessionContext,
)
from kosmos.permissions.steps.step1_config import check_config
from kosmos.permissions.steps.step6_sandbox import execute_sandboxed
from kosmos.permissions.steps.step7_audit import write_audit_log
from kosmos.permissions.steps.stubs import (
    check_authn,
    check_intent,
    check_params,
    check_terms,
)
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool, ToolResult
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Mapping from GovAPITool.auth_type to AccessTier
_AUTH_TYPE_TO_ACCESS_TIER: dict[str, AccessTier] = {
    "public": AccessTier.public,
    "api_key": AccessTier.api_key,
    "oauth": AccessTier.authenticated,
}

# Pre-execution steps (1-5), executed in order
_PRE_EXECUTION_STEPS: list[Callable[..., PermissionStepResult]] = [
    check_config,  # step 1
    check_intent,  # step 2 (stub)
    check_params,  # step 3 (stub)
    check_authn,  # step 4 (stub)
    check_terms,  # step 5 (stub)
]


# ---------------------------------------------------------------------------
# PermissionPipeline
# ---------------------------------------------------------------------------


class PermissionPipeline:
    """7-step permission gauntlet for tool execution.

    Args:
        executor: ToolExecutor for dispatching tool calls in step 6.
        registry: ToolRegistry for looking up tool definitions.
    """

    def __init__(self, executor: ToolExecutor, registry: ToolRegistry) -> None:
        self._executor = executor
        self._registry = registry

    async def run(
        self,
        tool_id: str,
        arguments_json: str,
        session_context: SessionContext,
        *,
        is_bypass_mode: bool = False,
    ) -> ToolResult:
        """Execute the full 7-step permission gauntlet.

        Steps:
        0. Bypass-immune check (always runs, even in bypass mode)
        1-5. Pre-execution steps (stop at first deny/escalate)
        6. Sandboxed execution
        7. Audit log (ALWAYS fires, regardless of outcome)

        Args:
            tool_id: The tool identifier to check.
            arguments_json: Raw JSON string of tool arguments.
            session_context: Session context from the query engine.
            is_bypass_mode: If True, steps 1-5 are skipped (bypass-immune
                rules still enforced).

        Returns:
            ToolResult — success if all steps pass and execution succeeds,
            or error with error_type="permission_denied" if denied.
        """
        # --- Look up tool and build request ---
        try:
            tool = self._registry.lookup(tool_id)
        except Exception as exc:
            logger.warning("PermissionPipeline: tool lookup failed for %r: %s", tool_id, exc)
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"Tool not found: {tool_id}",
                error_type="not_found",
            )

        access_tier = _AUTH_TYPE_TO_ACCESS_TIER.get(tool.auth_type, AccessTier.restricted)
        request = PermissionCheckRequest(
            tool_id=tool_id,
            arguments_json=arguments_json,
            access_tier=access_tier,
            is_personal_data=tool.is_personal_data,
            session_context=session_context,
            is_bypass_mode=is_bypass_mode,
        )

        # --- Step 0: Bypass-immune check (always runs) ---
        immune_result = check_bypass_immune(request)
        if immune_result is not None:
            write_audit_log(request, immune_result, None)
            return self._denied_result(tool_id, immune_result)

        # --- Steps 1-5: Pre-execution steps (skipped in bypass mode) ---
        if not request.is_bypass_mode:
            pre_deny = await self._run_pre_execution_steps(request)
            if pre_deny is not None:
                write_audit_log(request, pre_deny, None)
                return self._denied_result(tool_id, pre_deny)

        # --- Step 6: Validate input and execute sandboxed ---
        return await self._execute_step6(request, tool, tool_id, arguments_json)

    async def _run_pre_execution_steps(
        self, request: PermissionCheckRequest
    ) -> PermissionStepResult | None:
        """Run steps 1-5 in order; return the first deny/escalate result or None.

        On exception in a step, fail-closed: return a deny result (FR-013).
        """
        for step_fn in _PRE_EXECUTION_STEPS:
            try:
                raw_result = step_fn(request)
                if inspect.isawaitable(raw_result):
                    step_result: PermissionStepResult = await raw_result
                else:
                    step_result = raw_result
            except Exception as exc:
                step_name = getattr(step_fn, "__name__", repr(step_fn))
                logger.exception(
                    "PermissionPipeline: step %r raised unexpectedly: %s",
                    step_name,
                    exc,
                )
                return PermissionStepResult(
                    step=_PRE_EXECUTION_STEPS.index(step_fn) + 1,
                    decision=PermissionDecision.deny,
                    reason="internal_error",
                )

            if step_result.decision != PermissionDecision.allow:
                return step_result

        return None

    async def _execute_step6(
        self,
        request: PermissionCheckRequest,
        tool: GovAPITool,
        tool_id: str,
        arguments_json: str,
    ) -> ToolResult:
        """Validate input, resolve adapter, and run sandboxed execution (step 6)."""
        # Validate input
        try:
            validated_input = tool.input_schema.model_validate_json(arguments_json)
        except (ValidationError, ValueError) as exc:
            logger.warning(
                "PermissionPipeline: input validation failed for tool %r: %s",
                tool_id,
                exc,
            )
            validation_deny = PermissionStepResult(
                step=6,
                decision=PermissionDecision.deny,
                reason="validation_error",
            )
            write_audit_log(request, validation_deny, None)
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=str(exc),
                error_type="validation",
            )

        # Resolve adapter
        adapter_fn = self._executor._adapters.get(tool_id)  # noqa: SLF001
        if adapter_fn is None:
            no_adapter = PermissionStepResult(
                step=6,
                decision=PermissionDecision.deny,
                reason="no adapter registered for tool",
            )
            write_audit_log(request, no_adapter, None)
            return ToolResult(
                tool_id=tool_id,
                success=False,
                error=f"No adapter registered for tool {tool_id!r}",
                error_type="execution",
            )

        step6_result, tool_result = await execute_sandboxed(request, adapter_fn, validated_input)

        # --- Step 7: Audit log (ALWAYS fires) ---
        write_audit_log(request, step6_result, tool_result)

        if tool_result is None:
            return self._denied_result(tool_id, step6_result)
        return tool_result

    @staticmethod
    def _denied_result(tool_id: str, deciding_result: PermissionStepResult) -> ToolResult:
        """Build a denied ToolResult from a pipeline step decision."""
        return ToolResult(
            tool_id=tool_id,
            success=False,
            error=f"Permission denied at step {deciding_result.step}: {deciding_result.reason}",
            error_type="permission_denied",
        )
