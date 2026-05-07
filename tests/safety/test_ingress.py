# SPDX-License-Identifier: Apache-2.0
"""Ingress safety regression tests for structured public-API tool outputs."""

from __future__ import annotations

from ummaya.safety._ingress import apply_ingress_safety
from ummaya.safety._settings import SafetySettings


def test_ingress_preserves_koroad_coordinate_strings() -> None:
    """KOROAD coordinate strings are public geo fields, not phone numbers."""
    raw = {
        "kind": "collection",
        "items": [
            {
                "spot_nm": "서울 강남구 논현동(신사역교차로 부근)",
                "lo_crd": "127.019851372856",
                "la_crd": "37.516259723692",
            }
        ],
    }

    sanitized, event = apply_ingress_safety(
        raw,
        SafetySettings(redact_tool_output=True, injection_detector_enabled=True),
    )

    assert sanitized is raw
    assert event is None
    assert sanitized["items"][0]["lo_crd"] == "127.019851372856"


def test_ingress_still_redacts_standalone_korean_mobile_phone() -> None:
    raw = {
        "kind": "record",
        "item": {
            "lo_crd": "127.019851372856",
            "contact": "담당자 휴대전화 010-1234-5678",
        },
    }

    sanitized, event = apply_ingress_safety(
        raw,
        SafetySettings(redact_tool_output=True, injection_detector_enabled=True),
    )

    assert event is not None
    assert sanitized is not None
    assert sanitized["item"]["lo_crd"] == "127.019851372856"
    assert sanitized["item"]["contact"] == "담당자 휴대전화 <PHONE_KR>"
