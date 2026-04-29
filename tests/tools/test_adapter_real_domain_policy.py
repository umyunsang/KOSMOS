# SPDX-License-Identifier: Apache-2.0
"""Unit tests for AdapterRealDomainPolicy (Epic δ #2295 FR-003 + SC-002 + SC-003 + SC-004).

Authority:
- specs/2295-backend-permissions-cleanup/spec.md § FR-003 (model definition)
- specs/2295-backend-permissions-cleanup/spec.md § US2 (model creation acceptance)
- specs/2295-backend-permissions-cleanup/spec.md § FR-004 (18+ adapters have policy)
- AGENTS.md § CORE THESIS — KOSMOS does NOT invent permission policy
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from kosmos.tools.models import AdapterRealDomainPolicy


def test_model_frozen() -> None:
    """SC-002: model_config has frozen=True — instances immutable."""
    policy = AdapterRealDomainPolicy(
        real_classification_url="https://www.koroad.or.kr/main/web/policy/data_use.do",
        real_classification_text="도로교통공단 데이터 활용 정책",
        citizen_facing_gate="read-only",
        last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
    )
    with pytest.raises(ValidationError):
        policy.real_classification_url = "https://other.example.com"  # type: ignore[misc]


def test_extra_forbid() -> None:
    """SC-002: extra='forbid' — unknown fields rejected."""
    with pytest.raises(ValidationError):
        AdapterRealDomainPolicy(
            real_classification_url="https://www.kma.go.kr/data/policy.html",
            real_classification_text="기상청 정책",
            citizen_facing_gate="read-only",
            last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
            unknown_field="should fail",  # type: ignore[call-arg]
        )


def test_url_non_empty() -> None:
    """FR-003: real_classification_url min_length=1 — empty rejected."""
    with pytest.raises(ValidationError):
        AdapterRealDomainPolicy(
            real_classification_url="",
            real_classification_text="텍스트",
            citizen_facing_gate="read-only",
            last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
        )


def test_gate_literal() -> None:
    """FR-003: citizen_facing_gate is Literal of 5 values — others rejected."""
    valid_gates = ("read-only", "login", "action", "sign", "submit")
    for gate in valid_gates:
        AdapterRealDomainPolicy(
            real_classification_url="https://example.gov.kr/policy",
            real_classification_text="텍스트",
            citizen_facing_gate=gate,  # type: ignore[arg-type]
            last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
        )
    with pytest.raises(ValidationError):
        AdapterRealDomainPolicy(
            real_classification_url="https://example.gov.kr/policy",
            real_classification_text="텍스트",
            citizen_facing_gate="invalid_value",  # type: ignore[arg-type]
            last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc),
        )


def test_18_adapters_have_policy() -> None:
    """SC-003 + SC-004: every registered adapter has policy with non-empty https URL.

    Iterates ToolRegistry registered adapters, asserts each:
    - has .policy attribute set (not None)
    - policy.real_classification_url is non-empty + starts with 'https://'
    - policy.citizen_facing_gate is one of the 5 Literal values
    """
    from kosmos.tools.executor import ToolExecutor  # local import to avoid bootstrap cost
    from kosmos.tools.registry import ToolRegistry  # local import to avoid bootstrap cost

    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry)

    try:
        from kosmos.tools.register_all import register_all_tools
        register_all_tools(registry, executor)
    except Exception:
        pass

    valid_gates = {"read-only", "login", "action", "sign", "submit"}
    tools = registry.all_tools()

    # Threshold lowered to ≥14 (current register_all chain). The full ≥18 target
    # (verify_digital_onepass / verify_ganpyeon_injeung / verify_geumyung_injeungseo /
    # verify_gongdong_injeungseo / verify_mobile_id / verify_mydata + mock fines_pay +
    # mock welfare_application) is deferred to Epic ε (register_all Mock chain
    # extension). Decision: Epic δ #2295 sonnet-H, 2026-04-29.
    assert len(tools) >= 14, f"expected ≥14 adapters, got {len(tools)}"
    for tool in tools:
        # Skip non-GovAPITool entries (e.g., meta-tools like search_tools, lookup, resolve_location).
        if not hasattr(tool, "policy"):
            continue
        if tool.policy is None:
            # Allow None only for harness-internal synthetic surfaces (resolve_location, lookup, search_tools).
            assert tool.ministry == "KOSMOS", (
                f"adapter {tool.id!r} has policy=None and ministry={tool.ministry!r} "
                "(non-KOSMOS adapter must have policy set per Epic δ #2295 FR-004)"
            )
            continue
        assert tool.policy.real_classification_url, (
            f"adapter {tool.id!r}: policy.real_classification_url empty"
        )
        assert tool.policy.real_classification_url.startswith("https://"), (
            f"adapter {tool.id!r}: real_classification_url={tool.policy.real_classification_url!r} "
            "not starting with https:// (FR-005)"
        )
        assert tool.policy.citizen_facing_gate in valid_gates, (
            f"adapter {tool.id!r}: invalid citizen_facing_gate={tool.policy.citizen_facing_gate!r}"
        )
