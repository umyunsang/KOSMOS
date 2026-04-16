# SPDX-License-Identifier: Apache-2.0
"""Auth-gate test for nmc_emergency_search — T029.

SC-006: Every fetch call to nmc_emergency_search must be short-circuited by the
Layer 3 auth-gate (requires_auth=True) before any upstream NMC HTTP call is made.

This test programmatically registers NMC into a test-local registry (not the
global register_all.py registry, which is reserved for Stage 3 / T033), then
calls lookup(mode='fetch') and asserts:
  1. The returned envelope is LookupError with reason="auth_required".
  2. retryable=False.
  3. Zero upstream HTTP calls were made (respx call_count == 0).

No KOSMOS_NMC_* env vars are required because the gate fires before any network IO.
"""

from __future__ import annotations

import pytest
import respx

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.lookup import lookup
from kosmos.tools.models import LookupError, LookupFetchInput  # noqa: A004
from kosmos.tools.nmc.emergency_search import register
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Fixture: test-local registry + executor with NMC registered
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def nmc_registry() -> ToolRegistry:
    """ToolRegistry with only nmc_emergency_search registered (module scope)."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register(registry, executor)
    return registry


@pytest.fixture(scope="module")
def nmc_executor(nmc_registry: ToolRegistry) -> ToolExecutor:
    """ToolExecutor bound to the NMC-only registry."""
    executor = ToolExecutor(nmc_registry)
    # Re-register adapter into the second executor instance so invoke() finds it.
    # (The module-scope fixture above already registered into a private executor;
    # we create a fresh executor here that shares the registry but needs its own
    # adapter map wired up.)
    register(nmc_registry, executor)
    return executor


@pytest.fixture()
def nmc_reg_exec():
    """Function-scope registry + executor pair for isolation tests."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register(registry, executor)
    return registry, executor


# ---------------------------------------------------------------------------
# SC-006: Layer 3 auth-gate short-circuits with zero upstream calls
# ---------------------------------------------------------------------------


class TestNmcAuthGate:
    """Verify that the Layer 3 gate short-circuits NMC fetches unconditionally."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_returns_auth_required_error(self, nmc_reg_exec):
        """lookup(mode='fetch') on nmc_emergency_search returns LookupError(auth_required)."""
        registry, executor = nmc_reg_exec

        # Register a catch-all route for any nmc.go.kr URL so we can assert
        # it is never called (respx.mock enforces no unmatched calls by default
        # unless pass_through=True; this explicit route makes the intent clear).
        respx.get(url__regex=r".*nmc\.go\.kr.*").respond(200, json={})

        inp = LookupFetchInput(
            mode="fetch",
            tool_id="nmc_emergency_search",
            params={"lat": 37.5, "lon": 127.0, "limit": 5},
        )
        result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupError), (
            f"Expected LookupError, got {type(result).__name__}: {result!r}"
        )
        assert result.kind == "error"
        assert result.reason == "auth_required", (
            f"Expected reason='auth_required', got {result.reason!r}"
        )
        assert result.retryable is False, f"Expected retryable=False, got {result.retryable!r}"

    @pytest.mark.asyncio
    @respx.mock
    async def test_zero_upstream_calls(self, nmc_reg_exec):
        """No HTTP calls must be made to any NMC URL when auth gate fires."""
        registry, executor = nmc_reg_exec

        # Intercept ANY outbound HTTP call — if any slips through, respx will
        # raise httpx.ConnectError (unmatched request in strict mock mode).
        nmc_route = respx.get(url__regex=r".*nmc\.go\.kr.*").respond(200, json={})
        also_catch_all = respx.route().respond(200, json={})  # noqa: F841 — intentional catch-all

        inp = LookupFetchInput(
            mode="fetch",
            tool_id="nmc_emergency_search",
            params={"lat": 37.5, "lon": 127.0, "limit": 5},
        )
        await lookup(inp, executor=executor)

        # The NMC-specific route must have received exactly zero calls.
        assert nmc_route.call_count == 0, (
            f"Expected 0 NMC upstream calls, got {nmc_route.call_count}"
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_respx_call_count_zero_overall(self, nmc_reg_exec):
        """Total respx call count must be zero — the gate fires before any IO."""
        registry, executor = nmc_reg_exec

        # Register a pattern but assert it is never matched.
        respx.get(url__regex=r".*odcloud\.kr.*").respond(200, json={})

        inp = LookupFetchInput(
            mode="fetch",
            tool_id="nmc_emergency_search",
            params={"lat": 35.1, "lon": 129.0, "limit": 10},
        )
        await lookup(inp, executor=executor)

        # respx.calls is the global call log within the mock context.
        assert respx.calls.call_count == 0, (
            f"Expected respx.calls.call_count == 0, got {respx.calls.call_count}"
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_auth_gate_fires_regardless_of_params(self, nmc_reg_exec):
        """Gate must fire for all valid param combinations, not just sentinel values."""
        registry, executor = nmc_reg_exec

        respx.get(url__regex=r".*").respond(200, json={})

        test_cases = [
            {"lat": 0.0, "lon": 0.0, "limit": 1},
            {"lat": -90.0, "lon": -180.0, "limit": 100},
            {"lat": 90.0, "lon": 180.0, "limit": 50},
            {"lat": 37.5665, "lon": 126.9780, "limit": 3},
        ]
        for params in test_cases:
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="nmc_emergency_search",
                params=params,
            )
            result = await lookup(inp, executor=executor)
            assert isinstance(result, LookupError), (
                f"Expected LookupError for params={params}, got {type(result).__name__}"
            )
            assert result.reason == "auth_required", (
                f"Expected auth_required for params={params}, got {result.reason!r}"
            )

        # No upstream calls made across all test cases.
        assert respx.calls.call_count == 0
