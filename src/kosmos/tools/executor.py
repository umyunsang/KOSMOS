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
from typing import Any

from pydantic import BaseModel, ValidationError

from kosmos.tools.errors import ToolNotFoundError
from kosmos.tools.models import GovAPITool, ToolResult  # noqa: F401
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

AdapterFn = Callable[[BaseModel], Awaitable[dict[str, Any]]]


class ToolExecutor:
    """Dispatch LLM tool calls through validation, rate-limiting, and execution.

    The dispatch pipeline (in order):
    1. Lookup tool in registry.
    2. Parse and validate JSON arguments against input_schema.
    3. Check rate limit.
    4. Record rate-limit timestamp.
    5. Execute the registered adapter.
    6. Validate adapter output against output_schema.
    7. Return ToolResult(success=True, data=...).

    Any step failure returns ToolResult(success=False, ...) with an
    appropriate error_type. The executor itself never raises.
    """

    def __init__(self, registry: ToolRegistry) -> None:
        """Initialize the executor with a ToolRegistry.

        Args:
            registry: The tool registry used for lookup and rate-limit access.
        """
        self._registry = registry
        self._adapters: dict[str, AdapterFn] = {}

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
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Input validation failed for tool %s: %s", tool_name, exc)
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=str(exc),
                error_type="validation",
            )

        # Step 3: Check rate limit
        rate_limiter = self._registry.get_rate_limiter(tool_name)
        if not rate_limiter.check():
            logger.warning("Rate limit exceeded for tool: %s", tool_name)
            return ToolResult(
                tool_id=tool_name,
                success=False,
                error=f"Rate limit exceeded for tool {tool_name!r}",
                error_type="rate_limit",
            )

        # Step 4: Record call
        rate_limiter.record()

        # Step 5: Execute adapter
        adapter = self._adapters.get(tool_name)
        try:
            if adapter is None:
                raise RuntimeError(f"No adapter registered for tool {tool_name!r}")
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
