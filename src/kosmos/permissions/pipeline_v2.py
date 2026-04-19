# SPDX-License-Identifier: Apache-2.0
"""Permission pipeline v2 — Spec 033 (Epic #1297).

The v2 entry point ``evaluate()`` composes the five parallel workstream
modules into a single ordered gauntlet.  ``pipeline.py`` (the legacy v1
gauntlet) is NOT modified so existing behaviour is preserved.

Four-step pipeline order (contracts/mode-transition.contract.md § 5):
  1. ``killswitch.pre_evaluate(ctx)`` — NON-NEGOTIABLE pre-check (K1-K6).
     Runs BEFORE mode evaluation.  Cannot be short-circuited by any config.
  2. ``mode.evaluate(ctx)``           — Apply mode-specific auto-allow logic.
  3. ``rule.resolve(ctx)``            — Tri-state rule store lookup.
  4. ``prompt.ask(ctx)``              — Fallback: ask the citizen (PIPA 4-tuple).

Before step 1 we run an ``aal_backstop.check_aal_downgrade`` pre-dispatch
check (FR-F02) so a weaker runtime session can never execute a call that was
authorised at a higher AAL.  The pre-dispatch is ordered BEFORE killswitch
only because it is a cryptographic identity check and raising inside it
surfaces an explicit exception — it does not alter the documented
killswitch → mode → rule → prompt order.

Invariant P1 (contracts/mode-transition.contract.md § 5):
    Killswitch is step 1.  No exception.  Any implementation that runs
    Mode before Killswitch MUST fail ``test_killswitch_priority_order``.

Invariant P2:
    Killswitch returns ASK (forces the prompt to appear), not ALLOW/DENY.
    The citizen still makes the final decision.

Reference:
    specs/033-permission-v2-spectrum/contracts/mode-transition.contract.md § 5
    specs/033-permission-v2-spectrum/data-model.md § 2.1 (K1-K6)
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from kosmos.permissions import aal_backstop, killswitch, mode_bypass, mode_default
from kosmos.permissions.action_digest import compute_action_digest, generate_nonce
from kosmos.permissions.ledger import append as ledger_append
from kosmos.permissions.models import ConsentDecision, ToolPermissionContext
from kosmos.permissions.prompt import PIPAConsentPrompt
from kosmos.permissions.prompt import build as build_prompt
from kosmos.permissions.rules import RuleStore, ScopeContext

__all__ = [
    "ConsentPromptRequest",
    "ConsentPromptResponder",
    "LedgerConfig",
    "evaluate",
]

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Injectable inputs (kept as frozen dataclasses — stdlib only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsentPromptRequest:
    """PIPA §15(2) 4-tuple supplied by the adapter layer.

    The pipeline does not invent PIPA disclosures — the adapter declares the
    purpose, items, retention period, and refusal-rights copy that the citizen
    sees.  Attached to ``evaluate()`` only when the pipeline may reach Step 4.
    """

    purpose: str
    data_items: tuple[str, ...]
    retention_period: str
    refusal_right: str


@dataclass(frozen=True)
class LedgerConfig:
    """Filesystem paths required by ``ledger.append()`` at Step 4 grant time."""

    ledger_path: Path
    key_path: Path
    key_registry_path: Path


ConsentPromptResponder = Callable[[PIPAConsentPrompt], Awaitable[bool]]
"""Async callback invoked when the pipeline must ask the citizen.

The responder receives a fully-built ``PIPAConsentPrompt`` (renderable via
``prompt.render_text()``) and returns ``True`` (granted) or ``False``
(refused).  The TUI harness owns the rendering; this module only wires the
decision back into a ``ConsentDecision``.
"""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _RuleStoreDefaultModeAdapter:
    """Adapter bridging ``rules.RuleStore`` (two-arg) to the Protocol (one-arg).

    ``mode_default.resolve_default_mode()`` depends on a Protocol with
    ``resolve(tool_id) -> Literal["allow", "ask", "deny"] | None``.  The real
    ``rules.RuleStore.resolve(tool_id, scope_ctx)`` is two-argument and returns
    ``Literal["allow", "deny"] | None`` (None ≡ ask per Invariant R3).

    This adapter binds the ``scope_ctx`` at construction and maps ``None`` to
    ``"ask"`` so callers that want to distinguish the two get the semantic the
    Protocol documents.  "allow" / "deny" pass through unchanged.
    """

    __slots__ = ("_store", "_scope_ctx")

    def __init__(self, store: RuleStore, scope_ctx: ScopeContext) -> None:
        self._store = store
        self._scope_ctx = scope_ctx

    def resolve(self, tool_id: str) -> Literal["allow", "ask", "deny"] | None:
        result = self._store.resolve(tool_id, self._scope_ctx)
        if result is None:
            return "ask"
        return result


def _auto_allow_decision(
    ctx: ToolPermissionContext,
    *,
    scope: Literal["one-shot", "session", "user"],
    reason: str,
    action_digest: str,
) -> ConsentDecision:
    """Build a ``ConsentDecision(granted=True)`` for mode/rule auto-approve paths.

    The PIPA 4-tuple carries a placeholder purpose because auto-approve by
    definition did NOT render a prompt — Step 4 is where the full adapter
    tuple lands.  Callers that want the full 4-tuple in the decision must
    pass through Step 4.
    """
    return ConsentDecision(
        purpose=reason,
        data_items=(ctx.adapter_metadata.pipa_class,),
        retention_period="persistent" if scope == "user" else "일회성",
        refusal_right="동의 철회 가능 (/permissions revoke)",
        granted=True,
        tool_id=ctx.tool_id,
        pipa_class=ctx.adapter_metadata.pipa_class,
        auth_level=ctx.adapter_metadata.auth_level,
        decided_at=datetime.now(tz=UTC),
        action_digest=action_digest,
        scope=scope,
    )


def _auto_deny_decision(
    ctx: ToolPermissionContext,
    *,
    reason: str,
    action_digest: str,
) -> ConsentDecision:
    """Build a ``ConsentDecision(granted=False)`` for persistent deny rule paths."""
    return ConsentDecision(
        purpose=reason,
        data_items=(ctx.adapter_metadata.pipa_class,),
        retention_period="일회성",
        refusal_right="동의 철회 가능 (/permissions revoke)",
        granted=False,
        tool_id=ctx.tool_id,
        pipa_class=ctx.adapter_metadata.pipa_class,
        auth_level=ctx.adapter_metadata.auth_level,
        decided_at=datetime.now(tz=UTC),
        action_digest=action_digest,
        scope="one-shot",
    )


def _fresh_action_digest(
    ctx: ToolPermissionContext,
    arguments: Mapping[str, object] | None,
) -> str:
    """Compute a fresh per-call action digest (K6 distinct-digest guarantee).

    Uses the provided ``arguments`` if supplied; otherwise falls back to the
    ``ctx.arguments`` mapping.  A fresh nonce is generated on every call so
    two identical invocations produce distinct digests.
    """
    args = arguments if arguments is not None else dict(ctx.arguments)
    return compute_action_digest(ctx.tool_id, args, generate_nonce())


def _evaluate_plan_mode(
    ctx: ToolPermissionContext, action_digest: str
) -> ConsentDecision | Literal["ASK"]:
    """``plan`` mode: dry-run — auto-allow only reversible, non-sensitive calls."""
    md = ctx.adapter_metadata
    if md.is_irreversible or md.pipa_class != "일반":
        return "ASK"
    return _auto_allow_decision(
        ctx,
        scope="one-shot",
        reason="plan_mode_dry_run",
        action_digest=action_digest,
    )


def _evaluate_accept_edits_mode(
    ctx: ToolPermissionContext, action_digest: str
) -> ConsentDecision | Literal["ASK"]:
    """``acceptEdits`` mode: auto-approve reversible public / AAL1 calls."""
    md = ctx.adapter_metadata
    if md.is_irreversible:
        return "ASK"
    if md.auth_level not in {"public", "AAL1"}:
        return "ASK"
    if md.pipa_class in {"민감", "고유식별", "특수"}:
        return "ASK"
    return _auto_allow_decision(
        ctx,
        scope="one-shot",
        reason="accept_edits_reversible_low_risk",
        action_digest=action_digest,
    )


def _resolve_rule(
    ctx: ToolPermissionContext,
    rule_store: RuleStore,
    scope_ctx: ScopeContext,
    action_digest: str,
) -> ConsentDecision | None:
    """Step 3: persistent tri-state rule lookup (used by non-default modes)."""
    verdict = rule_store.resolve(ctx.tool_id, scope_ctx)
    if verdict == "allow":
        return _auto_allow_decision(
            ctx,
            scope="user",
            reason="persistent_allow_rule",
            action_digest=action_digest,
        )
    if verdict == "deny":
        return _auto_deny_decision(
            ctx,
            reason="persistent_deny_rule",
            action_digest=action_digest,
        )
    return None


def _record_auto_decision(
    ctx: ToolPermissionContext,
    *,
    decision: ConsentDecision,
    action_digest: str,
    ledger_config: LedgerConfig | None,
) -> None:
    """Persist a non-prompt decision to the consent ledger.

    Mode- and rule-store-driven decisions never pass through
    ``_prompt_and_record``, so this helper records them directly.  Keeping the
    audit trail complete (Invariant L1 + FR-D02) is the reason this is called
    from ``evaluate()`` before returning auto-approved / auto-denied paths.
    """
    if ledger_config is None:
        return
    ledger_append(
        tool_id=ctx.tool_id,
        mode=ctx.mode,
        granted=decision.granted,
        action_digest=action_digest,
        purpose=decision.purpose,
        data_items=decision.data_items,
        retention_period=decision.retention_period,
        refusal_right=decision.refusal_right,
        pipa_class=ctx.adapter_metadata.pipa_class,
        auth_level=ctx.adapter_metadata.auth_level,
        session_id=ctx.session_id,
        correlation_id=ctx.correlation_id,
        ledger_path=ledger_config.ledger_path,
        key_path=ledger_config.key_path,
        key_registry_path=ledger_config.key_registry_path,
    )


async def _prompt_and_record(
    ctx: ToolPermissionContext,
    consent_request: ConsentPromptRequest,
    responder: ConsentPromptResponder,
    ledger_config: LedgerConfig | None,
    action_digest: str,
) -> ConsentDecision:
    """Step 4: render PIPA prompt, await citizen response, seal the ledger record.

    The PIPA ``data_items`` tuple is flattened to a newline-separated string for
    the prompt model (which uses ``StrictStr``) while the ``ConsentDecision`` we
    return keeps the original tuple shape for audit consumers.
    """
    prompt = build_prompt(
        tool_id=ctx.tool_id,
        pipa_class=ctx.adapter_metadata.pipa_class,
        auth_level=ctx.adapter_metadata.auth_level,
        purpose=consent_request.purpose,
        data_items="\n".join(consent_request.data_items),
        retention_period=consent_request.retention_period,
        refusal_right=consent_request.refusal_right,
    )
    granted = await responder(prompt)

    decision = ConsentDecision(
        purpose=consent_request.purpose,
        data_items=consent_request.data_items,
        retention_period=consent_request.retention_period,
        refusal_right=consent_request.refusal_right,
        granted=granted,
        tool_id=ctx.tool_id,
        pipa_class=ctx.adapter_metadata.pipa_class,
        auth_level=ctx.adapter_metadata.auth_level,
        decided_at=datetime.now(tz=UTC),
        action_digest=action_digest,
        scope="one-shot",
    )

    if ledger_config is not None:
        ledger_append(
            tool_id=ctx.tool_id,
            mode=ctx.mode,
            granted=granted,
            action_digest=action_digest,
            purpose=consent_request.purpose,
            data_items=consent_request.data_items,
            retention_period=consent_request.retention_period,
            refusal_right=consent_request.refusal_right,
            pipa_class=ctx.adapter_metadata.pipa_class,
            auth_level=ctx.adapter_metadata.auth_level,
            session_id=ctx.session_id,
            correlation_id=ctx.correlation_id,
            ledger_path=ledger_config.ledger_path,
            key_path=ledger_config.key_path,
            key_registry_path=ledger_config.key_registry_path,
        )

    return decision


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


async def evaluate(
    ctx: ToolPermissionContext,
    *,
    rule_store: RuleStore,
    scope_ctx: ScopeContext | None = None,
    ctx_at_exec: ToolPermissionContext | None = None,
    arguments_for_digest: Mapping[str, object] | None = None,
    consent_request: ConsentPromptRequest | None = None,
    prompt_responder: ConsentPromptResponder | None = None,
    ledger_config: LedgerConfig | None = None,
) -> ConsentDecision:
    """Evaluate a tool call through the v2 permission pipeline.

    Pipeline steps (in required order):
      1. ``killswitch.pre_evaluate(ctx)`` — irreversible / AAL3 / 특수 gate (K1).
      2. ``mode.evaluate(ctx)``           — mode-specific auto-allow/deny.
      3. ``rule.resolve(ctx)``            — persistent tri-state rule lookup.
      4. ``prompt.ask(ctx)``              — citizen consent prompt fallback.

    A pre-dispatch ``aal_backstop.check_aal_downgrade`` check runs first
    (FR-F02); it raises ``AALDowngradeBlocked`` rather than returning a
    ``ConsentDecision``, so the documented four-step order above is preserved
    for Invariant K1 / P1.

    Args:
        ctx: The per-invocation tool permission context at prompt time.
        rule_store: Persistent tri-state rule store (required).
        scope_ctx: In-memory session + project rules.  Defaults to empty.
        ctx_at_exec: Execution-time context for the AAL backstop.  Defaults
            to ``ctx`` (no downgrade possible when they are the same object).
        arguments_for_digest: Arguments to hash into the action digest.
            When ``None`` the digest covers ``ctx.arguments``.
        consent_request: PIPA 4-tuple supplied by the adapter.  Required
            when the pipeline may reach Step 4 (killswitch ASK, mode ASK, or
            rule lookup returning no verdict).
        prompt_responder: Async callback that renders the prompt and returns
            the citizen's boolean decision.  Required for Step 4.
        ledger_config: Filesystem paths for ``ledger.append``.  Optional —
            omit to disable ledger writes (used only by tests that mock the
            ledger).

    Returns:
        A ``ConsentDecision`` indicating whether the tool call is granted or
        denied, along with the PIPA 4-tuple fields and ledger-binding digest.

    Raises:
        aal_backstop.AALDowngradeBlocked: if ``ctx_at_exec.auth_level`` differs
            from ``ctx.auth_level`` (FR-F02).
        RuntimeError: if the pipeline needs to prompt but no ``consent_request``
            / ``prompt_responder`` was supplied.
    """
    # ------------------------------------------------------------------
    # Step 0 (pre-dispatch, FR-F02) — AAL backstop.
    # ------------------------------------------------------------------
    aal_backstop.check_aal_downgrade(ctx, ctx_at_exec if ctx_at_exec is not None else ctx)

    # Compute a single per-call action digest.  K6 requires distinctness across
    # identical calls — satisfied by the nonce inside ``compute_action_digest``.
    action_digest = _fresh_action_digest(ctx, arguments_for_digest)

    effective_scope = scope_ctx if scope_ctx is not None else ScopeContext()

    # ------------------------------------------------------------------
    # Step 1 — Killswitch (Invariant P1 / K1).  If it fires, jump directly
    # to Step 4; mode and rule are bypassed so the citizen always decides.
    # ------------------------------------------------------------------
    killswitch_verdict = killswitch.pre_evaluate(ctx, ctx.adapter_metadata)
    if killswitch_verdict == "ASK":
        return await _run_prompt_fallback(
            ctx,
            consent_request=consent_request,
            prompt_responder=prompt_responder,
            ledger_config=ledger_config,
            action_digest=action_digest,
        )

    # ------------------------------------------------------------------
    # Step 2 — Mode evaluation.
    # ------------------------------------------------------------------
    mode_verdict = _dispatch_mode(
        ctx,
        rule_store=rule_store,
        scope_ctx=effective_scope,
        action_digest=action_digest,
    )
    if isinstance(mode_verdict, ConsentDecision):
        _record_auto_decision(
            ctx,
            decision=mode_verdict,
            action_digest=action_digest,
            ledger_config=ledger_config,
        )
        return mode_verdict

    # ------------------------------------------------------------------
    # Step 3 — Persistent rule resolve (skipped for ``default`` mode because
    # ``resolve_default_mode`` already walked the rule store for the "allow"
    # shortcut; we still need a second look to honour "deny" rules).
    # ------------------------------------------------------------------
    rule_decision = _resolve_rule(ctx, rule_store, effective_scope, action_digest)
    if rule_decision is not None:
        _record_auto_decision(
            ctx,
            decision=rule_decision,
            action_digest=action_digest,
            ledger_config=ledger_config,
        )
        return rule_decision

    # ------------------------------------------------------------------
    # Step 4 — Prompt fallback.
    # ------------------------------------------------------------------
    return await _run_prompt_fallback(
        ctx,
        consent_request=consent_request,
        prompt_responder=prompt_responder,
        ledger_config=ledger_config,
        action_digest=action_digest,
    )


# ---------------------------------------------------------------------------
# Mode + prompt dispatch helpers (kept small so evaluate() reads top-to-bottom)
# ---------------------------------------------------------------------------


def _dispatch_mode(
    ctx: ToolPermissionContext,
    *,
    rule_store: RuleStore,
    scope_ctx: ScopeContext,
    action_digest: str,
) -> ConsentDecision | Literal["ASK"]:
    """Route mode-specific evaluation to the matching resolver."""
    if ctx.mode == "default":
        adapter = _RuleStoreDefaultModeAdapter(rule_store, scope_ctx)
        result = mode_default.resolve_default_mode(ctx, adapter, action_digest=action_digest)
        if isinstance(result, ConsentDecision):
            return result
        return "ASK"

    if ctx.mode == "bypassPermissions":
        verdict = mode_bypass.resolve_bypass_mode(ctx, ctx.adapter_metadata)
        if verdict == "ALLOW":
            return _auto_allow_decision(
                ctx,
                scope="one-shot",
                reason="bypassPermissions_silent_allow",
                action_digest=action_digest,
            )
        return "ASK"

    if ctx.mode == "dontAsk":
        # dontAsk is allow-list only: require an explicit allow rule in the
        # store.  When no rule exists we fall through to the default-mode
        # behavior (which resolves the prompt), never silent-allow.
        verdict = mode_bypass.resolve_bypass_mode(ctx, ctx.adapter_metadata)
        if verdict == "ASK":
            return "ASK"
        adapter = _RuleStoreDefaultModeAdapter(rule_store, scope_ctx)
        default_result = mode_default.resolve_default_mode(
            ctx, adapter, action_digest=action_digest
        )
        if isinstance(default_result, ConsentDecision):
            return default_result
        return "ASK"

    if ctx.mode == "plan":
        return _evaluate_plan_mode(ctx, action_digest)

    if ctx.mode == "acceptEdits":
        return _evaluate_accept_edits_mode(ctx, action_digest)

    # Unknown mode — conservative fallback to prompt.
    _logger.warning("pipeline_v2: unknown mode %r — falling through to prompt", ctx.mode)
    return "ASK"


async def _run_prompt_fallback(
    ctx: ToolPermissionContext,
    *,
    consent_request: ConsentPromptRequest | None,
    prompt_responder: ConsentPromptResponder | None,
    ledger_config: LedgerConfig | None,
    action_digest: str,
) -> ConsentDecision:
    """Validate caller-supplied prompt dependencies before entering Step 4."""
    if consent_request is None or prompt_responder is None:
        raise RuntimeError(
            "pipeline_v2.evaluate reached Step 4 (prompt) but the caller did not "
            "supply `consent_request` + `prompt_responder`.  Wire the TUI layer "
            "to provide both before invoking the pipeline for this adapter."
        )
    return await _prompt_and_record(
        ctx,
        consent_request=consent_request,
        responder=prompt_responder,
        ledger_config=ledger_config,
        action_digest=action_digest,
    )
