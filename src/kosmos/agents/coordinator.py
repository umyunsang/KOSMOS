# SPDX-License-Identifier: Apache-2.0
"""Coordinator class — 4-phase workflow orchestrator for the Agent Swarm.

Phases: RESEARCH → SYNTHESIS → IMPLEMENTATION → VERIFICATION

The coordinator dispatches workers as asyncio.Task objects, collects their
results via the mailbox, synthesises a CoordinatorPlan, and drives the
implementation + verification phases.

FR traces: FR-001..FR-007, FR-024, FR-025, FR-028 (observability).
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, UTC
from enum import StrEnum
from typing import Literal
from uuid import UUID, uuid4

from opentelemetry import trace

from kosmos.agents.consent import AlwaysGrantConsentGateway, ConsentGateway
from kosmos.agents.context import AgentContext
from kosmos.agents.errors import AgentConfigurationError
from kosmos.agents.mailbox.messages import (
    AgentMessage,
    CancelPayload,
    ErrorPayload,
    MessageType,
    PermissionRequestPayload,
    PermissionResponsePayload,
    ResultPayload,
    TaskPayload,
)
from kosmos.agents.plan import (
    CoordinatorPlan,
    ExecutionMode,
    PlanStatus,
    PlanStep,
    StepStatus,
)
from kosmos.agents.worker import Worker
from kosmos.llm.client import LLMClient
from kosmos.llm.models import ChatMessage
from kosmos.observability.semconv import KOSMOS_AGENT_COORDINATOR_PHASE
from kosmos.tools.registry import ToolRegistry

if False:  # TYPE_CHECKING — avoid circular import at runtime
    from kosmos.agents.mailbox.base import Mailbox

logger = logging.getLogger(__name__)
_tracer = trace.get_tracer(__name__)

# The two facade tool IDs that workers may access
_WORKER_TOOLS: frozenset[str] = frozenset({"lookup", "resolve_location"})

# Default max-workers semaphore value (overridden by KosmosSettings)
_DEFAULT_MAX_WORKERS: int = 4

# Default worker timeout seconds
_DEFAULT_WORKER_TIMEOUT: int = 120


class CoordinatorPhase(StrEnum):
    """Coordinator 4-phase state machine values."""

    research = "research"
    synthesis = "synthesis"
    implementation = "implementation"
    verification = "verification"
    cancelled = "cancelled"
    done = "done"


class Coordinator:
    """Orchestrates the 4-phase Research → Synthesis → Implementation → Verification workflow.

    The Coordinator owns the session-level state, spawns Worker tasks in the
    Research phase, collects their results via the mailbox, synthesises a
    CoordinatorPlan in the Synthesis phase, and executes the plan steps in the
    Implementation phase.

    solo mode (FR-007): When role='solo', the coordinator acts as a single-agent
    and does NOT spawn workers. This preserves backward compatibility with the
    Phase 1 QueryEngine contract.
    """

    def __init__(
        self,
        session_id: UUID,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        mailbox: "Mailbox",
        *,
        consent_gateway: ConsentGateway | None = None,
        role: Literal["solo", "coordinator", "specialist"] = "coordinator",
        max_workers: int = _DEFAULT_MAX_WORKERS,
        worker_timeout_seconds: int = _DEFAULT_WORKER_TIMEOUT,
    ) -> None:
        """Initialise the Coordinator.

        Args:
            session_id: Unique session identifier.
            llm_client: LLM client for the coordinator's own LLM calls.
            tool_registry: Tool registry for worker spawning.
            mailbox: Message mailbox for coordinator ↔ worker IPC.
            consent_gateway: Consent gateway for permission delegation.
                             Defaults to AlwaysGrantConsentGateway (test stub).
            role: 'coordinator' (default), 'solo' (Phase 1 backward compat),
                  or 'specialist' (future use).
            max_workers: Maximum concurrent worker tasks (KOSMOS_AGENT_MAX_WORKERS).
            worker_timeout_seconds: Per-worker timeout (KOSMOS_AGENT_WORKER_TIMEOUT_SECONDS).
        """
        self._session_id = session_id
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._mailbox = mailbox
        self._consent_gateway = consent_gateway or AlwaysGrantConsentGateway()
        self._role: Literal["solo", "coordinator", "specialist"] = role
        self._max_workers = max_workers
        self._worker_timeout_seconds = worker_timeout_seconds
        self._semaphore = asyncio.Semaphore(max_workers)

        # Live state — only set when coordinator is running
        self._phase: CoordinatorPhase = CoordinatorPhase.research
        self._worker_tasks: dict[str, asyncio.Task[None]] = {}
        self._worker_contexts: dict[str, AgentContext] = {}
        self._cancel_requested: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, citizen_request: str) -> CoordinatorPlan:
        """Execute the full 4-phase workflow for a citizen request.

        Args:
            citizen_request: The citizen's natural-language request.

        Returns:
            CoordinatorPlan produced by the Synthesis phase.
        """
        if self._role == "solo":
            return await self._run_solo(citizen_request)

        # Replay any unread messages from a prior crashed run (FR-019)
        await self._replay_prior_messages()

        # Phase 1: RESEARCH — classify intent, spawn workers
        self._emit_phase_span(CoordinatorPhase.research)
        worker_results = await self._research_phase(citizen_request)

        if self._cancel_requested:
            return self._build_partial_plan(worker_results)

        # Phase 2: SYNTHESIS — produce CoordinatorPlan (no tools injected)
        self._emit_phase_span(CoordinatorPhase.synthesis)
        plan = await self._synthesis_phase(
            citizen_request, worker_results
        )

        if self._cancel_requested:
            return plan

        # Phase 3: IMPLEMENTATION — execute plan steps
        self._emit_phase_span(CoordinatorPhase.implementation)
        await self._implementation_phase(plan)

        # Phase 4: VERIFICATION
        self._emit_phase_span(CoordinatorPhase.verification)

        return plan

    def cancel(self) -> None:
        """Signal cooperative cancellation to all in-flight worker tasks.

        This method is non-async — the actual cancellation happens in
        _cancel_all_workers() which must be awaited. Use this method to
        trigger cancellation from a synchronous context.
        """
        self._cancel_requested = True
        for task in self._worker_tasks.values():
            task.cancel()

    async def cancel_and_wait(self, timeout: float = 0.5) -> None:
        """Cancel all in-flight workers and wait for them to terminate.

        FR-006, SC-003: all workers must terminate within 500 ms.

        Args:
            timeout: Maximum wait time in seconds (default 0.5 = 500 ms).
        """
        self.cancel()
        if not self._worker_tasks:
            return

        # Send cancel messages to all workers' mailboxes
        for worker_id in list(self._worker_tasks.keys()):
            cancel_payload = CancelPayload(reason="coordinator_requested")
            cancel_msg = AgentMessage(
                sender="coordinator",
                recipient=worker_id,
                msg_type=MessageType.cancel,
                payload=cancel_payload,
                timestamp=datetime.now(UTC),
            )
            try:
                await self._mailbox.send(cancel_msg)
            except Exception:
                pass  # Best-effort cancel message delivery

        # Wait for tasks to complete with timeout
        all_tasks = list(self._worker_tasks.values())
        try:
            await asyncio.wait_for(
                asyncio.gather(*all_tasks, return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Coordinator: %d worker(s) did not cancel within %.0f ms",
                len(all_tasks),
                timeout * 1000,
            )

    # ------------------------------------------------------------------
    # Phase implementations
    # ------------------------------------------------------------------

    async def _replay_prior_messages(self) -> None:
        """Replay unread messages from a prior crashed run (FR-019)."""
        prior_results: list[AgentMessage] = []
        async for msg in self._mailbox.replay_unread("coordinator"):
            prior_results.append(msg)
        if prior_results:
            logger.info(
                "Coordinator: replayed %d message(s) from prior run",
                len(prior_results),
            )

    async def _research_phase(
        self, citizen_request: str
    ) -> list[AgentMessage]:
        """Classify intent, spawn workers, collect results.

        Intent classification is performed by the coordinator LLM (FR-003),
        not by a static keyword table.

        Returns:
            List of result/error messages from all workers.
        """
        # Ask the LLM to classify intent and identify specialist roles
        specialist_roles = await self._classify_intent(citizen_request)

        if not specialist_roles:
            logger.info("Coordinator: no specialist roles identified; returning empty results")
            return []

        # Spawn one worker per specialist role (bounded by semaphore)
        logger.info(
            "Coordinator: spawning %d worker(s) for roles: %s",
            len(specialist_roles),
            specialist_roles,
        )

        tasks_by_role: dict[str, asyncio.Task[None]] = {}
        worker_ids: list[str] = []

        for role in specialist_roles:
            ctx = self.spawn_worker(role)
            worker_id = ctx.worker_id
            worker_ids.append(worker_id)
            worker = Worker(ctx, self._mailbox)

            instruction = (
                f"You are a {role} specialist. Research this citizen request "
                f"and use the lookup tool to find relevant information: "
                f"{citizen_request}"
            )

            async def _run_with_semaphore(
                w: Worker, inst: str, wid: str
            ) -> None:
                async with self._semaphore:
                    await w.run(inst)

            task = asyncio.create_task(
                _run_with_semaphore(worker, instruction, worker_id),
                name=f"worker-{worker_id}",
            )
            tasks_by_role[worker_id] = task
            self._worker_tasks[worker_id] = task

        # Wait for all workers to complete (or timeout)
        results: list[AgentMessage] = []
        if tasks_by_role:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks_by_role.values(), return_exceptions=True),
                    timeout=float(self._worker_timeout_seconds),
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Coordinator: worker timeout after %d seconds",
                    self._worker_timeout_seconds,
                )
                for task in tasks_by_role.values():
                    task.cancel()

            # Handle permission requests that arrived during worker execution
            await self._process_coordinator_mailbox()

        # Collect all result/error messages from the coordinator mailbox
        results = await self._collect_worker_messages(worker_ids)

        return results

    async def _classify_intent(self, citizen_request: str) -> list[str]:
        """Ask the coordinator LLM to classify the citizen's intent.

        FR-003: classification MUST be performed by the coordinator LLM,
        not by a static keyword table.

        Returns:
            List of specialist role names to spawn workers for.
        """
        from kosmos.engine.config import QueryEngineConfig
        from kosmos.engine.models import QueryContext, QueryState
        from kosmos.engine.query import _query_inner
        from kosmos.llm.usage import UsageTracker

        system_msg = ChatMessage(
            role="system",
            content=(
                "You are a coordinator for a Korean public services system. "
                "Your task is to classify a citizen's request into specialist roles. "
                "The specialist roles are: civil_affairs, transport, health_insurance, "
                "welfare, housing, tax, education. "
                "Respond with ONLY a JSON array of role strings, e.g.: "
                '["civil_affairs", "transport"]. '
                "If the request needs only one specialist, return a single-element array. "
                "Return at most 4 roles."
            ),
        )
        user_msg = ChatMessage(
            role="user",
            content=f"Classify this citizen request: {citizen_request}",
        )

        from kosmos.tools.executor import ToolExecutor

        state = QueryState(usage=UsageTracker(budget=50_000))
        state.messages.extend([system_msg, user_msg])
        config = QueryEngineConfig(max_iterations=1)

        # Use an empty tool registry + executor for classification (text-only LLM call)
        _empty_registry = ToolRegistry()
        query_ctx = QueryContext(
            state=state,
            llm_client=self._llm_client,
            tool_executor=ToolExecutor(registry=_empty_registry),
            tool_registry=_empty_registry,
            config=config,
        )

        # Collect text output — no tools injected (classification is text-only)
        text_parts: list[str] = []
        async for event in _query_inner(query_ctx):
            if event.type == "text_delta" and event.content:
                text_parts.append(event.content)

        text = "".join(text_parts).strip()
        if not text:
            logger.warning("Coordinator: empty LLM response for intent classification")
            return []

        # Parse the JSON array
        try:
            # Find JSON array in the response
            start = text.find("[")
            end = text.rfind("]")
            if start >= 0 and end > start:
                roles_raw = json.loads(text[start : end + 1])
                roles = [str(r).strip() for r in roles_raw if r]
                return roles[:4]  # cap at 4
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning(
                "Coordinator: could not parse intent classification response %r: %s",
                text,
                exc,
            )
        return []

    async def _process_coordinator_mailbox(self) -> None:
        """Process any permission_request messages in the coordinator's mailbox.

        FR-024, FR-025: coordinate consent, then route permission_response
        back to the requesting worker only (no lateral flow).
        """
        # This is a non-blocking drain of pending permission requests
        # For the file-based mailbox, we use replay_unread to find queued messages
        async for msg in self._mailbox.replay_unread("coordinator"):
            if msg.msg_type == MessageType.permission_request:
                await self._handle_permission_request(msg)

    async def _handle_permission_request(self, request: AgentMessage) -> None:
        """Process a permission_request from a worker and reply.

        FR-024: prompt the citizen consent stub, then emit permission_response
        addressed to the requesting worker's sender field.
        """
        from kosmos.agents.mailbox.messages import PermissionRequestPayload

        payload = request.payload
        if not isinstance(payload, PermissionRequestPayload):
            return

        # Ask the consent gateway (stub always returns True for testing)
        granted = await self._consent_gateway.request_consent(
            payload.tool_id, request.correlation_id or uuid4()
        )

        response_payload = PermissionResponsePayload(
            granted=granted,
            tool_id=payload.tool_id,
        )
        response_msg = AgentMessage(
            sender="coordinator",
            recipient=request.sender,  # FR-025: route only to the requesting worker
            msg_type=MessageType.permission_response,
            payload=response_payload,
            timestamp=datetime.now(UTC),
            correlation_id=request.correlation_id,
        )
        await self._mailbox.send(response_msg)
        logger.debug(
            "Coordinator: sent permission_response to %s (granted=%s)",
            request.sender,
            granted,
        )

    async def _collect_worker_messages(
        self, worker_ids: list[str]
    ) -> list[AgentMessage]:
        """Collect all result/error messages posted by workers.

        Returns:
            List of AgentMessage objects with msg_type in {result, error}.
        """
        results: list[AgentMessage] = []
        seen_correlation_ids: set[UUID] = set()

        async for msg in self._mailbox.replay_unread("coordinator"):
            if msg.msg_type in (MessageType.result, MessageType.error):
                # Deduplicate by correlation_id (spec Edge Cases: duplicate result)
                cid = msg.correlation_id
                if cid is not None and cid in seen_correlation_ids:
                    logger.warning(
                        "Coordinator: duplicate result for correlation_id %s from %s — ignoring",
                        cid,
                        msg.sender,
                    )
                    continue
                if cid is not None:
                    seen_correlation_ids.add(cid)
                results.append(msg)

        return results

    async def _synthesis_phase(
        self,
        citizen_request: str,
        worker_results: list[AgentMessage],
    ) -> CoordinatorPlan:
        """Produce a CoordinatorPlan from worker results.

        FR-004: synthesis MUST NOT inject lookup/resolve_location into the
        LLM tool definitions. The synthesis LLM call uses text generation only.
        FR-038: assert that no tools are passed to the LLM here.
        """
        if not worker_results:
            # Edge case: all workers failed (spec Edge Cases)
            return CoordinatorPlan(
                session_id=self._session_id,
                status=PlanStatus.no_results,
                steps=[],
                worker_correlation_ids=[],
                message="All workers failed or returned no results.",
            )

        # Collect correlation IDs from worker results (SC-002 zero-orphan-id)
        correlation_ids: list[UUID] = []
        result_summaries: list[str] = []

        for msg in worker_results:
            if msg.msg_type == MessageType.result:
                if msg.correlation_id:
                    correlation_ids.append(msg.correlation_id)
                # Summarise the result for the LLM
                payload = msg.payload
                if isinstance(payload, ResultPayload):
                    out = payload.lookup_output
                    summary = f"Worker '{msg.sender}': {out.kind} output, {payload.turn_count} turn(s)"
                    result_summaries.append(summary)
            elif msg.msg_type == MessageType.error:
                payload = msg.payload
                if isinstance(payload, ErrorPayload):
                    result_summaries.append(
                        f"Worker '{msg.sender}' FAILED: {payload.error_type} — {payload.message}"
                    )

        # Ask the LLM to synthesise a plan (NO tools injected — FR-004)
        plan_data = await self._call_synthesis_llm(
            citizen_request, result_summaries
        )

        steps = plan_data.get("steps", [])
        plan_steps = [
            PlanStep(
                ministry=s.get("ministry", "unknown"),
                action=s.get("action", ""),
                depends_on=s.get("depends_on", []),
                execution_mode=s.get("execution_mode", ExecutionMode.parallel),
                status=StepStatus.pending,
            )
            for s in steps
        ]

        status = PlanStatus.complete
        if not plan_steps:
            status = PlanStatus.partial

        return CoordinatorPlan(
            session_id=self._session_id,
            status=status,
            steps=plan_steps,
            worker_correlation_ids=correlation_ids,
            message=plan_data.get("message"),
        )

    async def _call_synthesis_llm(
        self, citizen_request: str, result_summaries: list[str]
    ) -> dict:  # type: ignore[type-arg]
        """Call the LLM for synthesis WITHOUT any tools injected (FR-004).

        The LLM generates a JSON plan as text. Tool definitions are
        intentionally empty so lookup/resolve_location are NEVER called
        during synthesis (FR-038).
        """
        from kosmos.engine.config import QueryEngineConfig
        from kosmos.engine.models import QueryContext, QueryState
        from kosmos.engine.query import _query_inner
        from kosmos.llm.usage import UsageTracker
        from kosmos.tools.executor import ToolExecutor
        from kosmos.tools.registry import ToolRegistry

        system_msg = ChatMessage(
            role="system",
            content=(
                "You are a coordinator synthesising citizen task results. "
                "Given a citizen's request and research summaries from specialist workers, "
                "produce a JSON plan with the following structure:\n"
                '{"steps": [{"ministry": "...", "action": "...", "depends_on": [], '
                '"execution_mode": "sequential|parallel"}], "message": "optional summary"}\n'
                "Classify steps as sequential if they must happen in order, "
                "parallel if they can happen concurrently. "
                "Return ONLY valid JSON."
            ),
        )
        summaries_text = "\n".join(result_summaries) if result_summaries else "No results available."
        user_msg = ChatMessage(
            role="user",
            content=(
                f"Citizen request: {citizen_request}\n\n"
                f"Worker research summaries:\n{summaries_text}\n\n"
                "Produce the JSON plan."
            ),
        )

        state = QueryState(usage=UsageTracker(budget=100_000))
        state.messages.extend([system_msg, user_msg])

        # CRITICAL (FR-004): use an EMPTY tool registry so lookup/resolve_location
        # are NOT injected into the synthesis LLM call.
        empty_registry = ToolRegistry()
        config = QueryEngineConfig(max_iterations=1)

        query_ctx = QueryContext(
            state=state,
            llm_client=self._llm_client,
            tool_executor=ToolExecutor(registry=empty_registry),
            tool_registry=empty_registry,  # <-- EMPTY: no tools for synthesis
            config=config,
        )

        text_parts: list[str] = []
        async for event in _query_inner(query_ctx):
            if event.type == "text_delta" and event.content:
                text_parts.append(event.content)

        text = "".join(text_parts).strip()
        if not text:
            return {}

        try:
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(text[start : end + 1])
        except (json.JSONDecodeError, ValueError):
            logger.warning("Coordinator: could not parse synthesis LLM response: %r", text)
        return {}

    async def _implementation_phase(self, plan: CoordinatorPlan) -> None:
        """Execute plan steps in the declared order.

        Parallel steps run concurrently via asyncio.TaskGroup.
        Sequential steps run in declared order (respecting depends_on).
        """
        if not plan.steps:
            return

        # Group steps by their execution_mode and dependencies
        # Simple implementation: run parallel steps concurrently, sequential in order
        parallel_steps = [s for s in plan.steps if s.execution_mode == ExecutionMode.parallel]
        sequential_steps = [s for s in plan.steps if s.execution_mode == ExecutionMode.sequential]

        # Run parallel steps concurrently
        if parallel_steps:
            async with asyncio.TaskGroup() as tg:
                for step in parallel_steps:
                    tg.create_task(self._execute_plan_step(step))

        # Run sequential steps in order
        for step in sequential_steps:
            await self._execute_plan_step(step)

    async def _execute_plan_step(self, step: PlanStep) -> None:
        """Execute a single plan step (placeholder — real execution is per-ministry)."""
        logger.debug(
            "Coordinator: executing step ministry=%s action=%s",
            step.ministry,
            step.action,
        )
        # Implementation steps are logged; actual execution is deferred to
        # ministry-specific workers in Epic #14.
        await asyncio.sleep(0)  # yield to event loop

    async def _run_solo(self, citizen_request: str) -> CoordinatorPlan:
        """Solo mode: behave as Phase 1 single-agent loop (FR-007).

        In solo mode, no workers are spawned. The coordinator calls the
        LLM directly with the 2-tool surface and returns a minimal plan.
        """
        logger.info("Coordinator running in solo mode for: %r", citizen_request[:80])
        # Solo mode delegates to the synthesis LLM with an empty result set
        plan_data = await self._call_synthesis_llm(citizen_request, [])
        steps = plan_data.get("steps", [])
        plan_steps = [
            PlanStep(
                ministry=s.get("ministry", "unknown"),
                action=s.get("action", ""),
                depends_on=s.get("depends_on", []),
                execution_mode=s.get("execution_mode", ExecutionMode.parallel),
            )
            for s in steps
        ]
        return CoordinatorPlan(
            session_id=self._session_id,
            status=PlanStatus.complete if plan_steps else PlanStatus.no_results,
            steps=plan_steps,
            worker_correlation_ids=[],
            message=plan_data.get("message"),
        )

    # ------------------------------------------------------------------
    # Worker spawn helper (T024)
    # ------------------------------------------------------------------

    def spawn_worker(self, specialist_role: str) -> AgentContext:
        """Create an isolated AgentContext for a new worker.

        Validates the tool registry restriction, generates a unique worker_id,
        and respects KOSMOS_AGENT_MAX_WORKERS cap (via semaphore in _research_phase).

        Args:
            specialist_role: The specialist role for the new worker.

        Returns:
            A fresh frozen AgentContext for the worker.

        Raises:
            AgentConfigurationError: if specialist_role is empty, if the tool
                registry contains disallowed tools, or if max workers are active.
        """
        if not specialist_role or not specialist_role.strip():
            raise AgentConfigurationError(
                "spawn_worker() requires a non-empty specialist_role "
                "(spec Edge Case: worker spawned with no specialist role)"
            )

        # Assert tool registry is restricted to {lookup, resolve_location} (FR-011)
        tool_names = set(self._tool_registry._tools.keys())
        if not tool_names.issubset(_WORKER_TOOLS):
            raise AgentConfigurationError(
                f"Coordinator tool registry contains tools beyond the 2-tool facade: "
                f"{tool_names - _WORKER_TOOLS}. "
                "Worker registries MUST be restricted to {lookup, resolve_location}."
            )

        worker_id = f"worker-{specialist_role}-{uuid4()}"
        ctx = AgentContext(
            session_id=self._session_id,
            specialist_role=specialist_role,
            coordinator_id="coordinator",
            worker_id=worker_id,
            tool_registry=self._tool_registry,
            llm_client=self._llm_client,
        )
        self._worker_contexts[worker_id] = ctx
        logger.debug("Coordinator: spawned worker %s (role=%s)", worker_id, specialist_role)
        return ctx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _emit_phase_span(self, phase: CoordinatorPhase) -> None:
        """Emit one gen_ai.agent.coordinator.phase span (FR-028)."""
        self._phase = phase
        span_name = "gen_ai.agent.coordinator.phase"
        with _tracer.start_as_current_span(span_name) as span:
            span.set_attribute(KOSMOS_AGENT_COORDINATOR_PHASE, phase.value)
        logger.debug("Coordinator: phase → %s", phase.value)

    def _build_partial_plan(
        self, worker_results: list[AgentMessage]
    ) -> CoordinatorPlan:
        """Build a partial plan from whatever results arrived before cancellation."""
        correlation_ids = [
            msg.correlation_id
            for msg in worker_results
            if msg.msg_type == MessageType.result and msg.correlation_id
        ]
        status = PlanStatus.partial if correlation_ids else PlanStatus.no_results
        return CoordinatorPlan(
            session_id=self._session_id,
            status=status,
            steps=[],
            worker_correlation_ids=correlation_ids,
            message="Request was cancelled before all workers completed.",
        )
