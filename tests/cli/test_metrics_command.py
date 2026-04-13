# SPDX-License-Identifier: Apache-2.0
"""Tests for /metrics REPL command (T019).

Validates:
- Empty MetricsCollector → "No metrics collected in this session."
- Non-empty collector → table with metric name and value
- No error on concurrent snapshot during writes (non-blocking)
- No metrics collector → "not enabled" message without error
"""

from __future__ import annotations

import threading
from io import StringIO

from rich.console import Console

from kosmos.observability.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_repl_with_metrics(mc: MetricsCollector | None = None):  # type: ignore[return]
    """Create a REPLLoop with a mock engine and the given MetricsCollector."""
    from unittest.mock import MagicMock  # noqa: PLC0415

    from kosmos.cli.config import CLIConfig  # noqa: PLC0415
    from kosmos.cli.renderer import EventRenderer  # noqa: PLC0415
    from kosmos.cli.repl import REPLLoop  # noqa: PLC0415

    console_output = StringIO()
    console = Console(file=console_output, highlight=False, markup=True)

    mock_engine = MagicMock()
    mock_registry = MagicMock()
    mock_renderer = MagicMock(spec=EventRenderer)

    config = CLIConfig()

    repl = REPLLoop(
        engine=mock_engine,
        registry=mock_registry,
        console=console,
        config=config,
        renderer=mock_renderer,
        metrics=mc,
    )
    return repl, console_output


# ---------------------------------------------------------------------------
# T019: test_metrics_empty_collector
# ---------------------------------------------------------------------------


def test_metrics_empty_collector() -> None:
    """When MetricsCollector has no data, output says 'No metrics collected'."""
    mc = MetricsCollector()
    repl, output = _make_repl_with_metrics(mc)

    repl._cmd_metrics()

    text = output.getvalue()
    assert "No metrics collected in this session." in text


# ---------------------------------------------------------------------------
# T019: test_metrics_renders_table
# ---------------------------------------------------------------------------


def test_metrics_renders_table() -> None:
    """After adding one counter and one histogram, /metrics renders values."""
    mc = MetricsCollector()
    mc.increment("tool.call_count", labels={"tool_id": "koroad"})
    mc.observe("llm.call_duration_ms", 42.0, labels={"model": "test-model"})

    repl, output = _make_repl_with_metrics(mc)
    repl._cmd_metrics()

    text = output.getvalue()
    # Should contain the counter metric name
    assert "tool.call_count" in text
    # Should contain counter value
    assert "1" in text
    # Should contain histogram metric name
    assert "llm.call_duration_ms" in text


# ---------------------------------------------------------------------------
# T019: test_metrics_no_error_concurrent
# ---------------------------------------------------------------------------


def test_metrics_no_error_concurrent() -> None:
    """snapshot() does not error when called concurrently with metric writes."""
    mc = MetricsCollector()
    repl, _ = _make_repl_with_metrics(mc)

    errors: list[Exception] = []

    def _write_metrics() -> None:
        for i in range(100):
            try:
                mc.increment(f"metric_{i}")
                mc.observe("dur", float(i))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

    writer = threading.Thread(target=_write_metrics)
    writer.start()

    # Read concurrently — should not raise
    for _ in range(10):
        try:
            repl._cmd_metrics()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    writer.join()
    assert not errors, f"Concurrent access errors: {errors}"


# ---------------------------------------------------------------------------
# T019: test_metrics_none_collector_no_error
# ---------------------------------------------------------------------------


def test_metrics_none_collector_no_error() -> None:
    """When no MetricsCollector, _cmd_metrics shows 'not enabled' without error."""
    repl, output = _make_repl_with_metrics(None)

    # Must not raise
    repl._cmd_metrics()

    text = output.getvalue()
    assert "not enabled" in text.lower() or "metrics" in text.lower()


# ---------------------------------------------------------------------------
# T019: test_metrics_gauges_rendered
# ---------------------------------------------------------------------------


def test_metrics_gauges_rendered() -> None:
    """Gauge values appear in the /metrics output."""
    mc = MetricsCollector()
    mc.set_gauge("session.active_connections", 5.0)

    repl, output = _make_repl_with_metrics(mc)
    repl._cmd_metrics()

    text = output.getvalue()
    assert "session.active_connections" in text
    assert "5" in text


# ---------------------------------------------------------------------------
# T019: test_metrics_command_registered
# ---------------------------------------------------------------------------


def test_metrics_command_registered() -> None:
    """The 'metrics' slash command is registered in the COMMANDS dict."""
    from kosmos.cli.models import COMMANDS  # noqa: PLC0415

    assert "metrics" in COMMANDS
    assert COMMANDS["metrics"].name == "metrics"
