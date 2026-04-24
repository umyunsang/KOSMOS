# SPDX-License-Identifier: Apache-2.0
"""T036 — E2E integration test for the ``subscribe`` primitive handle lifecycle.

Verifies:
- subscribe() creates a valid SubscriptionHandle (FR-011, Spec 031 §3).
- The handle has a session-scoped ID and lifetime bounds.
- A ToolCallAuditRecord can be constructed with primitive="subscribe" and the
  resolved tool_id as distinct fields (matching the audit contract exercised by
  T032 per Spec 024 §3).
- Iterating the handle yields typed SubscriptionEvent instances with the correct
  discriminated-union shape (data-model.md §3).

Spec divergences noted inline where the actual subscribe() signature differs from
the data-model.md §3 spec:
- DIVERGENCE-001: The spec describes ``lifetime: timedelta`` but the implementation
  uses ``lifetime_seconds: int`` (SubscribeInput.lifetime_seconds). Tests match
  actual code, not spec shape.
- DIVERGENCE-002: The spec's SubscriptionEvent discriminated union includes only 3
  variants (CbsBroadcastEvent | RestPullTickEvent | RssItemEvent); the implementation
  adds a 4th variant (SubscriptionBackpressureDrop) with kind="subscription_backpressure_drop".
- DIVERGENCE-003: subscribe() does not attach audit-ledger entries internally; the
  harness layer (Spec 024 T032) is responsible for wrapping the call with
  ToolCallAuditRecord. Tests construct the audit record explicitly to verify the
  field contract matches a real subscribe() invocation.

References:
- specs/031-five-primitive-harness/data-model.md §3
- specs/1634-tool-system-wiring/contracts/primitive-envelope.md §5
- src/kosmos/primitives/subscribe.py
- src/kosmos/security/audit.py (ToolCallAuditRecord)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import UTC, datetime

import pytest

from kosmos.primitives._errors import AdapterNotFoundError, SubscriptionBackpressureDrop
from kosmos.primitives.subscribe import (
    CbsBroadcastEvent,
    RssItemEvent,
    SubscribeInput,
    SubscriptionHandle,
    _get_handle_for_testing,
    subscribe,
)
from kosmos.security.audit import ToolCallAuditRecord

# Import mock adapters so their register_subscribe_adapter() side-effects run
from kosmos.tools.mock.cbs.disaster_feed import MOCK_CBS_DISASTER_TOOL
from kosmos.tools.mock.data_go_kr.rss_notices import MOCK_RSS_PUBLIC_NOTICES_TOOL

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_of(data: object) -> str:
    """Return a lowercase hex SHA-256 digest of the canonical JSON of data."""
    raw = json.dumps(data, sort_keys=True, default=str).encode()
    return hashlib.sha256(raw).hexdigest()


def _make_audit_record(
    tool_id: str,
    handle: SubscriptionHandle,
    session_id: str = "sess-test-001",
) -> ToolCallAuditRecord:
    """Construct a minimal valid ToolCallAuditRecord for a subscribe invocation.

    This mirrors the contract described in primitive-envelope.md §5:
    ``handle_id is recorded in the audit ledger as a Spec 024 entry with
    primitive="subscribe"``.

    The actual primitive= field is not part of ToolCallAuditRecord's schema
    (the schema stores tool_id, not a separate "primitive" string). The test
    verifies that tool_id maps 1:1 to the resolved adapter tool_id, which IS
    the primitive discriminator in the audit context.
    """
    input_payload = {"primitive": "subscribe", "tool_id": tool_id}
    output_payload = {"subscription_id": handle.subscription_id}
    return ToolCallAuditRecord(
        record_version="v1",
        tool_id=tool_id,
        adapter_mode="mock",
        session_id=session_id,
        caller_identity="test-citizen-001",
        permission_decision="allow",
        auth_level_presented="public",
        pipa_class="non_personal",
        dpa_reference=None,
        input_hash=_sha256_of(input_payload),
        output_hash=_sha256_of(output_payload),
        sanitized_output_hash=None,
        merkle_covered_hash="output_hash",
        merkle_leaf_id=None,
        timestamp=datetime.now(UTC),
        cost_tokens=0,
        rate_limit_bucket="subscribe-test",
        public_path_marker=False,
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestSubscribeE2E:
    """T036 — subscribe primitive handle lifecycle E2E tests."""

    # ------------------------------------------------------------------
    # TC-01: Handle creation shape (Spec 031 §3)
    # ------------------------------------------------------------------

    async def test_handle_has_subscription_id(self):
        """SubscriptionHandle.subscription_id must be a non-empty UUID string.

        FR-011: subscribe() returns a handle with a bounded lifetime.
        """
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={"burst_count": 1, "burst_delay_seconds": 0.0},
            lifetime_seconds=5,
        )
        handle = await _get_handle_for_testing(inp)

        assert isinstance(handle, SubscriptionHandle)
        assert len(handle.subscription_id) > 0
        # UUID4 canonical form is 36 chars (8-4-4-4-12 with dashes)
        assert len(handle.subscription_id) == 36, (
            f"Expected UUID4 length 36, got {len(handle.subscription_id)}"
        )

    async def test_handle_tool_id_matches_input(self):
        """SubscriptionHandle.tool_id must equal the resolved adapter tool_id."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=10,
        )
        handle = await _get_handle_for_testing(inp)
        assert handle.tool_id == MOCK_CBS_DISASTER_TOOL.tool_id

    async def test_handle_lifetime_bounds(self):
        """closes_at must equal opened_at + lifetime_seconds (FR-011).

        DIVERGENCE-001: spec uses ``lifetime: timedelta``; implementation uses
        ``lifetime_seconds: int``.
        """
        lifetime_seconds = 30
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=lifetime_seconds,
        )
        handle = await _get_handle_for_testing(inp)

        delta = (handle.closes_at - handle.opened_at).total_seconds()
        assert abs(delta - lifetime_seconds) < 1.0, (
            f"closes_at delta {delta:.2f}s should be ~{lifetime_seconds}s"
        )

    async def test_handle_ids_are_unique_across_subscriptions(self):
        """Each subscribe() call must produce a distinct subscription_id."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        handle_a = await _get_handle_for_testing(inp)
        handle_b = await _get_handle_for_testing(inp)
        assert handle_a.subscription_id != handle_b.subscription_id

    # ------------------------------------------------------------------
    # TC-02: Audit ledger compatibility (Spec 024 + primitive-envelope.md §5)
    # ------------------------------------------------------------------

    async def test_audit_record_created_with_subscribe_tool_id(self):
        """ToolCallAuditRecord can be built with the resolved tool_id from subscribe.

        primitive-envelope.md §5: handle_id is recorded in the audit ledger as
        a Spec 024 entry with primitive="subscribe" and the resolved tool_id.

        DIVERGENCE-003: subscribe() itself does not write to the audit ledger;
        the harness layer owns that. This test verifies the audit record contract
        is satisfiable by a subscribe invocation.
        """
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        handle = await _get_handle_for_testing(inp)

        # Must not raise — validates all I1..I5 invariants
        record = _make_audit_record(
            tool_id=handle.tool_id,
            handle=handle,
        )
        assert record.tool_id == MOCK_CBS_DISASTER_TOOL.tool_id
        assert record.adapter_mode == "mock"

    async def test_audit_record_tool_id_equals_resolved_adapter(self):
        """ToolCallAuditRecord.tool_id equals the resolved adapter tool_id, not 'subscribe'.

        The audit contract records the resolved adapter (e.g. 'mock_cbs_disaster_v1'),
        not the primitive verb ('subscribe'). This is the 'distinct fields' requirement
        from primitive-envelope.md §5.
        """
        inp = SubscribeInput(
            tool_id=MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id,
            params={},
            lifetime_seconds=5,
        )
        handle = await _get_handle_for_testing(inp)

        record = _make_audit_record(tool_id=handle.tool_id, handle=handle)
        # Adapter tool_id is distinct from the primitive verb "subscribe"
        assert record.tool_id != "subscribe"
        assert record.tool_id == MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id

    # ------------------------------------------------------------------
    # TC-03: Event iteration — CBS adapter (discriminated union shape)
    # ------------------------------------------------------------------

    async def test_subscribe_yields_cbs_broadcast_events(self):
        """subscribe() must yield CbsBroadcastEvent with correct kind discriminator.

        data-model.md §3: SubscriptionEvent is a discriminated union on ``kind``.
        CbsBroadcastEvent.kind == "cbs_broadcast".

        DIVERGENCE-002: implementation includes a 4th union variant
        (SubscriptionBackpressureDrop) not in the spec union; tests allow it.
        """
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={"burst_count": 2, "burst_delay_seconds": 0.0},
            lifetime_seconds=10,
        )
        events = []
        async with asyncio.timeout(15.0):
            async for event in subscribe(inp):
                if not isinstance(event, SubscriptionBackpressureDrop):
                    events.append(event)
                if len(events) >= 1:
                    break

        assert len(events) >= 1, "subscribe() must yield at least 1 CbsBroadcastEvent"
        first = events[0]
        assert isinstance(first, CbsBroadcastEvent)
        assert first.kind == "cbs_broadcast"

    async def test_cbs_event_shape_matches_spec(self):
        """First CbsBroadcastEvent must have all required fields per data-model.md §3."""
        inp = SubscribeInput(
            tool_id=MOCK_CBS_DISASTER_TOOL.tool_id,
            params={"burst_count": 1, "burst_delay_seconds": 0.0},
            lifetime_seconds=10,
        )
        event: CbsBroadcastEvent | None = None
        async with asyncio.timeout(15.0):
            async for ev in subscribe(inp):
                if isinstance(ev, CbsBroadcastEvent):
                    event = ev
                    break

        assert event is not None, "Expected at least one CbsBroadcastEvent"
        # Required fields per spec §3
        assert event.kind == "cbs_broadcast"
        assert event.cbs_message_id in range(4370, 4386)
        assert isinstance(event.received_at, datetime)
        assert event.received_at.tzinfo is not None, "received_at must be timezone-aware"
        assert len(event.payload_hash) == 64, "payload_hash must be a 64-char hex SHA-256"
        assert event.language in ("ko", "en")
        assert len(event.body) > 0

    # ------------------------------------------------------------------
    # TC-04: Event iteration — RSS adapter
    # ------------------------------------------------------------------

    async def test_subscribe_yields_rss_item_events(self):
        """subscribe() with RSS adapter yields RssItemEvent with kind='rss_item'."""
        inp = SubscribeInput(
            tool_id=MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id,
            params={"item_delay_seconds": 0.0},
            lifetime_seconds=10,
        )
        events = []
        async with asyncio.timeout(15.0):
            async for event in subscribe(inp):
                if isinstance(event, RssItemEvent):
                    events.append(event)
                if len(events) >= 1:
                    break

        assert len(events) >= 1, "subscribe() must yield at least 1 RssItemEvent"
        first = events[0]
        assert first.kind == "rss_item"
        assert len(first.guid) > 0
        assert len(first.title) > 0
        assert first.feed_tool_id == MOCK_RSS_PUBLIC_NOTICES_TOOL.tool_id

    # ------------------------------------------------------------------
    # TC-05: AdapterNotFoundError for unregistered tool_id
    # ------------------------------------------------------------------

    async def test_subscribe_returns_adapter_not_found_for_unknown_tool(self):
        """subscribe() with unknown tool_id returns AdapterNotFoundError synchronously.

        FR from subscribe.py: registry miss surfaces synchronously as
        AdapterNotFoundError, never leaking into the event stream.
        """
        inp = SubscribeInput(
            tool_id="nonexistent_tool_v99",
            params={},
            lifetime_seconds=5,
        )
        result = subscribe(inp)
        assert isinstance(result, AdapterNotFoundError)
        assert result.tool_id == "nonexistent_tool_v99"
        assert result.reason == "adapter_not_found"
