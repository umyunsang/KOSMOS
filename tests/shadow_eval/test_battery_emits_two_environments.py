# SPDX-License-Identifier: Apache-2.0
"""T018 — Shadow-eval battery emits spans for both deployment environments.

Covers FR-D03: the battery MUST emit OTEL spans tagged with
``deployment.environment=main`` (merge-base run) and
``deployment.environment=shadow`` (PR-head run), and both runs MUST exercise
the same battery input ids so downstream diff logic is deterministic.

Strategy:
- Import ``tests.shadow_eval.battery.run`` directly so the test shares the
  in-memory OTEL span exporter with the battery module — no subprocess fork.
- Wire a fresh ``TracerProvider`` + ``InMemorySpanExporter`` +
  ``SimpleSpanProcessor`` before each call; inject it into the battery module
  via ``monkeypatch.setattr`` on the module-level ``_tracer`` attribute that
  the battery module is expected to expose (mirroring the pattern used by
  ``tests/observability/test_llm_chat_span.py``).
- Supply an ``httpx.MockTransport`` to prevent any live network call (FR-D05).

Expected RED failure:
    ModuleNotFoundError: No module named 'tests.shadow_eval.battery'
    (battery.py does not exist until T040)
"""

from __future__ import annotations

import httpx
import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# ---------------------------------------------------------------------------
# Import the battery module under test.
#
# This import is intentionally at module scope so that pytest's collection
# phase raises ``ModuleNotFoundError`` immediately, producing the required RED
# failure before T040 is implemented.
# ---------------------------------------------------------------------------
from tests.shadow_eval.battery import run_async as battery_run  # noqa: E402 — RED until T040

# ---------------------------------------------------------------------------
# Attribute names (KOSMOS extension namespace per Spec 021 / FR-D03)
# ---------------------------------------------------------------------------

_ATTR_DEPLOYMENT_ENV = "deployment.environment"
_ATTR_BATTERY_INPUT_ID = "kosmos.eval.input_id"

_ENV_MAIN = "main"
_ENV_SHADOW = "shadow"


# ---------------------------------------------------------------------------
# Helper: minimal mock transport for isolation tests
# ---------------------------------------------------------------------------


def _make_mock_transport() -> httpx.MockTransport:
    """Return a no-op mock transport so no live HTTP calls are made."""

    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "mock-0",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    return httpx.MockTransport(_handler)


# ---------------------------------------------------------------------------
# Fixture: fresh InMemorySpanExporter wired into battery._tracer
# ---------------------------------------------------------------------------


def _make_exporter_and_provider() -> tuple[InMemorySpanExporter, TracerProvider]:
    """Create a new in-memory exporter + SDK TracerProvider for one battery run."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return exporter, provider


# ---------------------------------------------------------------------------
# Test 1: main-environment run emits at least one span tagged deployment.environment=main
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_battery_emits_main_environment_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run battery with environment='main'; assert at least one span carries
    attributes['deployment.environment'] == 'main'.

    RED until T040 creates tests/shadow_eval/battery.py.
    """
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    import tests.shadow_eval.battery as battery_mod

    exporter, provider = _make_exporter_and_provider()
    tracer = provider.get_tracer("tests.shadow_eval.battery")
    monkeypatch.setattr(battery_mod, "_tracer", tracer)

    await battery_run(environment=_ENV_MAIN, transport=_make_mock_transport())

    finished = exporter.get_finished_spans()
    assert finished, (
        "Expected at least one finished span from the battery (environment=main), got none."
    )

    env_values = [dict(span.attributes or {}).get(_ATTR_DEPLOYMENT_ENV) for span in finished]
    assert _ENV_MAIN in env_values, (
        f"No span carries {_ATTR_DEPLOYMENT_ENV!r}={_ENV_MAIN!r}. Observed values: {env_values}"
    )


# ---------------------------------------------------------------------------
# Test 2: shadow-environment run emits at least one span tagged deployment.environment=shadow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_battery_emits_shadow_environment_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run battery with environment='shadow'; assert at least one span carries
    attributes['deployment.environment'] == 'shadow'.

    RED until T040 creates tests/shadow_eval/battery.py.
    """
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    import tests.shadow_eval.battery as battery_mod

    exporter, provider = _make_exporter_and_provider()
    tracer = provider.get_tracer("tests.shadow_eval.battery")
    monkeypatch.setattr(battery_mod, "_tracer", tracer)

    await battery_run(environment=_ENV_SHADOW, transport=_make_mock_transport())

    finished = exporter.get_finished_spans()
    assert finished, (
        "Expected at least one finished span from the battery (environment=shadow), got none."
    )

    env_values = [dict(span.attributes or {}).get(_ATTR_DEPLOYMENT_ENV) for span in finished]
    assert _ENV_SHADOW in env_values, (
        f"No span carries {_ATTR_DEPLOYMENT_ENV!r}={_ENV_SHADOW!r}. Observed values: {env_values}"
    )


# ---------------------------------------------------------------------------
# Test 3: both environments share identical battery input ids (FR-D03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_both_environments_share_battery_input_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Run battery twice (main + shadow) and assert the set of
    ``kosmos.eval.input_id`` attribute values is identical across both runs.

    This ensures downstream diffing is deterministic — both environments
    exercise the same fixed input cases.

    RED until T040 creates tests/shadow_eval/battery.py.
    """
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    import tests.shadow_eval.battery as battery_mod

    # --- main run ---
    exporter_main, provider_main = _make_exporter_and_provider()
    tracer_main = provider_main.get_tracer("tests.shadow_eval.battery")
    monkeypatch.setattr(battery_mod, "_tracer", tracer_main)
    await battery_run(environment=_ENV_MAIN, transport=_make_mock_transport())
    spans_main = exporter_main.get_finished_spans()

    # --- shadow run ---
    exporter_shadow, provider_shadow = _make_exporter_and_provider()
    tracer_shadow = provider_shadow.get_tracer("tests.shadow_eval.battery")
    monkeypatch.setattr(battery_mod, "_tracer", tracer_shadow)
    await battery_run(environment=_ENV_SHADOW, transport=_make_mock_transport())
    spans_shadow = exporter_shadow.get_finished_spans()

    # Collect input ids from each run — only spans that carry the attribute.
    def _input_ids(spans: list) -> set[str]:  # type: ignore[type-arg]
        ids: set[str] = set()
        for span in spans:
            val = dict(span.attributes or {}).get(_ATTR_BATTERY_INPUT_ID)
            if val is not None:
                ids.add(str(val))
        return ids

    ids_main = _input_ids(spans_main)
    ids_shadow = _input_ids(spans_shadow)

    assert ids_main, (
        f"Expected at least one span with {_ATTR_BATTERY_INPUT_ID!r} in the main run. "
        f"Got zero. Spans exported: {len(spans_main)}."
    )
    assert ids_shadow, (
        f"Expected at least one span with {_ATTR_BATTERY_INPUT_ID!r} in the shadow run. "
        f"Got zero. Spans exported: {len(spans_shadow)}."
    )
    assert ids_main == ids_shadow, (
        f"Battery input ids differ between environments — the two runs did not exercise "
        f"the same inputs.\n"
        f"  main-only ids   : {ids_main - ids_shadow}\n"
        f"  shadow-only ids : {ids_shadow - ids_main}\n"
        f"  shared ids      : {ids_main & ids_shadow}"
    )
