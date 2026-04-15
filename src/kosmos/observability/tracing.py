# SPDX-License-Identifier: Apache-2.0
"""OpenTelemetry TracerProvider bootstrap for KOSMOS.

Provides ``TracingSettings`` (a Pydantic v2 model) and ``setup_tracing``, a
factory function that configures the global ``TracerProvider`` once at
application startup.

Design decisions:
- Only ``http/protobuf`` OTLP transport is supported (gRPC is prohibited per
  the wire contract; see ``contracts/otel-span-contract.md § Transport``).
- When ``OTEL_SDK_DISABLED=true`` or the endpoint is missing, a
  ``NoOpTracerProvider`` is returned and **no** ``BatchSpanProcessor`` or
  ``OTLPSpanExporter`` is ever constructed — guaranteeing zero network
  activity in CI (FR-009, SC-003, research.md § D4).
- ``service.version`` is read from ``pyproject.toml`` at boot time so it does
  not need to be hard-coded in the env file.

Usage::

    from kosmos.observability.tracing import setup_tracing

    provider = setup_tracing()   # reads env vars; returns NoOp if disabled
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Literal

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import NoOpTracerProvider
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Version helper
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _read_project_version() -> str:
    """Read ``[project].version`` from ``pyproject.toml``.

    Uses ``importlib.metadata`` as the primary path (works once the package is
    installed/editable).  Falls back to parsing ``pyproject.toml`` directly,
    and finally falls back to ``"0.0.0"`` if neither succeeds.
    """
    try:
        from importlib.metadata import version, PackageNotFoundError

        return version("kosmos")
    except Exception:  # noqa: BLE001
        pass

    try:
        import tomllib
        import pathlib

        # Walk up from this file to the repo root and find pyproject.toml.
        root = pathlib.Path(__file__).parent
        for _ in range(6):  # search up to 6 levels
            candidate = root / "pyproject.toml"
            if candidate.exists():
                with candidate.open("rb") as fh:
                    data = tomllib.load(fh)
                return str(data["project"]["version"])
            root = root.parent
    except Exception:  # noqa: BLE001
        pass

    return "0.0.0"


# ---------------------------------------------------------------------------
# TracingSettings
# ---------------------------------------------------------------------------


class TracingSettings(BaseModel):
    """Immutable tracing configuration derived from environment variables.

    All fields carry explicit types to satisfy Pydantic v2 strict mode.
    The model is ``frozen=True`` — instances are constructed once at boot and
    never mutated.

    Attributes:
        endpoint: OTLP HTTP endpoint URL.  ``None`` disables tracing (no-op).
        protocol: OTLP wire protocol.  Only ``"http/protobuf"`` is allowed.
        headers: Raw ``OTEL_EXPORTER_OTLP_HEADERS`` string (e.g.
            ``"Authorization=Basic%20<token>"``).
        service_name: OTel ``service.name`` resource attribute.
        service_version: OTel ``service.version`` resource attribute.
        environment: OTel ``deployment.environment.name`` resource attribute.
        semconv_opt_in: Value of ``OTEL_SEMCONV_STABILITY_OPT_IN``.
        disabled: When ``True``, ``setup_tracing`` returns ``NoOpTracerProvider``
            without constructing any exporter or processor.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    endpoint: str | None = Field(
        default=None,
        description=(
            "OTLP HTTP endpoint URL.  None means no exporter is configured"
            " and tracing falls back to no-op."
        ),
    )
    protocol: Literal["http/protobuf"] = Field(
        default="http/protobuf",
        description="OTLP wire protocol.  Only http/protobuf is supported (gRPC prohibited).",
    )
    headers: str | None = Field(
        default=None,
        description=(
            "Raw OTEL_EXPORTER_OTLP_HEADERS string, e.g. "
            "'Authorization=Basic%20<token>'.  Never logged."
        ),
    )
    service_name: str = Field(
        default="kosmos",
        description="OTel resource service.name attribute.",
    )
    service_version: str = Field(
        default="0.0.0",
        description=(
            "OTel resource service.version attribute.  Read from pyproject.toml at boot."
        ),
    )
    environment: str = Field(
        default="dev",
        description="OTel resource deployment.environment.name attribute.",
    )
    semconv_opt_in: str = Field(
        default="gen_ai_latest_experimental",
        description=(
            "Value of OTEL_SEMCONV_STABILITY_OPT_IN.  Controls which experimental"
            " semconv attributes are exposed by the SDK."
        ),
    )
    disabled: bool = Field(
        default=False,
        description=(
            "When True, setup_tracing returns NoOpTracerProvider with zero"
            " background threads or network activity."
        ),
    )


# ---------------------------------------------------------------------------
# setup_tracing
# ---------------------------------------------------------------------------

_WARN_MISSING_ENDPOINT_ONCE = True  # module-level sentinel for warn-once


def setup_tracing(settings: TracingSettings | None = None) -> TracerProvider | NoOpTracerProvider:
    """Configure and return the global ``TracerProvider``.

    When *settings* is ``None``, configuration is read from environment
    variables.  The returned provider is also registered as the global
    provider via ``trace.set_tracer_provider``.

    No-op paths (returns ``NoOpTracerProvider`` without constructing any
    exporter or processor):
    - ``OTEL_SDK_DISABLED=true`` (or ``settings.disabled=True``)
    - Endpoint not configured (``OTEL_EXPORTER_OTLP_ENDPOINT`` unset or
      ``settings.endpoint is None``)

    Args:
        settings: Pre-constructed settings.  When ``None``, env vars are read.

    Returns:
        A live ``TracerProvider`` if tracing is enabled and the endpoint is
        set; otherwise a ``NoOpTracerProvider``.
    """
    global _WARN_MISSING_ENDPOINT_ONCE  # noqa: PLW0603

    if settings is None:
        settings = _settings_from_env()

    if settings.disabled:
        provider: TracerProvider | NoOpTracerProvider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    if settings.endpoint is None:
        if _WARN_MISSING_ENDPOINT_ONCE:
            logger.warning(
                "KOSMOS tracing: OTEL_EXPORTER_OTLP_ENDPOINT is not set and"
                " OTEL_SDK_DISABLED is not 'true'.  Tracing will be disabled"
                " (no-op).  Set the endpoint or set OTEL_SDK_DISABLED=true to"
                " suppress this warning."
            )
            _WARN_MISSING_ENDPOINT_ONCE = False
        provider = NoOpTracerProvider()
        trace.set_tracer_provider(provider)
        return provider

    # Build real TracerProvider.
    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": settings.service_version,
            "deployment.environment.name": settings.environment,
        }
    )

    exporter_kwargs: dict[str, str] = {"endpoint": settings.endpoint}
    if settings.headers:
        exporter_kwargs["headers"] = settings.headers  # type: ignore[assignment]

    exporter = OTLPSpanExporter(**exporter_kwargs)  # type: ignore[arg-type]
    processor = BatchSpanProcessor(exporter)

    real_provider = TracerProvider(resource=resource)
    real_provider.add_span_processor(processor)

    trace.set_tracer_provider(real_provider)
    return real_provider


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _settings_from_env() -> TracingSettings:
    """Build ``TracingSettings`` by reading standard OTel environment variables."""
    disabled_raw = os.environ.get("OTEL_SDK_DISABLED", "false").strip().lower()
    disabled = disabled_raw == "true"

    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or None
    headers = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS") or None
    environment = os.environ.get("OTEL_DEPLOYMENT_ENVIRONMENT", "dev")
    semconv_opt_in = os.environ.get(
        "OTEL_SEMCONV_STABILITY_OPT_IN", "gen_ai_latest_experimental"
    )

    return TracingSettings(
        endpoint=endpoint,
        headers=headers,
        service_version=_read_project_version(),
        environment=environment,
        semconv_opt_in=semconv_opt_in,
        disabled=disabled,
    )
