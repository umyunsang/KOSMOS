# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 data models for the KOSMOS Tool System module."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GovAPITool(BaseModel):
    """Government API tool definition with fail-closed security defaults.

    All boolean safety fields default to the more restrictive value
    per Constitution § II (fail-closed principle).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: str
    """Stable snake_case identifier (e.g. ``koroad_accident_search``)."""

    name_ko: str
    """Korean display name shown to users."""

    provider: str
    """Ministry or agency that owns the API."""

    category: list[str]
    """Non-empty list of topic tags."""

    endpoint: str
    """API base URL."""

    auth_type: Literal["public", "api_key", "oauth"]
    """Authentication mechanism required by the upstream API."""

    input_schema: type[BaseModel]
    """Pydantic v2 model class for request parameters."""

    output_schema: type[BaseModel]
    """Pydantic v2 model class for response data."""

    search_hint: str
    """Bilingual (Korean + English) discovery keywords for semantic search."""

    # --- Fail-closed defaults (Constitution § II) ---
    requires_auth: bool = True
    """Whether citizen authentication is required. Defaults to True (fail-closed)."""

    is_concurrency_safe: bool = False
    """Safe to call concurrently. Defaults to False (fail-closed)."""

    is_personal_data: bool = True
    """Whether the response may contain PII. Defaults to True (fail-closed)."""

    cache_ttl_seconds: int = 0
    """Response cache lifetime in seconds. Defaults to 0 (no caching, fail-closed)."""

    rate_limit_per_minute: int = 10
    """Client-side rate limit; must be greater than zero."""

    is_core: bool = False
    """Whether the tool is included in the core prompt partition."""

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not re.fullmatch(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                f"Tool id {v!r} must match ^[a-z][a-z0-9_]*$ "
                "(lowercase, start with a letter, underscores only)"
            )
        return v

    @field_validator("category")
    @classmethod
    def _validate_category(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("category must not be empty")
        return v

    @field_validator("rate_limit_per_minute")
    @classmethod
    def _validate_rate_limit(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"rate_limit_per_minute must be > 0, got {v}")
        return v

    @field_validator("cache_ttl_seconds")
    @classmethod
    def _validate_cache_ttl(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"cache_ttl_seconds must be >= 0, got {v}")
        return v

    @field_validator("search_hint")
    @classmethod
    def _validate_search_hint(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("search_hint must not be empty or whitespace-only")
        return v

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    def to_openai_tool(self) -> dict[str, object]:
        """Export as an OpenAI function-calling tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": self.name_ko,
                "parameters": self.input_schema.model_json_schema(),
            },
        }


class ToolResult(BaseModel):
    """Result returned by the tool executor after dispatching a tool call."""

    model_config = ConfigDict(frozen=True)

    tool_id: str
    """Identifier of the tool that was called."""

    success: bool
    """Whether the execution completed without error."""

    data: dict[str, object] | None = None
    """Validated output payload; populated only on success."""

    error: str | None = None
    """Human-readable error message; populated only on failure."""

    error_type: (
        Literal["validation", "rate_limit", "not_found", "execution", "schema_mismatch"] | None
    ) = None
    """Structured error classification; populated only on failure."""

    @model_validator(mode="after")
    def _check_success_consistency(self) -> ToolResult:
        """Enforce invariants between success and error/data fields."""
        if self.success:
            if self.error is not None or self.error_type is not None:
                msg = "success=True must not have error or error_type set"
                raise ValueError(msg)
        else:
            if self.error is None or self.error_type is None:
                msg = "success=False must have both error and error_type set"
                raise ValueError(msg)
        return self


class ToolSearchResult(BaseModel):
    """A ranked search result returned by ``ToolRegistry.search()``."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tool: GovAPITool
    """The matched tool definition."""

    score: float
    """Relevance score; higher means more relevant."""

    matched_tokens: list[str]
    """Query tokens that contributed to this match."""


class SearchToolMatch(BaseModel):
    """A single lightweight match entry inside ``SearchToolsOutput``.

    Carries only the fields needed by the LLM to decide whether to call a tool,
    avoiding the heavyweight ``GovAPITool`` with embedded schema classes.
    """

    model_config = ConfigDict(frozen=True)

    tool_id: str
    """Stable snake_case tool identifier."""

    name_ko: str
    """Korean display name."""

    provider: str
    """Ministry or agency that owns the API."""

    category: list[str]
    """Topic tags."""

    description: str
    """Human-readable description derived from the tool's ``search_hint``."""

    score: float
    """Relevance score for this match."""


class SearchToolsInput(BaseModel):
    """Input schema for the ``search_tools`` meta-tool."""

    query: str
    """Search query in Korean or English keywords."""

    max_results: int = Field(default=5, gt=0)
    """Maximum number of results to return; must be greater than zero."""


class SearchToolsOutput(BaseModel):
    """Output schema for the ``search_tools`` meta-tool."""

    results: list[SearchToolMatch]
    """Ranked list of tool matches."""

    total_registered: int
    """Total number of tools currently registered in the registry."""
