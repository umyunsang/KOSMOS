# SPDX-License-Identifier: Apache-2.0
"""Standalone per-turn query loop for the KOSMOS Query Engine.

The ``query()`` async generator is the core execution loop that drives a single
turn of the engine: preprocess → immutable snapshot → LLM stream → tool dispatch
→ decide.  It is separated from ``QueryEngine`` to enable independent unit
testing (FR-012).
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext
from kosmos.engine.preprocessing import PreprocessingPipeline
from kosmos.engine.tokens import estimate_tokens
from kosmos.llm.models import ChatMessage, FunctionCall, ToolCall, ToolDefinition
from kosmos.tools.errors import ToolNotFoundError
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import ToolResult
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers for streaming tool-call accumulation
# ---------------------------------------------------------------------------


@dataclass
class _PendingToolCall:
    """Accumulator for streaming tool_call_delta events from a single tool."""

    index: int
    tool_call_id: str = ""
    function_name: str = ""
    function_args: str = ""


def _assemble_tool_calls(
    pending: dict[int, _PendingToolCall],
) -> list[ToolCall]:
    """Convert accumulated streaming deltas into finalized ToolCall objects.

    Returns tool calls sorted by their original stream index to preserve
    the order in which the model requested them.
    """
    return [
        ToolCall(
            id=p.tool_call_id,
            function=FunctionCall(
                name=p.function_name,
                arguments=p.function_args,
            ),
        )
        for p in sorted(pending.values(), key=lambda p: p.index)
    ]


# ---------------------------------------------------------------------------
# Concurrent tool dispatch (partition-sort algorithm, R-004)
# ---------------------------------------------------------------------------


async def dispatch_tool_calls(  # noqa: C901
    tool_calls: list[ToolCall],
    tool_registry: ToolRegistry,
    tool_executor: ToolExecutor,
) -> list[ToolResult]:
    """Dispatch multiple tool calls with concurrency optimization.

    Partition-sort algorithm:
    1. Look up each tool's ``is_concurrency_safe`` flag.
    2. Group consecutive concurrency-safe tools together.
    3. Execute each safe group concurrently via ``asyncio.TaskGroup``.
    4. Execute non-safe tools sequentially.
    5. Return results in the same order as the input ``tool_calls``.

    Args:
        tool_calls: List of ToolCall objects from the LLM response.
        tool_registry: Registry for looking up tool concurrency flags.
        tool_executor: Executor for dispatching individual calls.

    Returns:
        List of ToolResult objects, one per input tool_call, in order.
    """
    if not tool_calls:
        return []

    # Build (index, tool_call, is_safe) tuples
    indexed: list[tuple[int, ToolCall, bool]] = []
    for i, tc in enumerate(tool_calls):
        try:
            tool = tool_registry.lookup(tc.function.name)
            is_safe = tool.is_concurrency_safe
        except ToolNotFoundError:
            is_safe = False  # unknown tools dispatch sequentially (fail-closed)
        indexed.append((i, tc, is_safe))

    # Partition into consecutive groups of same concurrency type
    results: list[ToolResult | None] = [None] * len(tool_calls)
    group: list[tuple[int, ToolCall]] = []
    group_safe: bool | None = None

    async def _flush_group(items: list[tuple[int, ToolCall]], safe: bool) -> None:
        """Execute a group of tool calls, concurrently if safe."""
        if not items:
            return
        if safe and len(items) > 1:
            async with asyncio.TaskGroup() as tg:
                tasks = [
                    (
                        idx,
                        tg.create_task(
                            tool_executor.dispatch(tc.function.name, tc.function.arguments),
                        ),
                    )
                    for idx, tc in items
                ]
            for idx, task in tasks:
                results[idx] = task.result()
        else:
            for idx, tc in items:
                results[idx] = await tool_executor.dispatch(
                    tc.function.name,
                    tc.function.arguments,
                )

    for i, tc, is_safe in indexed:
        if group_safe is not None and is_safe != group_safe:
            await _flush_group(group, group_safe)
            group = []
        group_safe = is_safe
        group.append((i, tc))

    # Flush remaining group
    if group and group_safe is not None:
        await _flush_group(group, group_safe)

    return [r for r in results if r is not None]


# ---------------------------------------------------------------------------
# Public: per-turn query generator
# ---------------------------------------------------------------------------


async def query(ctx: QueryContext) -> AsyncIterator[QueryEvent]:  # noqa: C901
    """Execute one turn of the query loop.

    The loop:
    1. Create immutable message snapshot: ``list(ctx.state.messages)``
    2. Stream LLM completion with tool definitions
    3. Yield ``text_delta`` events as content streams
    4. If tool_calls in response:
       a. Yield ``tool_use`` events for each call
       b. Dispatch tools sequentially (US1 MVP)
       c. Yield ``tool_result`` events
       d. Append tool results to ``ctx.state.messages``
       e. Yield ``usage_update``
       f. Continue loop (iteration += 1)
    5. If no tool_calls: yield ``usage_update``, yield ``stop``, return
    6. If iteration >= ``config.max_iterations``: yield ``stop(max_iterations_reached)``

    Args:
        ctx: Per-turn context with references to state, LLM client, tools, config.

    Yields:
        QueryEvent stream as described above.
    """
    iteration = 0
    pipeline = PreprocessingPipeline()

    while iteration < ctx.config.max_iterations:
        # --- Preprocessing: compress context if approaching window limit ---
        total_tokens = sum(estimate_tokens(m.content or "") for m in ctx.state.messages)
        token_threshold = int(ctx.config.context_window * ctx.config.preprocessing_threshold)
        if total_tokens > token_threshold:
            logger.info(
                "Preprocessing triggered: %d tokens > %d threshold",
                total_tokens,
                token_threshold,
            )
            ctx.state.messages[:] = pipeline.run(
                ctx.state.messages,
                ctx.config,
                current_turn=ctx.state.turn_count,
            )

        # --- Immutable snapshot for prompt cache stability (R-003) ---
        snapshot = list(ctx.state.messages)

        # --- Export tool definitions (sorted for cache stability) ---
        raw_defs = ctx.tool_registry.export_core_tools_openai()
        tool_defs: list[ToolDefinition | dict[str, object]] | None = list(raw_defs) or None

        # --- Stream LLM completion ---
        pending_calls: dict[int, _PendingToolCall] = {}
        content_parts: list[str] = []
        usage = None

        try:
            async for event in ctx.llm_client.stream(
                snapshot,
                tools=tool_defs,
            ):
                if event.type == "content_delta" and event.content:
                    content_parts.append(event.content)
                    yield QueryEvent(type="text_delta", content=event.content)

                elif event.type == "tool_call_delta":
                    idx = event.tool_call_index if event.tool_call_index is not None else 0
                    if idx not in pending_calls:
                        pending_calls[idx] = _PendingToolCall(index=idx)
                    p = pending_calls[idx]
                    if event.tool_call_id:
                        p.tool_call_id = event.tool_call_id
                    if event.function_name:
                        p.function_name = event.function_name
                    if event.function_args_delta:
                        p.function_args += event.function_args_delta

                elif event.type == "usage":
                    usage = event.usage

        except Exception as exc:
            logger.exception("LLM stream failed: %s", exc)
            yield QueryEvent(
                type="stop",
                stop_reason=StopReason.error_unrecoverable,
                stop_message=f"LLM stream error: {exc}",
            )
            return

        # --- Assemble assistant message and append to history ---
        assembled_calls = _assemble_tool_calls(pending_calls) if pending_calls else []
        assistant_content = "".join(content_parts) or None

        ctx.state.messages.append(
            ChatMessage(
                role="assistant",
                content=assistant_content,
                tool_calls=assembled_calls or None,
            ),
        )

        # --- No tool calls: yield usage, stop, and return ---
        if not assembled_calls:
            if usage:
                yield QueryEvent(type="usage_update", usage=usage)
            yield QueryEvent(type="stop", stop_reason=StopReason.end_turn)
            return

        # --- Yield tool_use events before dispatch ---
        for tc in assembled_calls:
            yield QueryEvent(
                type="tool_use",
                tool_name=tc.function.name,
                tool_call_id=tc.id,
                arguments=tc.function.arguments,
            )

        # --- Dispatch tools (concurrent when safe, sequential otherwise) ---
        tool_results = await dispatch_tool_calls(
            assembled_calls,
            ctx.tool_registry,
            ctx.tool_executor,
        )

        # --- Append results to history and yield tool_result events ---
        for tc, result in zip(assembled_calls, tool_results, strict=True):
            if result.success:
                result_content = json.dumps(result.data, ensure_ascii=False)
            else:
                result_content = result.error or "Unknown error"

            ctx.state.messages.append(
                ChatMessage(
                    role="tool",
                    content=result_content,
                    tool_call_id=tc.id,
                ),
            )

            yield QueryEvent(type="tool_result", tool_result=result)

        # --- Yield usage after all tool dispatches (event ordering contract) ---
        if usage:
            yield QueryEvent(type="usage_update", usage=usage)

        iteration += 1
        logger.debug(
            "Query loop iteration %d/%d completed",
            iteration,
            ctx.config.max_iterations,
        )

    # --- Max iterations reached ---
    yield QueryEvent(
        type="stop",
        stop_reason=StopReason.max_iterations_reached,
        stop_message=(f"Reached maximum {ctx.config.max_iterations} iterations per turn"),
    )
