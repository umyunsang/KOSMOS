# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 data models for the KOSMOS Tool System module."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

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

    llm_description: str | None = None
    """Optional richer description shown to the LLM in the OpenAI tool definition.

    When present, ``to_openai_tool()`` emits this string as the ``description``
    field instead of ``name_ko``. Use this to communicate ordering prerequisites
    or tool-selection hints that the LLM must see *before* deciding to call the
    tool — field-level descriptions on the input schema are only seen after the
    model has already picked this tool, which is too late for ordering rules.
    """

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
        """Export as an OpenAI function-calling tool definition.

        Uses ``llm_description`` when set (richer ordering/prereq guidance),
        falling back to ``name_ko`` otherwise.
        """
        description = self.llm_description or self.name_ko
        return {
            "type": "function",
            "function": {
                "name": self.id,
                "description": description,
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
        Literal[
            "validation",
            "rate_limit",
            "not_found",
            "execution",
            "schema_mismatch",
            "permission_denied",
            "timeout",
            "circuit_open",
            "api_error",
            "auth_expired",
        ]
        | None
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
            if self.data is not None:
                msg = "success=False must not have data set"
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


# ---------------------------------------------------------------------------
# T005 — ResolveLocationInput
# ---------------------------------------------------------------------------


class ResolveLocationInput(BaseModel):
    """Input to the resolve_location tool.

    Converts a free-text place query into typed location identifiers.
    Field shapes and enum values are binding per contracts/resolve_location.input.schema.json.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=200)
    """Free-text place query, Korean or English (e.g., '서울 강남구')."""

    want: Literal[
        "coords",
        "adm_cd",
        "coords_and_admcd",
        "road_address",
        "jibun_address",
        "poi",
        "all",
    ] = "coords_and_admcd"
    """Which identifier(s) to resolve. Default 'coords_and_admcd' returns a
    ResolveBundle with both lat/lon and 10-digit 법정동 code."""

    near: tuple[float, float] | None = None
    """[lat, lon] tiebreaker when the query is ambiguous. Optional."""


# ---------------------------------------------------------------------------
# T006 — ResolveLocationOutput (6-variant discriminated union)
# ---------------------------------------------------------------------------


class CoordResult(BaseModel):
    """Geocoding result: latitude + longitude."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["coords"]
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    confidence: Literal["high", "medium", "low"]
    source: Literal["kakao", "juso", "sgis"]


class AdmCodeResult(BaseModel):
    """Administrative division code result (10-digit 법정동 code)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["adm_cd"]
    code: str = Field(pattern=r"^[0-9]{10}$")
    name: str
    level: Literal["sido", "sigungu", "eupmyeondong"]
    source: Literal["sgis", "juso"]


class AddressResult(BaseModel):
    """Structured address result."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["address"]
    road_address: str | None = None
    jibun_address: str | None = None
    postal_code: str | None = None
    source: Literal["kakao", "juso"]


class POIResult(BaseModel):
    """Point of interest result."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["poi"]
    name: str
    category: str
    lat: float
    lon: float
    source: Literal["kakao"]


class ResolveBundle(BaseModel):
    """Bundle of multiple resolve results with provenance."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["bundle"]
    source: Literal["bundle"]
    coords: CoordResult | None = None
    adm_cd: AdmCodeResult | None = None
    address: AddressResult | None = None
    poi: POIResult | None = None


class ResolveError(BaseModel):
    """Location resolution error with reason and optional candidates."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["error"]
    reason: Literal[
        "not_found",
        "ambiguous",
        "upstream_unavailable",
        "invalid_query",
        "empty_query",
        "out_of_domain",
    ]
    message: str
    candidates: list[CoordResult | AdmCodeResult | AddressResult | POIResult] = Field(
        default_factory=list
    )


ResolveLocationOutput = Annotated[
    CoordResult | AdmCodeResult | AddressResult | POIResult | ResolveBundle | ResolveError,
    Field(discriminator="kind"),
]
"""Discriminated union on `kind`. Binding variant names from docs/design/mvp-tools.md §4."""


# ---------------------------------------------------------------------------
# T007 — LookupInput (discriminated on `mode`)
# ---------------------------------------------------------------------------


class LookupSearchInput(BaseModel):
    """Input for lookup(mode='search'): BM25 gate over adapter registry."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["search"]
    query: str = Field(min_length=1, max_length=200)
    """Korean or English free-text describing the data you want."""

    domain: str | None = None
    """Optional facet filter (matches GovAPITool.category)."""

    top_k: int | None = Field(default=None, ge=1, le=20)
    """Per-call override; server-side clamp [1, 20]. If None, uses KOSMOS_LOOKUP_TOPK default."""


class LookupFetchInput(BaseModel):
    """Input for lookup(mode='fetch'): typed invocation of a specific adapter."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["fetch"]
    tool_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    """Must come from a previous `search` result. Never guess."""

    params: dict[str, object]
    """Validated against the target adapter's input_schema at fetch time."""

    page: int | None = Field(default=None, ge=1)


LookupInput = Annotated[
    LookupSearchInput | LookupFetchInput,
    Field(discriminator="mode"),
]
"""Discriminated union on `mode`. search → BM25; fetch → typed adapter invocation."""


# ---------------------------------------------------------------------------
# T008 — LookupOutput (5-variant discriminated union) + supporting types
# ---------------------------------------------------------------------------


class LookupMeta(BaseModel):
    """Metadata injected into every lookup(mode='fetch') response envelope."""

    model_config = ConfigDict(extra="forbid")

    source: str
    """tool_id of the adapter that handled this request."""

    fetched_at: datetime
    """UTC timestamp when the response was fetched."""

    request_id: str
    """UUID for this request, for tracing."""

    elapsed_ms: int = Field(ge=0)
    """Total elapsed time in milliseconds."""

    rate_limit_remaining: int | None = None
    """Remaining rate-limit slots for this adapter, if known."""


class AdapterCandidate(BaseModel):
    """A single search-result entry from lookup(mode='search')."""

    model_config = ConfigDict(extra="forbid")

    tool_id: str
    score: float = Field(ge=0)
    required_params: list[str]
    search_hint: str
    why_matched: str
    requires_auth: bool = False
    is_personal_data: bool = False


class LookupSearchResult(BaseModel):
    """Result from lookup(mode='search'): ranked adapter candidates."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["search"]
    candidates: list[AdapterCandidate]
    total_registry_size: int = Field(ge=0)
    effective_top_k: int = Field(ge=0, le=20)
    reason: Literal["ok", "empty_registry", "below_threshold"] = "ok"


class LookupRecord(BaseModel):
    """Single-record fetch result."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["record"]
    item: dict[str, object]
    meta: LookupMeta


class LookupCollection(BaseModel):
    """Collection fetch result (list of records)."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["collection"]
    items: list[dict[str, object]]
    total_count: int | None = None
    next_cursor: str | None = None
    meta: LookupMeta


class LookupTimeseries(BaseModel):
    """Time-series fetch result."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["timeseries"]
    points: list[dict[str, object]]
    interval: Literal["minute", "hour", "day"]
    meta: LookupMeta


class LookupError(BaseModel):  # noqa: A001
    """Structured error result from lookup operations."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["error"]
    reason: Literal[
        "auth_required",
        "stale_data",
        "timeout",
        "upstream_unavailable",
        "unknown_tool",
        "invalid_params",
        "out_of_domain",
        "empty_registry",
    ]
    message: str
    upstream_code: str | None = None
    upstream_message: str | None = None
    retryable: bool = False
    meta: LookupMeta | None = None


LookupOutput = Annotated[
    LookupSearchResult | LookupRecord | LookupCollection | LookupTimeseries | LookupError,
    Field(discriminator="kind"),
]
"""Discriminated union on `kind`. Variant names are BINDING per docs/design/mvp-tools.md §5.4."""
