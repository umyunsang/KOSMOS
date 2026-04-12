# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 models for the KOSMOS Context Assembly layer (Layer 5).

All models are frozen (immutable after construction) as required by
Constitution § III.  No ``Any`` types are used.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class SystemPromptConfig(BaseModel):
    """Configuration for the deterministic system prompt assembler.

    All fields are optional; defaults produce a sensible Korean-language
    platform prompt.  The same config instance always produces the same
    assembled prompt (required for FriendliAI prompt-cache stability).
    """

    model_config = ConfigDict(frozen=True)

    platform_name: str = "KOSMOS"
    """Display name injected into the platform identity section."""

    language: str = "ko"
    """BCP-47 language code for the language-policy section."""

    reminder_cadence: int = 5
    """Inject reminder block every N turns (turn 0 is excluded)."""

    personal_data_warning: bool = True
    """Include the personal-data handling reminder section when True."""

    @field_validator("platform_name")
    @classmethod
    def _platform_name_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("platform_name must not be empty or whitespace-only")
        return v

    @field_validator("language")
    @classmethod
    def _language_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("language must not be empty or whitespace-only")
        return v

    @field_validator("reminder_cadence")
    @classmethod
    def _reminder_cadence_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError(f"reminder_cadence must be > 0, got {v}")
        return v


class ContextLayer(BaseModel):
    """A single assembled context layer passed to the LLM.

    Invariant: ``role='system'`` requires ``layer_name='system_prompt'``.
    ``role='user'`` allows any layer_name.
    Content must be non-empty.
    """

    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user"]
    """Message role sent to the LLM."""

    layer_name: str
    """Logical name of this layer (e.g. 'system_prompt', 'turn_attachment')."""

    content: str
    """Assembled text content; must be non-empty."""

    @field_validator("content")
    @classmethod
    def _content_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ContextLayer.content must not be empty or whitespace-only")
        return v

    @field_validator("layer_name")
    @classmethod
    def _layer_name_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ContextLayer.layer_name must not be empty or whitespace-only")
        return v

    @model_validator(mode="after")
    def _role_layer_name_invariant(self) -> ContextLayer:
        """Enforce that system role always uses the 'system_prompt' layer name."""
        if self.role == "system" and self.layer_name != "system_prompt":
            raise ValueError(
                f"ContextLayer with role='system' must have layer_name='system_prompt', "
                f"got {self.layer_name!r}"
            )
        return self


class ContextBudget(BaseModel):
    """Frozen read-only snapshot of the context token budget.

    Use ``ContextBudget.from_estimate()`` to construct from raw numbers.
    """

    model_config = ConfigDict(frozen=True)

    estimated_tokens: int
    """Sum of estimated token counts across all assembled layers."""

    hard_limit_tokens: int
    """Hard cap: engine must not send a prompt exceeding this limit."""

    soft_limit_tokens: int
    """Soft warning threshold (default: 80% of hard limit)."""

    is_near_limit: bool
    """True when estimated_tokens >= soft_limit_tokens."""

    is_over_limit: bool
    """True when estimated_tokens >= hard_limit_tokens."""

    @classmethod
    def from_estimate(
        cls,
        estimated: int,
        hard_limit: int,
        soft_limit: int,
    ) -> ContextBudget:
        """Construct a ContextBudget, computing the boolean threshold flags.

        Args:
            estimated: Estimated token count for the full assembled context.
            hard_limit: Maximum tokens allowed before the engine must stop.
            soft_limit: Warning threshold (typically 80% of hard_limit).

        Returns:
            A frozen ContextBudget with all fields populated.
        """
        return cls(
            estimated_tokens=estimated,
            hard_limit_tokens=hard_limit,
            soft_limit_tokens=soft_limit,
            is_near_limit=estimated >= soft_limit,
            is_over_limit=estimated >= hard_limit,
        )


class AssembledContext(BaseModel):
    """Complete assembled context ready to be handed to the LLM.

    Combines the system layer, an optional per-turn attachment, the tool
    definitions list (core prefix + situational suffix), and the budget guard.
    """

    model_config = ConfigDict(frozen=True)

    system_layer: ContextLayer
    """System prompt layer; always present."""

    turn_attachment: ContextLayer | None = None
    """Per-turn dynamic context; None for empty sessions."""

    tool_definitions: list[dict[str, object]] = []
    """Tool schemas: core tools (sorted by id) then situational tools (sorted by id)."""

    budget: ContextBudget | None = None
    """Budget guard; None until BudgetEstimator is wired in."""
