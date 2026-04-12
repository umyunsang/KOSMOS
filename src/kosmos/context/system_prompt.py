# SPDX-License-Identifier: Apache-2.0
"""System prompt assembler for KOSMOS Context Assembly layer (Layer 5).

``SystemPromptAssembler.assemble()`` produces a deterministic, policy-aligned
system prompt string from a ``SystemPromptConfig``.  The output is identical
for equal config inputs, ensuring FriendliAI prompt-cache stability (NFR-003).

Mandatory sections (FR-009) in fixed order:
  1. Platform identity
  2. Language policy
  3. Tool-use policy
  4. Personal-data reminder (conditional on config.personal_data_warning)
"""

from __future__ import annotations

import logging

from kosmos.context.models import SystemPromptConfig

logger = logging.getLogger(__name__)

# Section separator — two newlines produce paragraph breaks in the LLM view.
_SECTION_SEP = "\n\n"


class SystemPromptAssembler:
    """Assembles the system prompt from a frozen ``SystemPromptConfig``.

    The assembler is stateless: ``assemble()`` accepts a config and returns a
    string. Caching is handled by the caller (``ContextBuilder``).
    """

    def assemble(self, config: SystemPromptConfig) -> str:
        """Assemble all mandatory sections into a single system prompt string.

        Args:
            config: Frozen configuration controlling platform name, language,
                    and which optional sections to include.

        Returns:
            Deterministic, non-empty system prompt string.
        """
        sections = [
            self._platform_identity_section(config),
            self._language_policy_section(config),
            self._tool_use_policy_section(),
        ]
        if config.personal_data_warning:
            sections.append(self._personal_data_reminder_section())

        prompt = _SECTION_SEP.join(sections)
        logger.debug("Assembled system prompt: %d characters", len(prompt))
        return prompt

    # ------------------------------------------------------------------
    # Mandatory section builders (FR-009)
    # ------------------------------------------------------------------

    def _platform_identity_section(self, config: SystemPromptConfig) -> str:
        """Section 1: Platform identity."""
        return (
            f"You are {config.platform_name}, a Korean public service AI assistant. "
            "You help citizens access government services and public information "
            "through available tools. Your goal is to provide accurate, helpful "
            "guidance based solely on verified government data sources."
        )

    def _language_policy_section(self, config: SystemPromptConfig) -> str:
        """Section 2: Language policy."""
        return (
            f"Always respond in {config.language} unless the citizen explicitly writes "
            "in another language. Use clear, accessible language appropriate for "
            "citizens unfamiliar with government procedures."
        )

    def _tool_use_policy_section(self) -> str:
        """Section 3: Tool-use policy."""
        return (
            "Use available tools when the citizen's request requires live data lookup "
            "from government APIs. Do not fabricate or estimate government data, "
            "regulations, or service availability. When a tool call is needed, "
            "invoke it before providing the final answer."
        )

    def _personal_data_reminder_section(self) -> str:
        """Section 4: Personal-data handling reminder (conditional)."""
        return (
            "Handle personal data with care. Do not log, repeat, or store citizen "
            "personal information beyond what is strictly necessary for the current "
            "request. Comply with all applicable Korean data protection regulations."
        )
