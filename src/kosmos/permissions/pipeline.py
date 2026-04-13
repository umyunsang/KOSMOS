# SPDX-License-Identifier: Apache-2.0
"""PermissionPipeline — 7-step permission gauntlet orchestrator.

Single entry point for Layer 1 (QueryEngine) to check permissions before
tool execution. Assembles the full pipeline: bypass-immune check → steps 1-5
(pre-execution) → step 6 (sandboxed execution) → step 7 (audit).
"""

from __future__ import annotations

import inspect
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from kosmos.permissions.bypass import check_bypass_immune
from kosmos.permissions.models import (
    AccessTier,
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
    SessionContext,
)
from kosmos.permissions.steps.refusal_circuit_breaker import (
    CONSECUTIVE_DENIAL_THRESHOLD,
    record_denial,
    record_success,
)
from kosmos.permissions.steps.step1_config import check_config
from kosmos.permissions.steps.step2_intent import check_intent
from kosmos.permissions.steps.step3_params import check_params
from kosmos.permissions.steps.step4_authn import check_authn
from kosmos.permissions.steps.step5_terms import check_terms
from kosmos.permissions.steps.step6_sandbox import execute_sandboxed
from kosmos.permissions.steps.step7_audit import write_audit_log
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import ToolResult
from kosmos.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from kosmos.observability.event_logger import ObservabilityEventLogger
    from kosmos.observability.metrics import MetricsCollector

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
    check_config,  # step 1: config-based access tier
    check_intent,  # step 2: rule-based intent analysis
    check_params,  # step 3: PII parameter inspection
    check_authn,  # step 4: citizen authentication level
    check_terms,  # step 5: ministry terms-of-use consent
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

    def __init__(
        self,
        executor: ToolExecutor,
        registry: ToolRegistry,
        metrics: MetricsCollector | None = None,
        event_logger: ObservabilityEventLogger | None = None,
    ) -> None:
        self._executor = executor
        self._registry = registry
        self._metrics: MetricsCollector | None = metrics
        self._event_logger: ObservabilityEventLogger | None = event_logger

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
        _pipeline_start = time.monotonic()
        _pipeline_result: ToolResult | None = None

        try:
            # --- Look up tool and build request ---
            try:
                tool = self._registry.lookup(tool_id)
            except Exception as exc:
                logger.warning("PermissionPipeline: tool lookup failed for %r: %s", tool_id, exc)
                not_found_request = PermissionCheckRequest(
                    tool_id=tool_id,
                    access_tier=AccessTier.restricted,
                    arguments_json=arguments_json,
                    session_context=session_context,
                    is_personal_data=False,
                    is_bypass_mode=is_bypass_mode,
                )
                not_found_result = PermissionStepResult(
                    decision=PermissionDecision.deny,
                    step=0,
                    reason="not_found",
                )
                write_audit_log(not_found_request, not_found_result, None)
                _pipeline_result = ToolResult(
                    tool_id=tool_id,
                    success=False,
                    error=f"Tool not found: {tool_id}",
                    error_type="not_found",
                )
                return _pipeline_result

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
                _pipeline_result = self._denied_result(tool_id, immune_result)
                return _pipeline_result

            # --- Steps 1-5: Pre-execution steps (skipped in bypass mode) ---
            if not request.is_bypass_mode:
                pre_deny = await self._run_pre_execution_steps(request)
                if pre_deny is not None:
                    write_audit_log(request, pre_deny, None)
                    _pipeline_result = self._denied_result(tool_id, pre_deny)
                    return _pipeline_result

            # --- Step 6: Execute sandboxed via executor.dispatch() ---
            _pipeline_result = await self._execute_step6(request, arguments_json)
            return _pipeline_result

        finally:
            _duration_ms = (time.monotonic() - _pipeline_start) * 1000
            self._metrics_record_pipeline_duration(_duration_ms)

    async def _run_pre_execution_steps(
        self, request: PermissionCheckRequest
    ) -> PermissionStepResult | None:
        """Run steps 1-5 in order; return the first deny/escalate result or None.

        On exception in a step, fail-closed: return a deny result (FR-013).
        On deny, the refusal circuit breaker is notified.
        On all steps passing, the circuit breaker's success counter is reset.
        """
        session_id = request.session_context.session_id

        for step_index, step_fn in enumerate(_PRE_EXECUTION_STEPS, start=1):
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
                deny = PermissionStepResult(
                    step=step_index,
                    decision=PermissionDecision.deny,
                    reason="internal_error",
                )
                _denial_count = record_denial(session_id, request.tool_id)
                self._metrics_record_decision(step_index, "deny")
                self._metrics_record_refusal_trip(request.tool_id, _denial_count)
                self._event_emit_decision(step_index, "deny", "internal_error", request.tool_id)
                return deny

            decision_str = (
                step_result.decision.value
                if hasattr(step_result.decision, "value")
                else str(step_result.decision)
            )
            if step_result.decision != PermissionDecision.allow:
                _denial_count = record_denial(session_id, request.tool_id)
                self._metrics_record_decision(step_index, decision_str)
                self._metrics_record_refusal_trip(request.tool_id, _denial_count)
                self._event_emit_decision(
                    step_index, decision_str, step_result.reason, request.tool_id
                )
                return step_result

            self._metrics_record_decision(step_index, "allow")
            self._event_emit_decision(step_index, "allow", step_result.reason, request.tool_id)

        # All pre-execution steps passed — reset the denial counter.
        record_success(session_id, request.tool_id)
        return None

    async def _execute_step6(
        self,
        request: PermissionCheckRequest,
        arguments_json: str,
    ) -> ToolResult:
        """Route tool execution through the sandboxed executor (step 6).

        Delegates all input validation, rate limiting, adapter execution, and
        output schema validation to executor.dispatch() — called inside the
        env-filtering sandbox so credentials are scoped to the tool's access tier.
        The tool_id is always derived from request.tool_id to prevent mis-scoping.
        """
        step6_result, tool_result = await execute_sandboxed(request, self._executor, arguments_json)

        # --- Step 7: Audit log (ALWAYS fires) ---
        write_audit_log(request, step6_result, tool_result)

        if step6_result.decision != PermissionDecision.allow:
            return self._denied_result(request.tool_id, step6_result)
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

    # ------------------------------------------------------------------
    # Private metrics helpers (fail-safe: never raise)
    # ------------------------------------------------------------------

    def _metrics_record_decision(self, step: int, decision: str) -> None:
        """Increment decision count metric; silently skip if no collector."""
        if self._metrics is None:
            return
        try:
            self._metrics.increment(
                "permission.decision_count",
                labels={"step": str(step), "decision": decision},
            )
        except Exception:  # noqa: BLE001
            logger.debug(
                "PermissionPipeline: metrics.increment(decision_count) failed",
                exc_info=True,
            )

    def _metrics_record_refusal_trip(self, tool_id: str, denial_count: int) -> None:
        """Increment refusal circuit trip counter when threshold is hit."""
        if self._metrics is None:
            return
        try:
            if denial_count == CONSECUTIVE_DENIAL_THRESHOLD:
                self._metrics.increment(
                    "permission.refusal_circuit_trips",
                    labels={"tool_id": tool_id},
                )
        except Exception:  # noqa: BLE001
            logger.debug(
                "PermissionPipeline: metrics.increment(refusal_circuit_trips) failed",
                exc_info=True,
            )

    def _metrics_record_pipeline_duration(self, duration_ms: float) -> None:
        """Record pipeline duration histogram; silently skip if no collector."""
        if self._metrics is None:
            return
        try:
            self._metrics.observe("permission.pipeline_duration_ms", duration_ms)
        except Exception:  # noqa: BLE001
            logger.debug(
                "PermissionPipeline: metrics.observe(pipeline_duration_ms) failed",
                exc_info=True,
            )

    def _event_emit_decision(
        self, step: int, decision: str, reason: str | None, tool_id: str
    ) -> None:
        """Emit permission_decision event; silently skip if no event_logger."""
        if self._event_logger is None:
            return
        try:
            from kosmos.observability.events import ObservabilityEvent  # noqa: PLC0415

            self._event_logger.emit(
                ObservabilityEvent(
                    event_type="permission_decision",
                    tool_id=tool_id,
                    success=(decision == "allow"),
                    metadata={"step": str(step), "decision": decision, "tool_id": tool_id},
                )
            )
        except Exception:  # noqa: BLE001
            logger.debug("PermissionPipeline: event_logger.emit failed", exc_info=True)
