# SPDX-License-Identifier: Apache-2.0
"""Regression guard: MetricsCollector public API must be unchanged after setup_tracing().

This test captures a structural snapshot of MetricsCollector (method names +
signatures + instance behavior) before and after calling setup_tracing() with
OTEL_SDK_DISABLED=true. Any accidental monkeypatching of MetricsCollector by
the OTel layer will cause this test to fail immediately.

Guard covers:
- T029: MetricsCollector public API invariant
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from kosmos.observability.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _public_methods(cls: type) -> dict[str, inspect.Signature]:
    """Return a mapping of public method name -> Signature for *cls*."""
    return {
        name: inspect.signature(method)
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def _class_level_attrs(cls: type) -> dict[str, Any]:
    """Return class-level attributes that are NOT callable and NOT dunder."""
    return {
        name: value
        for name, value in vars(cls).items()
        if not name.startswith("_") and not callable(value)
    }


def _snapshot_api(cls: type) -> dict[str, Any]:
    """Capture a full structural snapshot of *cls* public API."""
    methods = _public_methods(cls)
    return {
        "method_names": sorted(methods.keys()),
        "method_signatures": {name: str(sig) for name, sig in methods.items()},
        "class_attrs": _class_level_attrs(cls),
    }


def _snapshot_instance_behavior(mc: MetricsCollector) -> dict[str, Any]:
    """Invoke each public write method with trivial args and return a snapshot.

    This verifies that the *instance* works identically regardless of whether
    OTel tracing was set up.
    """
    mc.increment("test_counter", value=3, labels={"tool_id": "guard"})
    mc.observe("test_histogram", 42.0, labels={"tool_id": "guard"})
    mc.set_gauge("test_gauge", 7.5)

    return {
        "counter": mc.get_counter("test_counter", labels={"tool_id": "guard"}),
        "histogram_avg": mc.get_histogram_stats(
            "test_histogram", labels={"tool_id": "guard"}
        )["avg"],
        "gauge": mc.snapshot()["gauges"]["test_gauge"],
        "snapshot_keys": sorted(mc.snapshot().keys()),
    }


# ---------------------------------------------------------------------------
# T029: Structural invariant guard
# ---------------------------------------------------------------------------


class TestMetricsCollectorUnchanged:
    """Assert that setup_tracing() does not alter MetricsCollector's public API."""

    def test_public_method_names_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Public method names on MetricsCollector must be identical before and after OTel init."""
        # Snapshot BEFORE setup_tracing
        snapshot_before = _snapshot_api(MetricsCollector)

        # Call setup_tracing with SDK disabled (no network, no background thread)
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        # Snapshot AFTER setup_tracing
        snapshot_after = _snapshot_api(MetricsCollector)

        assert snapshot_before["method_names"] == snapshot_after["method_names"], (
            "MetricsCollector public method list changed after setup_tracing()! "
            f"Before: {snapshot_before['method_names']}  "
            f"After: {snapshot_after['method_names']}"
        )

    def test_public_method_signatures_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Method signatures must be byte-identical before and after OTel init."""
        snapshot_before = _snapshot_api(MetricsCollector)

        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        snapshot_after = _snapshot_api(MetricsCollector)

        assert snapshot_before["method_signatures"] == snapshot_after["method_signatures"], (
            "MetricsCollector method signatures changed after setup_tracing()! "
            f"Diff: {set(snapshot_before['method_signatures'].items()) ^ set(snapshot_after['method_signatures'].items())}"  # noqa: E501
        )

    def test_class_level_attrs_unchanged(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Class-level (non-callable) attributes must be unchanged after OTel init."""
        snapshot_before = _snapshot_api(MetricsCollector)

        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        snapshot_after = _snapshot_api(MetricsCollector)

        assert snapshot_before["class_attrs"] == snapshot_after["class_attrs"], (
            "MetricsCollector class-level attributes changed after setup_tracing()! "
            f"Before: {snapshot_before['class_attrs']}  "
            f"After: {snapshot_after['class_attrs']}"
        )


# ---------------------------------------------------------------------------
# T029: Instance behavior invariant guard
# ---------------------------------------------------------------------------


class TestMetricsCollectorBehaviorUnchanged:
    """Verify that MetricsCollector instances behave identically before/after OTel init."""

    def test_instance_behavior_before_setup_tracing(self) -> None:
        """MetricsCollector works correctly when OTel has NOT been initialized."""
        mc = MetricsCollector()
        behavior = _snapshot_instance_behavior(mc)

        assert behavior["counter"] == 3
        assert behavior["histogram_avg"] == 42.0
        assert behavior["gauge"] == 7.5
        assert behavior["snapshot_keys"] == ["counters", "gauges", "histograms"]

    def test_instance_behavior_after_setup_tracing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """MetricsCollector works identically after OTel has been initialized (no-op mode)."""
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        mc = MetricsCollector()
        behavior = _snapshot_instance_behavior(mc)

        assert behavior["counter"] == 3
        assert behavior["histogram_avg"] == 42.0
        assert behavior["gauge"] == 7.5
        assert behavior["snapshot_keys"] == ["counters", "gauges", "histograms"]

    def test_instance_behavior_is_byte_identical(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Behavior snapshot dict must be equal before and after setup_tracing."""
        mc_before = MetricsCollector()
        behavior_before = _snapshot_instance_behavior(mc_before)

        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        mc_after = MetricsCollector()
        behavior_after = _snapshot_instance_behavior(mc_after)

        assert behavior_before == behavior_after, (
            "MetricsCollector instance behavior changed after setup_tracing()! "
            f"Before: {behavior_before}  After: {behavior_after}"
        )

    def test_reset_works_identically_after_setup_tracing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """reset() must clear all state identically before and after OTel init."""
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        mc = MetricsCollector()
        mc.increment("x", value=10)
        mc.observe("y", 99.0)
        mc.set_gauge("z", 1.0)
        mc.reset()

        assert mc.get_counter("x") == 0
        assert mc.get_histogram_stats("y")["count"] == 0.0
        assert mc.snapshot() == {"counters": {}, "gauges": {}, "histograms": {}}
