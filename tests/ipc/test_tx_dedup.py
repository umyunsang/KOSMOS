# SPDX-License-Identifier: Apache-2.0
"""Tests for ToolExecutorDispatch deduplication semantics (T047).

Required test scenarios per tasks.md T047:
- test_double_submit_hits_cache
- test_cache_state_span_attribute  (asserts kosmos.ipc.tx.cache_state="hit")
- test_distinct_tx_id_no_dedup
- test_reversible_tool_bypasses_cache

Additional coverage:
- Audit event shape on miss (status="ok")
- Audit event shape on hit (status="dedup_hit", original_correlation_id populated)
- Audit event shape on error miss (status="error", not cached)
- FR-031: failed irreversible call is not cached; re-execution is allowed
- FR-032: transaction_id=None forces bypass regardless of is_irreversible
- ValueError raised when is_irreversible=True and transaction_id=None
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from kosmos.ipc.tx_cache import (
    DispatchResult,
    ToolCallResponse,
    ToolExecutorDispatch,
    TransactionLRU,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION = "sess-dedup-test"
TOOL_SUBMIT = "gov24_submit"
TOOL_LOOKUP = "lookup"


def _success_response(tool_id: str = TOOL_SUBMIT) -> ToolCallResponse:
    return ToolCallResponse(
        tool_id=tool_id,
        success=True,
        data={"receipt_no": "K20260419-001"},
    )


def _error_response(tool_id: str = TOOL_SUBMIT) -> ToolCallResponse:
    return ToolCallResponse(
        tool_id=tool_id,
        success=False,
        error="Service temporarily unavailable",
        error_type="ServiceError",
    )


def _make_executor(response: ToolCallResponse) -> MagicMock:
    """Return a mock executor function that always returns *response*."""
    mock = MagicMock(return_value=response)
    return mock


def _dispatch(
    executor_fn: Any,
    *,
    tool_id: str = TOOL_SUBMIT,
    session_id: str = SESSION,
    correlation_id: str = "corr-test-001",
    transaction_id: str | None = "tx-test-001",
    is_irreversible: bool = True,
    lru: TransactionLRU | None = None,
) -> DispatchResult:
    if lru is None:
        lru = TransactionLRU(capacity=512)
    dispatcher = ToolExecutorDispatch(lru=lru, executor_fn=executor_fn)
    return dispatcher.dispatch(
        tool_id=tool_id,
        params={"citizen_id": "test-user"},
        session_id=session_id,
        correlation_id=correlation_id,
        transaction_id=transaction_id,
        is_irreversible=is_irreversible,
    )


# ---------------------------------------------------------------------------
# T047 required tests
# ---------------------------------------------------------------------------


class TestDoubleSubmitHitsCache:
    """test_double_submit_hits_cache — second call with same tx_id returns cached result."""

    def test_double_submit_hits_cache(self) -> None:
        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_success_response())
        dispatcher = ToolExecutorDispatch(lru=lru, executor_fn=executor)

        first = dispatcher.dispatch(
            tool_id=TOOL_SUBMIT,
            params={"citizen_id": "user-1"},
            session_id=SESSION,
            correlation_id="corr-001",
            transaction_id="tx-double-submit",
            is_irreversible=True,
        )
        assert first.cache_state == "miss"
        assert executor.call_count == 1

        # Second call with the same transaction_id
        second = dispatcher.dispatch(
            tool_id=TOOL_SUBMIT,
            params={"citizen_id": "user-1"},
            session_id=SESSION,
            correlation_id="corr-002",  # new correlation_id — same tx_id
            transaction_id="tx-double-submit",
            is_irreversible=True,
        )
        assert second.cache_state == "hit"
        assert executor.call_count == 1  # executor NOT called again

        # Cached response must match first execution
        assert second.response.tool_id == first.response.tool_id
        assert second.response.success is True
        assert second.response.data == {"receipt_no": "K20260419-001"}


class TestCacheStateSpanAttribute:
    """test_cache_state_span_attribute — kosmos.ipc.tx.cache_state is set on OTEL span."""

    def test_miss_sets_span_attribute(self) -> None:
        from unittest.mock import patch

        mock_span = MagicMock()
        with patch("kosmos.ipc.tx_cache.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span

            _dispatch(_make_executor(_success_response()), transaction_id="tx-span-miss")

        # Extract all set_attribute calls
        calls = {call.args[0]: call.args[1] for call in mock_span.set_attribute.call_args_list}
        assert calls.get("kosmos.ipc.tx.cache_state") == "miss"

    def test_hit_sets_span_attribute(self) -> None:
        from unittest.mock import patch

        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_success_response())
        dispatcher = ToolExecutorDispatch(lru=lru, executor_fn=executor)

        # First call: cache miss (populate the cache)
        dispatcher.dispatch(
            tool_id=TOOL_SUBMIT,
            params={},
            session_id=SESSION,
            correlation_id="corr-a",
            transaction_id="tx-span-hit",
            is_irreversible=True,
        )

        # Second call: cache hit — check span attribute
        mock_span = MagicMock()
        with patch("kosmos.ipc.tx_cache.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span

            dispatcher.dispatch(
                tool_id=TOOL_SUBMIT,
                params={},
                session_id=SESSION,
                correlation_id="corr-b",
                transaction_id="tx-span-hit",
                is_irreversible=True,
            )

        calls = {call.args[0]: call.args[1] for call in mock_span.set_attribute.call_args_list}
        assert calls.get("kosmos.ipc.tx.cache_state") == "hit"

    def test_bypass_sets_span_attribute(self) -> None:
        from unittest.mock import patch

        mock_span = MagicMock()
        with patch("kosmos.ipc.tx_cache.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span

            _dispatch(
                _make_executor(_success_response(TOOL_LOOKUP)),
                tool_id=TOOL_LOOKUP,
                is_irreversible=False,
                transaction_id=None,
            )

        calls = {call.args[0]: call.args[1] for call in mock_span.set_attribute.call_args_list}
        assert calls.get("kosmos.ipc.tx.cache_state") == "bypass"


class TestDistinctTxIdNoDedup:
    """test_distinct_tx_id_no_dedup — different tx_ids execute independently."""

    def test_distinct_tx_id_no_dedup(self) -> None:
        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_success_response())
        dispatcher = ToolExecutorDispatch(lru=lru, executor_fn=executor)

        for i in range(5):
            result = dispatcher.dispatch(
                tool_id=TOOL_SUBMIT,
                params={"idx": i},
                session_id=SESSION,
                correlation_id=f"corr-{i}",
                transaction_id=f"tx-distinct-{i:04d}",
                is_irreversible=True,
            )
            assert result.cache_state == "miss"

        assert executor.call_count == 5

    def test_same_tx_id_different_sessions_no_dedup(self) -> None:
        """Same tx_id in different sessions must NOT share the cache (FR-030)."""
        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_success_response())
        dispatcher = ToolExecutorDispatch(lru=lru, executor_fn=executor)

        for sess in ["sess-a", "sess-b"]:
            result = dispatcher.dispatch(
                tool_id=TOOL_SUBMIT,
                params={},
                session_id=sess,
                correlation_id="corr-x",
                transaction_id="tx-shared-id",  # same tx_id, different sessions
                is_irreversible=True,
            )
            assert result.cache_state == "miss"

        assert executor.call_count == 2


class TestReversibleToolBypassesCache:
    """test_reversible_tool_bypasses_cache — reversible tools skip the LRU entirely."""

    def test_reversible_tool_bypasses_cache(self) -> None:
        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_success_response(TOOL_LOOKUP))

        result1 = _dispatch(
            executor,
            tool_id=TOOL_LOOKUP,
            is_irreversible=False,
            transaction_id=None,
            lru=lru,
        )
        assert result1.cache_state == "bypass"
        assert result1.audit_event is None

        # Same call again — executor is called every time (no cache)
        result2 = _dispatch(
            executor,
            tool_id=TOOL_LOOKUP,
            is_irreversible=False,
            transaction_id=None,
            lru=lru,
        )
        assert result2.cache_state == "bypass"
        assert executor.call_count == 2

        # LRU must be empty — nothing was stored
        assert lru.size == 0

    def test_bypass_with_transaction_id_provided(self) -> None:
        """is_irreversible=False bypasses even when transaction_id is given."""
        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_success_response(TOOL_LOOKUP))

        result = _dispatch(
            executor,
            tool_id=TOOL_LOOKUP,
            is_irreversible=False,
            transaction_id="tx-irrelevant",  # ignored for reversible
            lru=lru,
        )
        assert result.cache_state == "bypass"
        assert lru.size == 0


# ---------------------------------------------------------------------------
# Audit event shape
# ---------------------------------------------------------------------------


class TestAuditEventShape:
    """TxDedupAuditEvent must be correctly populated for each path."""

    def test_miss_ok_audit_event(self) -> None:
        result = _dispatch(
            _make_executor(_success_response()),
            correlation_id="corr-miss-ok",
            transaction_id="tx-audit-ok",
        )
        assert result.audit_event is not None
        assert result.audit_event.status == "ok"
        assert result.audit_event.correlation_id == "corr-miss-ok"
        assert result.audit_event.transaction_id == "tx-audit-ok"
        assert result.audit_event.original_correlation_id is None
        assert isinstance(result.audit_event.ts, datetime)

    def test_miss_error_audit_event(self) -> None:
        result = _dispatch(
            _make_executor(_error_response()),
            correlation_id="corr-miss-err",
            transaction_id="tx-audit-err",
        )
        assert result.audit_event is not None
        assert result.audit_event.status == "error"
        assert result.audit_event.original_correlation_id is None

    def test_hit_dedup_audit_event(self) -> None:
        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_success_response())

        # First call (miss)
        first = _dispatch(
            executor,
            correlation_id="corr-original",
            transaction_id="tx-dedup-audit",
            lru=lru,
        )
        assert first.audit_event is not None
        assert first.audit_event.status == "ok"

        # Second call (hit)
        second = _dispatch(
            executor,
            correlation_id="corr-duplicate",
            transaction_id="tx-dedup-audit",
            lru=lru,
        )
        assert second.audit_event is not None
        assert second.audit_event.status == "dedup_hit"
        # FR-030: original_correlation_id must reference first execution
        assert second.audit_event.original_correlation_id == "corr-original"
        assert second.audit_event.correlation_id == "corr-duplicate"

    def test_bypass_has_no_audit_event(self) -> None:
        result = _dispatch(
            _make_executor(_success_response(TOOL_LOOKUP)),
            tool_id=TOOL_LOOKUP,
            is_irreversible=False,
            transaction_id=None,
        )
        assert result.audit_event is None


# ---------------------------------------------------------------------------
# FR-031: errors on irreversible tools are not cached
# ---------------------------------------------------------------------------


class TestFR031ErrorNotCached:
    """Failed irreversible tool calls must NOT be stored in the cache.

    A failed civic submission might succeed on retry; caching the failure would
    permanently block re-execution within the same session.
    """

    def test_error_response_not_cached(self) -> None:
        lru = TransactionLRU(capacity=512)

        # First call: executor returns an error
        executor = _make_executor(_error_response())
        result1 = _dispatch(executor, transaction_id="tx-err-retry", lru=lru)
        assert result1.cache_state == "miss"
        assert result1.response.success is False

        # LRU must be empty — error was not cached
        assert lru.size == 0

        # Second call: now executor returns success
        executor.return_value = _success_response()
        result2 = _dispatch(executor, transaction_id="tx-err-retry", lru=lru)
        assert result2.cache_state == "miss"  # still a miss (first call wasn't cached)
        assert result2.response.success is True
        assert executor.call_count == 2

    def test_error_then_success_audit_trail(self) -> None:
        """Audit events for error miss and subsequent success miss are both emitted."""
        lru = TransactionLRU(capacity=512)
        executor = _make_executor(_error_response())

        r1 = _dispatch(executor, transaction_id="tx-err-audit", lru=lru)
        assert r1.audit_event is not None
        assert r1.audit_event.status == "error"

        executor.return_value = _success_response()
        r2 = _dispatch(executor, transaction_id="tx-err-audit", lru=lru)
        assert r2.audit_event is not None
        assert r2.audit_event.status == "ok"


# ---------------------------------------------------------------------------
# ValueError on is_irreversible=True + transaction_id=None
# ---------------------------------------------------------------------------


class TestInvariantViolation:
    def test_irreversible_without_transaction_id_raises(self) -> None:
        with pytest.raises(ValueError, match="transaction_id"):
            _dispatch(
                _make_executor(_success_response()),
                is_irreversible=True,
                transaction_id=None,
            )
