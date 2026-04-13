# SPDX-License-Identifier: Apache-2.0
"""File-based persistent response cache for tool adapter results.

Complements the in-memory ``ResponseCache`` with cross-session persistence.
Entries are stored as JSON files under ``~/.kosmos/cache/<tool_id>/``.

Design decisions:
- ``asyncio.to_thread()`` for all file I/O — no new dependencies.
- Graceful degradation: any filesystem failure logs a warning and continues
  without caching (fail-open for the persistence layer; fail-closed is
  already enforced by the caller via TTL=0 checks).
- LRU eviction is performed by comparing ``cached_at`` timestamps when the
  total entry count exceeds ``max_entries``.
- Keys are the SHA-256 hash of ``(tool_id, sorted_params)`` — identical to
  the in-memory cache key scheme to allow future unification.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import time
from pathlib import Path

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR: Path = Path.home() / ".kosmos" / "cache"
_DEFAULT_MAX_ENTRIES: int = 1024


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


class PersistentCacheEntry(BaseModel):
    """Serialisable cache entry stored as a JSON file on disk."""

    model_config = ConfigDict(frozen=True)

    tool_id: str
    """Identifier of the tool whose response is cached."""

    key: str
    """Cache key (SHA-256 hex digest)."""

    data: dict[str, object]
    """The cached response payload."""

    cached_at: float
    """Unix wall-clock timestamp (time.time()) at which the entry was stored."""

    ttl_seconds: int
    """Cache lifetime in seconds; 0 means do not cache."""


# ---------------------------------------------------------------------------
# Persistent cache
# ---------------------------------------------------------------------------


class PersistentResponseCache:
    """File-based LRU response cache.

    One JSON file per cache entry, named ``<key>.json`` under
    ``<cache_dir>/<tool_id>/``.

    Thread/coroutine safety: all I/O is dispatched to a thread pool via
    ``asyncio.to_thread()``.  Concurrent put/get calls on the same key may
    race on the underlying files but will not corrupt data — the worst case
    is a redundant write or a stale read, both acceptable for a best-effort
    cache.
    """

    def __init__(
        self,
        cache_dir: Path | None = None,
        max_entries: int = _DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        self._max_entries = max_entries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def compute_key(tool_id: str, params: dict[str, object]) -> str:
        """Compute a deterministic SHA-256 cache key.

        Args:
            tool_id: Stable snake_case tool identifier.
            params: JSON-serialisable dict of tool arguments.

        Returns:
            Lowercase hex-encoded SHA-256 digest.
        """
        payload = json.dumps({"tool_id": tool_id, **params}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode()).hexdigest()

    async def get(self, key: str) -> PersistentCacheEntry | None:
        """Retrieve a cache entry if it exists and has not expired.

        Args:
            key: Cache key from ``compute_key()``.

        Returns:
            ``PersistentCacheEntry`` if present and fresh; ``None`` otherwise.
        """
        try:
            entry = await asyncio.to_thread(self._read_entry, key)
        except Exception:  # noqa: BLE001
            logger.warning("Persistent cache read failed for key %s", key, exc_info=True)
            return None

        if entry is None:
            return None

        age = time.time() - entry.cached_at
        if age > entry.ttl_seconds:
            logger.debug("Persistent cache entry expired for key=%s (age=%.1fs)", key, age)
            return None

        logger.debug("Persistent cache hit for key=%s (age=%.1fs)", key, age)
        return entry

    async def put(self, key: str, value: dict[str, object], ttl: int, tool_id: str = "") -> None:
        """Store a response in the persistent cache.

        Silently skips writes when ``ttl == 0``.  After a successful write,
        triggers LRU eviction if the total entry count exceeds ``max_entries``.

        Args:
            key: Cache key from ``compute_key()``.
            value: Response payload to store.
            ttl: Time-to-live in seconds; 0 disables caching.
            tool_id: Tool identifier used to organise entries in subdirectories.
        """
        if ttl == 0:
            return

        entry = PersistentCacheEntry(
            tool_id=tool_id,
            key=key,
            data=value,
            cached_at=time.time(),
            ttl_seconds=ttl,
        )
        try:
            await asyncio.to_thread(self._write_entry, key, tool_id, entry)
        except Exception:  # noqa: BLE001
            logger.warning("Persistent cache write failed for key %s", key, exc_info=True)
            return

        # Evict if over capacity (best-effort; failures are non-fatal)
        try:
            total = await asyncio.to_thread(self._count_entries)
            if total > self._max_entries:
                await asyncio.to_thread(self._evict_lru, total - self._max_entries)
        except Exception:  # noqa: BLE001
            logger.warning("Persistent cache eviction failed", exc_info=True)

    async def evict_expired(self) -> int:
        """Remove all expired entries from the cache directory.

        Returns:
            Number of entries removed.
        """
        try:
            return await asyncio.to_thread(self._do_evict_expired)
        except Exception:  # noqa: BLE001
            logger.warning("Persistent cache evict_expired failed", exc_info=True)
            return 0

    async def clear(self) -> None:
        """Remove all cache entries from the cache directory."""
        try:
            await asyncio.to_thread(self._do_clear)
        except Exception:  # noqa: BLE001
            logger.warning("Persistent cache clear failed", exc_info=True)

    # ------------------------------------------------------------------
    # Synchronous helpers (run inside asyncio.to_thread)
    # ------------------------------------------------------------------

    def _entry_path(self, key: str, tool_id: str = "") -> Path:
        """Return the filesystem path for *key*.

        Entries are placed under ``<cache_dir>/<tool_id>/`` when tool_id is
        provided, or directly under ``<cache_dir>/`` otherwise.
        """
        if tool_id:
            return self._cache_dir / tool_id / f"{key}.json"
        return self._cache_dir / f"{key}.json"

    def _read_entry(self, key: str) -> PersistentCacheEntry | None:
        """Search for *key* across all sub-directories.

        The tool_id sub-directory is not encoded in the key, so we scan all
        immediate children of ``_cache_dir`` that could contain the file.
        """
        # Direct lookup first (no sub-directory)
        direct = self._cache_dir / f"{key}.json"
        if direct.exists():
            return self._parse_file(direct)

        # Sub-directory scan
        if self._cache_dir.exists():
            for subdir in self._cache_dir.iterdir():
                if subdir.is_dir():
                    candidate = subdir / f"{key}.json"
                    if candidate.exists():
                        return self._parse_file(candidate)

        return None

    def _parse_file(self, path: Path) -> PersistentCacheEntry | None:
        """Parse a JSON cache file and return the entry, or None on error."""
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return PersistentCacheEntry.model_validate(data)
        except Exception:  # noqa: BLE001
            logger.warning("Corrupt or unreadable cache file: %s", path, exc_info=True)
            # Remove corrupt file to prevent repeated parse errors
            with contextlib.suppress(Exception):
                path.unlink(missing_ok=True)
            return None

    def _write_entry(self, key: str, tool_id: str, entry: PersistentCacheEntry) -> None:
        """Write *entry* to disk as a JSON file."""
        path = self._entry_path(key, tool_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            entry.model_dump_json(indent=None),
            encoding="utf-8",
        )

    def _all_entry_paths(self) -> list[Path]:
        """Return all ``*.json`` cache file paths, recursively."""
        if not self._cache_dir.exists():
            return []
        return list(self._cache_dir.rglob("*.json"))

    def _count_entries(self) -> int:
        return len(self._all_entry_paths())

    def _evict_lru(self, count: int) -> None:
        """Remove *count* least-recently cached entries (by ``cached_at``)."""
        all_paths = self._all_entry_paths()
        if not all_paths:
            return

        # Gather (cached_at, path) pairs — skip unreadable files
        timed: list[tuple[float, Path]] = []
        for p in all_paths:
            entry = self._parse_file(p)
            if entry is not None:
                timed.append((entry.cached_at, p))

        # Sort oldest-first
        timed.sort(key=lambda t: t[0])

        for _, path in timed[:count]:
            try:
                path.unlink(missing_ok=True)
                logger.debug("Persistent cache LRU eviction: %s", path)
            except Exception:  # noqa: BLE001
                logger.warning("Could not evict cache file %s", path, exc_info=True)

    def _do_evict_expired(self) -> int:
        """Remove expired entries; return the count removed."""
        now = time.time()
        removed = 0
        for path in self._all_entry_paths():
            entry = self._parse_file(path)
            if entry is None:
                removed += 1  # corrupt file already removed in _parse_file
                continue
            age = now - entry.cached_at
            if age > entry.ttl_seconds:
                try:
                    path.unlink(missing_ok=True)
                    removed += 1
                    logger.debug("Evicted expired cache entry: %s", path)
                except Exception:  # noqa: BLE001
                    logger.warning("Could not evict expired file %s", path, exc_info=True)
        return removed

    def _do_clear(self) -> None:
        """Remove all cache files (but preserve the directory structure)."""
        for path in self._all_entry_paths():
            try:
                path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                logger.warning("Could not remove cache file %s", path, exc_info=True)
