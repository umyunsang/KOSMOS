# SPDX-License-Identifier: Apache-2.0
"""Unit tests for kosmos.tools.executor.ToolExecutor."""

from __future__ import annotations

import json

import pytest

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_executor(  # noqa: E501
    sample_tool_factory,
    mock_tool_adapter,
    *,
    tool_id: str = "kma_weather_forecast",
):
    """Build a ToolExecutor pre-loaded with one tool and its adapter."""
    registry = ToolRegistry()
    tool = sample_tool_factory(id=tool_id)
    registry.register(tool)
    executor = ToolExecutor(registry)
    executor.register_adapter(tool_id, mock_tool_adapter)
    return executor


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_success(sample_tool_factory, mock_tool_adapter):
    """Valid arguments produce a ToolResult with success=True and correct data."""
    executor = _make_executor(sample_tool_factory, mock_tool_adapter)
    args = json.dumps({"city": "Seoul"})

    result = await executor.dispatch("kma_weather_forecast", args)

    assert result.success is True
    assert result.tool_id == "kma_weather_forecast"
    assert result.error is None
    assert result.error_type is None
    assert result.data is not None
    assert result.data["temperature"] == 22.5
    assert result.data["humidity"] == 45


@pytest.mark.asyncio
async def test_dispatch_unknown_tool(sample_tool_factory, mock_tool_adapter):
    """Dispatching a tool_id not in the registry returns error_type='not_found'."""
    executor = _make_executor(sample_tool_factory, mock_tool_adapter)
    args = json.dumps({"city": "Busan"})

    result = await executor.dispatch("nonexistent_tool", args)

    assert result.success is False
    assert result.tool_id == "nonexistent_tool"
    assert result.error_type == "not_found"
    assert result.error is not None
    assert result.data is None


@pytest.mark.asyncio
async def test_dispatch_invalid_input_bad_json(sample_tool_factory, mock_tool_adapter):
    """Malformed JSON returns error_type='validation'."""
    executor = _make_executor(sample_tool_factory, mock_tool_adapter)

    result = await executor.dispatch("kma_weather_forecast", "{not valid json}")

    assert result.success is False
    assert result.error_type == "validation"
    assert result.data is None


@pytest.mark.asyncio
async def test_dispatch_invalid_input_schema_violation(sample_tool_factory, mock_tool_adapter):
    """Valid JSON that fails schema validation returns error_type='validation'."""
    executor = _make_executor(sample_tool_factory, mock_tool_adapter)
    # Pydantic v2 coerces int->str, so test with a missing required field instead
    args_missing = json.dumps({"date": "2026-04-12"})
    result = await executor.dispatch("kma_weather_forecast", args_missing)

    assert result.success is False
    assert result.error_type == "validation"
    assert result.data is None


@pytest.mark.asyncio
async def test_dispatch_rate_limit_exceeded(sample_tool_factory, mock_tool_adapter):
    """After exhausting the rate limit, dispatch returns error_type='rate_limit'."""
    registry = ToolRegistry()
    # Set rate_limit_per_minute=1 so one call exhausts it
    tool = sample_tool_factory(id="kma_weather_forecast", rate_limit_per_minute=1)
    registry.register(tool)
    executor = ToolExecutor(registry)
    executor.register_adapter("kma_weather_forecast", mock_tool_adapter)

    args = json.dumps({"city": "Seoul"})

    # First call should succeed (consumes the only slot)
    first = await executor.dispatch("kma_weather_forecast", args)
    assert first.success is True

    # Second call should be rate-limited
    second = await executor.dispatch("kma_weather_forecast", args)
    assert second.success is False
    assert second.error_type == "rate_limit"
    assert second.data is None


@pytest.mark.asyncio
async def test_dispatch_adapter_exception(sample_tool_factory):
    """An adapter that raises RuntimeError returns error_type='execution'."""
    registry = ToolRegistry()
    tool = sample_tool_factory(id="kma_weather_forecast")
    registry.register(tool)
    executor = ToolExecutor(registry)

    async def _failing_adapter(validated_input):
        raise RuntimeError("upstream service unavailable")

    executor.register_adapter("kma_weather_forecast", _failing_adapter)

    result = await executor.dispatch("kma_weather_forecast", json.dumps({"city": "Incheon"}))

    assert result.success is False
    assert result.error_type == "execution"
    assert "upstream service unavailable" in (result.error or "")
    assert result.data is None


@pytest.mark.asyncio
async def test_dispatch_output_schema_mismatch(sample_tool_factory):
    """An adapter returning wrong shape returns error_type='schema_mismatch'."""
    registry = ToolRegistry()
    tool = sample_tool_factory(id="kma_weather_forecast")
    registry.register(tool)
    executor = ToolExecutor(registry)

    async def _wrong_shape_adapter(validated_input):
        # Missing required fields: temperature, condition, humidity
        return {"unexpected_field": "oops"}

    executor.register_adapter("kma_weather_forecast", _wrong_shape_adapter)

    result = await executor.dispatch("kma_weather_forecast", json.dumps({"city": "Daegu"}))

    assert result.success is False
    assert result.error_type == "schema_mismatch"
    assert result.data is None
