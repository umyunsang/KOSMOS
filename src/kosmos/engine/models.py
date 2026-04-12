# SPDX-License-Identifier: Apache-2.0
"""Core state models for the KOSMOS Query Engine (Layer 1).

Three model types form the session and per-turn state contract:

- QueryState   — mutable per-session state that accumulates across turns.
                 Implemented as a plain dataclass because Pydantic frozen models
                 cannot be mutated in-place.
- QueryContext — frozen per-turn context assembled at the start of each
                 iteration and discarded when the turn ends.  Holds references
                 to the session infrastructure (LLM client, executor, registry).
- SessionBudget — frozen read-only snapshot of remaining budget, derived from
                  QueryState + QueryEngineConfig via SessionBudget.from_state().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from kosmos.engine.config import QueryEngineConfig
from kosmos.llm.models import ChatMessage
from kosmos.llm.usage import UsageTracker

if TYPE_CHECKING:
    from kosmos.llm.client import LLMClient
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# QueryState
# ---------------------------------------------------------------------------


@dataclass
class QueryState:
    """Mutable per-session state that grows across turns.

    Holds the running message history, turn counter, token usage tracker,
    and a log of tasks resolved during the session.

    The ``usage`` field must be supplied at construction time — there is no
    default because the budget configuration is caller-owned.
    """

    usage: UsageTracker
    """Session-level token usage tracker (caller-supplied, no default)."""

    messages: list[ChatMessage] = field(default_factory=list)
    """Ordered conversation history accumulated across all turns."""

    turn_count: int = 0
    """Number of completed turns in this session."""

    resolved_tasks: list[str] = field(default_factory=list)
    """Human-readable descriptions of tasks resolved during the session."""


# ---------------------------------------------------------------------------
# QueryContext
# ---------------------------------------------------------------------------


class QueryContext(BaseModel):
    """Frozen per-turn context assembled at the start of each iteration.

    Created once per turn, passed through the tool loop, and discarded when
    the turn ends.  Holds references to the session infrastructure objects
    that are shared across iterations within a single turn.

    ``arbitrary_types_allowed`` is required because the infrastructure objects
    (LLMClient, ToolExecutor, ToolRegistry, UsageTracker, QueryState) are not
    Pydantic models.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    state: QueryState
    """Mutable session state shared across all turns."""

    llm_client: LLMClient
    """Async LLM client used to issue completion requests."""

    tool_executor: ToolExecutor
    """Dispatcher that validates and executes tool calls."""

    tool_registry: ToolRegistry
    """Registry of available government API tools."""

    config: QueryEngineConfig
    """Immutable engine configuration for this session."""

    iteration: int = 0
    """Zero-based iteration counter within the current turn."""


# ---------------------------------------------------------------------------
# SessionBudget
# ---------------------------------------------------------------------------


class SessionBudget(BaseModel):
    """Frozen read-only snapshot of the current session budget status.

    Derived from QueryState and QueryEngineConfig via the class method
    ``from_state()``.  All fields are non-negative integers or a boolean flag;
    ``is_exhausted`` is True when either the token budget or the turn budget
    is fully consumed.
    """

    model_config = ConfigDict(frozen=True)

    tokens_used: int
    """Total tokens consumed so far in this session."""

    tokens_remaining: int
    """Tokens still available before the session budget is exhausted."""

    tokens_budget: int
    """Configured token budget for the session."""

    turns_used: int
    """Number of turns completed so far."""

    turns_remaining: int
    """Turns still available before the session turn limit is reached."""

    turns_budget: int
    """Configured maximum turns for the session."""

    is_exhausted: bool
    """True when either the token budget or the turn budget is fully consumed."""

    @classmethod
    def from_state(cls, state: QueryState, config: QueryEngineConfig) -> SessionBudget:
        """Construct a SessionBudget snapshot from current session state.

        Args:
            state: The mutable QueryState holding live usage counters.
            config: The engine configuration supplying budget limits.

        Returns:
            A frozen SessionBudget reflecting the current state of the session.
        """
        return cls(
            tokens_used=state.usage.total_used,
            tokens_remaining=state.usage.remaining,
            tokens_budget=state.usage._budget,
            turns_used=state.turn_count,
            turns_remaining=max(0, config.max_turns - state.turn_count),
            turns_budget=config.max_turns,
            is_exhausted=state.usage.is_exhausted or state.turn_count >= config.max_turns,
        )
