# SPDX-License-Identifier: Apache-2.0
"""Killswitch pre-evaluation — Spec 033 T028/T029 (WS4).

Implements the NON-NEGOTIABLE Constitution §II killswitch check that runs
BEFORE any mode evaluation in the permission pipeline.

Invariants enforced here:
- K1: Killswitch is step 1 in the pipeline.  ``KILLSWITCH_ORDER = 1`` constant
      + ``assert_killswitch_first()`` assertion helper enforce this structurally.
- K2: ``bypassPermissions`` mode + ``is_irreversible=True`` → return ``"ASK"``.
- K3: ``bypassPermissions`` mode + ``pipa_class="특수"`` → return ``"ASK"``.
- K4: ``bypassPermissions`` mode + ``auth_level="AAL3"`` → return ``"ASK"``.
- K5 (no caching): Killswitch-triggered prompts MUST NOT be cached.  This module
      contains no caching state.  The complementary ``mode_bypass.resolve_bypass_mode()``
      also accepts no cache argument.
- K6 (distinct digests): enforced externally via ``action_digest.compute_action_digest()``
      (nonce differs per call) — not directly in this module.
- A1 (fail-closed metadata): callers use ``adapter_metadata.project()`` to build
      ``AdapterPermissionMetadata``; that function fails closed on missing fields.

This module is PURE — it does not write to ledger, TUI, or pipeline_v2.
Lead wires it into ``pipeline_v2.py`` at integration step (not this module).

Reference:
    specs/033-permission-v2-spectrum/spec.md §US3
    specs/033-permission-v2-spectrum/contracts/mode-transition.contract.md § 5
    specs/033-permission-v2-spectrum/data-model.md § 2.1 K1–K6
"""

from __future__ import annotations

import logging
from typing import Literal

from kosmos.permissions.models import AdapterPermissionMetadata, ToolPermissionContext

__all__ = [
    "KILLSWITCH_ORDER",
    "KillswitchReason",
    "pre_evaluate",
    "assert_killswitch_first",
]

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline order constant (Invariant K1)
# ---------------------------------------------------------------------------

KILLSWITCH_ORDER: int = 1
"""Step index (1-based) at which the killswitch MUST appear in the pipeline.

The pipeline has the following required order (contracts/mode-transition.contract.md § 5):
  1. killswitch.pre_evaluate()    ← this module; MUST be first (K1)
  2. mode.evaluate()
  3. rule.resolve()
  4. prompt.ask()

Any re-ordering MUST fail ``test_killswitch_priority_order`` (T035).
"""

# ---------------------------------------------------------------------------
# Killswitch trigger reasons
# ---------------------------------------------------------------------------

KillswitchReason = Literal["irreversible", "pipa_class_특수", "aal3"]
"""Machine-readable reason string for the killswitch OTEL span.

Values:
    ``irreversible``   — adapter.is_irreversible is True (K2).
    ``pipa_class_특수`` — adapter.pipa_class == "특수" (K3).
    ``aal3``           — adapter.auth_level == "AAL3" (K4).
"""

# ---------------------------------------------------------------------------
# High-risk modes that activate the killswitch
# ---------------------------------------------------------------------------

_BYPASS_MODES: frozenset[str] = frozenset({"bypassPermissions", "dontAsk"})
"""Modes under which the killswitch is evaluated.

Both ``bypassPermissions`` and ``dontAsk`` attempt to short-circuit normal
prompting.  The killswitch ensures they never silently execute irreversible,
PIPA 특수-class, or AAL3 tools.

Note: ``dontAsk`` is also caught here (see spec.md US3 Scenario 2: 'rule is
ignored') even though the task description mentions only ``bypassPermissions``.
The Constitution §II requirement is unambiguous: no mode can bypass killswitch.
"""


# ---------------------------------------------------------------------------
# Core function (T028)
# ---------------------------------------------------------------------------


def pre_evaluate(
    ctx: ToolPermissionContext,
    metadata: AdapterPermissionMetadata,
) -> Literal["ASK"] | None:
    """Run the NON-NEGOTIABLE killswitch pre-check before any mode evaluation.

    Returns ``"ASK"`` when the current session mode is a bypass mode AND any of
    the following killswitch conditions is true (K2, K3, K4):

    - ``metadata.is_irreversible is True`` — irreversible side-effect adapter (K2)
    - ``metadata.pipa_class == "특수"``   — PIPA special-category data (K3)
    - ``metadata.auth_level == "AAL3"``   — highest AAL requirement (K4)

    Returns ``None`` when:
    - The current mode is not a bypass mode (normal evaluation applies), OR
    - None of the above killswitch conditions is met.

    This function is PURE and STATELESS.  It does not mutate ctx or metadata,
    does not write to the ledger, and does not cache any result (K5).

    Invariant K1: This function MUST be called as step 1 in the pipeline,
    before ``mode.evaluate()``, ``rule.resolve()``, and ``prompt.ask()``.
    ``assert_killswitch_first()`` provides a structural assertion helper.

    Args:
        ctx: The per-invocation tool permission context (session mode, tool id, etc.).
        metadata: The frozen adapter permission metadata projection.

    Returns:
        ``"ASK"`` if the killswitch fires (citizen must be prompted, no exceptions).
        ``None`` if no killswitch condition is met (normal evaluation continues).
    """
    if ctx.mode not in _BYPASS_MODES:
        # Normal evaluation path — killswitch does not apply.
        return None

    reason: KillswitchReason | None = _evaluate_reason(metadata)
    if reason is None:
        # Bypass mode but no killswitch condition — silent allow is permitted
        # by mode semantics.
        return None

    _logger.warning(
        "Killswitch triggered: tool_id=%r mode=%r reason=%r "
        "session_id=%r correlation_id=%r — forcing ASK (K%s)",
        ctx.tool_id,
        ctx.mode,
        reason,
        ctx.session_id,
        ctx.correlation_id,
        _reason_to_invariant(reason),
    )
    return "ASK"


def _evaluate_reason(metadata: AdapterPermissionMetadata) -> KillswitchReason | None:
    """Return the first matching killswitch reason, or None if no condition fires.

    Priority: irreversible (K2) > pipa_class_특수 (K3) > aal3 (K4).
    (Priority only matters for OTEL reason attribute; all three mandate ASK.)
    """
    if metadata.is_irreversible:
        return "irreversible"
    if metadata.pipa_class == "특수":
        return "pipa_class_특수"
    if metadata.auth_level == "AAL3":
        return "aal3"
    return None


def _reason_to_invariant(reason: KillswitchReason) -> str:
    """Map a killswitch reason to the Constitution invariant tag for logging."""
    mapping: dict[KillswitchReason, str] = {
        "irreversible": "2",
        "pipa_class_특수": "3",
        "aal3": "4",
    }
    return mapping.get(reason, "?")


# ---------------------------------------------------------------------------
# Pipeline order assertion helper (T029)
# ---------------------------------------------------------------------------


def assert_killswitch_first(pipeline_step_order: list[str] | tuple[str, ...]) -> None:
    """Assert that the killswitch is the first step in the pipeline.

    This function provides a structural invariant check (K1) that can be
    called from test suites and pipeline wiring code.  It raises
    ``AssertionError`` if the killswitch step is not at index 0 (i.e.,
    the first element of ``pipeline_step_order``).

    Convention: each element of ``pipeline_step_order`` must be the
    fully-qualified step name as a string.  The killswitch step is
    identified by checking whether the element *contains* the substring
    ``"killswitch"``.

    Args:
        pipeline_step_order: An ordered sequence of step name strings
            representing the pipeline execution order, index 0 = first step.

    Raises:
        AssertionError: If the killswitch step is not at position 0.
        ValueError: If ``pipeline_step_order`` is empty.

    Example::

        >>> assert_killswitch_first(["killswitch.pre_evaluate", "mode.evaluate"])
        # passes silently

        >>> assert_killswitch_first(["mode.evaluate", "killswitch.pre_evaluate"])
        # AssertionError: Invariant K1 violation: ...
    """
    if not pipeline_step_order:
        raise ValueError(
            "assert_killswitch_first: pipeline_step_order must be non-empty. "
            "The pipeline must have at least one step."
        )

    first_step = pipeline_step_order[0]
    if "killswitch" not in first_step.lower():
        position = next(
            (i for i, s in enumerate(pipeline_step_order) if "killswitch" in s.lower()),
            -1,
        )
        raise AssertionError(
            f"Invariant K1 violation: killswitch step must be at position 0 "
            f"(first) in the pipeline order.  "
            f"Found killswitch at position {position} in order "
            f"{list(pipeline_step_order)!r}.  "
            "Any re-ordering of the pipeline that puts Mode/Rule/Prompt before "
            "Killswitch MUST fail this assertion.  "
            "Reference: specs/033-permission-v2-spectrum/contracts/"
            "mode-transition.contract.md § 5 — 'Killswitch runs FIRST'."
        )
