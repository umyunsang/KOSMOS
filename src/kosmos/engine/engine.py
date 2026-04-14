# SPDX-License-Identifier: Apache-2.0
"""Per-session orchestrator for the KOSMOS Query Engine.

``QueryEngine`` is the only public entry point for consumers of the query
engine module. It owns the session state and delegates per-turn execution to
the standalone ``query()`` async generator.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from kosmos.context.builder import ContextBuilder
from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext, QueryState, SessionBudget
from kosmos.engine.query import query
from kosmos.llm.client import LLMClient
from kosmos.llm.models import ChatMessage
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from kosmos.permissions.models import SessionContext
    from kosmos.permissions.pipeline import PermissionPipeline

logger = logging.getLogger(__name__)


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
        context_builder: Context assembly helper used to build the system
                         message and per-turn attachments. A default
                         ContextBuilder is created if None.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        tool_executor: ToolExecutor,
        config: QueryEngineConfig | None = None,
        context_builder: ContextBuilder | None = None,
        permission_pipeline: PermissionPipeline | None = None,
        permission_session: SessionContext | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._tool_executor = tool_executor
        self._config = config or QueryEngineConfig()
        self._context_builder = context_builder or ContextBuilder(registry=tool_registry)
        self._permission_pipeline = permission_pipeline
        self._permission_session = permission_session

        system_msg = self._context_builder.build_system_message()
        self._state = QueryState(
            usage=llm_client.usage,
            messages=[system_msg],
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

        # --- Budget check via context assembly (before mutating message history) ---
        # Build the assembled context first so that a budget-exceeded early exit
        # does not leave a stray attachment in self._state.messages.
        assembled = self._context_builder.build_assembled_context(
            self._state,
            api_health=None,
            hard_limit=self._config.context_window,
        )
        # assembled.tool_definitions is intentionally not used here: tool defs are
        # exported inside the per-turn query loop via ToolRegistry.export_core_tools_openai()
        # (see query.py) to ensure the snapshot is taken after the user message is appended.
        if assembled.budget and assembled.budget.is_over_limit:
            yield QueryEvent(
                type="stop",
                stop_reason=StopReason.api_budget_exceeded,
                stop_message="Context token budget exceeded",
            )
            return

        # --- Context assembly: insert turn attachment after passing budget check ---
        # Re-use the turn_attachment already computed in assembled; avoids a second
        # call to build_turn_attachment() which would duplicate context assembly work.
        if assembled.turn_attachment is not None:
            self._state.messages.append(
                ChatMessage(role="user", content=assembled.turn_attachment.content),
            )

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
            permission_pipeline=self._permission_pipeline,
            session_context=self._permission_session,
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

    def reset(self) -> None:
        """Reset the conversation state for a new session.

        Clears the message history (re-initialises with the system message),
        resets the turn counter, and preserves the existing token usage tracker
        so that the budget continues from where it left off.
        """
        system_msg = self._context_builder.build_system_message()
        self._state = QueryState(
            usage=self._llm_client.usage,
            messages=[system_msg],
        )
        logger.info("QueryEngine reset: conversation cleared")

    def set_permission_session(self, session: SessionContext | None) -> None:
        """Update the permission-pipeline session used for subsequent turns.

        The REPL calls this when it creates or resumes a session so that
        the ``session_id`` recorded in permission audits matches the real
        REPL session identifier instead of a placeholder.

        Args:
            session: Fresh :class:`SessionContext`, or ``None`` to disable
                permission checks (not recommended in production).
        """
        self._permission_session = session
        if session is not None:
            logger.info(
                "QueryEngine permission session updated: session_id=%s",
                session.session_id,
            )
        else:
            logger.warning("QueryEngine permission session cleared")

    @property
    def permission_session(self) -> SessionContext | None:
        """Return the currently installed permission :class:`SessionContext`."""
        return self._permission_session

    @property
    def permission_pipeline(self) -> PermissionPipeline | None:
        """Return the installed :class:`PermissionPipeline`, if any."""
        return self._permission_pipeline

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
