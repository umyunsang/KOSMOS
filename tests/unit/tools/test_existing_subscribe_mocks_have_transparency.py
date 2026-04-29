# SPDX-License-Identifier: Apache-2.0
"""T027 — Parameterised test: existing subscribe mocks declare transparency metadata.

Covers:
- mock_cbs_disaster_v1 (cbs.disaster_feed)
- mock_rest_pull_tick_v1 (data_go_kr.rest_pull_tick)
- mock_rss_public_notices_v1 (data_go_kr.rss_notices)

Subscribe mocks yield streaming events rather than a single response dict,
so transparency fields are declared via a module-level get_transparency_metadata()
function. This test calls that function and asserts all six fields are present
and non-empty.

Contract: specs/2296-ax-mock-adapters/contracts/mock-adapter-response-shape.md § 4
"""

from __future__ import annotations

import importlib

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
# Subscribe adapter module paths + expected values
# ---------------------------------------------------------------------------

_SUBSCRIBE_ADAPTER_CASES = [
    (
        "kosmos.tools.mock.cbs.disaster_feed",
        "mock_cbs_disaster_v1",
        "EU CB-PWS (Cell Broadcast Public Warning System)",
        "ax-infrastructure-callable-channel",
    ),
    (
        "kosmos.tools.mock.data_go_kr.rest_pull_tick",
        "mock_rest_pull_tick_v1",
        "(generic REST polling)",
        "ax-infrastructure-callable-channel",
    ),
    (
        "kosmos.tools.mock.data_go_kr.rss_notices",
        "mock_rss_public_notices_v1",
        "(generic RSS feed)",
        "ax-infrastructure-callable-channel",
    ),
]


@pytest.mark.parametrize(
    "module_path,adapter_id,expected_intl_ref,expected_ref_impl",
    [
        pytest.param(*case, id=case[1])
        for case in _SUBSCRIBE_ADAPTER_CASES
    ],
)
def test_subscribe_mock_has_transparency_metadata_function(
    module_path: str,
    adapter_id: str,
    expected_intl_ref: str,
    expected_ref_impl: str,
) -> None:
    """Each subscribe mock must expose get_transparency_metadata() returning six fields."""
    module = importlib.import_module(module_path)

    assert hasattr(module, "get_transparency_metadata"), (
        f"Module {module_path!r} must expose get_transparency_metadata() "
        f"(Epic ε #2296 T027 retrofit requirement)"
    )

    metadata = module.get_transparency_metadata()

    # Assert all six fields are present and non-empty
    for field in _TRANSPARENCY_FIELDS:
        value = metadata.get(field)
        assert value is not None and isinstance(value, str) and value.strip(), (
            f"Subscribe adapter {adapter_id!r}: get_transparency_metadata() "
            f"returned missing or empty {field!r}. Got: {value!r}"
        )

    # Assert _mode is exactly "mock"
    assert metadata["_mode"] == "mock", (
        f"{adapter_id!r}: _mode must be 'mock', got {metadata['_mode']!r}"
    )

    # Assert international reference matches expected value
    assert metadata["_international_reference"] == expected_intl_ref, (
        f"{adapter_id!r}: _international_reference mismatch. "
        f"Expected {expected_intl_ref!r}, got {metadata['_international_reference']!r}"
    )

    # Assert reference_implementation matches expected value
    assert metadata["_reference_implementation"] == expected_ref_impl, (
        f"{adapter_id!r}: _reference_implementation mismatch. "
        f"Expected {expected_ref_impl!r}, got {metadata['_reference_implementation']!r}"
    )


@pytest.mark.parametrize(
    "module_path,adapter_id,_intl,_ref",
    [
        pytest.param(*case, id=case[1])
        for case in _SUBSCRIBE_ADAPTER_CASES
    ],
)
def test_subscribe_mock_transparency_all_fields_are_url_shaped_where_appropriate(
    module_path: str,
    adapter_id: str,
    _intl: str,
    _ref: str,
) -> None:
    """policy_authority and actual_endpoint_when_live must be URL-shaped (start with https://)."""
    module = importlib.import_module(module_path)
    metadata = module.get_transparency_metadata()

    policy_authority = metadata.get("_policy_authority", "")
    assert policy_authority.startswith("https://"), (
        f"{adapter_id!r}: _policy_authority must start with 'https://', "
        f"got {policy_authority!r}"
    )

    actual_endpoint = metadata.get("_actual_endpoint_when_live", "")
    assert actual_endpoint.startswith("https://"), (
        f"{adapter_id!r}: _actual_endpoint_when_live must start with 'https://', "
        f"got {actual_endpoint!r}"
    )


def test_subscribe_adapter_ids_are_registered() -> None:
    """All three subscribe adapters must be registered in the subscribe _ADAPTER_REGISTRY."""
    # Trigger imports to ensure self-registration
    from kosmos.primitives.subscribe import _SUBSCRIBE_ADAPTERS
    from kosmos.tools.mock.cbs.disaster_feed import MOCK_CBS_DISASTER_TOOL  # noqa: F401
    from kosmos.tools.mock.data_go_kr.rest_pull_tick import MOCK_REST_PULL_TICK_TOOL  # noqa: F401
    from kosmos.tools.mock.data_go_kr.rss_notices import MOCK_RSS_PUBLIC_NOTICES_TOOL  # noqa: F401

    expected_tool_ids = {
        "mock_cbs_disaster_v1",
        "mock_rest_pull_tick_v1",
        "mock_rss_public_notices_v1",
    }
    for tool_id in expected_tool_ids:
        assert tool_id in _SUBSCRIBE_ADAPTERS, (
            f"Subscribe adapter {tool_id!r} not found in _SUBSCRIBE_ADAPTERS. "
            f"Available: {list(_SUBSCRIBE_ADAPTERS.keys())}"
        )
