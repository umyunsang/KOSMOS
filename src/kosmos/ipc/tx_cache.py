# SPDX-License-Identifier: Apache-2.0
"""TransactionLRU — per-session idempotency LRU cache (Spec 032 T014 / T040-T043).

Prevents double-submission of irreversible civic actions (FR-026..033).
Uses stdlib ``collections.OrderedDict`` — no new runtime deps (SC-008).

Invariants (data-model.md §4.5):
- T1: Key tuple elements are non-empty strings.
- T2: is_irreversible=True entries MUST be in pinned_keys.
- T3: cache size <= capacity + len(pinned_keys) at all times.
- T4: Eviction order: OrderedDict FIFO, skipping pinned_keys.
- T5: cached_response must be JSON-serialisable (pydantic .model_dump() result).

Spec 032 T040-T043 additions:
- ``ToolCallResponse`` — lightweight response envelope for cached-response
  round-trip (T042, contract §2.5).
- ``TxDedupAuditEvent`` — lightweight audit event emitted on every dispatch
  (hit AND miss), coupling Spec 024 audit intent (T043, contract §2.7).
  The full ``ToolCallAuditRecord`` (with Merkle hashes) is constructed by the
  outer executor; this event carries the dedup status so the executor knows
  whether to write status="ok"|"error" (miss) or status="dedup_hit" (hit).
- ``ToolExecutorDispatch`` — Stripe 3-step dispatcher:
  lookup → execute on miss → record+pin for irreversible (T040).
  Sets OTEL span attribute ``kosmos.ipc.tx.cache_state`` (FR-033, T040).
"""

from __future__ import annotations

import logging
import os
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from opentelemetry import trace

from kosmos.ipc.otel_constants import (
    KOSMOS_IPC_CORRELATION_ID,
    KOSMOS_IPC_TRANSACTION_ID,
    KOSMOS_IPC_TX_CACHE_STATE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------

_DEFAULT_CAPACITY: int = int(os.environ.get("KOSMOS_IPC_TX_CACHE_CAPACITY", "512"))

# ---------------------------------------------------------------------------
# ToolCallResponse — cached response envelope (T042)
# ---------------------------------------------------------------------------


@dataclass
class ToolCallResponse:
    """Lightweight response envelope stored in the tx cache.

    Designed for JSON-safe round-trip:
    - Stored via ``model_dump(mode="json")`` equivalent (``to_dict()``).
    - Replayed via ``from_dict()`` which validates field presence.

    For Pydantic-modelled responses from the actual tool executor, callers
    SHOULD use the tool's own output model for the round-trip; this class
    is the *IPC-layer* carrier that the cache understands.
    """

    tool_id: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict (T5: JSON-serialisable)."""
        return {
            "tool_id": self.tool_id,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "error_type": self.error_type,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolCallResponse:
        """Reconstruct from a cached dict (validate on read, contract §2.5).

        Raises ``ValueError`` if required fields are absent or malformed.
        """
        if "tool_id" not in data or "success" not in data:
            raise ValueError(
                "ToolCallResponse.from_dict: required fields 'tool_id' and 'success' missing"
            )
        return cls(
            tool_id=data["tool_id"],
            success=bool(data["success"]),
            data=data.get("data"),
            error=data.get("error"),
            error_type=data.get("error_type"),
        )


# ---------------------------------------------------------------------------
# TxDedupAuditEvent — lightweight audit coupling (T043)
# ---------------------------------------------------------------------------

TxAuditStatus = Literal["ok", "error", "dedup_hit"]


@dataclass(frozen=True)
class TxDedupAuditEvent:
    """Lightweight dedup-decision audit event (Spec 032 T043, contract §2.7).

    Emitted by ``ToolExecutorDispatch`` on EVERY irreversible tool dispatch —
    both cache hits and misses. The outer ``ToolExecutor`` layer MUST consume
    this event to write the full ``ToolCallAuditRecord`` (Spec 024), supplying
    the Merkle hashes and session context that only the executor possesses.

    Fields
    ------
    session_id : str
        Session scope.
    transaction_id : str
        UUIDv7 of the action.
    tool_id : str
        Adapter identifier.
    correlation_id : str
        Originating request correlation id.
    status : TxAuditStatus
        ``"ok"``      — first execution, completed successfully (cache miss → success).
        ``"error"``   — first execution, tool call failed (cache miss → failure).
        ``"dedup_hit"`` — duplicate submit; cached response returned without execution.
    original_correlation_id : str | None
        For ``"dedup_hit"`` only: the ``correlation_id`` of the ORIGINAL first
        execution. Enables audit join: hit row references miss row (FR-030).
    ts : datetime
        UTC timestamp of the dedup decision.
    """

    session_id: str
    transaction_id: str
    tool_id: str
    correlation_id: str
    status: TxAuditStatus
    original_correlation_id: str | None
    ts: datetime


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
        Adapter identifier (e.g. ``gov24_apply_submit``).
    is_irreversible : bool
        If True, entry is pinned (never evicted, T2).
    first_seen_ts : datetime
        Write time (UTC).
    cached_response : dict[str, Any]
        Serialised tool response for dedup replay (T5: JSON-serialisable).
        Store via ``ToolCallResponse.to_dict()``; replay via
        ``ToolCallResponse.from_dict()``.
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
    # Write operations (T041: pin enforcement on is_irreversible=True)
    # ------------------------------------------------------------------

    def record(self, entry: TxEntry) -> None:
        """Insert *entry* into the cache.

        Auto-pins if ``entry.is_irreversible=True`` (T2, T041).
        Evicts the oldest non-pinned entry when capacity is exceeded (T3, T4).
        """
        key = (entry.session_id, entry.transaction_id)

        # Overwrite if already present (e.g., update cached_response)
        if key in self._cache:
            self._cache[key] = entry
            if entry.is_irreversible:
                self._pinned_keys.add(key)  # T041: irreversible => always pinned
            logger.debug(
                "tx_cache.record.overwrite",
                extra={"session_id": entry.session_id, "transaction_id": entry.transaction_id},
            )
            return

        # Auto-pin irreversible entries (T2, T041)
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
# ToolExecutorDispatch — Stripe 3-step integration (T040)
# ---------------------------------------------------------------------------


@dataclass
class DispatchResult:
    """Result of a ``ToolExecutorDispatch.dispatch()`` call.

    Attributes
    ----------
    response : ToolCallResponse
        The tool response (either freshly executed or replayed from cache).
    cache_state : Literal["hit", "miss", "bypass"]
        - ``"miss"``   — tool was executed; result stored in cache.
        - ``"hit"``    — duplicate tx_id; cached result returned.
        - ``"bypass"`` — tool is reversible (is_irreversible=False); cache not used.
    audit_event : TxDedupAuditEvent | None
        Populated for irreversible tools (hit + miss). None for bypass.
    """

    response: ToolCallResponse
    cache_state: Literal["hit", "miss", "bypass"]
    audit_event: TxDedupAuditEvent | None


# Type alias for the executor callable injected into ToolExecutorDispatch.
# Signature: (tool_id, params, session_id, correlation_id) -> ToolCallResponse
ToolExecutorFn = Callable[
    [str, dict[str, Any], str, str],
    ToolCallResponse,
]


class ToolExecutorDispatch:
    """Stripe 3-step idempotency dispatcher (Spec 032 T040, contract §2.2).

    Integrates ``TransactionLRU`` into the tool execution path:

    Step 1 — Lookup: check the LRU cache for ``(session_id, transaction_id)``.
    Step 2 — Execute on miss: call the underlying ``executor_fn``.
    Step 3 — Record + pin: store the result and auto-pin if irreversible.

    OTEL span attributes are set on the current span (FR-033):
    - ``kosmos.ipc.tx.cache_state`` = ``"hit"`` | ``"miss"`` | ``"bypass"``
    - ``kosmos.ipc.transaction_id`` (when present)
    - ``kosmos.ipc.correlation_id`` (always)

    For reversible tools (``is_irreversible=False``) the cache is bypassed
    entirely — ``transaction_id=None`` is the signal (FR-032).

    Audit coupling (T043): a ``TxDedupAuditEvent`` is returned in
    ``DispatchResult.audit_event`` for every irreversible call. The outer
    ``ToolExecutor`` MUST use this to write a ``ToolCallAuditRecord``
    (Spec 024) so that PIPA §26 safeguard audit trail is complete.
    """

    def __init__(
        self,
        lru: TransactionLRU,
        executor_fn: ToolExecutorFn,
    ) -> None:
        self._lru = lru
        self._executor_fn = executor_fn

    def dispatch(
        self,
        *,
        tool_id: str,
        params: dict[str, Any],
        session_id: str,
        correlation_id: str,
        transaction_id: str | None,
        is_irreversible: bool,
    ) -> DispatchResult:
        """Execute a tool call with idempotency semantics.

        Parameters
        ----------
        tool_id : str
            Adapter identifier.
        params : dict[str, Any]
            Tool invocation parameters.
        session_id : str
            Session scope for dedup keying (FR-030).
        correlation_id : str
            Request correlation id for OTEL and audit.
        transaction_id : str | None
            UUIDv7 idempotency key. Must be non-None for irreversible tools.
            ``None`` bypasses the cache (FR-032).
        is_irreversible : bool
            Whether the tool produces a non-undoable side effect (Spec 024
            ``AdapterRegistration.is_irreversible``).

        Returns
        -------
        DispatchResult
            Contains the response, cache_state, and audit_event.

        Raises
        ------
        ValueError
            If ``is_irreversible=True`` but ``transaction_id`` is None.
        """
        span = trace.get_current_span()

        # Promote correlation_id to OTEL span (always)
        span.set_attribute(KOSMOS_IPC_CORRELATION_ID, correlation_id)

        # FR-032: reversible tool — bypass cache entirely
        if not is_irreversible or transaction_id is None:
            if is_irreversible and transaction_id is None:
                raise ValueError(
                    f"dispatch: is_irreversible=True requires a non-None transaction_id "
                    f"(tool_id={tool_id!r}, session_id={session_id!r})"
                )
            span.set_attribute(KOSMOS_IPC_TX_CACHE_STATE, "bypass")
            logger.debug(
                "tx_cache.dispatch.bypass",
                extra={"tool_id": tool_id, "session_id": session_id},
            )
            response = self._executor_fn(tool_id, params, session_id, correlation_id)
            return DispatchResult(
                response=response,
                cache_state="bypass",
                audit_event=None,
            )

        # Promote transaction_id to OTEL span
        span.set_attribute(KOSMOS_IPC_TRANSACTION_ID, transaction_id)

        # Step 1: Lookup (contract §2.2)
        hit = self._lru.get(session_id, transaction_id)
        if hit is not None:
            # Cache HIT — return stored response without executing (FR-027)
            span.set_attribute(KOSMOS_IPC_TX_CACHE_STATE, "hit")
            logger.info(
                "tx_cache.dispatch.hit",
                extra={
                    "tool_id": tool_id,
                    "session_id": session_id,
                    "transaction_id": transaction_id,
                    "original_correlation_id": hit.correlation_id,
                },
            )
            # T042: reconstruct response via from_dict (validate-on-read, contract §2.5)
            try:
                cached_response = ToolCallResponse.from_dict(hit.cached_response)
            except (ValueError, KeyError) as exc:
                logger.error(
                    "tx_cache.dispatch.cached_response_corrupt",
                    extra={
                        "error": str(exc),
                        "transaction_id": transaction_id,
                    },
                )
                # Fail-closed: treat corrupted cache as a miss
                cached_response = None

            if cached_response is None:
                # Fall through to re-execute on corrupt cache
                span.set_attribute(KOSMOS_IPC_TX_CACHE_STATE, "miss")
            else:
                # T043: emit dedup_hit audit event (contract §2.7)
                audit_event = TxDedupAuditEvent(
                    session_id=session_id,
                    transaction_id=transaction_id,
                    tool_id=tool_id,
                    correlation_id=correlation_id,
                    status="dedup_hit",
                    original_correlation_id=hit.correlation_id,  # FR-030 reference
                    ts=datetime.now(UTC),
                )
                logger.info(
                    "tx_cache.audit.dedup_hit",
                    extra={
                        "session_id": session_id,
                        "transaction_id": transaction_id,
                        "original_correlation_id": hit.correlation_id,
                        "status": "dedup_hit",
                    },
                )
                return DispatchResult(
                    response=cached_response,
                    cache_state="hit",
                    audit_event=audit_event,
                )

        # Step 2: Execute on miss (contract §2.2)
        span.set_attribute(KOSMOS_IPC_TX_CACHE_STATE, "miss")
        logger.debug(
            "tx_cache.dispatch.miss",
            extra={
                "tool_id": tool_id,
                "session_id": session_id,
                "transaction_id": transaction_id,
            },
        )
        response = self._executor_fn(tool_id, params, session_id, correlation_id)

        # FR-031: only cache on success (errors might yield different results on retry)
        # Exception: is_irreversible + error → block retries (store error marker)
        if response.success:
            # Step 3: Record + pin for irreversible (T041, contract §2.2)
            entry = TxEntry(
                session_id=session_id,
                transaction_id=transaction_id,
                tool_id=tool_id,
                is_irreversible=is_irreversible,
                first_seen_ts=datetime.now(UTC),
                # T042: store via to_dict() (contract §2.5)
                cached_response=response.to_dict(),
                correlation_id=correlation_id,
            )
            self._lru.record(entry)  # auto-pins if is_irreversible=True (T041)
            audit_status: TxAuditStatus = "ok"
        else:
            # Error on irreversible: do NOT cache result (FR-031)
            # The absence from cache means re-execution will be attempted.
            # (For true irreversible 500s, upstream retry-confirmation is the
            # operator's responsibility; deferred per spec §6.)
            audit_status = "error"

        # T043: emit miss-path audit event (contract §2.7)
        audit_event = TxDedupAuditEvent(
            session_id=session_id,
            transaction_id=transaction_id,
            tool_id=tool_id,
            correlation_id=correlation_id,
            status=audit_status,
            original_correlation_id=None,  # this IS the original
            ts=datetime.now(UTC),
        )
        logger.info(
            "tx_cache.audit.miss",
            extra={
                "session_id": session_id,
                "transaction_id": transaction_id,
                "status": audit_status,
            },
        )
        return DispatchResult(
            response=response,
            cache_state="miss",
            audit_event=audit_event,
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
    "TxDedupAuditEvent",
    "TxAuditStatus",
    "ToolCallResponse",
    "DispatchResult",
    "ToolExecutorDispatch",
    "ToolExecutorFn",
    "TransactionLRU",
    "get_global_tx_lru",
]
