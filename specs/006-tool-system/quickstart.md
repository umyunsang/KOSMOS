# Quickstart: Tool System & Registry

**Feature**: Epic #6 — Tool System & Registry

## Setup

```bash
uv sync
```

No additional environment variables are required for the tool system itself. Individual tool adapters may require API keys.

## Basic Usage

### Registering a tool

```python
from pydantic import BaseModel
from kosmos.tools import GovAPITool, ToolRegistry

# Define input/output schemas
class WeatherInput(BaseModel):
    city: str
    date: str | None = None

class WeatherOutput(BaseModel):
    temperature: float
    condition: str
    humidity: int

# Create tool definition (fail-closed defaults apply)
weather_tool = GovAPITool(
    id="kma_weather_forecast",
    name_ko="날씨예보",
    provider="기상청",
    category=["날씨", "기상"],
    endpoint="http://apis.data.go.kr/1360000/...",
    auth_type="api_key",
    input_schema=WeatherInput,
    output_schema=WeatherOutput,
    search_hint="날씨 예보 weather forecast 기상청 KMA temperature",
    # Explicit overrides (everything else stays fail-closed):
    is_personal_data=False,  # weather is public data
    cache_ttl_seconds=300,   # cache for 5 minutes
    is_core=True,            # always loaded in prompt
)

# Register
registry = ToolRegistry()
registry.register(weather_tool)
```

### Searching tools

```python
results = registry.search("날씨 weather")
for result in results:
    print(f"{result.tool.id}: {result.tool.name_ko} (score: {result.score})")
```

### Exporting for LLM

```python
# Get deterministic core tool list for prompt caching
openai_tools = registry.export_core_tools_openai()
# LLMClient.complete() accepts both ToolDefinition models and raw dicts:
# response = await llm_client.complete(messages, tools=openai_tools)
```

### Dispatching a tool call

```python
from kosmos.tools import ToolExecutor

executor = ToolExecutor(registry)
result = await executor.dispatch(
    tool_name="kma_weather_forecast",
    arguments_json='{"city": "서울"}'
)

if result.success:
    print(result.data)
else:
    print(f"Error: {result.error} ({result.error_type})")
```

### Rate limit checking

```python
tool = registry.lookup("kma_weather_forecast")
# Rate limiter is managed by the registry internally
# ToolExecutor checks rate limits before dispatching
```

## Running Tests

```bash
# Unit tests (all use mock tools, no API access)
uv run pytest tests/tools/

# No live tests needed for the registry itself
```
