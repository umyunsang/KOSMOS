# SPDX-License-Identifier: Apache-2.0
"""Security invariant tests for Scenario 1 Route Safety (030 rebase).

Verifies FR-009/FR-010: V1-V6 security invariants are enforced through
ToolRegistry.register() backstop. A misconfigured adapter clone must raise
ValidationError (V6: auth_type ↔ auth_level consistency violation).

These tests confirm that the two seed adapters (koroad, kma) pass the
full V1-V6 backstop when registered via the normal path.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from kosmos.tools.errors import RegistrationError
from kosmos.tools.models import AdapterRealDomainPolicy, GovAPITool
from kosmos.tools.registry import ToolRegistry
from tests.engine.conftest import MockInput, MockOutput

# ---------------------------------------------------------------------------
# Helper: clone of koroad adapter with deliberate V6 violation
# After Epic δ #2295 Path B, V6 is enforced via policy.citizen_facing_gate.
# A V6 violation is triggered by auth_type="public" + policy.citizen_facing_gate
# that derives AAL3 (sign or submit), since public only allows public/AAL1.
# ---------------------------------------------------------------------------


def _make_broken_tool(
    *,
    auth_type: str,
    citizen_facing_gate: str = "sign",
) -> GovAPITool:
    """Build a GovAPITool with deliberate auth_type ↔ derived_auth_level V6 violation.

    auth_type='public' with citizen_facing_gate='sign' (derives AAL3) triggers V6.
    """
    return GovAPITool(
        id="broken_koroad_clone",
        name_ko="깨진 테스트 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="https://test.example.com/api",
        auth_type=auth_type,  # type: ignore[arg-type]
        input_schema=MockInput,
        output_schema=MockOutput,
        search_hint="broken clone for V6 violation test",
        is_core=False,
        is_concurrency_safe=True,
        cache_ttl_seconds=0,
        rate_limit_per_minute=60,
        policy=AdapterRealDomainPolicy(
            real_classification_url="https://test.example.com/policy",
            real_classification_text="테스트 V6 위반 정책",
            citizen_facing_gate=citizen_facing_gate,  # type: ignore[arg-type]
            last_verified=datetime(2026, 4, 29, tzinfo=UTC),
        ),
    )


# ---------------------------------------------------------------------------
# T029: V6 backstop — auth_type ↔ auth_level mismatch raises ValidationError
# ---------------------------------------------------------------------------


def test_v6_violation_raises_on_construction() -> None:
    """FR-009 V6: auth_type=public + policy.citizen_facing_gate=sign (derives AAL3) is disallowed.

    After Epic δ #2295 Path B, V6 is enforced via policy.citizen_facing_gate derivation.
    auth_type='public' only permits public/AAL1; 'sign' derives AAL3 → V6 violation.
    The V6 @model_validator catches this at construction time.
    """
    with pytest.raises(ValidationError) as exc_info:
        _make_broken_tool(auth_type="public", citizen_facing_gate="sign")

    errors = exc_info.value.errors()
    assert any("v6" in str(e).lower() or "auth" in str(e).lower() for e in errors), (
        f"Expected V6 auth-related ValidationError, got: {errors}"
    )


def test_v6_violation_also_blocked_by_registry() -> None:
    """FR-010: ToolRegistry.register() backstop blocks model_construct bypass.

    Even if a misconfigured tool somehow bypasses Pydantic construction
    (e.g., model_construct), the registry backstop must reject it.

    We test the normal path: registry.register() on a valid tool succeeds,
    and attempting to register the same tool with a V6 violation (if it
    could be constructed) fails at the registry level.

    Since GovAPITool V6 validator fires at construction, this test verifies
    that the registry's own check raises on the same invariant.
    """
    registry = ToolRegistry()

    # Construct via model_construct to bypass pydantic validators (simulates
    # a supply-chain attack that bypasses construction-time checks).
    # The registry backstop must catch this.
    # After Epic δ #2295 Path B: policy.citizen_facing_gate='sign' derives AAL3,
    # which conflicts with auth_type='public' (only permits public/AAL1).
    try:
        broken = GovAPITool.model_construct(
            id="bypass_attempt",
            name_ko="바이패스 시도",
            ministry="OTHER",
            category=["test"],
            endpoint="https://test.example.com/api",
            auth_type="public",
            input_schema=MockInput,
            output_schema=MockOutput,
            search_hint="bypass test",
            is_core=False,
            is_concurrency_safe=True,
            cache_ttl_seconds=0,
            rate_limit_per_minute=60,
            policy=AdapterRealDomainPolicy(
                real_classification_url="https://test.example.com/policy",
                real_classification_text="바이패스 V6 위반 정책",
                citizen_facing_gate="sign",  # derives AAL3 — violates V6 with public auth_type
                last_verified=datetime(2026, 4, 29, tzinfo=UTC),
            ),
        )
        # If model_construct succeeded, the registry backstop must reject it
        with pytest.raises((ValidationError, ValueError, RegistrationError)) as exc_info:
            registry.register(broken)

        assert exc_info.value is not None, "Registry backstop must reject V6-violating tool"

    except (ValidationError, TypeError):
        # model_construct itself raised — acceptable, means pydantic enforces even on construct
        pass


# ---------------------------------------------------------------------------
# T029: Positive test — valid MVP adapters pass all V1-V6 checks
# ---------------------------------------------------------------------------


def test_mvp_adapters_pass_v1_to_v6() -> None:
    """FR-009/010: Both seed adapters satisfy V1-V6 when registered normally.

    koroad_accident_hazard_search: auth_type='public', auth_level='AAL1', requires_auth=True
    kma_forecast_fetch: auth_type='public', auth_level='AAL1', requires_auth=True

    This is the MVP meta-tool pattern: (public, AAL1) + requires_auth=True
    is explicitly documented as compliant (not an exemption).
    """
    from kosmos.recovery.executor import RecoveryExecutor
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.kma.forecast_fetch import KMA_FORECAST_FETCH_TOOL
    from kosmos.tools.koroad.accident_hazard_search import register as reg_koroad

    registry = ToolRegistry()
    recovery = RecoveryExecutor()
    executor = ToolExecutor(registry, recovery_executor=recovery)

    # Register koroad through normal path — must not raise
    reg_koroad(registry, executor)

    # Register KMA through normal path — must not raise
    registry.register(KMA_FORECAST_FETCH_TOOL)

    assert registry.lookup("koroad_accident_hazard_search") is not None
    assert registry.lookup("kma_forecast_fetch") is not None
