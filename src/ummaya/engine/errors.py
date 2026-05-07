# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the UMMAYA Query Engine module."""

from __future__ import annotations


class UmmayaEngineError(Exception):
    """Base exception for the UMMAYA Query Engine module."""


class BudgetExhaustedError(UmmayaEngineError):
    """Raised when session budget (tokens or turns) is exhausted."""


class MaxIterationsError(UmmayaEngineError):
    """Raised when per-turn iteration limit is reached."""


class QueryCancelledError(UmmayaEngineError):
    """Raised when the caller cancels the query (breaks async for)."""
