# SPDX-License-Identifier: Apache-2.0
"""Per-session orchestrator for the KOSMOS Query Engine.

``QueryEngine`` is the only public entry point for consumers of the query
engine module. It owns the session state and delegates per-turn execution to
the standalone ``query()`` async generator.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext, QueryState, SessionBudget
from kosmos.engine.query import query
from kosmos.llm.client import LLMClient
from kosmos.llm.models import ChatMessage
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are KOSMOS, a Korean public service AI assistant. "
    "You help citizens access government services through available tools. "
    "Answer in Korean. Use tools when the citizen's request requires data lookup."
)


class QueryEngine:
    """Per-session orchestrator for the KOSMOS query engine.

    The only public entry point for consumers. Each instance manages one
    conversational session: it owns the message history, token budget, and
    turn counter, and delegates per-turn execution to ``query()``.

    Args:
        llm_client: Configured LLM client for streaming completions.
        tool_registry: Registry with registered tools and rate limiters.
        tool_executor: Dispatcher with registered adapters.
        config: Engine configuration. Uses defaults if None.
        system_prompt: System prompt for the LLM. Uses a minimal
                      hardcoded prompt for v1 if None.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: QueryEngineConfig | None = None,
        system_prompt: str | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor
        self._config = config or QueryEngineConfig()
        self._system_prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT

        self._state = QueryState(
            usage=llm_client.usage,
            messages=[ChatMessage(role="system", content=self._system_prompt)],
        )

        logger.info(
            "QueryEngine initialized: max_iterations=%d, max_turns=%d, context_window=%d, tools=%d",
            self._config.max_iterations,
            self._config.max_turns,
            self._config.context_window,
            len(self._tool_registry),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, user_message: str) -> AsyncIterator[QueryEvent]:
        """Execute a single turn of the query engine.

        This is the primary public API. Each call represents one citizen turn:
        the user message is appended to history, and the engine loops through
        LLM call → tool dispatch → decide until a stop condition.

        Args:
            user_message: The citizen's natural-language input.

        Yields:
            QueryEvent: Progress events in order — text_delta, tool_use,
                        tool_result, usage_update, and finally stop.

        Raises:
            No exceptions propagate. All errors are captured as
            QueryEvent(type="stop", stop_reason=StopReason.error_unrecoverable).
        """
        logger.info(
            "Turn %d started: %s",
            self._state.turn_count + 1,
            user_message[:80],
        )

        # --- Budget enforcement: check turn limit before processing ---
        if self._state.turn_count >= self._config.max_turns:
            budget_snap = self.budget
            yield QueryEvent(
                type="stop",
                stop_reason=StopReason.api_budget_exceeded,
                stop_message=(
                    f"Turn budget exhausted: {budget_snap.turns_used}"
                    f"/{budget_snap.turns_budget} turns used"
                ),
            )
            return

        # --- Budget enforcement: check token budget ---
        if self._state.usage.is_exhausted:
            budget_snap = self.budget
            yield QueryEvent(
                type="stop",
                stop_reason=StopReason.api_budget_exceeded,
                stop_message=(
                    f"Token budget exhausted: {budget_snap.tokens_used}"
                    f"/{budget_snap.tokens_budget} tokens used"
                ),
            )
            return

        # Append user message to history
        self._state.messages.append(
            ChatMessage(role="user", content=user_message),
        )

        # Create per-turn context
        ctx = QueryContext(
            state=self._state,
            llm_client=self._llm_client,
            tool_executor=self._tool_executor,
            tool_registry=self._tool_registry,
            config=self._config,
        )

        # Delegate to per-turn query loop
        try:
            async for event in query(ctx):
                yield event
        except Exception as exc:
            logger.exception("Unexpected error in query loop: %s", exc)
            yield QueryEvent(
                type="stop",
                stop_reason=StopReason.error_unrecoverable,
                stop_message=f"Unexpected error: {exc}",
            )
        finally:
            self._state.turn_count += 1
            logger.info(
                "Turn %d completed: tokens_used=%d, messages=%d",
                self._state.turn_count,
                self._state.usage.total_used,
                len(self._state.messages),
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def budget(self) -> SessionBudget:
        """Return a read-only snapshot of current budget status."""
        return SessionBudget.from_state(self._state, self._config)

    @property
    def message_count(self) -> int:
        """Return the number of messages in the conversation history."""
        return len(self._state.messages)
