# SPDX-License-Identifier: Apache-2.0
"""T011 — PII redaction smoke test for the local OTel Collector.

Tests that the ``attributes/pii_redact`` processor in
``infra/otel-collector/config.yaml`` correctly:

  (a) deletes ``patient.name`` and ``patient.phone`` before Langfuse ingestion
  (b) hashes ``kosmos.location.query`` to its SHA-256 hex digest

This test is marked ``@pytest.mark.live`` and is **skipped by default** in CI
(AGENTS.md hard rule: never call live external APIs from CI tests).

Prerequisites for local execution
----------------------------------
- Full stack running: ``docker compose -f docker-compose.dev.yml up -d``
- All services healthy (especially ``langfuse-web`` and ``otelcol``)
- ``KOSMOS_LANGFUSE_OTLP_AUTH_HEADER`` set in the environment (or ``.env``)
  containing the Base64-encoded ``pk-lf-xxx:sk-lf-xxx`` credential
- ``KOSMOS_OTEL_COLLECTOR_PORT`` (default: ``4318``) matches the running collector

Run locally::

    uv run pytest -m live tests/live/test_collector_pii_redaction.py -v

Spec reference: SC-003, FR-006, Phase 4 US2.
"""

from __future__ import annotations

import hashlib
import os
import time

import pytest

# ---------------------------------------------------------------------------
# Skip conditions (evaluated at collection time for clarity)
# ---------------------------------------------------------------------------

_AUTH_HEADER = os.environ.get("KOSMOS_LANGFUSE_OTLP_AUTH_HEADER", "")
_COLLECTOR_PORT_RAW = os.environ.get("KOSMOS_OTEL_COLLECTOR_PORT", "4318")
try:
    _COLLECTOR_PORT = int(_COLLECTOR_PORT_RAW)
except ValueError:
    _COLLECTOR_PORT = 4318  # fall back to default; invalid value surfaced at test time

_LANGFUSE_BASE_URL = "http://localhost:3000"
_LANGFUSE_HEALTH_URL = f"{_LANGFUSE_BASE_URL}/api/public/health"
_LANGFUSE_TRACES_URL = f"{_LANGFUSE_BASE_URL}/api/public/traces"

# The SHA-256 hex hash of "서울역" (UTF-8) that the collector should produce.
_EXPECTED_HASH = hashlib.sha256("서울역".encode()).hexdigest()


def _langfuse_reachable() -> bool:
    """Return True if the local Langfuse health endpoint responds with HTTP 200."""
    try:
        import httpx  # noqa: PLC0415

        resp = httpx.get(_LANGFUSE_HEALTH_URL, timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=False)
def _require_live_stack() -> None:
    """Skip the entire module when the live stack is unavailable."""
    if not _AUTH_HEADER:
        pytest.skip(
            "KOSMOS_LANGFUSE_OTLP_AUTH_HEADER is unset — "
            "run the Langfuse first-run bootstrap (docs/observability.md §5) "
            "and set the env var before executing live PII redaction tests."
        )
    if not _langfuse_reachable():
        pytest.skip(
            f"Langfuse health endpoint unreachable at {_LANGFUSE_HEALTH_URL}. "
            "Start the stack with: docker compose -f docker-compose.dev.yml up -d"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _emit_test_span(trace_id_hex: str) -> None:
    """Emit one span to the local collector with PII and location attributes.

    Uses the opentelemetry-sdk (spec 021 existing dep) to send via OTLP HTTP.
    The span carries:
      - patient.name = "TEST_OPERATOR"   (must be deleted by collector)
      - patient.phone = "010-0000-0000"  (must be deleted by collector)
      - kosmos.location.query = "서울역"  (must be hashed by collector)
    """
    from opentelemetry import trace  # noqa: PLC0415
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource  # noqa: PLC0415
    from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415
    from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags  # noqa: PLC0415

    endpoint = f"http://localhost:{_COLLECTOR_PORT}"

    exporter = OTLPSpanExporter(
        endpoint=f"{endpoint}/v1/traces",
        timeout=10,
    )
    provider = TracerProvider(
        resource=Resource.create({"service.name": "kosmos-pii-redaction-test"})
    )
    provider.add_span_processor(BatchSpanProcessor(exporter, max_export_batch_size=1))

    # Convert hex trace_id to int for the SDK
    trace_id_int = int(trace_id_hex, 16)
    ctx = SpanContext(
        trace_id=trace_id_int,
        span_id=0xABCDEF1234567890,
        is_remote=True,
        trace_flags=TraceFlags(0x01),
    )
    link_ctx = trace.use_span(NonRecordingSpan(ctx))

    tracer = provider.get_tracer("kosmos.test.pii_redaction")
    with link_ctx, tracer.start_as_current_span(
        "test.pii_redaction_smoke",
        context=trace.set_span_in_context(NonRecordingSpan(ctx)),
    ) as span:
        span.set_attribute("patient.name", "TEST_OPERATOR")
        span.set_attribute("patient.phone", "010-0000-0000")
        span.set_attribute("kosmos.location.query", "서울역")
        span.set_attribute("kosmos.test.marker", "spec028-pii-smoke")

    # Force flush to send before the provider is garbage-collected
    provider.force_flush(timeout_millis=10_000)
    provider.shutdown()


def _fetch_trace_from_langfuse(trace_id_hex: str) -> dict | None:
    """Query the Langfuse public API for the trace by ID.

    Returns the trace dict or None if not found.
    """
    import httpx  # noqa: PLC0415

    url = f"{_LANGFUSE_TRACES_URL}/{trace_id_hex}"
    headers: dict[str, str] = {}
    if _AUTH_HEADER:
        headers["Authorization"] = _AUTH_HEADER

    resp = httpx.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        return resp.json()
    return None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_patient_name_deleted_by_collector(_require_live_stack: None) -> None:
    """(a) patient.name and patient.phone are absent from the stored span (SC-003 part 1).

    Emits a span with patient.name and patient.phone, waits for the batch
    processor timeout (5 s) plus a safety buffer, then queries Langfuse to
    verify the attributes are absent.
    """
    import secrets

    trace_id_hex = secrets.token_hex(16)

    _emit_test_span(trace_id_hex)

    # Wait for batch processor timeout (5 s) + Langfuse ingestion buffer
    time.sleep(8)

    trace = _fetch_trace_from_langfuse(trace_id_hex)
    assert trace is not None, (
        f"Trace {trace_id_hex!r} not found in Langfuse after 8 s. "
        "Check collector logs: docker compose -f docker-compose.dev.yml logs otelcol --tail=50"
    )

    # Collect all attribute keys from all observations in the trace
    all_attribute_keys: set[str] = set()
    for observation in trace.get("observations", []):
        attrs = observation.get("attributes", {}) or {}
        all_attribute_keys.update(attrs.keys())
    # Also check top-level input/output/metadata
    if trace.get("input"):
        all_attribute_keys.update({"input"})

    assert "patient.name" not in all_attribute_keys, (
        f"patient.name MUST NOT appear in Langfuse trace (PIPA §26 redaction). "
        f"Found keys: {sorted(all_attribute_keys)}"
    )
    assert "patient.phone" not in all_attribute_keys, (
        f"patient.phone MUST NOT appear in Langfuse trace (PIPA §26 redaction). "
        f"Found keys: {sorted(all_attribute_keys)}"
    )


@pytest.mark.live
def test_location_query_hashed_by_collector(_require_live_stack: None) -> None:
    """(b) kosmos.location.query is replaced with its SHA-256 hash (SC-003 part 2).

    The collector's hash action replaces the raw '서울역' string with the
    64-char SHA-256 hex digest before forwarding to Langfuse.
    """
    import secrets

    trace_id_hex = secrets.token_hex(16)

    _emit_test_span(trace_id_hex)

    # Wait for batch processor + Langfuse ingestion
    time.sleep(8)

    trace = _fetch_trace_from_langfuse(trace_id_hex)
    assert trace is not None, (
        f"Trace {trace_id_hex!r} not found in Langfuse after 8 s. "
        "Check: docker compose -f docker-compose.dev.yml logs otelcol --tail=50"
    )

    # Find kosmos.location.query in any observation
    location_query_values: list[str] = []
    for observation in trace.get("observations", []):
        attrs = observation.get("attributes", {}) or {}
        if "kosmos.location.query" in attrs:
            location_query_values.append(str(attrs["kosmos.location.query"]))

    assert location_query_values, (
        "kosmos.location.query attribute not found in Langfuse trace. "
        "It should be present (as a hash), but not the raw value."
    )

    for value in location_query_values:
        assert value == _EXPECTED_HASH, (
            f"kosmos.location.query must equal SHA-256('서울역') = {_EXPECTED_HASH!r}.\n"
            f"  Got: {value!r}\n"
            "  If this is the raw string, the collector's hash action did not fire."
        )
        assert value != "서울역", (
            "kosmos.location.query must NOT be the raw '서울역' string after collector processing."
        )
