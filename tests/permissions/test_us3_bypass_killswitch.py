# SPDX-License-Identifier: Apache-2.0
"""Integration test — US3 bypassPermissions + irreversible adapter (T036).

User Story 3: Irreversible actions are NEVER silently executed under
bypassPermissions mode.  Every call prompts the citizen; every call gets a
DISTINCT action_digest in the ledger.

Test coverage:
  - ``bypassPermissions`` mode + ``is_irreversible=True`` × 2 calls
  - Both calls trigger the killswitch → ``"ASK"`` returned
  - The two ``action_digest`` values are DISTINCT (K6, SC-007)
  - ``dontAsk`` mode also triggers the killswitch (spec.md US3 §2)
  - Non-bypass mode does NOT trigger the killswitch
  - Non-irreversible adapter does NOT trigger the killswitch in bypass mode
  - pipa_class=``특수`` triggers the killswitch (K3)
  - auth_level=``AAL3`` triggers the killswitch (K4)

Reference:
    specs/033-permission-v2-spectrum/spec.md §US3
    specs/033-permission-v2-spectrum/data-model.md § 2.1 K2/K3/K4/K5/K6
    specs/033-permission-v2-spectrum/tasks.md T036
"""

from __future__ import annotations

from kosmos.permissions.action_digest import compute_action_digest, generate_nonce
from kosmos.permissions.killswitch import pre_evaluate
from kosmos.permissions.mode_bypass import resolve_bypass_mode
from kosmos.permissions.models import AdapterPermissionMetadata, ToolPermissionContext

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_metadata(
    *,
    tool_id: str = "minwon_submit",
    is_irreversible: bool = True,
    auth_level: str = "AAL2",
    pipa_class: str = "일반",
    requires_auth: bool = True,
    auth_type: str = "oauth",
) -> AdapterPermissionMetadata:
    """Build an AdapterPermissionMetadata for testing."""
    return AdapterPermissionMetadata(
        tool_id=tool_id,
        is_irreversible=is_irreversible,
        auth_level=auth_level,  # type: ignore[arg-type]
        pipa_class=pipa_class,  # type: ignore[arg-type]
        requires_auth=requires_auth,
        auth_type=auth_type,  # type: ignore[arg-type]
    )


def _make_ctx(
    *,
    tool_id: str = "minwon_submit",
    mode: str = "bypassPermissions",
    is_irreversible: bool = True,
    auth_level: str = "AAL2",
    pipa_class: str = "일반",
    session_id: str = "test-session-us3",
    correlation_id: str = "corr-001",
    arguments: dict | None = None,
    adapter_metadata: AdapterPermissionMetadata | None = None,
) -> ToolPermissionContext:
    """Build a ToolPermissionContext for testing."""
    meta = adapter_metadata or _make_metadata(
        tool_id=tool_id,
        is_irreversible=is_irreversible,
        auth_level=auth_level,
        pipa_class=pipa_class,
    )
    return ToolPermissionContext(
        tool_id=tool_id,
        mode=mode,  # type: ignore[arg-type]
        is_irreversible=is_irreversible,
        auth_level=auth_level,  # type: ignore[arg-type]
        pipa_class=pipa_class,  # type: ignore[arg-type]
        session_id=session_id,
        correlation_id=correlation_id,
        arguments=arguments or {"form": "minwon_form_a", "applicant": "citizen_01"},
        adapter_metadata=meta,
    )


# ---------------------------------------------------------------------------
# Core US3 invariant: bypassPermissions + irreversible → ASK every call
# ---------------------------------------------------------------------------


class TestBypassIrreversibleKillswitch:
    """killswitch.pre_evaluate fires for bypassPermissions + irreversible (K2)."""

    def test_single_call_returns_ask(self) -> None:
        """Single call in bypass mode with irreversible adapter returns ASK."""
        ctx = _make_ctx(mode="bypassPermissions", is_irreversible=True)
        meta = ctx.adapter_metadata
        result = pre_evaluate(ctx, meta)
        assert result == "ASK", (
            f"Expected 'ASK' for bypassPermissions+irreversible, got {result!r} (K2)"
        )

    def test_two_consecutive_calls_both_return_ask(self) -> None:
        """Two consecutive bypass+irreversible calls BOTH return ASK (K2, K5 — no caching)."""
        ctx1 = _make_ctx(mode="bypassPermissions", is_irreversible=True, correlation_id="corr-001")
        ctx2 = _make_ctx(mode="bypassPermissions", is_irreversible=True, correlation_id="corr-002")

        result1 = pre_evaluate(ctx1, ctx1.adapter_metadata)
        result2 = pre_evaluate(ctx2, ctx2.adapter_metadata)

        assert result1 == "ASK", f"First call must return ASK, got {result1!r}"
        assert result2 == "ASK", f"Second call must return ASK, got {result2!r}"

    def test_two_calls_produce_distinct_action_digests(self) -> None:
        """Two identical bypass+irreversible calls get DISTINCT action_digests (K6, SC-007)."""
        tool_id = "minwon_submit"
        arguments = {"form": "minwon_form_a", "applicant": "citizen_01"}

        nonce1 = generate_nonce()
        nonce2 = generate_nonce()

        digest1 = compute_action_digest(tool_id, arguments, nonce1)
        digest2 = compute_action_digest(tool_id, arguments, nonce2)

        assert digest1 != digest2, (
            "Invariant K6: two bypass calls with identical tool_id+arguments must "
            "produce DISTINCT action_digests.  Nonces differ per call, so digests must differ."
        )
        assert len(digest1) == 64, f"SHA-256 hex must be 64 chars, got {len(digest1)}"
        assert len(digest2) == 64, f"SHA-256 hex must be 64 chars, got {len(digest2)}"
        # Verify hex pattern
        assert all(c in "0123456789abcdef" for c in digest1), "digest1 must be lowercase hex"
        assert all(c in "0123456789abcdef" for c in digest2), "digest2 must be lowercase hex"


# ---------------------------------------------------------------------------
# K3: pipa_class=특수 triggers killswitch in bypass mode
# ---------------------------------------------------------------------------


class TestBypassPipaClassToksuKillswitch:
    """killswitch.pre_evaluate fires for bypassPermissions + pipa_class=특수 (K3)."""

    def test_toksu_class_returns_ask(self) -> None:
        """pipa_class=특수 in bypass mode returns ASK (K3)."""
        ctx = _make_ctx(mode="bypassPermissions", is_irreversible=False, pipa_class="특수")
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result == "ASK", f"Expected 'ASK' for pipa_class=특수, got {result!r} (K3)"

    def test_toksu_class_in_dontask_mode_returns_ask(self) -> None:
        """pipa_class=특수 in dontAsk mode also returns ASK (spec.md US3 §2)."""
        ctx = _make_ctx(mode="dontAsk", is_irreversible=False, pipa_class="특수")
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result == "ASK", f"Expected 'ASK' for pipa_class=특수+dontAsk, got {result!r}"


# ---------------------------------------------------------------------------
# K4: auth_level=AAL3 triggers killswitch in bypass mode
# ---------------------------------------------------------------------------


class TestBypassAAL3Killswitch:
    """killswitch.pre_evaluate fires for bypassPermissions + auth_level=AAL3 (K4)."""

    def test_aal3_returns_ask(self) -> None:
        """auth_level=AAL3 in bypass mode returns ASK (K4)."""
        ctx = _make_ctx(mode="bypassPermissions", is_irreversible=False, auth_level="AAL3")
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result == "ASK", f"Expected 'ASK' for AAL3 bypass, got {result!r} (K4)"

    def test_aal3_in_dontask_mode_returns_ask(self) -> None:
        """auth_level=AAL3 in dontAsk mode also returns ASK."""
        ctx = _make_ctx(mode="dontAsk", is_irreversible=False, auth_level="AAL3")
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result == "ASK", f"Expected 'ASK' for AAL3+dontAsk, got {result!r}"


# ---------------------------------------------------------------------------
# Non-killswitch paths: normal modes + non-triggering adapters → None
# ---------------------------------------------------------------------------


class TestNonKillswitchPaths:
    """Killswitch returns None for non-triggering combinations."""

    def test_default_mode_no_killswitch(self) -> None:
        """default mode never triggers the killswitch (killswitch targets bypass modes)."""
        ctx = _make_ctx(mode="default", is_irreversible=True)
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result is None, (
            f"Expected None for default+irreversible (killswitch only fires in bypass modes), "
            f"got {result!r}"
        )

    def test_plan_mode_no_killswitch(self) -> None:
        """plan mode never triggers the killswitch."""
        ctx = _make_ctx(mode="plan", is_irreversible=True)
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result is None

    def test_accept_edits_mode_no_killswitch(self) -> None:
        """acceptEdits mode never triggers the killswitch."""
        ctx = _make_ctx(mode="acceptEdits", is_irreversible=True)
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result is None

    def test_bypass_mode_reversible_aal1_general_returns_none(self) -> None:
        """Reversible + AAL1 + 일반 adapter in bypass mode: no killswitch trigger."""
        ctx = _make_ctx(
            mode="bypassPermissions",
            is_irreversible=False,
            auth_level="AAL1",
            pipa_class="일반",
        )
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result is None, (
            f"Expected None for reversible+AAL1+일반 in bypass mode, got {result!r}"
        )

    def test_bypass_mode_aal2_personal_reversible_returns_none(self) -> None:
        """AAL2 + 일반 pipa_class + reversible adapter in bypass mode: no trigger."""
        # AAL2 is not AAL3, so no K4. 일반 is not 특수, so no K3.
        # Not irreversible, so no K2. → no killswitch.
        ctx = _make_ctx(
            mode="bypassPermissions",
            is_irreversible=False,
            auth_level="AAL2",
            pipa_class="일반",
        )
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result is None

    def test_bypass_mode_sensitive_with_irreversible_triggers_irreversible_reason(self) -> None:
        """irreversible takes priority over pipa_class=민감 in reason evaluation."""
        ctx = _make_ctx(
            mode="bypassPermissions",
            is_irreversible=True,
            pipa_class="민감",  # Should trigger K2 (irreversible) first
        )
        result = pre_evaluate(ctx, ctx.adapter_metadata)
        assert result == "ASK"


# ---------------------------------------------------------------------------
# mode_bypass.resolve_bypass_mode() — defense-in-depth backstop
# ---------------------------------------------------------------------------


class TestResolvBypassMode:
    """resolve_bypass_mode() is the defense-in-depth backstop."""

    def test_irreversible_returns_ask(self) -> None:
        """Irreversible adapter → resolve_bypass_mode returns ASK."""
        ctx = _make_ctx(mode="bypassPermissions", is_irreversible=True)
        result = resolve_bypass_mode(ctx, ctx.adapter_metadata)
        assert result == "ASK"

    def test_reversible_returns_allow(self) -> None:
        """Reversible + non-triggering adapter → resolve_bypass_mode returns ALLOW."""
        ctx = _make_ctx(
            mode="bypassPermissions",
            is_irreversible=False,
            auth_level="AAL1",
            pipa_class="일반",
        )
        result = resolve_bypass_mode(ctx, ctx.adapter_metadata)
        assert result == "ALLOW"

    def test_function_has_no_cache_parameter(self) -> None:
        """resolve_bypass_mode must NOT have a 'cache' parameter (Invariant K5)."""
        import inspect  # noqa: PLC0415

        sig = inspect.signature(resolve_bypass_mode)
        assert "cache" not in sig.parameters, (
            "Invariant K5: resolve_bypass_mode MUST NOT have a 'cache' parameter. "
            "Caching bypass-mode decisions is explicitly prohibited."
        )

    def test_function_is_not_memoized(self) -> None:
        """resolve_bypass_mode must not be decorated with functools.lru_cache or similar (K5)."""
        # Check for common memoization decorators
        func = resolve_bypass_mode
        assert not hasattr(func, "cache_info"), (
            "Invariant K5: resolve_bypass_mode must not be memoized with lru_cache."
        )
        assert not hasattr(func, "__wrapped__") or "cache" not in str(
            getattr(func, "__wrapped__", "")
        ), "Invariant K5: resolve_bypass_mode must not be wrapped with a caching decorator."


# ---------------------------------------------------------------------------
# action_digest — unique nonce per call (K6)
# ---------------------------------------------------------------------------


class TestActionDigestDistinctness:
    """compute_action_digest produces distinct digests when nonces differ (K6)."""

    def test_distinct_digests_for_100_calls(self) -> None:
        """100 consecutive calls with uuid7 nonces produce 100 distinct digests (K6)."""
        tool_id = "minwon_submit"
        arguments = {"form": "A", "applicant": "citizen_01"}

        digests = {compute_action_digest(tool_id, arguments, generate_nonce()) for _ in range(100)}

        assert len(digests) == 100, (
            f"Expected 100 distinct digests, got {len(digests)}. "
            "Invariant K6: each bypass call must produce a unique action_digest."
        )

    def test_digest_is_64_hex_chars(self) -> None:
        """action_digest must be 64 lowercase hexadecimal characters (SHA-256)."""
        digest = compute_action_digest("test_tool", {"a": 1}, generate_nonce())
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_deterministic_given_same_nonce(self) -> None:
        """Same tool_id + arguments + nonce → same digest (deterministic)."""
        nonce = generate_nonce()
        d1 = compute_action_digest("test_tool", {"a": 1}, nonce)
        d2 = compute_action_digest("test_tool", {"a": 1}, nonce)
        assert d1 == d2, "Same inputs must produce same digest (determinism check)"

    def test_different_arguments_produce_different_digests(self) -> None:
        """Different arguments → different digests (same nonce for isolation)."""
        nonce = generate_nonce()
        d1 = compute_action_digest("test_tool", {"a": 1}, nonce)
        d2 = compute_action_digest("test_tool", {"a": 2}, nonce)
        assert d1 != d2, "Different arguments must produce different digests"


# ---------------------------------------------------------------------------
# SC-007: Two bypass calls → 2 ledger records with distinct action_digests
# ---------------------------------------------------------------------------


class TestUS3AcceptanceScenario1:
    """SC-007 acceptance: bypassPermissions + irreversible × 2 → 2 distinct digests.

    Mirrors quickstart.md scenario 3 / tasks.md T036.
    """

    def test_two_bypass_calls_produce_two_distinct_digests(self) -> None:
        """Simulate US3 scenario 1: bypass + irreversible × 2 calls.

        Assertions:
          (1) Both pre_evaluate calls return "ASK" (killswitch fires each time).
          (2) Two distinct action_digest values would appear in ledger (K6).
        """
        tool_id = "minwon_submit"
        arguments = {"form": "minwon_form_a", "applicant": "citizen_01"}

        # Call 1
        ctx1 = _make_ctx(
            mode="bypassPermissions",
            is_irreversible=True,
            correlation_id="corr-call-1",
        )
        result1 = pre_evaluate(ctx1, ctx1.adapter_metadata)

        # Call 2 — same parameters, different correlation_id (new IPC envelope)
        ctx2 = _make_ctx(
            mode="bypassPermissions",
            is_irreversible=True,
            correlation_id="corr-call-2",
        )
        result2 = pre_evaluate(ctx2, ctx2.adapter_metadata)

        # Assertion (1): both prompts appeared (killswitch fired)
        assert result1 == "ASK", f"Call 1 must trigger ASK, got {result1!r}"
        assert result2 == "ASK", f"Call 2 must trigger ASK, got {result2!r}"

        # Assertion (2): distinct digests would be recorded in ledger (K6)
        nonce1 = generate_nonce()
        nonce2 = generate_nonce()
        digest1 = compute_action_digest(tool_id, arguments, nonce1)
        digest2 = compute_action_digest(tool_id, arguments, nonce2)

        assert digest1 != digest2, (
            "Invariant K6 / SC-007: ledger MUST have 2 records with DISTINCT "
            "action_digest values.  Identical action_digests would indicate "
            "replay / caching violation."
        )
