# SPDX-License-Identifier: Apache-2.0
"""In-process metrics collector for KOSMOS observability.

Collects counters, histograms, and gauges purely in memory.  No external
agents, no network I/O.  All operations are deliberately simple and cheap
so that metrics instrumentation never becomes a hot path.

Failure contract: every public method silently logs a warning on unexpected
errors and continues — metrics failures must never crash the main flow.

Label encoding: labels are appended to the metric name as a sorted
comma-separated list of ``key=value`` pairs, e.g.
``tool.call_count{tool_id=koroad_accident_search}``.
"""

from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)


def _encode_name(name: str, labels: dict[str, str] | None) -> str:
    """Return a label-qualified metric name.

    Args:
        name: Base metric name.
        labels: Optional key/value label pairs to qualify the metric.

    Returns:
        ``"name{k1=v1,k2=v2}"`` if labels are present, otherwise just
        ``"name"``.
    """
    if not labels:
        return name
    parts = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{name}{{{parts}}}"


class MetricsCollector:
    """In-process metrics collector for observability.

    Three metric types are supported:

    * **Counters** — monotonically increasing integers (e.g. call counts,
      error counts).  Use ``increment()``.
    * **Histograms** — ordered list of observed float values (e.g. latency in
      milliseconds).  Use ``observe()``.  Stats (min, max, avg, p50, p95, p99)
      are computed lazily via ``get_histogram_stats()``.
    * **Gauges** — current instantaneous value (e.g. active connections,
      cache size).  Use ``set_gauge()``.

    All methods are fail-safe: any unexpected error is caught, logged as a
    warning, and ignored.
    """

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def increment(
        self,
        name: str,
        value: int = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Increment a counter by *value*.

        Args:
            name: Metric name.
            value: Amount to add; must be positive.
            labels: Optional label qualifiers.
        """
        try:
            key = _encode_name(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value
        except Exception:  # noqa: BLE001
            logger.warning("MetricsCollector.increment failed: name=%s", name, exc_info=True)

    def observe(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a single observation in a histogram.

        Args:
            name: Metric name.
            value: Observed value (e.g. duration in milliseconds).
            labels: Optional label qualifiers.
        """
        try:
            key = _encode_name(name, labels)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
        except Exception:  # noqa: BLE001
            logger.warning("MetricsCollector.observe failed: name=%s", name, exc_info=True)

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge to *value*.

        Args:
            name: Metric name (no labels — gauges represent a single current
                value and do not benefit from label sharding).
            value: The current gauge value.
        """
        try:
            self._gauges[name] = value
        except Exception:  # noqa: BLE001
            logger.warning("MetricsCollector.set_gauge failed: name=%s", name, exc_info=True)

    # ------------------------------------------------------------------
    # Read methods
    # ------------------------------------------------------------------

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> int:
        """Return the current value of a counter (0 if never incremented).

        Args:
            name: Metric name.
            labels: Optional label qualifiers.

        Returns:
            Current counter value.
        """
        try:
            key = _encode_name(name, labels)
            return self._counters.get(key, 0)
        except Exception:  # noqa: BLE001
            logger.warning("MetricsCollector.get_counter failed: name=%s", name, exc_info=True)
            return 0

    def get_histogram_stats(
        self,
        name: str,
        labels: dict[str, str] | None = None,
    ) -> dict[str, float]:
        """Return summary statistics for a histogram.

        Computes min, max, avg (mean), p50, p95, and p99 from all recorded
        observations.  Returns a dict of zeros for an empty histogram.

        Args:
            name: Metric name.
            labels: Optional label qualifiers.

        Returns:
            Dict with keys: ``min``, ``max``, ``avg``, ``p50``, ``p95``,
            ``p99``, ``count``.
        """
        _empty: dict[str, float] = {
            "min": 0.0,
            "max": 0.0,
            "avg": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "count": 0.0,
        }
        try:
            key = _encode_name(name, labels)
            values = self._histograms.get(key)
            if not values:
                return _empty

            sorted_vals = sorted(values)
            count = len(sorted_vals)

            def _percentile(p: float) -> float:
                idx = p / 100.0 * (count - 1)
                lower = int(math.floor(idx))
                upper = int(math.ceil(idx))
                if lower == upper:
                    return sorted_vals[lower]
                frac = idx - lower
                return sorted_vals[lower] * (1.0 - frac) + sorted_vals[upper] * frac

            return {
                "min": sorted_vals[0],
                "max": sorted_vals[-1],
                "avg": sum(sorted_vals) / count,
                "p50": _percentile(50),
                "p95": _percentile(95),
                "p99": _percentile(99),
                "count": float(count),
            }
        except Exception:  # noqa: BLE001
            logger.warning(
                "MetricsCollector.get_histogram_stats failed: name=%s", name, exc_info=True
            )
            return _empty

    def snapshot(self) -> dict[str, object]:
        """Return a full dump of all metrics as a plain dict.

        The returned structure is::

            {
                "counters": {"metric_name": int, ...},
                "gauges": {"metric_name": float, ...},
                "histograms": {
                    "metric_name": {
                        "min": float, "max": float, "avg": float,
                        "p50": float, "p95": float, "p99": float,
                        "count": float,
                    },
                    ...
                },
            }

        Returns:
            A shallow copy of the current metrics state.
        """
        try:
            histogram_stats: dict[str, dict[str, float]] = {}
            for key in self._histograms:
                # _encode_name has already been applied when the key was stored;
                # pass an empty base name and pre-encoded key directly.
                values = self._histograms[key]
                if not values:
                    continue
                sorted_vals = sorted(values)
                count = len(sorted_vals)

                def _percentile(p: float, sv: list[float] = sorted_vals, n: int = count) -> float:
                    idx = p / 100.0 * (n - 1)
                    lower = int(math.floor(idx))
                    upper = int(math.ceil(idx))
                    if lower == upper:
                        return sv[lower]
                    frac = idx - lower
                    return sv[lower] * (1.0 - frac) + sv[upper] * frac

                histogram_stats[key] = {
                    "min": sorted_vals[0],
                    "max": sorted_vals[-1],
                    "avg": sum(sorted_vals) / count,
                    "p50": _percentile(50),
                    "p95": _percentile(95),
                    "p99": _percentile(99),
                    "count": float(count),
                }

            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": histogram_stats,
            }
        except Exception:  # noqa: BLE001
            logger.warning("MetricsCollector.snapshot failed", exc_info=True)
            return {"counters": {}, "gauges": {}, "histograms": {}}

    def reset(self) -> None:
        """Clear all metrics state.

        Intended for use in tests and health-check resets.  Does not affect
        the identity of the collector instance.
        """
        try:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
        except Exception:  # noqa: BLE001
            logger.warning("MetricsCollector.reset failed", exc_info=True)
