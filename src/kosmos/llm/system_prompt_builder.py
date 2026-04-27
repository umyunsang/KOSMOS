# SPDX-License-Identifier: Apache-2.0
"""System prompt augmentation helper for the KOSMOS LLM harness.

Mirrors _cc_reference/api.ts:appendSystemContext + _cc_reference/prompts.ts dynamic composition.

This module provides a single pure function that appends a structured tool inventory
section to a base system prompt. The augmented text is byte-stable for byte-identical
inputs: no datetime, no environment variable lookups, and JSON object keys are sorted
deterministically. Byte stability is required for LLM provider prompt-cache reuse
(Spec 026 prompt-hash invariant) — the augmentation is excluded from the
``kosmos.prompt.hash`` OTEL span attribute (which hashes only the base prompt),
but the augmented text itself must be stable so the provider can serve cache hits
on repeated turns with the same tool inventory.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from kosmos.llm.models import ToolDefinition as LLMToolDefinition

logger = logging.getLogger(__name__)

_SECTION_HEADER = "\n\n## Available tools\n\n"
_BLOCK_SEPARATOR = "\n\n"


def build_system_prompt_with_tools(
    base: str,
    tools: list[LLMToolDefinition],
) -> str:
    """Append a formatted tool inventory section to a base system prompt.

    Returns ``base`` byte-for-byte when ``tools`` is empty. Otherwise appends
    ``"\\n\\n## Available tools\\n\\n"`` followed by one Markdown block per tool,
    separated by a single blank line.

    Tool order in the output matches the input list order. The caller is
    responsible for sorting (e.g. alphabetically by ``function.name``) if a
    stable order is desired across turns.

    Args:
        base: The unmodified system prompt body. May be empty; the function
            does not raise on empty base (caller's responsibility).
        tools: Active tool definitions for the current turn. When empty the
            function is a no-op and returns ``base`` unchanged.

    Returns:
        The (possibly augmented) system prompt string.
    """
    if not tools:
        return base

    blocks: list[str] = []
    for tool in tools:
        parameters: dict[str, Any] = tool.function.parameters or {}
        block = (
            f"### {tool.function.name}\n"
            f"\n"
            f"{tool.function.description}\n"
            f"\n"
            f"**Parameters**:\n"
            f"\n"
            f"```json\n"
            f"{json.dumps(parameters, indent=2, sort_keys=True, ensure_ascii=False)}\n"
            f"```"
        )
        blocks.append(block)

    augmented = base + _SECTION_HEADER + _BLOCK_SEPARATOR.join(blocks)

    logger.debug(
        "kosmos.system_prompt.augmented_chars=%d kosmos.system_prompt.tool_count=%d",
        len(augmented) - len(base),
        len(tools),
    )

    return augmented
