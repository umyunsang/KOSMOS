# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the KOSMOS Tool System module."""

from __future__ import annotations

import os
from enum import StrEnum


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
        super().__init__(f"Rate limit exceeded for tool {tool_id!r}: limit={limit}")
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


class ConfigurationError(KosmosToolError):
    """A required environment variable is missing or empty."""

    def __init__(self, var_name: str) -> None:
        super().__init__(
            f"Required environment variable {var_name!r} is not set or is empty. "
            f"Set it before calling this tool."
        )
        self.var_name = var_name


# ---------------------------------------------------------------------------
# T009 — Closed enums for LookupError / ResolveError reasons
# ---------------------------------------------------------------------------


class LookupErrorReason(StrEnum):
    """Closed set of reasons for a LookupError envelope.

    Members (10 total):
        auth_required: Tool requires an auth credential not yet provided.
        stale_data: Upstream data breached the freshness SLO (e.g., NMC hvidate).
        timeout: Upstream request exceeded the per-tool timeout budget.
        upstream_unavailable: Upstream transport failure or non-2xx response.
        unknown_tool: Requested tool id is not in the registry.
        invalid_params: Input parameters failed schema validation.
        out_of_domain: Input parameters are valid shape but outside the tool's supported domain.
        empty_registry: Registry was queried with no tools registered.
        content_blocked: LLM pre/post-call content violated the moderation policy
            (specs/026-safety-rails § FR-008..FR-011).
        injection_detected: Tool output carried indirect-injection signals and was
            blocked before reaching the LLM context (specs/026-safety-rails § FR-012..FR-015).
    """

    auth_required = "auth_required"
    stale_data = "stale_data"
    timeout = "timeout"
    upstream_unavailable = "upstream_unavailable"
    unknown_tool = "unknown_tool"
    invalid_params = "invalid_params"
    out_of_domain = "out_of_domain"
    empty_registry = "empty_registry"
    content_blocked = "content_blocked"
    injection_detected = "injection_detected"


class ResolveErrorReason(StrEnum):
    """Closed set of reasons for a ResolveError envelope."""

    not_found = "not_found"
    ambiguous = "ambiguous"
    upstream_unavailable = "upstream_unavailable"
    invalid_query = "invalid_query"
    empty_query = "empty_query"
    out_of_domain = "out_of_domain"


# ---------------------------------------------------------------------------
# T009 — Additional exception types
# ---------------------------------------------------------------------------


class EnvelopeNormalizationError(KosmosToolError):
    """Handler returned a payload that does not match the LookupOutput discriminated union."""

    def __init__(self, tool_id: str, detail: str) -> None:
        super().__init__(f"Envelope normalization failed for tool {tool_id!r}: {detail}")
        self.tool_id = tool_id
        self.detail = detail


class RegistrationError(KosmosToolError):
    """Adapter registration violated an invariant.

    Example: ``is_personal_data=True`` without ``requires_auth=True`` (FR-038).
    """

    def __init__(self, tool_id: str, message: str) -> None:
        super().__init__(f"Registration error for tool {tool_id!r}: {message}")
        self.tool_id = tool_id


class Layer3GateViolation(KosmosToolError):  # noqa: N818
    """Raised when an NMC-style stub adapter's handler body is reached despite the Layer 3 gate.

    This should never occur in production — it signals a programming error.
    """

    def __init__(self, tool_id: str) -> None:
        super().__init__(
            f"Layer3GateViolation: handler body of {tool_id!r} was invoked "
            "despite the auth_required short-circuit. This is a bug."
        )
        self.tool_id = tool_id


def _require_env(var_name: str) -> str:
    """Read an environment variable and raise ConfigurationError if absent or empty.

    Strips surrounding whitespace before the emptiness check.

    Args:
        var_name: The name of the environment variable to read.

    Returns:
        The stripped, non-empty value of the variable.

    Raises:
        ConfigurationError: If the variable is missing or contains only whitespace.
    """
    value = os.environ.get(var_name, "").strip()
    if not value:
        raise ConfigurationError(var_name)
    return value
