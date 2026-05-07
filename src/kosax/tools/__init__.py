# SPDX-License-Identifier: Apache-2.0
"""Tool system and registry for government API tools."""

from kosax.tools.errors import (
    ConfigurationError,
    DuplicateToolError,
    KosaxToolError,
    RateLimitExceededError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
    _require_env,
)
from kosax.tools.executor import ToolExecutor
from kosax.tools.models import (
    GovAPITool,
    SearchToolMatch,
    SearchToolsInput,
    SearchToolsOutput,
    ToolResult,
    ToolSearchResult,
)
from kosax.tools.rate_limiter import RateLimiter
from kosax.tools.registry import ToolRegistry

__all__ = [
    "ConfigurationError",
    "DuplicateToolError",
    "GovAPITool",
    "KosaxToolError",
    "RateLimitExceededError",
    "RateLimiter",
    "SearchToolMatch",
    "SearchToolsInput",
    "SearchToolsOutput",
    "ToolExecutionError",
    "ToolExecutor",
    "ToolNotFoundError",
    "ToolRegistry",
    "ToolResult",
    "ToolSearchResult",
    "ToolValidationError",
    "_require_env",
]
