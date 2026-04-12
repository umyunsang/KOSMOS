# Quickstart: LLM Client Integration

**Feature**: Epic #4 — LLM Client Integration

## Setup

```bash
# Install dependencies
uv sync

# Set required environment variable
export KOSMOS_FRIENDLI_TOKEN="your-token-here"

# Optional configuration
export KOSMOS_FRIENDLI_BASE_URL="https://api.friendli.ai/v1"
export KOSMOS_FRIENDLI_MODEL="dep89a2fde0e09"
export KOSMOS_LLM_SESSION_BUDGET="100000"
```

## Basic Usage

### Non-streaming completion

```python
from kosmos.llm import LLMClient, ChatMessage

async with LLMClient() as client:
    response = await client.complete([
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hello!"),
    ])
    print(response.content)
    print(f"Tokens used: {response.usage.total_tokens}")
```

### Streaming completion

```python
from kosmos.llm import LLMClient, ChatMessage

async with LLMClient() as client:
    async for event in client.stream([
        ChatMessage(role="user", content="Explain Python async generators."),
    ]):
        if event.type == "content_delta":
            print(event.content, end="", flush=True)
        elif event.type == "usage":
            print(f"\nTokens: {event.usage.total_tokens}")
```

### With tool definitions

```python
from kosmos.llm import LLMClient, ChatMessage, ToolDefinition, FunctionSchema

tools = [
    ToolDefinition(
        type="function",
        function=FunctionSchema(
            name="get_weather",
            description="Get current weather for a location",
            parameters={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"}
                },
                "required": ["location"],
            },
        ),
    )
]

async with LLMClient() as client:
    response = await client.complete(
        [ChatMessage(role="user", content="What's the weather in Seoul?")],
        tools=tools,
    )
    if response.tool_calls:
        for call in response.tool_calls:
            print(f"Tool: {call.function.name}({call.function.arguments})")
```

### Budget tracking

```python
async with LLMClient() as client:
    print(f"Budget remaining: {client.usage.remaining}")

    response = await client.complete([...])
    print(f"Budget remaining: {client.usage.remaining}")
    print(f"Calls made: {client.usage.call_count}")
```

## Running Tests

```bash
# Unit tests (uses recorded fixtures, no API access needed)
uv run pytest tests/llm/

# Live tests are planned for Phase 2 (requires valid KOSMOS_FRIENDLI_TOKEN)
# uv run pytest tests/llm/ -m live
```
