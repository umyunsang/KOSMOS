# SPDX-License-Identifier: Apache-2.0
"""Tool dispatcher for the KOSMOS Tool System module.

Resolves tool calls from the LLM by name, validates input/output against
Pydantic schemas, enforces rate limits, and returns a structured ToolResult.
The executor never raises — all error paths are captured in ToolResult.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from kosmos.tools.errors import ToolNotFoundError
from kosmos.tools.models import ToolResult
from kosmos.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from kosmos.recovery.executor import RecoveryExecutor

logger = logging.getLogger(__name__)

AdapterFn = Callable[[BaseModel], Awaitable[dict[str, Any]]]


class ToolExecutor:
    """Dispatch LLM tool calls through validation, rate-limiting, and execution.

    The dispatch pipeline (in order):
    1. Lookup tool in registry.
    2. Parse and validate JSON arguments against input_schema.
    3. Verify adapter exists.
    4. If RecoveryExecutor is absent: check and record rate limit, then call
       adapter directly.
    5. If RecoveryExecutor is present: delegate to it for retry / circuit-breaker /
       cache — rate limiting is handled internally by RecoveryExecutor to avoid
       charging a slot before a circuit-open or cache-hit short-circuit.
    6. Validate adapter output against output_schema.
    7. Return ToolResult(success=True, data=...).

    Any step failure returns ToolResult(success=False, ...) with an
    appropriate error_type. The executor itself never raises.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        recovery_executor: RecoveryExecutor | None = None,
    ) -> None:
        """Initialize the executor with a ToolRegistry.

        Args:
            registry: The tool registry used for lookup and rate-limit access.
            recovery_executor: Optional RecoveryExecutor providing Layer 6
                error recovery (retry, circuit breaker, cache fallback).
                When absent, the adapter is called directly (backward-compatible).
        """
        self._registry = registry
        self._adapters: dict[str, AdapterFn] = {}
        self._recovery_executor = recovery_executor

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
        # Step 1: Lookup tool
        try:
            tool = self._registry.lookup(tool_name)
        except ToolNotFoundError as exc:
            logger.warning("Tool not found: %s", tool_name)
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
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=f"No adapter registered for tool {tool_name!r}",
                error_type="execution",
            )

        # Step 4/5: Execute adapter — rate limiting placement depends on recovery mode.
        #
        # When RecoveryExecutor is present, skip rate limiting here and delegate
        # everything to it.  RecoveryExecutor may short-circuit via a circuit-open
        # check or a cache hit *before* reaching the actual adapter call, so
        # charging a rate-limit slot at this point would be premature.
        #
        # When RecoveryExecutor is absent, apply rate limiting as usual around
        # the direct adapter invocation.
        if self._recovery_executor is not None:
            # Delegate to RecoveryExecutor for retry / circuit-breaker / cache.
            # Rate limiting is handled internally by RecoveryExecutor.
            recovery_result = await self._recovery_executor.execute(
                tool,
                adapter,
                validated_input,
                is_foreground=True,
            )
            tool_result = recovery_result.tool_result
            if not tool_result.success:
                return tool_result
            result_dict = dict(tool_result.data or {})
        else:
            rate_limiter = self._registry.get_rate_limiter(tool_name)
            if not rate_limiter.check():
                logger.warning("Rate limit exceeded for tool: %s", tool_name)
                return ToolResult(
                    tool_id=tool_name,
                    success=False,
                    error=f"Rate limit exceeded for tool {tool_name!r}",
                    error_type="rate_limit",
                )
            rate_limiter.record()
            try:
                result_dict = await adapter(validated_input)
            except Exception as exc:
                logger.exception("Adapter execution failed for tool %s: %s", tool_name, exc)
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
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=str(exc),
                error_type="schema_mismatch",
            )

        # Step 7: Return success
        logger.info("Tool dispatch succeeded: %s", tool_name)
        return ToolResult(
            tool_id=tool_name,
            success=True,
            data=validated_output.model_dump(),
        )
