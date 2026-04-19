# SPDX-License-Identifier: Apache-2.0
"""Tests for irreversible-tool auto-pin enforcement and resume-replay survival (T046).

Covers:
- Auto-pin: is_irreversible=True entry is added to pinned_keys on record()
- Auto-pin survives overwrite: re-recording the same key preserves pin
- Pin survives resume replay: simulating session-drop and reload leaves entry intact
- Mixed workload: pinned and non-pinned interleave correctly
"""

from __future__ import annotations

from datetime import UTC, datetime

from kosmos.ipc.tx_cache import (
    ToolCallResponse,
    TransactionLRU,
    TxEntry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION = "sess-irr-pin"


def _entry(
    tx_id: str,
    *,
    session_id: str = SESSION,
    is_irreversible: bool,
    correlation_id: str = "corr-default",
) -> TxEntry:
    resp = ToolCallResponse(tool_id="submit", success=True, data={"ref": "K20260419"})
    return TxEntry(
        session_id=session_id,
        transaction_id=tx_id,
        tool_id="submit",
        is_irreversible=is_irreversible,
        first_seen_ts=datetime(2026, 4, 19, 12, 0, 0, tzinfo=UTC),
        cached_response=resp.to_dict(),
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Auto-pin on record()
# ---------------------------------------------------------------------------


class TestAutoPinOnRecord:
    """T041: is_irreversible=True must add the key to pinned_keys."""

    def test_irreversible_auto_pinned(self) -> None:
        lru = TransactionLRU(capacity=8)
        lru.record(_entry("tx-sub-001", is_irreversible=True))
        assert lru.pinned_count == 1

    def test_reversible_not_pinned(self) -> None:
        lru = TransactionLRU(capacity=8)
        lru.record(_entry("tx-look-001", is_irreversible=False))
        assert lru.pinned_count == 0
        assert lru.size == 1

    def test_multiple_irreversible_all_pinned(self) -> None:
        lru = TransactionLRU(capacity=8)
        tx_ids = [f"tx-irr-{i}" for i in range(5)]
        for tx_id in tx_ids:
            lru.record(_entry(tx_id, is_irreversible=True))
        assert lru.pinned_count == 5
        assert lru.size == 5

    def test_overwrite_preserves_pin(self) -> None:
        """Re-recording an is_irreversible entry must keep it pinned."""
        lru = TransactionLRU(capacity=8)
        lru.record(_entry("tx-sub-001", is_irreversible=True))
        # Overwrite with updated cached_response
        lru.record(_entry("tx-sub-001", is_irreversible=True, correlation_id="corr-v2"))
        assert lru.pinned_count == 1

    def test_overwrite_reversible_entry_stays_unpinned(self) -> None:
        """Re-recording a reversible entry must not accidentally pin it."""
        lru = TransactionLRU(capacity=8)
        lru.record(_entry("tx-rev-001", is_irreversible=False))
        lru.record(_entry("tx-rev-001", is_irreversible=False))
        assert lru.pinned_count == 0

    def test_mixed_irreversible_and_reversible(self) -> None:
        """Only is_irreversible entries appear in pinned_count."""
        lru = TransactionLRU(capacity=16)
        for i in range(4):
            lru.record(_entry(f"tx-irr-{i}", is_irreversible=True))
        for i in range(6):
            lru.record(_entry(f"tx-rev-{i}", is_irreversible=False))
        assert lru.pinned_count == 4
        assert lru.size == 10

    def test_pinned_entry_not_evicted_under_pressure(self) -> None:
        """Irreversible entries survive even when capacity is filled repeatedly."""
        cap = 4
        lru = TransactionLRU(capacity=cap)

        # Record one irreversible (pinned)
        lru.record(_entry("tx-sacred", is_irreversible=True))

        # Flood with reversible entries to trigger eviction pressure
        for i in range(cap * 3):
            lru.record(_entry(f"tx-rev-{i:03d}", is_irreversible=False))

        # Sacred entry must survive all evictions
        assert lru.get(SESSION, "tx-sacred") is not None
        assert lru.pinned_count == 1


# ---------------------------------------------------------------------------
# Pin survives resume replay (T046)
# ---------------------------------------------------------------------------


class TestPinSurvivesResumeReplay:
    """Simulate session-drop and reload: entries replayed from durable storage
    must remain pinned after re-ingestion into a fresh TransactionLRU.

    The TransactionLRU itself is in-memory; persistence is external (out of scope
    for this spec).  This test validates the pattern: serialise → deserialise →
    record() into a new LRU instance → pin is re-established.
    """

    def test_replay_irreversible_entry_repins(self) -> None:
        """After simulated session-drop, re-recording an irreversible entry pins it."""
        # Simulate original recording
        original_lru = TransactionLRU(capacity=8)
        original_entry = _entry("tx-sub-resume", is_irreversible=True)
        original_lru.record(original_entry)

        # Simulate serialisation (only the data dict survives a restart)
        serialised = {
            "session_id": original_entry.session_id,
            "transaction_id": original_entry.transaction_id,
            "tool_id": original_entry.tool_id,
            "is_irreversible": original_entry.is_irreversible,
            "first_seen_ts": original_entry.first_seen_ts,
            "cached_response": original_entry.cached_response,
            "correlation_id": original_entry.correlation_id,
        }

        # Fresh LRU after restart
        fresh_lru = TransactionLRU(capacity=8)
        replayed_entry = TxEntry(**serialised)
        fresh_lru.record(replayed_entry)

        # Pin must be re-established
        assert fresh_lru.pinned_count == 1
        assert fresh_lru.get(SESSION, "tx-sub-resume") is not None

    def test_replay_multiple_sessions(self) -> None:
        """Replay entries from two different sessions; each must be independently pinned."""
        lru = TransactionLRU(capacity=32)

        sessions = ["sess-alpha", "sess-beta"]
        for sess in sessions:
            for i in range(3):
                lru.record(
                    _entry(f"tx-{i}", session_id=sess, is_irreversible=True)
                )

        # 6 irreversible entries total, across 2 sessions
        assert lru.pinned_count == 6

        # Evict manually — all pinned, nothing evicted
        for _ in range(10):
            evicted = lru.evict_oldest_non_pinned()
            assert evicted is False

        # All entries still present
        for sess in sessions:
            for i in range(3):
                assert lru.get(sess, f"tx-{i}") is not None

    def test_resume_replay_idempotency(self) -> None:
        """Re-recording the same irreversible entry twice (idempotent replay) must
        not increase pinned_count."""
        lru = TransactionLRU(capacity=8)
        entry = _entry("tx-idempotent", is_irreversible=True)
        lru.record(entry)
        lru.record(entry)  # duplicate record (resume replay)
        assert lru.pinned_count == 1
        assert lru.size == 1

    def test_cached_response_roundtrip_on_replay(self) -> None:
        """Replayed entry's cached_response must survive from_dict() reconstruction."""
        lru = TransactionLRU(capacity=8)
        lru.record(_entry("tx-sub-rr", is_irreversible=True))

        hit = lru.get(SESSION, "tx-sub-rr")
        assert hit is not None

        # T042: validate that from_dict() can reconstruct
        response = ToolCallResponse.from_dict(hit.cached_response)
        assert response.tool_id == "submit"
        assert response.success is True
        assert response.data == {"ref": "K20260419"}
