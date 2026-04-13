# SPDX-License-Identifier: Apache-2.0
"""Tool dispatcher for the KOSMOS Tool System module.

Resolves tool calls from the LLM by name, validates input/output against
Pydantic schemas, enforces rate limits, and returns a structured ToolResult.
The executor never raises — all error paths are captured in ToolResult.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from kosmos.tools.errors import ToolNotFoundError
from kosmos.tools.models import ToolResult
from kosmos.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from kosmos.observability.metrics import MetricsCollector
    from kosmos.recovery.executor import RecoveryExecutor

logger = logging.getLogger(__name__)

AdapterFn = Callable[[BaseModel], Awaitable[dict[str, Any]]]


class ToolExecutor:
    """Dispatch LLM tool calls through validation, rate-limiting, and execution.

    The dispatch pipeline (in order):
    1. Lookup tool in registry.
    2. Parse and validate JSON arguments against input_schema.
    3. Verify adapter exists.
    4. Check and record rate limit.
    5. If RecoveryExecutor is present: delegate for retry / circuit-breaker /
       cache.  If absent: call adapter directly.
    6. Validate adapter output against output_schema.
    7. Return ToolResult(success=True, data=...).

    Any step failure returns ToolResult(success=False, ...) with an
    appropriate error_type. The executor itself never raises.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        recovery_executor: RecoveryExecutor | None = None,
        metrics: MetricsCollector | None = None,
    ) -> None:
        """Initialize the executor with a ToolRegistry.

        Args:
            registry: The tool registry used for lookup and rate-limit access.
            recovery_executor: Optional RecoveryExecutor providing Layer 6
                error recovery (retry, circuit breaker, cache fallback).
                When absent, the adapter is called directly (backward-compatible).
            metrics: Optional MetricsCollector for recording tool call telemetry.
                When absent, metrics instrumentation is skipped (backward-compatible).
        """
        self._registry = registry
        self._adapters: dict[str, AdapterFn] = {}
        self._recovery_executor = recovery_executor
        self._metrics: MetricsCollector | None = metrics

    def register_adapter(self, tool_id: str, adapter: AdapterFn) -> None:
        """Register an async adapter function for a tool.

        Args:
            tool_id: The stable snake_case tool identifier.
            adapter: Async callable accepting a validated Pydantic model instance
                     and returning a plain dict matching output_schema.
        """
        self._adapters[tool_id] = adapter
        logger.debug("Registered adapter for tool: %s", tool_id)

    async def dispatch(self, tool_name: str, arguments_json: str) -> ToolResult:
        """Execute a tool call end-to-end.

        Args:
            tool_name: The tool identifier to look up in the registry.
            arguments_json: JSON string of the tool arguments.

        Returns:
            ToolResult with success=True and data on success, or
            success=False with error/error_type on any failure.
        """
        dispatch_start = time.monotonic()
        self._metrics_increment("tool.call_count", tool_name)

        # Step 1: Lookup tool
        try:
            tool = self._registry.lookup(tool_name)
        except ToolNotFoundError as exc:
            logger.warning("Tool not found: %s", tool_name)
            self._metrics_increment("tool.error_count", tool_name)
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=str(exc),
                error_type="not_found",
            )

        # Step 2: Parse and validate input
        try:
            raw_args = json.loads(arguments_json)
            validated_input = tool.input_schema.model_validate(raw_args)
        except (TypeError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Input validation failed for tool %s: %s", tool_name, exc)
            self._metrics_increment("tool.error_count", tool_name)
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=str(exc),
                error_type="validation",
            )

        # Step 3: Verify adapter exists before consuming a rate-limit slot
        adapter = self._adapters.get(tool_name)
        if adapter is None:
            logger.warning("No adapter registered for tool: %s", tool_name)
            self._metrics_increment("tool.error_count", tool_name)
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=f"No adapter registered for tool {tool_name!r}",
                error_type="execution",
            )

        # Step 4/5: Execute adapter with rate limiting + optional recovery.
        #
        # Rate-limit check runs first to reject early when over quota.
        # ``record()`` is deferred to just before the actual adapter call so
        # that RecoveryExecutor short-circuits (cache hit, circuit-open) do
        # NOT consume a rate-limit slot.
        rate_limiter = self._registry.get_rate_limiter(tool_name)
        if not rate_limiter.check():
            logger.warning("Rate limit exceeded for tool: %s", tool_name)
            self._metrics_increment("tool.error_count", tool_name)
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=f"Rate limit exceeded for tool {tool_name!r}",
                error_type="rate_limit",
            )

        if self._recovery_executor is not None:
            # Pass rate_limiter to RecoveryExecutor so record() is called
            # only when the adapter is actually invoked (not on cache hit
            # or circuit-open short-circuit).
            recovery_result = await self._recovery_executor.execute(
                tool,
                adapter,
                validated_input,
                is_foreground=True,
                rate_limiter=rate_limiter,
            )
            tool_result = recovery_result.tool_result
            if not tool_result.success:
                self._metrics_increment("tool.error_count", tool_name)
                self._metrics_observe_duration(
                    "tool.duration_ms", tool_name, (time.monotonic() - dispatch_start) * 1000
                )
                return tool_result
            result_dict = dict(tool_result.data or {})
        else:
            rate_limiter.record()
            try:
                result_dict = await adapter(validated_input)
            except Exception as exc:
                logger.exception("Adapter execution failed for tool %s: %s", tool_name, exc)
                self._metrics_increment("tool.error_count", tool_name)
                self._metrics_observe_duration(
                    "tool.duration_ms", tool_name, (time.monotonic() - dispatch_start) * 1000
                )
                return ToolResult(
                    tool_id=tool_name,
                    success=False,
                    error=str(exc),
                    error_type="execution",
                )

        # Step 6: Validate output
        try:
            validated_output = tool.output_schema.model_validate(result_dict)
        except ValidationError as exc:
            logger.warning("Output schema mismatch for tool %s: %s", tool_name, exc)
            self._metrics_increment("tool.error_count", tool_name)
            self._metrics_observe_duration(
                "tool.duration_ms", tool_name, (time.monotonic() - dispatch_start) * 1000
            )
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=str(exc),
                error_type="schema_mismatch",
            )

        # Step 7: Return success
        logger.info("Tool dispatch succeeded: %s", tool_name)
        self._metrics_increment("tool.success_count", tool_name)
        self._metrics_observe_duration(
            "tool.duration_ms", tool_name, (time.monotonic() - dispatch_start) * 1000
        )
        return ToolResult(
            tool_id=tool_name,
            success=True,
            data=validated_output.model_dump(),
        )

    # ------------------------------------------------------------------
    # Private metrics helpers (fail-safe: never raise)
    # ------------------------------------------------------------------

    def _metrics_increment(self, name: str, tool_name: str, value: int = 1) -> None:
        if self._metrics is None:
            return
        try:
            self._metrics.increment(name, value=value, labels={"tool_id": tool_name})
        except Exception:  # noqa: BLE001
            logger.debug("metrics.increment failed for %s", name, exc_info=True)

    def _metrics_observe_duration(self, name: str, tool_name: str, duration_ms: float) -> None:
        if self._metrics is None:
            return
        try:
            self._metrics.observe(name, duration_ms, labels={"tool_id": tool_name})
        except Exception:  # noqa: BLE001
            logger.debug("metrics.observe failed for %s", name, exc_info=True)
