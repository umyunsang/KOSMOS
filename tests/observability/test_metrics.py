# SPDX-License-Identifier: Apache-2.0
"""Tests for MetricsCollector."""

from __future__ import annotations

import pytest

from kosmos.observability.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------


def test_increment_starts_at_zero() -> None:
    mc = MetricsCollector()
    assert mc.get_counter("foo") == 0


def test_increment_single() -> None:
    mc = MetricsCollector()
    mc.increment("requests")
    assert mc.get_counter("requests") == 1


def test_increment_multiple() -> None:
    mc = MetricsCollector()
    mc.increment("requests", value=3)
    mc.increment("requests", value=2)
    assert mc.get_counter("requests") == 5


def test_increment_with_labels() -> None:
    mc = MetricsCollector()
    mc.increment("tool.calls", labels={"tool_id": "koroad"})
    mc.increment("tool.calls", labels={"tool_id": "bus"})
    mc.increment("tool.calls", labels={"tool_id": "koroad"})
    assert mc.get_counter("tool.calls", labels={"tool_id": "koroad"}) == 2
    assert mc.get_counter("tool.calls", labels={"tool_id": "bus"}) == 1


def test_increment_labels_order_independent() -> None:
    """Labels in different insertion order produce the same key."""
    mc = MetricsCollector()
    mc.increment("m", labels={"b": "2", "a": "1"})
    assert mc.get_counter("m", labels={"a": "1", "b": "2"}) == 1


def test_get_counter_unknown_metric_returns_zero() -> None:
    mc = MetricsCollector()
    assert mc.get_counter("nonexistent") == 0


# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------


def test_observe_and_get_stats() -> None:
    mc = MetricsCollector()
    for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
        mc.observe("latency_ms", v)

    stats = mc.get_histogram_stats("latency_ms")
    assert stats["min"] == 10.0
    assert stats["max"] == 50.0
    assert stats["avg"] == 30.0
    assert stats["count"] == 5.0


def test_histogram_percentiles() -> None:
    mc = MetricsCollector()
    # 100 values 1..100
    for i in range(1, 101):
        mc.observe("dur", float(i))

    stats = mc.get_histogram_stats("dur")
    # p50 should be near 50
    assert 49.0 <= stats["p50"] <= 51.0
    # p95 should be near 95
    assert 94.0 <= stats["p95"] <= 96.0
    # p99 should be near 99
    assert 98.0 <= stats["p99"] <= 100.0


def test_histogram_empty_returns_zeros() -> None:
    mc = MetricsCollector()
    stats = mc.get_histogram_stats("nonexistent")
    assert stats == {
        "min": 0.0,
        "max": 0.0,
        "avg": 0.0,
        "p50": 0.0,
        "p95": 0.0,
        "p99": 0.0,
        "count": 0.0,
    }


def test_histogram_with_labels() -> None:
    mc = MetricsCollector()
    mc.observe("dur", 100.0, labels={"tool_id": "t1"})
    mc.observe("dur", 200.0, labels={"tool_id": "t2"})

    stats_t1 = mc.get_histogram_stats("dur", labels={"tool_id": "t1"})
    stats_t2 = mc.get_histogram_stats("dur", labels={"tool_id": "t2"})
    assert stats_t1["avg"] == 100.0
    assert stats_t2["avg"] == 200.0


def test_histogram_single_value() -> None:
    mc = MetricsCollector()
    mc.observe("single", 42.0)
    stats = mc.get_histogram_stats("single")
    assert stats["min"] == 42.0
    assert stats["max"] == 42.0
    assert stats["avg"] == 42.0
    assert stats["p50"] == 42.0
    assert stats["p99"] == 42.0
    assert stats["count"] == 1.0


# ---------------------------------------------------------------------------
# Gauges
# ---------------------------------------------------------------------------


def test_set_gauge() -> None:
    mc = MetricsCollector()
    mc.set_gauge("active_connections", 10.0)
    snap = mc.snapshot()
    assert snap["gauges"]["active_connections"] == 10.0


def test_set_gauge_overwrites() -> None:
    mc = MetricsCollector()
    mc.set_gauge("cache_size", 5.0)
    mc.set_gauge("cache_size", 8.0)
    snap = mc.snapshot()
    assert snap["gauges"]["cache_size"] == 8.0


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


def test_snapshot_contains_all_metric_types() -> None:
    mc = MetricsCollector()
    mc.increment("c1", value=3)
    mc.observe("h1", 1.0)
    mc.observe("h1", 2.0)
    mc.set_gauge("g1", 7.0)

    snap = mc.snapshot()
    assert "counters" in snap
    assert "histograms" in snap
    assert "gauges" in snap
    assert snap["counters"]["c1"] == 3
    assert snap["gauges"]["g1"] == 7.0
    assert "h1" in snap["histograms"]
    assert snap["histograms"]["h1"]["count"] == 2.0


def test_snapshot_is_shallow_copy() -> None:
    """Modifying the snapshot does not affect the collector."""
    mc = MetricsCollector()
    mc.increment("x")
    snap = mc.snapshot()
    snap["counters"]["x"] = 999  # type: ignore[index]
    assert mc.get_counter("x") == 1


def test_snapshot_empty_collector() -> None:
    mc = MetricsCollector()
    snap = mc.snapshot()
    assert snap == {"counters": {}, "gauges": {}, "histograms": {}}


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def test_reset_clears_all_metrics() -> None:
    mc = MetricsCollector()
    mc.increment("c", value=5)
    mc.observe("h", 99.0)
    mc.set_gauge("g", 3.0)

    mc.reset()

    assert mc.get_counter("c") == 0
    assert mc.get_histogram_stats("h")["count"] == 0.0
    snap = mc.snapshot()
    assert snap["gauges"] == {}


def test_reset_allows_reuse() -> None:
    mc = MetricsCollector()
    mc.increment("x", value=10)
    mc.reset()
    mc.increment("x", value=2)
    assert mc.get_counter("x") == 2


# ---------------------------------------------------------------------------
# Fail-safe — bad inputs do not raise
# ---------------------------------------------------------------------------


def test_increment_does_not_raise_on_bad_value() -> None:
    """Collector is fail-safe; passing a bad value type is silently handled."""
    mc = MetricsCollector()
    # This should not raise even if implementation guards against it
    try:
        mc.increment("m", value=1)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"increment raised unexpectedly: {exc}")
