# Data Model: Tool System & Registry (Layer 2)

**Feature**: Epic #6 — Tool System & Registry
**Date**: 2026-04-12

## Entities

### 1. GovAPITool

The central model defining a government API tool. All fields from `docs/vision.md` Layer 2.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | `str` | Yes | — | Stable identifier, snake_case (e.g., `koroad_accident_search`) |
| `name_ko` | `str` | Yes | — | Korean display name (e.g., `교통사고정보`) |
| `provider` | `str` | Yes | — | Ministry or agency name (e.g., `도로교통공단`) |
| `category` | `list[str]` | Yes | — | Topic tags (e.g., `["교통", "안전"]`) |
| `endpoint` | `str` | Yes | — | API base URL |
| `auth_type` | `Literal["public", "api_key", "oauth"]` | Yes | — | Authentication method |
| `input_schema` | `type[BaseModel]` | Yes | — | Pydantic v2 model class for request parameters |
| `output_schema` | `type[BaseModel]` | Yes | — | Pydantic v2 model class for response data |
| `requires_auth` | `bool` | No | `True` | Whether citizen auth is required (FAIL-CLOSED) |
| `is_concurrency_safe` | `bool` | No | `False` | Safe to call in parallel (FAIL-CLOSED) |
| `is_personal_data` | `bool` | No | `True` | Whether response contains PII (FAIL-CLOSED) |
| `cache_ttl_seconds` | `int` | No | `0` | Response cache lifetime (FAIL-CLOSED: no caching) |
| `rate_limit_per_minute` | `int` | No | `10` | Client-side rate limit |
| `search_hint` | `str` | Yes | — | Korean + English discovery keywords |
| `is_core` | `bool` | No | `False` | Whether tool is in the core prompt partition |

**Validation**:
- `id` must match pattern `^[a-z][a-z0-9_]*$`
- `category` must not be empty
- `rate_limit_per_minute` must be > 0
- `cache_ttl_seconds` must be >= 0
- `search_hint` must not be empty

---

### 2. ToolRegistry

Central registry for tool management.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `_tools` | `dict[str, GovAPITool]` | Internal | `{}` | Registered tools by id |
| `_rate_limiters` | `dict[str, RateLimiter]` | Internal | `{}` | Per-tool rate limiters |

**Methods**:
- `register(tool: GovAPITool) -> None`: Register a tool. Raises `DuplicateToolError` if id exists.
- `lookup(tool_id: str) -> GovAPITool`: Get tool by id. Raises `ToolNotFoundError` if missing.
- `search(query: str) -> list[ToolSearchResult]`: Search tools by keyword. Returns ranked results.
- `core_tools() -> list[GovAPITool]`: Get core tools, sorted by id (deterministic).
- `situational_tools() -> list[GovAPITool]`: Get non-core tools.
- `export_core_tools_openai() -> list[dict]`: Export core tools in OpenAI function-calling format.
- `all_tools() -> list[GovAPITool]`: Get all registered tools.

---

### 3. ToolSearchResult

A search result from `search_tools()`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `tool` | `GovAPITool` | Yes | — | The matched tool |
| `score` | `float` | Yes | — | Relevance score (higher = more relevant) |
| `matched_tokens` | `list[str]` | Yes | — | Which query tokens matched |

---

### 4. RateLimiter

Per-tool rate limiter using sliding window.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `limit` | `int` | Yes | — | Max calls per minute |
| `_timestamps` | `deque[float]` | Internal | `deque()` | Call timestamps |
| `window_seconds` | `float` | No | `60.0` | Window size |

**Methods**:
- `check() -> bool`: Can a call be made right now?
- `record() -> None`: Record a call timestamp.
- `remaining() -> int`: How many calls are left in the current window?
- `reset() -> None`: Clear all timestamps.

---

### 5. ToolExecutor

Dispatches tool calls from the LLM with validation.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `registry` | `ToolRegistry` | Yes | — | The tool registry to dispatch against |

**Methods**:
- `dispatch(tool_name: str, arguments_json: str) -> ToolResult`: Full dispatch pipeline (lookup → validate input → check rate limit → execute → validate output).

---

### 6. ToolResult

Result from tool execution.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `tool_id` | `str` | Yes | — | Which tool was called |
| `success` | `bool` | Yes | — | Whether execution succeeded |
| `data` | `dict[str, object]` | No | `None` | Validated output data (if success) |
| `error` | `str \| None` | No | `None` | Error message (if failure) |
| `error_type` | `Literal["validation", "rate_limit", "not_found", "execution", "schema_mismatch"] \| None` | No | `None` | Error classification |

---

### 7. SearchToolsInput

Input schema for the `search_tools` meta-tool (registered in the registry for LLM discovery).

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | `str` | Yes | — | Search query (Korean or English keywords) |
| `max_results` | `int` | No | `5` | Maximum number of results to return |

---

### 8. SearchToolsOutput

Output schema for the `search_tools` meta-tool.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `results` | `list[SearchToolMatch]` | Yes | — | Matched tools |
| `total_registered` | `int` | Yes | — | Total tools in registry |

---

### 9. SearchToolMatch

A single match in `SearchToolsOutput`.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `tool_id` | `str` | Yes | — | Tool identifier |
| `name_ko` | `str` | Yes | — | Korean display name |
| `provider` | `str` | Yes | — | Ministry/agency |
| `category` | `list[str]` | Yes | — | Topic tags |
| `description` | `str` | Yes | — | Generated from search_hint |
| `score` | `float` | Yes | — | Relevance score |

## Relationships

```
ToolRegistry ──contains──→ dict[str, GovAPITool]
ToolRegistry ──manages──→ dict[str, RateLimiter]
ToolExecutor ──uses──→ ToolRegistry
ToolExecutor ──returns──→ ToolResult
GovAPITool ──references──→ type[BaseModel] (input_schema)
GovAPITool ──references──→ type[BaseModel] (output_schema)
GovAPITool ──exports──→ OpenAI ToolDefinition format
ToolRegistry.search() ──returns──→ list[ToolSearchResult]
search_tools meta-tool ──uses──→ SearchToolsInput → ToolRegistry.search() → SearchToolsOutput
```
