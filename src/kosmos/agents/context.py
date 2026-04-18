# SPDX-License-Identifier: Apache-2.0
"""AgentContext — frozen per-worker injection model.

Pinned at worker spawn time by the Coordinator. Immutable after construction.
FR-010.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from kosmos.llm.client import LLMClient
from kosmos.tools.registry import ToolRegistry


class AgentContext(BaseModel):
    """Immutable per-worker context pinned at spawn time.

    The coordinator constructs one AgentContext per worker. Workers receive
    it at construction and MUST NOT share it with other workers.

    The tool_registry MUST be restricted to {"lookup", "resolve_location"}
    before AgentContext is constructed. This restriction is asserted in
    Coordinator.spawn_worker() (FR-011) rather than here, because
    ToolRegistry is not a Pydantic model and the set of registered tool IDs
    can change after registry construction.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,  # LLMClient, ToolRegistry are non-Pydantic
    )

    session_id: UUID
    """Session identifier; shared across coordinator + all workers in this session."""

    specialist_role: str = Field(min_length=1, max_length=64)
    """Worker's specialist role (e.g., 'transport', 'welfare', 'civil_affairs').

    Must be non-empty — coordinator raises AgentConfigurationError at spawn if empty.
    """

    coordinator_id: str = Field(default="coordinator", frozen=True)
    """Sender ID of the coordinator. Always the literal string 'coordinator'."""

    worker_id: str = Field(min_length=1, max_length=128)
    """Unique sender ID of this worker. Format: 'worker-<role>-<uuid4>'."""

    tool_registry: ToolRegistry
    """Tool registry — MUST be restricted to {'lookup', 'resolve_location'}.

    The restriction is asserted by Coordinator.spawn_worker() before AgentContext
    construction; AgentContext itself cannot validate this at __init__ time because
    ToolRegistry is not a Pydantic model.
    """

    llm_client: LLMClient
    """Shared LLM client (per-session semaphore reused per Spec 019)."""
