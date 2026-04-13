# SPDX-License-Identifier: Apache-2.0
"""Context Assembly layer for KOSMOS (Layer 5).

Assembles deterministic system prompts, per-turn attachments,
tool schema injection with cache partitioning, budget guards, and
context compaction.

Public API:

    ContextBuilder      — main facade; assemble full context for each turn
    SystemPromptConfig  — configuration for system prompt assembly
    ContextLayer        — single assembled context layer
    ContextBudget       — token budget guard (frozen snapshot)
    AssembledContext    — complete assembled context for one LLM turn
    CompactionConfig    — compaction thresholds and strategy settings
    CompactionResult    — immutable record of a compaction operation
    AutoCompactor       — orchestrates tiered compaction (micro → summary → aggressive)
"""

from __future__ import annotations

from kosmos.context.auto_compact import AutoCompactor
from kosmos.context.builder import ContextBuilder
from kosmos.context.compact_models import CompactionConfig, CompactionResult
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
    "CompactionConfig",
    "CompactionResult",
    "AutoCompactor",
]
