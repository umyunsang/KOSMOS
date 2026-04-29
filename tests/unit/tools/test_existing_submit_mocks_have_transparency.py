# SPDX-License-Identifier: Apache-2.0
"""T026 — Parameterised test: existing submit mocks carry six transparency fields.

Covers:
- mock_traffic_fine_pay_v1 (data_go_kr.fines_pay)
- mock_welfare_application_submit_v1 (mydata.welfare_application)

Each is retrofitted via stamp_mock_response — this test asserts the six fields
are present and non-empty in adapter_receipt after a successful invocation.

Contract: specs/2296-ax-mock-adapters/contracts/mock-adapter-response-shape.md § 4
"""

from __future__ import annotations

import pytest

_TRANSPARENCY_FIELDS = (
    "_mode",
    "_reference_implementation",
    "_actual_endpoint_when_live",
    "_security_wrapping_pattern",
    "_policy_authority",
    "_international_reference",
)

# ---------------------------------------------------------------------------
# Test cases — (adapter_id, params_dict) tuples
# ---------------------------------------------------------------------------

_SUBMIT_ADAPTER_CASES = [
    (
        "mock_traffic_fine_pay_v1",
        {"fine_reference": "FINE-2026-001", "payment_method": "card"},
    ),
    (
        "mock_welfare_application_submit_v1",
        {
            "applicant_id": "di-test-applicant-001",
            "benefit_code": "기초생활수급",
            "application_type": "new",
            "household_size": 3,
        },
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adapter_id,params",
    [pytest.param(case[0], case[1], id=case[0]) for case in _SUBMIT_ADAPTER_CASES],
)
async def test_existing_submit_mock_has_six_transparency_fields(
    adapter_id: str,
    params: dict,
) -> None:
    """Each existing submit mock's adapter_receipt must carry all six transparency fields.

    Invokes the adapter's invoke() function directly with minimal valid params
    and asserts that adapter_receipt contains each of the six fields as non-empty strings.
    """
    # Ensure mock modules are imported (they self-register on import)
    import kosmos.tools.mock.data_go_kr.fines_pay  # noqa: F401
    import kosmos.tools.mock.mydata.welfare_application  # noqa: F401
    from kosmos.primitives.submit import _ADAPTER_REGISTRY

    assert adapter_id in _ADAPTER_REGISTRY, (
        f"Adapter {adapter_id!r} not found in submit _ADAPTER_REGISTRY after import. "
        f"Available: {list(_ADAPTER_REGISTRY.keys())}"
    )

    _registration, invoke_fn = _ADAPTER_REGISTRY[adapter_id]
    result = await invoke_fn(params)

    receipt = result.adapter_receipt
    for field in _TRANSPARENCY_FIELDS:
        value = receipt.get(field)
        assert value is not None and isinstance(value, str) and value.strip(), (
            f"Submit adapter {adapter_id!r}: adapter_receipt missing or empty {field!r}. "
            f"Got: {value!r}"
        )

    # _mode must be exactly "mock"
    assert receipt["_mode"] == "mock", (
        f"{adapter_id!r}: _mode must be 'mock', got {receipt['_mode']!r}"
    )


@pytest.mark.asyncio
async def test_fines_pay_transparency_international_reference() -> None:
    """mock_traffic_fine_pay_v1 must reference 'UK GOV.UK Pay'."""
    import kosmos.tools.mock.data_go_kr.fines_pay  # noqa: F401
    from kosmos.primitives.submit import _ADAPTER_REGISTRY

    _registration, invoke_fn = _ADAPTER_REGISTRY["mock_traffic_fine_pay_v1"]
    result = await invoke_fn({"fine_reference": "FINE-TEST-001", "payment_method": "bank_transfer"})
    assert result.adapter_receipt["_international_reference"] == "UK GOV.UK Pay"


@pytest.mark.asyncio
async def test_welfare_application_transparency_international_reference() -> None:
    """mock_welfare_application_submit_v1 must reference 'Estonia X-Road'."""
    import kosmos.tools.mock.mydata.welfare_application  # noqa: F401
    from kosmos.primitives.submit import _ADAPTER_REGISTRY

    _registration, invoke_fn = _ADAPTER_REGISTRY["mock_welfare_application_submit_v1"]
    result = await invoke_fn(
        {
            "applicant_id": "di-test-002",
            "benefit_code": "장애인지원",
            "application_type": "renewal",
            "household_size": 2,
        }
    )
    assert result.adapter_receipt["_international_reference"] == "Estonia X-Road"
    assert result.adapter_receipt["_reference_implementation"] == "public-mydata-action-extension"
