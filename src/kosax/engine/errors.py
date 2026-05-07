# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the KOSAX Query Engine module."""

from __future__ import annotations


class KosaxEngineError(Exception):
    """Base exception for the KOSAX Query Engine module."""


class BudgetExhaustedError(KosaxEngineError):
    """Raised when session budget (tokens or turns) is exhausted."""


class MaxIterationsError(KosaxEngineError):
    """Raised when per-turn iteration limit is reached."""


class QueryCancelledError(KosaxEngineError):
    """Raised when the caller cancels the query (breaks async for)."""
