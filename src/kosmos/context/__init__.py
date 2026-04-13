# SPDX-License-Identifier: Apache-2.0
"""Context Assembly layer for KOSMOS (Layer 5).

Assembles deterministic system prompts, per-turn attachments,
tool schema injection with cache partitioning, and budget guards.

Public API:

    ContextBuilder      — main facade; assemble full context for each turn
    SystemPromptConfig  — configuration for system prompt assembly
    ContextLayer        — single assembled context layer
    ContextBudget       — token budget guard (frozen snapshot)
    AssembledContext    — complete assembled context for one LLM turn
"""

from __future__ import annotations

from kosmos.context.builder import ContextBuilder
from kosmos.context.models import (
    AssembledContext,
    ContextBudget,
    ContextLayer,
    SystemPromptConfig,
)

__all__ = [
    "ContextBuilder",
    "SystemPromptConfig",
    "ContextLayer",
    "ContextBudget",
    "AssembledContext",
]
