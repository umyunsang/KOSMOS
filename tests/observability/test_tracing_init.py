# SPDX-License-Identifier: Apache-2.0
"""T012 — Unit tests for setup_tracing() initialization paths.

Covers:
- Case 1: OTEL_SDK_DISABLED=true → NoOpTracerProvider returned.
- Case 2: Endpoint configured → real TracerProvider with BatchSpanProcessor.
- Case 3: Endpoint missing, disabled unset → WARNING emitted once; subsequent
          calls do not re-emit the warning.
"""

from __future__ import annotations

import logging

import pytest

from opentelemetry.trace import NoOpTracerProvider
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reset_warn_sentinel() -> None:
    """Reset the module-level warn-once sentinel so each test starts clean."""
    import kosmos.observability.tracing as tracing_mod

    tracing_mod._WARN_MISSING_ENDPOINT_ONCE = True


# ---------------------------------------------------------------------------
# Case 1: OTEL_SDK_DISABLED=true → NoOpTracerProvider
# ---------------------------------------------------------------------------


def test_setup_tracing_disabled_returns_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """When OTEL_SDK_DISABLED=true, setup_tracing() returns a NoOpTracerProvider."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    _reset_warn_sentinel()

    from kosmos.observability.tracing import setup_tracing, TracingSettings

    settings = TracingSettings(disabled=True)
    provider = setup_tracing(settings)

    assert isinstance(provider, NoOpTracerProvider), (
        "Expected NoOpTracerProvider when disabled=True, got %s" % type(provider)
    )

    # Spans from a NoOp provider must be non-recording.
    tracer = provider.get_tracer("test")
    span = tracer.start_span("probe")
    assert not span.is_recording(), "NoOp span must be non-recording"
    span.end()


def test_setup_tracing_disabled_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """When OTEL_SDK_DISABLED env var is 'true', _settings_from_env sets disabled=True."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    _reset_warn_sentinel()

    from kosmos.observability.tracing import _settings_from_env

    settings = _settings_from_env()
    assert settings.disabled is True
    assert settings.endpoint is None


# ---------------------------------------------------------------------------
# Case 2: Endpoint configured → real TracerProvider with BatchSpanProcessor
# ---------------------------------------------------------------------------


def test_setup_tracing_with_endpoint_returns_real_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When endpoint is set and not disabled, returns a real TracerProvider."""
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    _reset_warn_sentinel()

    from kosmos.observability.tracing import setup_tracing, TracingSettings

    # Do not pass headers to avoid SDK header-parsing ValueError in test env.
    settings = TracingSettings(
        endpoint="http://localhost:4318",
        headers=None,
        protocol="http/protobuf",
        disabled=False,
    )
    provider = setup_tracing(settings)

    assert isinstance(provider, TracerProvider), (
        "Expected SDK TracerProvider when endpoint is set, got %s" % type(provider)
    )

    # Verify that a BatchSpanProcessor is registered on the provider.
    # SDK TracerProvider stores processors in ._active_span_processor which is
    # a SynchronousMultiSpanProcessor (or similar).  We inspect the internal
    # list; the exact attribute name varies by SDK version, so we fall back to
    # checking that the tracer can produce a recording span.
    tracer = provider.get_tracer("test")
    span = tracer.start_span("probe")
    assert span.is_recording(), "Span from real TracerProvider must be recording"
    span.end()

    # Best-effort: inspect processor list for BatchSpanProcessor presence.
    span_processor = getattr(provider, "_active_span_processor", None)
    if span_processor is not None:
        processors = getattr(span_processor, "_span_processors", None)
        if processors is not None:
            processor_types = [type(p).__name__ for p in processors]
            assert any(
                "BatchSpanProcessor" in t for t in processor_types
            ), f"Expected BatchSpanProcessor in processors, found: {processor_types}"


def test_setup_tracing_real_provider_has_batch_processor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Directly construct settings and assert BatchSpanProcessor is attached."""
    _reset_warn_sentinel()

    from kosmos.observability.tracing import setup_tracing, TracingSettings

    settings = TracingSettings(
        endpoint="http://localhost:4318",
        disabled=False,
    )
    provider = setup_tracing(settings)

    assert isinstance(provider, TracerProvider)

    # Traverse the processor chain and confirm at least one BatchSpanProcessor.
    found_batch = False
    sp = getattr(provider, "_active_span_processor", None)
    if sp is not None:
        # SynchronousMultiSpanProcessor stores list in ._span_processors
        inner = getattr(sp, "_span_processors", [])
        for proc in inner:
            if isinstance(proc, BatchSpanProcessor):
                found_batch = True
                break
        if not found_batch:
            # Some SDK versions wrap in a single-processor structure
            if isinstance(sp, BatchSpanProcessor):
                found_batch = True
    assert found_batch, "Expected at least one BatchSpanProcessor registered on provider"


# ---------------------------------------------------------------------------
# Case 3: Endpoint missing, disabled unset → WARNING emitted once only
# ---------------------------------------------------------------------------


def test_setup_tracing_missing_endpoint_warns_once(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Missing endpoint without OTEL_SDK_DISABLED should emit WARNING exactly once."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    _reset_warn_sentinel()

    from kosmos.observability.tracing import setup_tracing, TracingSettings

    settings_no_endpoint = TracingSettings(endpoint=None, disabled=False)

    with caplog.at_level(logging.WARNING, logger="kosmos.observability.tracing"):
        provider1 = setup_tracing(settings_no_endpoint)

    warning_messages = [
        r.message for r in caplog.records if r.levelno == logging.WARNING
    ]
    assert len(warning_messages) >= 1, "Expected at least one WARNING on first call"
    assert any("OTEL_EXPORTER_OTLP_ENDPOINT" in m for m in warning_messages), (
        "WARNING should mention OTEL_EXPORTER_OTLP_ENDPOINT"
    )

    # Returns NoOpTracerProvider when endpoint is absent.
    assert isinstance(provider1, NoOpTracerProvider)


def test_setup_tracing_missing_endpoint_no_repeat_warn(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Subsequent calls with missing endpoint must NOT re-emit the warning."""
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    monkeypatch.setenv("OTEL_SDK_DISABLED", "false")
    _reset_warn_sentinel()

    from kosmos.observability.tracing import setup_tracing, TracingSettings
    import kosmos.observability.tracing as tracing_mod

    settings_no_endpoint = TracingSettings(endpoint=None, disabled=False)

    # First call: emits the warning and flips the sentinel to False.
    with caplog.at_level(logging.WARNING, logger="kosmos.observability.tracing"):
        setup_tracing(settings_no_endpoint)

    first_call_warnings = [
        r.message for r in caplog.records if r.levelno == logging.WARNING
    ]

    caplog.clear()

    # Second call: sentinel is now False, must not re-warn.
    with caplog.at_level(logging.WARNING, logger="kosmos.observability.tracing"):
        setup_tracing(settings_no_endpoint)

    second_call_warnings = [
        r.message
        for r in caplog.records
        if r.levelno == logging.WARNING and "OTEL_EXPORTER_OTLP_ENDPOINT" in r.message
    ]

    assert len(second_call_warnings) == 0, (
        "Subsequent call must not re-emit the endpoint warning; "
        f"got: {second_call_warnings}"
    )
