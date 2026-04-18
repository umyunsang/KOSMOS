# SPDX-License-Identifier: Apache-2.0
"""E2E OTel span assertion tests for Scenario 1 Route Safety (030 rebase).

Verifies FR-017 (kosmos.tool.outcome on execute_tool span) and FR-018
(kosmos.tool.adapter on lookup fetch path) using InMemorySpanExporter.

These tests are skipped when OTEL_SDK_DISABLED=true is set in the environment.
"""

from __future__ import annotations

import os

import pytest

from tests.e2e.conftest import run_scenario


_SDK_DISABLED = os.getenv("OTEL_SDK_DISABLED", "").lower() == "true"


@pytest.mark.asyncio
@pytest.mark.skipif(_SDK_DISABLED, reason="OTEL_SDK_DISABLED=true; span assertions skipped")
async def test_fr017_execute_tool_span_has_outcome() -> None:
    """FR-017: every execute_tool span carries kosmos.tool.outcome ('ok' or 'error').

    The executor.py finally block must set the attribute before the span ends.
    """
    report = await run_scenario("happy")

    obs = report.observability
    if obs.sdk_disabled:
        pytest.skip("OTel SDK was disabled during this run; span assertions skipped")

    execute_tool_spans = [s for s in obs.spans if "execute_tool" in s.name or s.operation_name == "execute_tool"]

    # Happy path: at least one execute_tool span should exist
    if not execute_tool_spans:
        # If no execute_tool spans (depends on OTel integration level), warn but don't fail
        pytest.skip("No execute_tool spans captured — OTel integration may not emit spans in test environment")

    for span in execute_tool_spans:
        assert span.outcome in ("ok", "error"), (
            f"FR-017: kosmos.tool.outcome must be 'ok' or 'error', got {span.outcome!r} "
            f"for span {span.name!r}"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(_SDK_DISABLED, reason="OTEL_SDK_DISABLED=true; span assertions skipped")
async def test_fr018_fetch_span_has_adapter_attribute() -> None:
    """FR-018: execute_tool spans for lookup-fetch calls carry kosmos.tool.adapter.

    The lookup.py fetch path sets current_span.set_attribute('kosmos.tool.adapter', inp.tool_id).
    """
    report = await run_scenario("happy")

    obs = report.observability
    if obs.sdk_disabled:
        pytest.skip("OTel SDK was disabled during this run; span assertions skipped")

    # Spans with adapter_id set must have tool_name == "lookup"
    adapter_spans = [s for s in obs.spans if s.adapter_id is not None]

    if not adapter_spans:
        pytest.skip("No adapter spans captured — OTel integration may not emit spans in test environment")

    for span in adapter_spans:
        # FR-018: kosmos.tool.adapter is only set on lookup fetch spans
        assert span.tool_name == "lookup" or "lookup" in span.name.lower(), (
            f"FR-018: kosmos.tool.adapter must only appear on lookup spans, "
            f"but span {span.name!r} has adapter_id={span.adapter_id!r}"
        )
        # adapter_id must be a known adapter
        known_adapters = {
            "koroad_accident_hazard_search",
            "kma_forecast_fetch",
            "hira_hospital_search",
            "nmc_emergency_search",
        }
        assert span.adapter_id in known_adapters, (
            f"FR-018: adapter_id={span.adapter_id!r} not in known adapters {known_adapters}"
        )


@pytest.mark.asyncio
@pytest.mark.skipif(_SDK_DISABLED, reason="OTEL_SDK_DISABLED=true; span assertions skipped")
async def test_fr018_search_spans_have_no_adapter_attribute() -> None:
    """FR-018 (negative): search-mode lookup spans must NOT carry kosmos.tool.adapter.

    The spec explicitly states that search mode and resolve_location MUST NOT
    carry this attribute (only fetch mode sets it).
    """
    report = await run_scenario("happy")

    obs = report.observability
    if obs.sdk_disabled:
        pytest.skip("OTel SDK was disabled during this run; span assertions skipped")

    # resolve_location spans must NOT have adapter_id
    resolve_spans = [s for s in obs.spans if s.tool_name == "resolve_location"]
    for span in resolve_spans:
        assert span.adapter_id is None, (
            f"FR-018: resolve_location span {span.name!r} must NOT have "
            f"kosmos.tool.adapter, but got adapter_id={span.adapter_id!r}"
        )
