# SPDX-License-Identifier: Apache-2.0
"""TransactionLRU — per-session idempotency LRU cache (Spec 032 T014).

Prevents double-submission of irreversible civic actions (FR-026..033).
Uses stdlib ``collections.OrderedDict`` — no new runtime deps (SC-008).

Invariants (data-model.md §4.5):
- T1: Key tuple elements are non-empty strings.
- T2: is_irreversible=True entries MUST be in pinned_keys.
- T3: cache size <= capacity + len(pinned_keys) at all times.
- T4: Eviction order: OrderedDict FIFO, skipping pinned_keys.
- T5: cached_response must be JSON-serialisable (pydantic .model_dump() result).
"""

from __future__ import annotations

import logging
import os
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

_DEFAULT_CAPACITY: int = int(os.environ.get("KOSMOS_IPC_TX_CACHE_CAPACITY", "512"))

# ---------------------------------------------------------------------------
# TxEntry
# ---------------------------------------------------------------------------


@dataclass
class TxEntry:
    """A single transaction cache entry.

    Fields
    ------
    session_id : str
        Session scope key (T1: non-empty).
    transaction_id : str
        UUIDv7 transaction identifier (T1: non-empty).
    tool_id : str
        Adapter identifier (e.g. ``gov24.apply_submit``).
    is_irreversible : bool
        If True, entry is pinned (never evicted, T2).
    first_seen_ts : datetime
        Write time (UTC).
    cached_response : dict[str, Any]
        Serialised tool response for dedup replay (T5: JSON-serialisable).
    correlation_id : str
        Originating correlation for audit linkage (FR-029).
    """

    session_id: str
    transaction_id: str
    tool_id: str
    is_irreversible: bool
    first_seen_ts: datetime
    cached_response: dict[str, Any]
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.session_id:
            raise ValueError("TxEntry.session_id must be non-empty (T1)")
        if not self.transaction_id:
            raise ValueError("TxEntry.transaction_id must be non-empty (T1)")


# ---------------------------------------------------------------------------
# TransactionLRU
# ---------------------------------------------------------------------------


class TransactionLRU:
    """Process-global LRU cache keyed by ``(session_id, transaction_id)``.

    The cache is normally a module-level singleton, one instance per backend
    process.  For tests, create a fresh instance with a smaller capacity.

    capacity
        Maximum number of non-pinned entries.  Defaults to
        ``KOSMOS_IPC_TX_CACHE_CAPACITY`` (512).
    """

    def __init__(self, capacity: int | None = None) -> None:
        self._capacity: int = capacity if capacity is not None else _DEFAULT_CAPACITY
        if self._capacity < 1:
            raise ValueError("capacity must be >= 1")

        self._cache: OrderedDict[tuple[str, str], TxEntry] = OrderedDict()
        self._pinned_keys: set[tuple[str, str]] = set()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, session_id: str, transaction_id: str) -> TxEntry | None:
        """Look up an entry.  Does NOT touch LRU order (pure lookup).

        Returns None on miss.
        """
        key = (session_id, transaction_id)
        return self._cache.get(key)

    def is_duplicate(self, session_id: str, transaction_id: str) -> bool:
        """Sugar over ``get(..) is not None``."""
        return self.get(session_id, transaction_id) is not None

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def record(self, entry: TxEntry) -> None:
        """Insert *entry* into the cache.

        Auto-pins if ``entry.is_irreversible=True`` (T2).
        Evicts the oldest non-pinned entry when capacity is exceeded (T3, T4).
        """
        key = (entry.session_id, entry.transaction_id)

        # Overwrite if already present (e.g., update cached_response)
        if key in self._cache:
            self._cache[key] = entry
            if entry.is_irreversible:
                self._pinned_keys.add(key)
            logger.debug(
                "tx_cache.record.overwrite",
                extra={"session_id": entry.session_id, "transaction_id": entry.transaction_id},
            )
            return

        # Auto-pin irreversible entries (T2)
        if entry.is_irreversible:
            self._pinned_keys.add(key)

        self._cache[key] = entry

        # Evict oldest non-pinned if over capacity (T3, T4)
        while self._non_pinned_count() > self._capacity:
            self._evict_oldest_non_pinned()

        logger.debug(
            "tx_cache.record",
            extra={
                "session_id": entry.session_id,
                "transaction_id": entry.transaction_id,
                "is_irreversible": entry.is_irreversible,
                "cache_size": len(self._cache),
            },
        )

    def pin(self, session_id: str, transaction_id: str) -> None:
        """Explicitly pin an entry (prevent eviction)."""
        key = (session_id, transaction_id)
        if key in self._cache:
            self._pinned_keys.add(key)

    def unpin(self, session_id: str, transaction_id: str) -> None:
        """Remove pin from an entry (makes it eviction-eligible again)."""
        key = (session_id, transaction_id)
        self._pinned_keys.discard(key)

    def evict_oldest_non_pinned(self) -> bool:
        """Manually evict the oldest non-pinned entry.

        Returns True if an entry was evicted, False if all entries are pinned.
        """
        return self._evict_oldest_non_pinned()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _non_pinned_count(self) -> int:
        return sum(1 for k in self._cache if k not in self._pinned_keys)

    def _evict_oldest_non_pinned(self) -> bool:
        """FIFO eviction of oldest non-pinned entry.  Returns True on success."""
        for key in self._cache:
            if key not in self._pinned_keys:
                evicted = self._cache.pop(key)
                logger.debug(
                    "tx_cache.evict",
                    extra={
                        "session_id": evicted.session_id,
                        "transaction_id": evicted.transaction_id,
                    },
                )
                return True
        return False  # All pinned — nothing to evict

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        """Total entries (pinned + non-pinned)."""
        return len(self._cache)

    @property
    def pinned_count(self) -> int:
        return len(self._pinned_keys)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"TransactionLRU(capacity={self._capacity}, "
            f"size={self.size}, pinned={self.pinned_count})"
        )


# ---------------------------------------------------------------------------
# Module-level singleton (process-global)
# ---------------------------------------------------------------------------

_GLOBAL_TX_LRU: TransactionLRU | None = None


def get_global_tx_lru() -> TransactionLRU:
    """Return the process-global TransactionLRU, creating it on first call."""
    global _GLOBAL_TX_LRU
    if _GLOBAL_TX_LRU is None:
        _GLOBAL_TX_LRU = TransactionLRU()
    return _GLOBAL_TX_LRU


__all__ = [
    "TxEntry",
    "TransactionLRU",
    "get_global_tx_lru",
]
