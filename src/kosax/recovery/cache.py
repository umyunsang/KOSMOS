# SPDX-License-Identifier: Apache-2.0
"""Response cache for tool adapter results.

Provides a bounded LRU in-memory cache keyed on (tool_id, sha256(arguments)).
A TTL of 0 means "no caching" (fail-closed default per Constitution § II).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_MAX_ENTRIES: int = 256


class CacheEntry(BaseModel):
    """A single cached response entry."""

    model_config = ConfigDict(frozen=True)

    tool_id: str
    """Identifier of the tool whose response is cached."""

    arguments_hash: str
    """SHA-256 hex digest of the serialized input arguments."""

    data: dict[str, object]
    """The cached response data."""

    cached_at: float
    """Monotonic clock value (time.monotonic()) at which the entry was stored.

    This is *not* a wall-clock Unix timestamp; comparisons must use
    time.monotonic() as the reference.
    """

    ttl_seconds: int
    """Cache lifetime in seconds; 0 means this entry should never be used."""


class ResponseCache:
    """Bounded LRU in-memory cache for tool responses.

    Uses collections.OrderedDict to implement LRU eviction:
    - On every get hit the entry is moved to the end (most-recent).
    - On put when the cache is full the front entry (least-recent) is evicted.
    """

    def __init__(self, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        self._max = max_entries
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_hash(self, arguments: dict[str, object]) -> str:
        """Compute a deterministic SHA-256 hash of *arguments*.

        Keys are sorted to ensure hash stability regardless of insertion order.

        Args:
            arguments: Arbitrary JSON-serialisable dict of tool arguments.

        Returns:
            Lowercase hex-encoded SHA-256 digest.
        """
        serialized = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(serialized.encode()).hexdigest()

    def get(self, tool_id: str, arguments_hash: str) -> dict[str, object] | None:
        """Retrieve a cached response if it exists and has not expired.

        Expired entries are **not** deleted so that ``get_stale()`` can still
        return them as a fallback after a failed live API call.  LRU eviction
        in ``put()`` naturally reclaims capacity over time.

        Args:
            tool_id: Tool identifier.
            arguments_hash: SHA-256 hash of the arguments (from compute_hash).

        Returns:
            The cached data dict, or None if missing or expired.
        """
        key = self._make_key(tool_id, arguments_hash)
        entry = self._store.get(key)
        if entry is None:
            return None

        if entry.ttl_seconds == 0:
            # Should not be stored but guard defensively
            return None

        age = time.monotonic() - entry.cached_at
        if age > entry.ttl_seconds:
            logger.debug("Cache entry expired for tool=%s (age=%.1fs)", tool_id, age)
            return None

        # Move to end (most-recently used)
        self._store.move_to_end(key)
        logger.debug("Cache hit for tool=%s (age=%.1fs)", tool_id, age)
        return dict(entry.data)

    def get_stale(self, tool_id: str, arguments_hash: str) -> dict[str, object] | None:
        """Retrieve a cached response regardless of expiry, without deleting it.

        This method is intended for the stale-cache fallback path: when a live
        API call has failed, an expired entry is still better than no data.
        Unlike get(), this method does **not** delete the entry if it has
        expired, so the stale data remains available for subsequent fallback
        calls within the same session.

        Args:
            tool_id: Tool identifier.
            arguments_hash: SHA-256 hash of the arguments (from compute_hash).

        Returns:
            The cached data dict (fresh or stale), or None if no entry
            exists or the TTL is 0.
        """
        key = self._make_key(tool_id, arguments_hash)
        entry = self._store.get(key)
        if entry is None or entry.ttl_seconds == 0:
            return None
        age = time.monotonic() - entry.cached_at
        logger.debug(
            "Stale cache read for tool=%s (age=%.1fs, ttl=%ds)",
            tool_id,
            age,
            entry.ttl_seconds,
        )
        return dict(entry.data)

    def put(
        self,
        tool_id: str,
        arguments_hash: str,
        data: dict[str, object],
        ttl_seconds: int,
    ) -> None:
        """Store a response in the cache.

        Entries with ttl_seconds=0 are silently discarded (fail-closed).

        Args:
            tool_id: Tool identifier.
            arguments_hash: SHA-256 hash of the arguments.
            data: Response data to cache.
            ttl_seconds: Lifetime in seconds; 0 disables caching.
        """
        if ttl_seconds == 0:
            return  # fail-closed: do not cache when TTL is 0

        key = self._make_key(tool_id, arguments_hash)
        entry = CacheEntry(
            tool_id=tool_id,
            arguments_hash=arguments_hash,
            data=data,
            cached_at=time.monotonic(),
            ttl_seconds=ttl_seconds,
        )
        self._store[key] = entry
        self._store.move_to_end(key)

        # Evict LRU entries if over capacity
        while len(self._store) > self._max:
            evicted_key, _ = self._store.popitem(last=False)
            logger.debug("Cache LRU eviction: %s", evicted_key)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_key(tool_id: str, arguments_hash: str) -> str:
        return f"{tool_id}:{arguments_hash}"
