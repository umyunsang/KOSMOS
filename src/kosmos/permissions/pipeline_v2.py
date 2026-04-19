# SPDX-License-Identifier: Apache-2.0
"""Permission pipeline v2 skeleton — Spec 033 (Epic #1297).

Defines the v2 evaluation entry point ``evaluate()`` which will be filled by
the five parallel workstream Teammates (Phases 3-7).

This module deliberately avoids modifying ``pipeline.py`` (the existing v1
``PermissionPipeline`` gauntlet) to prevent any regression risk.  The v2
entry point is a new function in a new module.

Four-step pipeline order (contracts/mode-transition.contract.md § 5):
  1. ``killswitch.pre_evaluate(ctx)`` — NON-NEGOTIABLE pre-check (K1–K6).
     Runs BEFORE mode evaluation.  Cannot be short-circuited by any config.
  2. ``mode.evaluate(ctx)``           — Apply mode-specific auto-allow logic.
  3. ``rule.resolve(ctx)``            — Tri-state rule store lookup.
  4. ``prompt.ask(ctx)``              — Fallback: ask the citizen (PIPA 4-tuple).

Invariant P1 (contracts/mode-transition.contract.md § 5):
    Killswitch is step 1.  No exception.  Any implementation that runs
    Mode before Killswitch MUST fail ``test_killswitch_priority_order``.

Invariant P2:
    Killswitch returns ASK (forces the prompt to appear), not ALLOW/DENY.
    The citizen still makes the final decision.

Reference:
    specs/033-permission-v2-spectrum/contracts/mode-transition.contract.md § 5
    specs/033-permission-v2-spectrum/data-model.md § 2.1 (K1–K6)
"""

from __future__ import annotations

from kosmos.permissions.models import ConsentDecision, ToolPermissionContext

__all__ = ["evaluate"]


async def evaluate(ctx: ToolPermissionContext) -> ConsentDecision:
    """Evaluate a tool call request through the v2 permission pipeline.

    This is a STUB.  The four-step pipeline body will be implemented by the
    five parallel workstream Teammates (Phases 3-7):

      - WS4 implements ``killswitch.pre_evaluate()`` + ``prompt.ask()``
      - WS1 implements ``mode.evaluate()``
      - WS2 implements ``rule.resolve()``

    Until all four steps land, calling this function raises
    ``NotImplementedError``.

    Args:
        ctx: The per-invocation tool permission context containing the tool id,
             current mode, adapter metadata, session context, and call arguments.

    Returns:
        A ``ConsentDecision`` indicating whether the tool call is granted or
        denied, along with the PIPA 4-tuple fields and ledger-binding digest.

    Raises:
        NotImplementedError: Always — stub pending Phase 3-7 implementation.

    Pipeline steps (in required order):
      1. ``killswitch.pre_evaluate(ctx)`` — irreversible / AAL3 / 특수 gate.
      2. ``mode.evaluate(ctx)``           — mode-specific auto-allow/deny.
      3. ``rule.resolve(ctx)``            — persistent tri-state rule lookup.
      4. ``prompt.ask(ctx)``              — citizen consent prompt fallback.
    """
    raise NotImplementedError(
        "Permission pipeline v2 is not yet implemented. "
        "Steps will be filled by Phases 3-7 workstream Teammates. "
        "Pipeline order: killswitch.pre_evaluate → mode.evaluate → "
        "rule.resolve → prompt.ask"
    )
