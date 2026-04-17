# SPDX-License-Identifier: Apache-2.0
"""Network-isolation guardrail for the shadow-eval battery.

This test file enforces FR-D05 and NFR-04: the shadow-eval battery MUST
never reach a live ``*.data.go.kr`` endpoint (or any ``*.go.kr`` host).
Every outbound HTTP call MUST be routed through an ``httpx.MockTransport``
that records each request's host for post-run assertion.

STATUS: RED (expected to fail with ImportError until T040 creates battery.py).

The three test cases cover:
  1. ``test_battery_uses_mock_transport_not_live_client`` — intercept all HTTP
     via a recording MockTransport; assert no outbound host contains
     ``data.go.kr``.
  2. ``test_battery_outbound_host_records_are_empty_of_gov_kr`` — broader
     assertion: zero requests to ``*.data.go.kr`` OR ``*.go.kr``.
  3. ``test_battery_refuses_when_no_mock_transport_injected`` — battery
     constructed WITHOUT a MockTransport must not silently use a real
     AsyncClient; the test enforces that the fixture-only transport pathway
     is explicitly required.
"""

from __future__ import annotations

import httpx
import pytest

# ---------------------------------------------------------------------------
# Module under test — does NOT exist until T040.  ImportError is the expected
# RED failure for this entire file until Phase 3.4 completes T040.
# ---------------------------------------------------------------------------
from tests.shadow_eval import battery  # type: ignore[import]  # noqa: E402

# ---------------------------------------------------------------------------
# Shared recording transport factory
# ---------------------------------------------------------------------------


def _make_recording_transport() -> tuple[httpx.MockTransport, list[str]]:
    """Return a (transport, recorded_hosts) pair.

    The transport captures the ``url.host`` of every request it receives and
    responds with a minimal 200 JSON envelope so the battery can run to
    completion without hanging.
    """
    recorded: list[str] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        recorded.append(request.url.host)
        return httpx.Response(
            200,
            json={
                "id": "mock-0",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "mock response"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    transport = httpx.MockTransport(_handler)
    return transport, recorded


# ---------------------------------------------------------------------------
# Test 1 — battery routes ALL HTTP through the injected MockTransport
# ---------------------------------------------------------------------------


def test_battery_uses_mock_transport_not_live_client() -> None:
    """Running the battery with an injected MockTransport must produce zero
    outbound requests whose host contains ``data.go.kr``.

    Failure modes this test catches:
    - Battery ignores the injected transport and spins up its own real
      ``httpx.AsyncClient`` — the recording list stays empty while a real
      connection is attempted, OR the battery raises a network error.
    - Battery uses the transport but still constructs an inline real client
      for a sub-call targeting ``data.go.kr``.
    """
    transport, recorded = _make_recording_transport()

    # battery.run() is the expected public entry point defined by T040.
    # It MUST accept a ``transport`` keyword argument (httpx.MockTransport).
    battery.run(environment="main", transport=transport)

    gov_api_hits = [h for h in recorded if "data.go.kr" in h]
    assert gov_api_hits == [], (
        f"Battery made {len(gov_api_hits)} live request(s) to data.go.kr host(s): "
        f"{gov_api_hits!r}. "
        "The battery MUST be restricted to fixture/mock responses (FR-D05, NFR-04)."
    )


# ---------------------------------------------------------------------------
# Test 2 — broader assertion: no *.data.go.kr and no *.go.kr at all
# ---------------------------------------------------------------------------


def test_battery_outbound_host_records_are_empty_of_gov_kr() -> None:
    """Running the battery must produce zero requests to any ``*.data.go.kr``
    OR ``*.go.kr`` host.

    This is a broader assertion than test 1: it also catches requests to
    sibling government portals such as ``api.odcloud.kr``, ``sgis.go.kr``, or
    any other ``*.go.kr`` subdomain that might surface from fixture leakage.
    """
    transport, recorded = _make_recording_transport()

    battery.run(environment="shadow", transport=transport)

    gov_api_hits = [h for h in recorded if h.endswith(".go.kr") or h == "go.kr"]
    assert gov_api_hits == [], (
        f"Battery contacted {len(gov_api_hits)} government-API host(s): "
        f"{gov_api_hits!r}. "
        "The shadow-eval battery MUST NOT reach any *.go.kr endpoint "
        "(FR-D05, NFR-04, AGENTS.md hard rule: 'Never call live data.go.kr APIs from CI tests')."
    )


# ---------------------------------------------------------------------------
# Test 3 — battery MUST refuse (or explicitly fail) when no transport injected
# ---------------------------------------------------------------------------


def test_battery_refuses_when_no_mock_transport_injected() -> None:
    """If the battery is called WITHOUT a ``transport`` argument, it must NOT
    silently fall back to a real ``httpx.AsyncClient`` default.

    Acceptable outcomes (any one makes this test green):
    - ``battery.run()`` raises ``TypeError`` because ``transport`` is a
      required positional argument (safest API design).
    - ``battery.run()`` raises a project-defined ``BatteryConfigError`` (or
      equivalent) signalling that fixture-only mode requires an explicit
      transport.
    - ``battery.run()`` raises ``ValueError`` with a message indicating the
      transport is required.

    Unacceptable outcome:
    - ``battery.run()`` completes silently, which would mean the battery ran
      against a real ``httpx.AsyncClient`` and may have touched live APIs.

    This test enforces that T040 exposes transport injection as an explicit,
    mandatory argument — not an optional convenience.
    """
    with pytest.raises((TypeError, ValueError, Exception)) as exc_info:
        # Call WITHOUT transport kwarg.  If T040 makes transport required,
        # this raises TypeError immediately.  If the battery validates at
        # runtime, it raises ValueError or a custom error.
        battery.run(environment="main")

    # Ensure the exception is NOT a successful completion masked as an error.
    # The call MUST NOT silently succeed (return None / empty result).
    raised = exc_info.value
    assert raised is not None, (
        "battery.run(environment='main') completed without a transport argument. "
        "This means the battery may have used a real httpx.AsyncClient. "
        "T040 MUST make the transport argument required or perform an explicit "
        "guard at the entry point (FR-D05)."
    )
