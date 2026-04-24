# SPDX-License-Identifier: Apache-2.0
"""T031 — submit primitive denial path tests.

Verifies that when the permission check refuses a submit call:
  - The adapter's invoke() is never called (no side effects).
  - No adapter dispatch occurs (verified via unittest.mock.patch spy).
  - A structured refusal (SubmitOutput with status=rejected) is returned.
  - The tier gate is the enforcement mechanism (Spec 031 SC-005).

The test uses ``mock_traffic_fine_pay_v1`` (registered at import time) and
monkeypatches ``check_tier_gate`` to force a denial without needing a real
AuthContext implementation.

No live network calls are made.

References
----------
- specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 3
- src/kosmos/primitives/submit.py (check_tier_gate + submit dispatcher)
- src/kosmos/tools/mock/data_go_kr/fines_pay.py
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# Ensure adapter is registered in the dispatcher before tests run
import kosmos.tools.mock.data_go_kr.fines_pay  # noqa: F401
from kosmos.primitives.submit import SubmitOutput, SubmitStatus, submit


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


TOOL_ID = "mock_traffic_fine_pay_v1"
VALID_PARAMS = {
    "fine_reference": "FINE-2026-DENY-001",
    "payment_method": "bank_transfer",
}

# A simulated tier-gate rejection payload matching check_tier_gate return shape
_FORCED_REJECTION = {
    "rejected": True,
    "reason": "published_tier_minimum='ganpyeon_injeung_kakao_aal2' not met: test forced denial",
}


# ---------------------------------------------------------------------------
# T031-A: Adapter is not called when tier gate denies
# ---------------------------------------------------------------------------


class TestSubmitDenialNoAdapterCall:
    """When check_tier_gate returns a rejection, invoke() must never be called."""

    @pytest.mark.asyncio
    async def test_adapter_invoke_not_called_on_denial(self) -> None:
        """Denied submit call must not dispatch to the adapter invoke()."""
        spy_invoke = AsyncMock(name="spy_invoke")

        with (
            patch(
                "kosmos.primitives.submit.check_tier_gate",
                return_value=_FORCED_REJECTION,
            ),
            patch.dict(
                "kosmos.primitives.submit._ADAPTER_REGISTRY",
                {
                    TOOL_ID: (
                        kosmos.tools.mock.data_go_kr.fines_pay.REGISTRATION,
                        spy_invoke,
                    )
                },
            ),
        ):
            result = await submit(
                tool_id=TOOL_ID,
                params=VALID_PARAMS,
                auth_context=None,
            )

        # Adapter invoke must NOT have been called
        spy_invoke.assert_not_called()
        # A structured rejection SubmitOutput is returned (not an exception)
        assert isinstance(result, SubmitOutput)
        assert result.status == SubmitStatus.rejected

    @pytest.mark.asyncio
    async def test_denial_returns_structured_reject_not_exception(self) -> None:
        """Denied submit must surface as SubmitOutput(status=rejected), not raise."""
        with patch(
            "kosmos.primitives.submit.check_tier_gate",
            return_value=_FORCED_REJECTION,
        ):
            result = await submit(
                tool_id=TOOL_ID,
                params=VALID_PARAMS,
                auth_context=None,
            )

        assert isinstance(result, SubmitOutput), (
            f"Expected SubmitOutput on denial, got {type(result).__name__}"
        )
        assert result.status == SubmitStatus.rejected

    @pytest.mark.asyncio
    async def test_denial_carries_reason_in_adapter_receipt(self) -> None:
        """Rejected SubmitOutput must include 'reason' in adapter_receipt."""
        with patch(
            "kosmos.primitives.submit.check_tier_gate",
            return_value=_FORCED_REJECTION,
        ):
            result = await submit(
                tool_id=TOOL_ID,
                params=VALID_PARAMS,
                auth_context=None,
            )

        assert isinstance(result, SubmitOutput)
        assert result.status == SubmitStatus.rejected
        # The dispatcher puts the tier-gate reason into adapter_receipt
        assert "reason" in result.adapter_receipt, (
            "Rejected SubmitOutput must carry 'reason' in adapter_receipt"
        )

    @pytest.mark.asyncio
    async def test_denial_transaction_id_is_deterministic(self) -> None:
        """Even rejected calls must produce a deterministic transaction_id (FR-004)."""
        with patch(
            "kosmos.primitives.submit.check_tier_gate",
            return_value=_FORCED_REJECTION,
        ):
            result1 = await submit(
                tool_id=TOOL_ID,
                params=VALID_PARAMS,
                auth_context=None,
            )
            result2 = await submit(
                tool_id=TOOL_ID,
                params=VALID_PARAMS,
                auth_context=None,
            )

        assert isinstance(result1, SubmitOutput)
        assert isinstance(result2, SubmitOutput)
        assert result1.transaction_id == result2.transaction_id, (
            "Deterministic transaction_id must be identical for identical inputs (FR-004)"
        )


# ---------------------------------------------------------------------------
# T031-B: Denial via real insufficient-tier auth context (no monkeypatch)
# ---------------------------------------------------------------------------


class TestSubmitDenialRealTierGate:
    """Denial via the real tier-gate logic with an insufficient AuthContext."""

    @pytest.mark.asyncio
    async def test_aal1_context_denied_for_aal2_adapter(self) -> None:
        """AAL1 auth context must be denied by the real tier gate for an AAL2 adapter."""
        from pydantic import BaseModel, ConfigDict

        class _MinimalAuthContext(BaseModel):
            model_config = ConfigDict(frozen=True, extra="allow")
            published_tier: str

        # digital_onepass_level1_aal1 is AAL1 — below the required AAL2
        auth_ctx = _MinimalAuthContext(published_tier="digital_onepass_level1_aal1")

        spy_invoke = AsyncMock(name="spy_invoke")
        with patch.dict(
            "kosmos.primitives.submit._ADAPTER_REGISTRY",
            {
                TOOL_ID: (
                    kosmos.tools.mock.data_go_kr.fines_pay.REGISTRATION,
                    spy_invoke,
                )
            },
        ):
            result = await submit(
                tool_id=TOOL_ID,
                params=VALID_PARAMS,
                auth_context=auth_ctx,
            )

        spy_invoke.assert_not_called()
        assert isinstance(result, SubmitOutput)
        assert result.status == SubmitStatus.rejected

    @pytest.mark.asyncio
    async def test_no_auth_context_denied_for_tier_gated_adapter(self) -> None:
        """No auth context must be denied for a tier-gated adapter (fail-closed)."""
        spy_invoke = AsyncMock(name="spy_invoke")
        with patch.dict(
            "kosmos.primitives.submit._ADAPTER_REGISTRY",
            {
                TOOL_ID: (
                    kosmos.tools.mock.data_go_kr.fines_pay.REGISTRATION,
                    spy_invoke,
                )
            },
        ):
            result = await submit(
                tool_id=TOOL_ID,
                params=VALID_PARAMS,
                auth_context=None,
            )

        spy_invoke.assert_not_called()
        assert isinstance(result, SubmitOutput)
        assert result.status == SubmitStatus.rejected
