# SPDX-License-Identifier: Apache-2.0
"""Spec 025 V6 AAL downgrade backstop — Spec 033 FR-F02.

Detects and blocks AAL (Authenticator Assurance Level) downgrade attempts
where a tool call was authorised at a high AAL at prompt time (e.g., AAL3)
but the session's effective auth level at execution time is lower (e.g., AAL1).

This module is a **downstream consumer** of Spec 025 V6.  It MUST NOT modify
any source in ``kosmos.tools.models`` or ``kosmos.security.audit``.

FR-F02: if ``ctx_at_prompt.auth_level != ctx_at_exec.auth_level``, block
  execution and raise ``AALDowngradeBlocked`` regardless of mode or rule.

Edge case (spec.md §Edge Cases — "AAL 다운그레이드 시도"):
  Adapter auth_level=AAL2 but session holds only AAL1 credentials —
  blocked irrespective of PermissionMode or RuleStore state.

Reference:
  specs/033-permission-v2-spectrum/spec.md §FR-F02 + §Edge Cases
  specs/025-tool-security-v6/spec.md (auth_type ↔ auth_level invariant)
  src/kosmos/tools/models.py _AUTH_TYPE_LEVEL_MAPPING (V6 mapping table)
  src/kosmos/permissions/models.py ToolPermissionContext
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from kosmos.permissions.models import ToolPermissionContext

__all__ = [
    "AALDowngradeBlocked",
    "check_aal_downgrade",
]

_logger = logging.getLogger(__name__)

# Ordinal ranking of AAL levels for comparison.
# Higher index = higher assurance level.
_AAL_ORDER: dict[str, int] = {
    "public": 0,
    "AAL1": 1,
    "AAL2": 2,
    "AAL3": 3,
}

AALLevelLiteral = Literal["public", "AAL1", "AAL2", "AAL3"]


@dataclass(frozen=True)
class AALDowngradeBlocked(Exception):  # noqa: N818 — spec 033 FR-F02 mandates this exact name
    """Raised when a AAL downgrade attack is detected at execution time.

    FR-F02 enforcement: if the auth_level in the ToolPermissionContext at
    prompt time does not match the effective auth_level at execution time,
    the pipeline MUST block the tool call.

    This is distinct from Spec 025 V6 which enforces the static
    ``auth_type ↔ auth_level`` consistency invariant on adapter declarations.
    This backstop enforces the *dynamic* runtime invariant: auth level at
    prompt time must equal auth level at execution time.

    Attributes:
        tool_id: The adapter that was targeted by the downgrade attempt.
        prompt_auth_level: The auth_level present in the context at prompt time.
        execution_auth_level: The auth_level present in the context at execution.
    """

    tool_id: str
    prompt_auth_level: str
    execution_auth_level: str

    def __str__(self) -> str:
        return (
            f"FR-F02 AALDowngradeBlocked: tool={self.tool_id!r} "
            f"prompt_auth_level={self.prompt_auth_level!r} "
            f"execution_auth_level={self.execution_auth_level!r}. "
            "Tool call blocked — auth level must remain constant between "
            "prompt time and execution time (Spec 033 FR-F02 + Spec 025 V6)."
        )


def check_aal_downgrade(
    ctx_at_prompt: ToolPermissionContext,
    ctx_at_exec: ToolPermissionContext,
) -> None:
    """Check for AAL downgrade between prompt time and execution time.

    Validates that the ``auth_level`` in *ctx_at_prompt* (the context at the
    time the permission pipeline evaluated and the citizen consented) is
    identical to the ``auth_level`` in *ctx_at_exec* (the context at the
    time the tool is actually dispatched).

    This prevents a session downgrade attack where an adversary obtains
    consent at a high AAL (e.g., AAL3) but then executes the call with
    a weaker session (e.g., AAL1 after a re-authentication step was
    silently dropped).

    Both contexts must reference the same ``tool_id`` — a mismatch is itself
    a security error.

    Args:
        ctx_at_prompt: The ToolPermissionContext captured at prompt/consent time.
        ctx_at_exec: The ToolPermissionContext captured at execution/dispatch time.

    Returns:
        None — silently returns when auth levels match.

    Raises:
        AALDowngradeBlocked: When auth_level differs between contexts.
        ValueError: When tool_id differs between the two contexts (protocol error).
    """
    if ctx_at_prompt.tool_id != ctx_at_exec.tool_id:
        raise ValueError(
            f"AAL backstop protocol error: ctx_at_prompt.tool_id="
            f"{ctx_at_prompt.tool_id!r} != ctx_at_exec.tool_id="
            f"{ctx_at_exec.tool_id!r}. "
            "Both contexts must reference the same tool invocation."
        )

    prompt_level = ctx_at_prompt.auth_level
    exec_level = ctx_at_exec.auth_level

    if prompt_level == exec_level:
        # No downgrade — fast path.
        return

    # Determine direction for logging clarity.
    prompt_rank = _AAL_ORDER.get(prompt_level, -1)
    exec_rank = _AAL_ORDER.get(exec_level, -1)

    # Downgrade: exec is weaker; upgrade: exec is stronger. Both are blocked (FR-F02).
    direction = "downgrade" if exec_rank < prompt_rank else "upgrade"

    _logger.warning(
        "aal_backstop.blocked: tool_id=%s direction=%s prompt_level=%s exec_level=%s",
        ctx_at_prompt.tool_id,
        direction,
        prompt_level,
        exec_level,
    )

    raise AALDowngradeBlocked(
        tool_id=ctx_at_prompt.tool_id,
        prompt_auth_level=prompt_level,
        execution_auth_level=exec_level,
    )
