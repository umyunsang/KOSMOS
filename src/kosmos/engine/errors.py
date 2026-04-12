# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for the KOSMOS Query Engine module."""

from __future__ import annotations


class KosmosEngineError(Exception):
    """Base exception for the KOSMOS Query Engine module."""


class BudgetExhaustedError(KosmosEngineError):
    """Raised when session budget (tokens or turns) is exhausted."""


class MaxIterationsError(KosmosEngineError):
    """Raised when per-turn iteration limit is reached."""


class QueryCancelledError(KosmosEngineError):
    """Raised when the caller cancels the query (breaks async for)."""
