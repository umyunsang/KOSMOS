# SPDX-License-Identifier: Apache-2.0
"""Dynamic system-prompt assembler (Epic #2152 R2).

Mirrors Pydantic AI's ``@agent.system_prompt`` decorator pattern + Claude Code
2.1.88 ``systemPromptSections.ts`` memoization framework. Provides a typed
surface where future per-turn injectors (memdir consent summary, ministry
scope, session-start date) register lazily without mutating the cacheable
static prefix.

Contract: ``specs/2152-system-prompt-redesign/contracts/prompt-assembler.md``
invariants I-A1..I-A7. Data model: ``data-model.md`` §1, §2, §3, §6.

Reference sources (Constitution Principle I — reference-driven):
- Pydantic AI core concepts: https://pydantic.dev/docs/ai/core-concepts/agent/
- CC sourcemap: ``.references/claude-code-sourcemap/restored-src/src/constants/prompts.ts:491-555``
  (the ``dynamicSections`` array) and ``systemPromptSections.ts:1-68``
  (memoization framework).
"""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kosmos.context.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


# Boundary marker — kept identical to ``kosmos.ipc.stdio._DYNAMIC_BOUNDARY_MARKER``
# and ``kosmos.llm.client``'s slicing literal so all three sites agree.
DYNAMIC_BOUNDARY_MARKER = "\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n"

# Required XML tag pairs — must all appear in ``prompts/system_v1.md`` (R1).
_REQUIRED_TAG_PAIRS = (
    ("<role>", "</role>"),
    ("<core_rules>", "</core_rules>"),
    ("<tool_usage>", "</tool_usage>"),
    ("<output_style>", "</output_style>"),
)

_DYNAMIC_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class PromptAssemblyError(ValueError):
    """Raised when prompt assembly hits an unrecoverable invariant violation.

    Examples:
        Required XML tag missing in ``prompts/system_v1.md``;
        decorator name that does not match snake_case;
        duplicate decorator name with a divergent function;
        produced static prefix does not terminate with the boundary marker.
    """


class PromptSection(BaseModel):
    """One of the four XML-tagged sections in ``prompts/system_v1.md``.

    Frozen — instances are immutable once constructed.
    """

    model_config = ConfigDict(frozen=True)

    tag: Literal["role", "core_rules", "tool_usage", "output_style"]
    body: str = Field(min_length=1)


class PromptAssemblyContext(BaseModel):
    """Read-only context passed to every dynamic-suffix decorator.

    Mirrors Pydantic AI's ``RunContext[T]`` pattern.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str
    """Stable across all turns of a TUI session (UUID4)."""

    session_started_at: datetime
    """ISO-8601 UTC timestamp."""

    tool_inventory: tuple[str, ...]
    """Sorted tuple of tool IDs registered at chat-request time. Tuple, not
    list, so it cannot be mutated after construction."""

    dynamic_inputs: dict[str, str] = Field(default_factory=dict)
    """Free-form key-value bag for memdir consent / ministry-scope / future
    injectors. Keys MUST be snake_case (validator enforces); values are
    pre-stringified by the caller."""

    @model_validator(mode="after")
    def _validate_dynamic_input_keys(self) -> PromptAssemblyContext:
        for key in self.dynamic_inputs:
            if not _DYNAMIC_NAME_RE.match(key):
                raise PromptAssemblyError(
                    f"dynamic_inputs key {key!r} must match {_DYNAMIC_NAME_RE.pattern}"
                )
        return self


class SystemPromptManifest(BaseModel):
    """Output of ``PromptAssembler.build(ctx)`` — the bytes sent to the LLM.

    Frozen. Constructor enforces ``prefix_hash == sha256(static_prefix)`` and
    that ``static_prefix`` ends with the boundary marker so the cache invariant
    cannot be violated by a malformed manifest.
    """

    model_config = ConfigDict(frozen=True)

    static_prefix: str = Field(min_length=1)
    dynamic_suffix: str = ""
    prefix_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_marker_and_hash(self) -> SystemPromptManifest:
        if not self.static_prefix.endswith(DYNAMIC_BOUNDARY_MARKER):
            raise PromptAssemblyError(
                "static_prefix must terminate with SYSTEM_PROMPT_DYNAMIC_BOUNDARY"
            )
        expected = hashlib.sha256(self.static_prefix.encode("utf-8")).hexdigest()
        if self.prefix_hash != expected:
            raise PromptAssemblyError(
                "prefix_hash diverges from sha256(static_prefix) — cache invariant violated"
            )
        return self


# Type alias for dynamic-section injector callables.
DynamicSectionFn = Callable[[PromptAssemblyContext], "str | None"]


class PromptAssembler:
    """Composes the citizen-domain system prompt from a static prefix + a
    decorator-registered dynamic suffix.

    Construction is fail-closed (Constitution Principle II): if the loaded
    static prompt is missing any of the four required XML tag pairs, the
    constructor raises immediately so the chat-request path cannot proceed
    with a malformed prompt.
    """

    def __init__(self, static_prefix_source: PromptLoader) -> None:
        loaded = static_prefix_source.load("system_v1")
        for opening, closing in _REQUIRED_TAG_PAIRS:
            if opening not in loaded or closing not in loaded:
                raise PromptAssemblyError(
                    f"system_v1.md missing required XML tag pair {opening}…{closing}"
                )
        self._static_body = loaded
        self._registry: dict[str, DynamicSectionFn] = {}

    def register(self, name: str, fn: DynamicSectionFn) -> None:
        """Register a dynamic-suffix injector under a unique snake_case name."""
        if not _DYNAMIC_NAME_RE.match(name):
            raise PromptAssemblyError(
                f"decorator name {name!r} must match {_DYNAMIC_NAME_RE.pattern}"
            )
        existing = self._registry.get(name)
        if existing is not None and existing is not fn:
            raise PromptAssemblyError(
                f"decorator name {name!r} already registered with a different function"
            )
        self._registry[name] = fn

    def build(self, ctx: PromptAssemblyContext) -> SystemPromptManifest:
        """Build the manifest for one chat-request turn.

        Returns:
            ``SystemPromptManifest`` with byte-stable ``static_prefix`` /
            ``prefix_hash`` and a possibly-empty ``dynamic_suffix``.
        """
        static_prefix = self._static_body
        if not static_prefix.endswith(DYNAMIC_BOUNDARY_MARKER):
            static_prefix = static_prefix.rstrip("\n") + DYNAMIC_BOUNDARY_MARKER

        suffix_parts: list[str] = []
        for name, fn in self._registry.items():
            try:
                value = fn(ctx)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "kosmos.prompt_assembler injector %r raised %s; skipping",
                    name,
                    exc.__class__.__name__,
                )
                value = None
            if value is None:
                continue
            if not isinstance(value, str):  # type: ignore[unreachable]
                raise PromptAssemblyError(
                    f"injector {name!r} returned non-str: {type(value).__name__}"
                )
            suffix_parts.append(value)

        dynamic_suffix = "\n".join(suffix_parts)
        prefix_hash = hashlib.sha256(static_prefix.encode("utf-8")).hexdigest()

        return SystemPromptManifest(
            static_prefix=static_prefix,
            dynamic_suffix=dynamic_suffix,
            prefix_hash=prefix_hash,
        )


def system_prompt(
    assembler: PromptAssembler, name: str
) -> Callable[[DynamicSectionFn], DynamicSectionFn]:
    """Pydantic-AI-style decorator helper. Sugar over ``assembler.register``.

    Usage::

        @system_prompt(assembler, name="ministry_scope")
        def ministry_scope_section(ctx: PromptAssemblyContext) -> str | None:
            scope = ctx.dynamic_inputs.get("ministry_scope")
            return f"<ministry_scope>{scope}</ministry_scope>" if scope else None

    The decorated function is returned unchanged so it remains directly
    callable for unit tests.
    """

    def _decorator(fn: DynamicSectionFn) -> DynamicSectionFn:
        assembler.register(name, fn)
        return fn

    return _decorator
