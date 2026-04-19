# SPDX-License-Identifier: Apache-2.0
"""Default permission mode resolver — Spec 033 FR-A01, US1.

This module implements the ``default`` mode decision logic: a tool call is
auto-allowed only when a persistent ``allow`` rule exists in the rule store
for the adapter.  In all other cases the pipeline falls through to the prompt.

Design constraints (hard rules from WS3 assignment):
  - DOES NOT edit ``pipeline_v2.py`` — Lead wires the resolver in.
  - DOES NOT edit ``rules.py`` or ``session_boot.py`` — WS2 territory.
  - The ``RuleStore`` is injected as a parameter (dependency injection).
  - No new runtime dependencies.

This module is stateless and side-effect-free: it only reads the rule store
and returns a decision.  All mutable state lives in the injected ``RuleStore``.

Reference:
  - specs/033-permission-v2-spectrum/spec.md §US1, FR-A01
  - specs/033-permission-v2-spectrum/data-model.md § 1.2 (PermissionRule)
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import TYPE_CHECKING, Literal, Protocol

from kosmos.permissions.models import ConsentDecision, ToolPermissionContext

if TYPE_CHECKING:
    pass

__all__ = ["resolve_default_mode"]

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# RuleStore protocol (structural typing — avoids circular import with WS2)
# ---------------------------------------------------------------------------


class RuleStore(Protocol):
    """Minimal interface for the persistent rule store (WS2 implementation).

    This protocol is structural: any object with a ``resolve(tool_id)`` method
    that returns a tri-state decision string is compatible.

    Invariant: ``resolve()`` MUST return one of ``"allow"`` | ``"ask"`` | ``"deny"``
    or ``None`` (no persistent rule).
    """

    def resolve(self, tool_id: str) -> Literal["allow", "ask", "deny"] | None:
        """Look up the persistent rule for *tool_id*.

        Args:
            tool_id: Canonical adapter identifier.

        Returns:
            ``"allow"`` — persistent allow rule exists.
            ``"deny"``  — persistent deny rule exists.
            ``"ask"``   — explicit ask rule exists (no persistent decision).
            ``None``    — no rule; the pipeline should ASK the citizen.
        """
        ...


# ---------------------------------------------------------------------------
# Public resolver
# ---------------------------------------------------------------------------


def resolve_default_mode(
    ctx: ToolPermissionContext,
    rule_store: RuleStore,
    *,
    action_digest: str | None = None,
) -> ConsentDecision | Literal["ASK"]:
    """Apply ``default`` mode logic to a tool permission context.

    ``default`` mode behaviour (FR-A01, CC 2.1.88 semantic parity):
    - If a persistent ``allow`` rule exists for the adapter → return an
      auto-generated ``ConsentDecision`` with ``granted=True``.
    - Otherwise → return the sentinel string ``"ASK"``, signalling that the
      pipeline must prompt the citizen for consent.

    ``"deny"`` rules in the rule store also cause the pipeline to bypass the
    prompt and return a denial.  This function returns ``"ASK"`` for all
    non-``allow`` cases because the caller (pipeline_v2.py) is responsible
    for converting the rule store ``deny`` result into the correct
    ``ConsentDecision(granted=False)`` — keeping this function single-purpose.

    Note: This function is deliberately PURE with respect to the ledger.  It
    does not append any record.  The caller is responsible for calling
    ``ledger.append()`` after this function returns (whether auto-allowed or
    prompted).

    Args:
        ctx: Per-invocation tool permission context.
        rule_store: Injected persistent rule store (WS2 implementation).
        action_digest: Pre-computed per-call digest from
            ``action_digest.compute_action_digest()``.  When supplied it is
            attached verbatim to the returned ConsentDecision so the
            pipeline-wide "one nonce per call" invariant (K6) survives.
            When ``None`` a deterministic correlation-id-derived fallback is
            used — correct for isolated unit tests but not for the audit
            trail, so pipeline_v2 always supplies a fresh nonce-based digest.

    Returns:
        ``ConsentDecision`` if the rule store has a persistent ``allow`` rule,
        or the sentinel string ``"ASK"`` if the pipeline should prompt.
    """
    if ctx.mode != "default":
        # This resolver is only authoritative for ``default`` mode.
        # Other modes are handled by their own resolvers (WS1 workstream).
        _logger.debug(
            "resolve_default_mode called for non-default mode %r; returning ASK",
            ctx.mode,
        )
        return "ASK"

    rule = rule_store.resolve(ctx.tool_id)

    if rule == "allow":
        _logger.debug(
            "default mode: persistent allow rule found for tool_id=%s → auto-allow",
            ctx.tool_id,
        )
        # Build a minimal ConsentDecision representing the auto-allow.
        # The PIPA 4-tuple fields are populated from the adapter metadata
        # where available; the pipeline_v2.py caller fills in the ledger record.
        # Use placeholder strings for fields not available at this layer
        # (the pipeline wires in the prompt builder which provides full 4-tuple).
        from datetime import datetime

        # Prefer the pipeline-supplied nonce-based digest (Invariant K6).  In
        # standalone unit tests (pipeline not wired) fall back to a
        # correlation-id-derived digest so this function stays callable.
        if action_digest is None:
            import hashlib

            from kosmos.permissions.canonical_json import canonicalize

            digest_input = canonicalize(
                {
                    "tool_id": ctx.tool_id,
                    "correlation_id": ctx.correlation_id,
                    "auto_allow": True,
                }
            )
            action_digest = hashlib.sha256(digest_input).hexdigest()

        return ConsentDecision(
            purpose="persistent_allow_rule",
            data_items=(ctx.adapter_metadata.pipa_class,),
            retention_period="persistent",
            refusal_right="동의 철회 가능 (/permissions revoke)",
            granted=True,
            tool_id=ctx.tool_id,
            pipa_class=ctx.adapter_metadata.pipa_class,
            auth_level=ctx.adapter_metadata.auth_level,
            decided_at=datetime.now(tz=UTC),
            action_digest=action_digest,
            scope="user",
        )

    # No rule, ask rule, or deny rule → signal the pipeline to prompt.
    _logger.debug(
        "default mode: rule=%r for tool_id=%s → ASK",
        rule,
        ctx.tool_id,
    )
    return "ASK"
