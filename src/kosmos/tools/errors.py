# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the KOSMOS Tool System module."""

from __future__ import annotations


class KosmosToolError(Exception):
    """Base exception for tool system errors."""


class DuplicateToolError(KosmosToolError):
    """Tool with this id is already registered."""

    def __init__(self, tool_id: str) -> None:
        super().__init__(f"Tool already registered: {tool_id!r}")
        self.tool_id = tool_id


class ToolNotFoundError(KosmosToolError):
    """No tool with this id in the registry."""

    def __init__(self, tool_id: str) -> None:
        super().__init__(f"Tool not found: {tool_id!r}")
        self.tool_id = tool_id


class ToolValidationError(KosmosToolError):
    """Input or output validation failed against schema."""

    def __init__(
        self,
        tool_id: str,
        message: str,
        validation_errors: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.tool_id = tool_id
        self.validation_errors = validation_errors or []


class RateLimitExceededError(KosmosToolError):
    """Tool's rate limit has been exceeded."""

    def __init__(self, tool_id: str, limit: int | float) -> None:
        super().__init__(
            f"Rate limit exceeded for tool {tool_id!r}: limit={limit}"
        )
        self.tool_id = tool_id
        self.limit = limit


class ToolExecutionError(KosmosToolError):
    """Tool adapter raised an error during execution."""

    def __init__(
        self,
        tool_id: str,
        message: str,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.tool_id = tool_id
        self.cause = cause
