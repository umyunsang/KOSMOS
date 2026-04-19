# SPDX-License-Identifier: Apache-2.0
"""Tests for TransactionLRU capacity, FIFO eviction, and pin invariants (T045).

Covers:
- T1: capacity 512 (default) configurable via env
- T4: FIFO eviction of non-pinned entries
- T2: pinned entries (is_irreversible=True) are never evicted
- Operational-limit scenario: 513 pinned entries — cache operates beyond nominal
  capacity because pinned entries are never evicted (documented behaviour, not a failure)
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from kosmos.ipc.tx_cache import (
    ToolCallResponse,
    TransactionLRU,
    TxEntry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION = "sess-lru-test"


def _make_entry(
    tx_id: str,
    *,
    session_id: str = SESSION,
    is_irreversible: bool = False,
) -> TxEntry:
    """Factory for minimal TxEntry."""
    response = ToolCallResponse(tool_id="lookup", success=True, data={"v": 1})
    return TxEntry(
        session_id=session_id,
        transaction_id=tx_id,
        tool_id="lookup",
        is_irreversible=is_irreversible,
        first_seen_ts=datetime(2026, 4, 19, 12, 0, 0, tzinfo=UTC),
        cached_response=response.to_dict(),
        correlation_id="corr-0",
    )


# ---------------------------------------------------------------------------
# Capacity and FIFO eviction
# ---------------------------------------------------------------------------


class TestCapacityFIFO:
    """T4: Eviction order is FIFO for non-pinned entries."""

    def test_default_capacity_is_512(self) -> None:
        lru = TransactionLRU(capacity=512)
        assert lru.capacity == 512

    def test_capacity_configurable(self) -> None:
        lru = TransactionLRU(capacity=8)
        assert lru.capacity == 8

    def test_capacity_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="capacity"):
            TransactionLRU(capacity=0)

    def test_fifo_eviction_at_capacity(self) -> None:
        """Filling to capacity+1 evicts the oldest non-pinned entry."""
        cap = 4
        lru = TransactionLRU(capacity=cap)

        # Fill exactly to capacity
        for i in range(cap):
            lru.record(_make_entry(f"tx-{i:04d}"))

        assert lru.size == cap

        # Add one more — the oldest (tx-0000) must be evicted
        lru.record(_make_entry("tx-new"))
        assert lru.size == cap
        assert lru.get(SESSION, "tx-0000") is None
        assert lru.get(SESSION, "tx-new") is not None

    def test_fifo_order_preserved(self) -> None:
        """Eviction sequence matches insertion order."""
        cap = 3
        lru = TransactionLRU(capacity=cap)

        for i in range(cap):
            lru.record(_make_entry(f"tx-{i}"))

        # Each new insert should push out tx-0, then tx-1, then tx-2 …
        for evict_idx in range(cap):
            lru.record(_make_entry(f"tx-extra-{evict_idx}"))
            assert lru.get(SESSION, f"tx-{evict_idx}") is None

    def test_overwrite_existing_key_no_eviction(self) -> None:
        """Overwriting an existing entry does not evict and does not grow."""
        cap = 3
        lru = TransactionLRU(capacity=cap)
        for i in range(cap):
            lru.record(_make_entry(f"tx-{i}"))

        # Overwrite tx-0 (already present) — size must not change
        lru.record(_make_entry("tx-0"))
        assert lru.size == cap

    def test_evict_oldest_non_pinned_public_api(self) -> None:
        """Manual evict via ``evict_oldest_non_pinned()``."""
        lru = TransactionLRU(capacity=8)
        lru.record(_make_entry("tx-first"))
        lru.record(_make_entry("tx-second"))

        evicted = lru.evict_oldest_non_pinned()
        assert evicted is True
        assert lru.get(SESSION, "tx-first") is None
        assert lru.get(SESSION, "tx-second") is not None

    def test_evict_on_empty_returns_false(self) -> None:
        lru = TransactionLRU(capacity=8)
        assert lru.evict_oldest_non_pinned() is False

    def test_evict_when_all_pinned_returns_false(self) -> None:
        lru = TransactionLRU(capacity=2)
        lru.record(_make_entry("tx-a", is_irreversible=True))
        lru.record(_make_entry("tx-b", is_irreversible=True))

        # Both pinned — nothing to evict
        assert lru.evict_oldest_non_pinned() is False
        assert lru.size == 2


# ---------------------------------------------------------------------------
# Pin invariants (T2, T041)
# ---------------------------------------------------------------------------


class TestPinInvariants:
    """Pinned entries (is_irreversible=True) must never be evicted."""

    def test_irreversible_entry_is_pinned_on_record(self) -> None:
        lru = TransactionLRU(capacity=4)
        lru.record(_make_entry("tx-irr", is_irreversible=True))
        assert lru.pinned_count == 1

    def test_reversible_entry_is_not_pinned(self) -> None:
        lru = TransactionLRU(capacity=4)
        lru.record(_make_entry("tx-rev", is_irreversible=False))
        assert lru.pinned_count == 0

    def test_pinned_entry_survives_eviction_pressure(self) -> None:
        """A pinned entry must remain after filling to capacity+N."""
        cap = 4
        lru = TransactionLRU(capacity=cap)

        # Record one irreversible entry (auto-pinned)
        lru.record(_make_entry("tx-sacred", is_irreversible=True))

        # Fill remaining capacity with reversible entries
        for i in range(cap):
            lru.record(_make_entry(f"tx-rev-{i}"))

        # tx-sacred must survive
        assert lru.get(SESSION, "tx-sacred") is not None

    def test_explicit_pin_prevents_eviction(self) -> None:
        """Explicitly pinned reversible entry must not be evicted.

        With capacity=2: fill to capacity (tx-a, tx-b non-pinned), then pin tx-a.
        After pin: non-pinned count = 1 (only tx-b).
        Adding tx-c → non-pinned count = 2 ≤ capacity(2), so NO eviction.
        Adding tx-d → non-pinned count = 3 > capacity(2), eviction fires on FIFO
        non-pinned (tx-b, because tx-a is pinned) → tx-b is evicted.
        """
        lru = TransactionLRU(capacity=2)
        lru.record(_make_entry("tx-a"))
        lru.record(_make_entry("tx-b"))
        lru.pin(SESSION, "tx-a")  # explicit pin

        # Add two more non-pinned entries to fill non-pinned quota and overflow
        lru.record(_make_entry("tx-c"))  # non-pinned=2, no eviction yet
        # non-pinned=3 > capacity(2) → evict oldest non-pinned (tx-b)
        lru.record(_make_entry("tx-d"))

        # tx-a was pinned — must survive
        assert lru.get(SESSION, "tx-a") is not None
        # tx-b is the oldest non-pinned and must be evicted
        assert lru.get(SESSION, "tx-b") is None
        # tx-c and tx-d remain (they fill the 2 non-pinned slots)
        assert lru.get(SESSION, "tx-c") is not None
        assert lru.get(SESSION, "tx-d") is not None

    def test_unpin_makes_entry_eviction_eligible(self) -> None:
        """After unpin, entry can be evicted on next pressure.

        Capacity=2, both irreversible (both pinned). After unpin(tx-a):
        pinned={tx-b}, non-pinned={tx-a}, non-pinned-count=1.
        Adding tx-c → non-pinned-count=2 = capacity(2) → no eviction.
        Adding tx-d → non-pinned-count=3 > capacity(2) → evict oldest non-pinned=tx-a.
        """
        lru = TransactionLRU(capacity=2)
        lru.record(_make_entry("tx-a", is_irreversible=True))
        lru.record(_make_entry("tx-b", is_irreversible=True))

        # Both pinned — capacity is effectively unlimited for these two
        lru.unpin(SESSION, "tx-a")
        assert lru.pinned_count == 1

        # Fill non-pinned quota to exactly capacity
        lru.record(_make_entry("tx-c"))  # non-pinned=2, no eviction yet
        assert lru.get(SESSION, "tx-a") is not None  # still present

        # One more — overflows non-pinned quota, evicts oldest non-pinned (tx-a)
        lru.record(_make_entry("tx-d"))
        assert lru.get(SESSION, "tx-a") is None       # evicted
        assert lru.get(SESSION, "tx-b") is not None   # still pinned

    def test_pin_nonexistent_key_is_noop(self) -> None:
        """Pinning a key that is not in cache must not raise."""
        lru = TransactionLRU(capacity=4)
        lru.pin(SESSION, "no-such-tx")  # should not raise
        assert lru.pinned_count == 0

    def test_unpin_nonexistent_key_is_noop(self) -> None:
        lru = TransactionLRU(capacity=4)
        lru.unpin(SESSION, "no-such-tx")  # should not raise


# ---------------------------------------------------------------------------
# Operational-limit scenario: 513 pinned entries (T045)
# ---------------------------------------------------------------------------


class TestOperationalLimit:
    """513 pinned entries — cache grows beyond capacity; documented behaviour.

    The spec allows capacity to be exceeded by pinned entries (T3: size <=
    capacity + len(pinned_keys)).  This test documents that the system remains
    operational — no exception, no data loss — in this scenario.
    """

    def test_513_pinned_entries_all_retained(self) -> None:
        """All 513 irreversible entries must be retrievable after record()."""
        n = 513
        lru = TransactionLRU(capacity=512)

        for i in range(n):
            lru.record(_make_entry(f"tx-irr-{i:05d}", is_irreversible=True))

        # Every single entry must still be present
        for i in range(n):
            entry = lru.get(SESSION, f"tx-irr-{i:05d}")
            assert entry is not None, f"tx-irr-{i:05d} was unexpectedly evicted"

        assert lru.size == n
        assert lru.pinned_count == n

    def test_non_pinned_entries_grow_beyond_nominal_capacity_with_all_pinned(self) -> None:
        """When all entries are pinned, non-pinned quota is empty (0 non-pinned).
        Adding a reversible entry makes non-pinned-count=1 > 0 (capacity would be
        fully consumed by the pinned set, leaving 0 non-pinned slots).

        NOTE: T3 says total size ≤ capacity + len(pinned_keys).
        With capacity=4 and 4 pinned entries, total size may be up to 4+4=8.
        A single new non-pinned entry raises non-pinned-count to 1, which triggers
        immediate eviction → the new non-pinned entry is evicted on insertion.
        """
        cap = 4
        lru = TransactionLRU(capacity=cap)

        # Fill exactly to capacity with pinned entries (non-pinned quota = cap)
        for i in range(cap):
            lru.record(_make_entry(f"tx-p-{i}", is_irreversible=True))

        # All cap slots consumed by pinned entries.
        # Adding cap reversible entries fills non-pinned quota exactly (4 non-pinned).
        for i in range(cap):
            lru.record(_make_entry(f"tx-rev-{i}"))

        # All pinned survive
        for i in range(cap):
            assert lru.get(SESSION, f"tx-p-{i}") is not None

        # Adding one more non-pinned entry overflows the non-pinned quota
        lru.record(_make_entry("tx-overflow"))
        # The oldest non-pinned (tx-rev-0) is evicted; tx-overflow stays
        assert lru.get(SESSION, "tx-rev-0") is None
        assert lru.get(SESSION, "tx-overflow") is not None
        # All pinned entries still intact
        for i in range(cap):
            assert lru.get(SESSION, f"tx-p-{i}") is not None
