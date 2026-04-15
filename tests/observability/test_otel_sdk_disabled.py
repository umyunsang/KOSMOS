# SPDX-License-Identifier: Apache-2.0
"""Tests verifying that OTEL_SDK_DISABLED=true produces a fully no-op tracer.

Acceptance criteria (spec 021 / T017):
- setup_tracing() returns a provider whose tracer yields non-recording spans.
- No BatchSpanProcessor is registered (provider is NoOpTracerProvider).
- Zero OTLP-shaped HTTP calls are made when spans are created/ended.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace as otel_trace
from opentelemetry.trace import NoOpTracerProvider

from kosmos.observability.tracing import TracingSettings, _settings_from_env, setup_tracing

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _noop_settings() -> TracingSettings:
    """Return a settings object that explicitly disables the SDK."""
    return TracingSettings(disabled=True)


# ---------------------------------------------------------------------------
# T017-A: returned provider is NoOpTracerProvider; spans are non-recording
# ---------------------------------------------------------------------------


def test_sdk_disabled_returns_noop_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """setup_tracing() with disabled=True must return a NoOpTracerProvider."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    provider = setup_tracing(_noop_settings())

    assert isinstance(provider, NoOpTracerProvider)


def test_sdk_disabled_spans_are_non_recording(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spans produced by the no-op provider must report is_recording() == False."""
    provider = setup_tracing(_noop_settings())

    tracer = provider.get_tracer("test-tracer")
    with tracer.start_as_current_span("test-op") as span:
        assert span.is_recording() is False


def test_sdk_disabled_get_tracer_shorthand(monkeypatch: pytest.MonkeyPatch) -> None:
    """After setup_tracing(disabled) the global tracer also yields non-recording spans."""
    setup_tracing(_noop_settings())

    tracer = otel_trace.get_tracer("x")
    with tracer.start_as_current_span("y") as span:
        assert span.is_recording() is False


# ---------------------------------------------------------------------------
# T017-B: no BatchSpanProcessor registered
# ---------------------------------------------------------------------------


def test_sdk_disabled_no_batch_processor() -> None:
    """NoOpTracerProvider must not have any active span processor."""
    provider = setup_tracing(_noop_settings())

    # NoOpTracerProvider has no _active_span_processor attribute — that is the
    # cleanest indicator that no BatchSpanProcessor was registered.
    # We verify by asserting the returned type directly.
    assert isinstance(provider, NoOpTracerProvider), (
        f"Expected NoOpTracerProvider (no BatchSpanProcessor path taken); got {type(provider)!r}"
    )
    # Additionally confirm the SDK TracerProvider subclass was NOT used.
    from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider

    assert not isinstance(provider, SDKTracerProvider)


# ---------------------------------------------------------------------------
# T017-C: zero OTLP HTTP calls during span operations
# ---------------------------------------------------------------------------


def test_sdk_disabled_no_otlp_http_calls() -> None:
    """Span creation/end with no-op provider must not trigger any HTTP activity."""
    http_post_calls: list[tuple[object, ...]] = []

    mock_post = MagicMock(side_effect=lambda *a, **kw: http_post_calls.append((a, kw)))

    with (
        patch("httpx.post", mock_post),
        patch("httpx.Client.post", mock_post),
    ):
        provider = setup_tracing(_noop_settings())
        tracer = provider.get_tracer("kosmos")

        with tracer.start_as_current_span("chat") as span:
            # Simulate attribute setting — would trigger export in real provider
            if span.is_recording():
                span.set_attribute("gen_ai.operation.name", "chat")

    assert len(http_post_calls) == 0, (
        f"Expected zero HTTP POST calls; got {len(http_post_calls)}: {http_post_calls}"
    )


# ---------------------------------------------------------------------------
# T017-D: _settings_from_env reads OTEL_SDK_DISABLED correctly
# ---------------------------------------------------------------------------


def test_settings_from_env_disabled_true(monkeypatch: pytest.MonkeyPatch) -> None:
    """_settings_from_env() must set disabled=True when OTEL_SDK_DISABLED=true."""
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    settings = _settings_from_env()

    assert settings.disabled is True


def test_settings_from_env_disabled_false_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """_settings_from_env() must set disabled=False when OTEL_SDK_DISABLED is absent."""
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    settings = _settings_from_env()

    assert settings.disabled is False
