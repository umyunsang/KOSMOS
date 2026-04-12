# Contract: Tool System & Registry API

**Module**: `kosmos.tools`
**Date**: 2026-04-12

## Public Interface

### GovAPITool

```python
class GovAPITool(BaseModel):
    """Government API tool definition with fail-closed defaults."""

    id: str                                          # snake_case identifier
    name_ko: str                                     # Korean display name
    provider: str                                    # Ministry/agency
    category: list[str]                              # Topic tags
    endpoint: str                                    # API base URL
    auth_type: Literal["public", "api_key", "oauth"] # Auth method
    input_schema: type[BaseModel]                    # Request params model
    output_schema: type[BaseModel]                   # Response data model
    search_hint: str                                 # Bilingual discovery keywords

    # Fail-closed defaults (Constitution § II)
    requires_auth: bool = True
    is_concurrency_safe: bool = False
    is_personal_data: bool = True
    cache_ttl_seconds: int = 0
    rate_limit_per_minute: int = 10
    is_core: bool = False

    def to_openai_tool(self) -> dict:
        """Export as OpenAI function-calling tool definition."""
```

### ToolRegistry

```python
class ToolRegistry:
    """Central registry for government API tools."""

    def __init__(self) -> None: ...

    def register(self, tool: GovAPITool) -> None:
        """Register a tool. Raises DuplicateToolError if id already registered."""

    def lookup(self, tool_id: str) -> GovAPITool:
        """Look up tool by id. Raises ToolNotFoundError if not found."""

    def search(self, query: str, max_results: int = 5) -> list[ToolSearchResult]:
        """Search tools by Korean or English keywords in search_hint."""

    def core_tools(self) -> list[GovAPITool]:
        """Return core tools sorted by id (deterministic for prompt caching)."""

    def situational_tools(self) -> list[GovAPITool]:
        """Return non-core tools."""

    def export_core_tools_openai(self) -> list[dict]:
        """Export core tools as OpenAI function-calling definitions."""

    def all_tools(self) -> list[GovAPITool]:
        """Return all registered tools."""

    def __len__(self) -> int: ...
    def __contains__(self, tool_id: str) -> bool: ...
```

### ToolExecutor

```python
class ToolExecutor:
    """Dispatches tool calls with input/output validation and rate limiting."""

    def __init__(self, registry: ToolRegistry) -> None: ...

    async def dispatch(self, tool_name: str, arguments_json: str) -> ToolResult:
        """Full dispatch pipeline.

        Steps:
        1. Lookup tool in registry
        2. Validate arguments against input_schema
        3. Check rate limit
        4. Execute tool adapter
        5. Validate result against output_schema
        6. Return ToolResult

        Returns ToolResult with success=False for any failure (never raises).
        """
```

### RateLimiter

```python
class RateLimiter:
    """Sliding-window rate limiter for per-tool call throttling."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None: ...

    def check(self) -> bool:
        """Can a call be made right now?"""

    def record(self) -> None:
        """Record a call timestamp."""

    @property
    def remaining(self) -> int:
        """Remaining calls in current window."""

    def reset(self) -> None:
        """Clear all timestamps."""
```

## Error Hierarchy

```python
class KosmosToolError(Exception):
    """Base exception for tool system errors."""

class DuplicateToolError(KosmosToolError):
    """Tool with this id is already registered."""

class ToolNotFoundError(KosmosToolError):
    """No tool with this id in the registry."""

class ToolValidationError(KosmosToolError):
    """Input or output validation failed against schema."""

class RateLimitExceededError(KosmosToolError):
    """Tool's rate limit has been exceeded."""

class ToolExecutionError(KosmosToolError):
    """Tool adapter raised an error during execution."""
```

## Module Layout

```
src/kosmos/tools/
├── __init__.py          # Public exports: GovAPITool, ToolRegistry, ToolExecutor
├── models.py            # GovAPITool, ToolResult, ToolSearchResult, SearchToolsInput/Output
├── registry.py          # ToolRegistry implementation
├── executor.py          # ToolExecutor dispatch logic
├── rate_limiter.py      # RateLimiter sliding window
├── errors.py            # Error hierarchy
└── search.py            # search_tools meta-tool and search logic
```

## Integration Points

- **Epic #4 (LLM Client)**: `GovAPITool.to_openai_tool()` produces `ToolDefinition` dicts consumed by `LLMClient.complete(tools=...)` and `LLMClient.stream(tools=...)`.
- **Epic #5 (Query Engine)**: `ToolExecutor.dispatch()` is called when the query engine processes `tool_calls` from the LLM response.
- **Epic #7 (API Adapters)**: Each adapter creates a `GovAPITool` instance and registers it with the `ToolRegistry`.
