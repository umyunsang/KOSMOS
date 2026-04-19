# SPDX-License-Identifier: Apache-2.0
"""Bypass mode resolver — Spec 033 T030 (WS4).

Pure module providing ``resolve_bypass_mode()`` — the defense-in-depth backstop
for ``bypassPermissions`` mode evaluation AFTER the killswitch has already run.

Invariants enforced here:
- K5 (no caching): this function has NO cache parameter and NO memoization state.
  Bypass-mode prompts MUST NOT be cached — every call is re-evaluated from scratch.
  Any caller that attempts to add caching around this function violates K5.

This module is intentionally minimal.  Its only job is to provide a clear
behavioral contract for ``bypassPermissions`` / ``dontAsk`` mode:

  - If the killswitch was already triggered upstream, the decision to return
    ``"ALLOW"`` or ``"ASK"`` is determined by this module as a defense-in-depth
    backstop.
  - If the killswitch was NOT triggered, return ``"ALLOW"`` (silent allow is
    the mode's intended behavior for non-killswitch calls).

Note: The killswitch check in ``killswitch.pre_evaluate()`` runs FIRST (K1).
This module's primary function is as a defense-in-depth layer — if somehow
the pipeline is wired incorrectly and the killswitch result is lost, this
backstop provides a second chance to detect and force the prompt.

Reference:
    specs/033-permission-v2-spectrum/spec.md §US3
    specs/033-permission-v2-spectrum/data-model.md § 2.1 K5
    specs/033-permission-v2-spectrum/contracts/mode-transition.contract.md § 5
"""

from __future__ import annotations

import logging
from typing import Literal

from kosmos.permissions.killswitch import pre_evaluate
from kosmos.permissions.models import AdapterPermissionMetadata, ToolPermissionContext

__all__ = ["resolve_bypass_mode"]

_logger = logging.getLogger(__name__)


def resolve_bypass_mode(
    ctx: ToolPermissionContext,
    metadata: AdapterPermissionMetadata,
) -> Literal["ALLOW", "ASK"]:
    """Resolve the bypass mode decision for a tool call.

    This function is the defense-in-depth backstop for ``bypassPermissions``
    and ``dontAsk`` mode evaluation.  It is called AFTER the killswitch has
    already run in the pipeline.

    Decision logic:
    - If the killswitch fires (``pre_evaluate()`` returns ``"ASK"``):
        return ``"ASK"`` — the citizen MUST be prompted, no exceptions.
    - Otherwise:
        return ``"ALLOW"`` — the bypass mode's silent-allow semantics apply.

    CRITICAL — No caching (Invariant K5):
        This function has NO cache parameter and NO memoization.  Bypass-mode
        prompts MUST NOT be cached.  The nonce-based ``action_digest`` mechanism
        (``action_digest.compute_action_digest()``) ensures every call gets a
        distinct ledger record (K6).  Caching the ALLOW decision here would
        undermine the per-call audit requirement.

    CRITICAL — No cache argument accepted:
        The function signature deliberately provides no ``cache`` parameter.
        Any attempt to add caching by modifying this signature violates K5 and
        MUST be rejected during code review.

    Args:
        ctx: The per-invocation tool permission context.  ``ctx.mode`` MUST be
             ``"bypassPermissions"`` or ``"dontAsk"`` for this function to be
             called (by convention — it works correctly for other modes too but
             is semantically a bypass-mode concern).
        metadata: The frozen adapter permission metadata projection.

    Returns:
        ``"ALLOW"`` if the bypass mode's silent-allow semantics apply
            (no killswitch condition met).
        ``"ASK"``  if the killswitch fires (citizen must be prompted).

    Example::

        # Non-killswitch call in bypass mode → silent allow
        >>> result = resolve_bypass_mode(ctx_bypass, metadata_reversible)
        >>> assert result == "ALLOW"

        # Irreversible call in bypass mode → must ask
        >>> result = resolve_bypass_mode(ctx_bypass, metadata_irreversible)
        >>> assert result == "ASK"
    """
    killswitch_result = pre_evaluate(ctx, metadata)

    if killswitch_result == "ASK":
        _logger.info(
            "resolve_bypass_mode: killswitch backstop triggered for tool_id=%r "
            "mode=%r — returning ASK (K5 no-cache; defense-in-depth).",
            ctx.tool_id,
            ctx.mode,
        )
        return "ASK"

    _logger.debug(
        "resolve_bypass_mode: no killswitch condition for tool_id=%r mode=%r "
        "— returning ALLOW (bypass mode silent-allow path).",
        ctx.tool_id,
        ctx.mode,
    )
    return "ALLOW"
