# SPDX-License-Identifier: Apache-2.0
"""Integration test — US4 tri-state persistence across restarts (T040).

Quickstart Scenario 4:
  1. Write 3 user-scope rules: allow / deny / ask for three distinct adapters.
  2. Simulate process restart: re-instantiate the ``RuleStore`` from the same
     path (without carrying over in-memory state).
  3. Assert that ``resolve()`` returns the expected result for each adapter
     (SC-002 acceptance criteria).

Scenario 4 details:
  - adapter ``kma_forecast_fetch``     → decision ``allow``
  - adapter ``hira_hospital_search``   → decision ``deny``
  - adapter ``nmc_emergency_search``   → decision ``ask`` (≡ None per R3)

After restart all three rules are loaded from disk and resolve correctly.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kosmos.permissions.rules import RuleStore, ScopeContext, make_rule
from kosmos.permissions.session_boot import reset_session_state

# ---------------------------------------------------------------------------
# Helper: create a valid empty permissions.json for testing
# ---------------------------------------------------------------------------


def _create_valid_store(path: Path) -> None:
    """Write a valid (initially empty) permissions.json at *path*."""
    import json

    doc = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "rules": [],
    }
    # Write with mode 0o600
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(doc).encode("utf-8"))
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUS4TriStatePersistence:
    """Scenario 4 integration: 3 rules → restart → 3 expected behaviors (SC-002)."""

    def test_allow_rule_survives_restart(self, tmp_path: Path) -> None:
        """allow rule for kma_forecast_fetch persists through restart."""
        store_path = tmp_path / "permissions.json"

        # --- Phase 1: write rule (simulates first session) ---
        store_before = RuleStore(store_path)
        # File absent on first boot — start fresh
        rule = make_rule(
            tool_id="kma_forecast_fetch",
            decision="allow",
            scope="user",
            mode="default",
        )
        store_before.save_rule(rule)

        # --- Phase 2: simulate restart via reset_session_state ---
        boot_state = reset_session_state(store_path)
        assert boot_state.rules_loaded is True
        assert boot_state.mode == "default"  # M3/PR1
        assert boot_state.user_rule_count == 1

        # --- Phase 3: resolve returns "allow" ---
        empty_ctx = ScopeContext()
        decision = boot_state.rule_store.resolve("kma_forecast_fetch", empty_ctx)
        assert decision == "allow", f"Expected 'allow' after restart, got {decision!r}"

    def test_deny_rule_survives_restart(self, tmp_path: Path) -> None:
        """deny rule for hira_hospital_search persists through restart."""
        store_path = tmp_path / "permissions.json"

        store_before = RuleStore(store_path)
        rule = make_rule(
            tool_id="hira_hospital_search",
            decision="deny",
            scope="user",
            mode="default",
        )
        store_before.save_rule(rule)

        boot_state = reset_session_state(store_path)
        assert boot_state.rules_loaded is True
        assert boot_state.mode == "default"

        empty_ctx = ScopeContext()
        decision = boot_state.rule_store.resolve("hira_hospital_search", empty_ctx)
        assert decision == "deny", f"Expected 'deny' after restart, got {decision!r}"

    def test_ask_rule_returns_none_after_restart(self, tmp_path: Path) -> None:
        """ask rule for nmc_emergency_search resolves to None after restart (R3)."""
        store_path = tmp_path / "permissions.json"

        store_before = RuleStore(store_path)
        rule = make_rule(
            tool_id="nmc_emergency_search",
            decision="ask",
            scope="user",
            mode="default",
        )
        store_before.save_rule(rule)

        boot_state = reset_session_state(store_path)
        assert boot_state.rules_loaded is True
        assert boot_state.mode == "default"

        empty_ctx = ScopeContext()
        decision = boot_state.rule_store.resolve("nmc_emergency_search", empty_ctx)
        # R3: ask ≡ no-rule → None
        assert decision is None, f"Expected None (ask≡no-rule R3) after restart, got {decision!r}"

    def test_three_rules_together_survive_restart(self, tmp_path: Path) -> None:
        """Full scenario 4: write 3 rules, restart, assert all 3 expected behaviors."""
        store_path = tmp_path / "permissions.json"

        # --- Phase 1: write all 3 rules in a single session ---
        store_before = RuleStore(store_path)
        store_before.save_rule(
            make_rule(tool_id="kma_forecast_fetch", decision="allow", scope="user")
        )
        store_before.save_rule(
            make_rule(tool_id="hira_hospital_search", decision="deny", scope="user")
        )
        store_before.save_rule(
            make_rule(tool_id="nmc_emergency_search", decision="ask", scope="user")
        )

        assert len(store_before.list_rules(scope="user")) == 3

        # --- Phase 2: simulate restart ---
        boot_state = reset_session_state(store_path)
        assert boot_state.rules_loaded is True
        assert boot_state.mode == "default"  # M3/PR1: mode NEVER persists
        assert boot_state.user_rule_count == 3

        store_after = boot_state.rule_store
        empty_ctx = ScopeContext()

        # --- Phase 3: verify all 3 expected behaviors ---
        assert store_after.resolve("kma_forecast_fetch", empty_ctx) == "allow"
        assert store_after.resolve("hira_hospital_search", empty_ctx) == "deny"
        assert store_after.resolve("nmc_emergency_search", empty_ctx) is None  # R3

    def test_mode_is_always_default_on_restart(self, tmp_path: Path) -> None:
        """Invariant M3/PR1: mode is ALWAYS default on restart, never persisted."""
        store_path = tmp_path / "permissions.json"

        # Write a valid rule store (mode is irrelevant — not stored)
        store = RuleStore(store_path)
        store.save_rule(
            make_rule(tool_id="koroad_accident_hazard_search", decision="allow", scope="user")
        )

        boot_state = reset_session_state(store_path)
        assert boot_state.mode == "default", (
            f"M3/PR1 violated: mode after restart must be 'default', got {boot_state.mode!r}"
        )

    def test_session_scope_rules_not_persisted(self, tmp_path: Path) -> None:
        """session-scope rules are NOT persisted to disk and are absent after restart."""
        store_path = tmp_path / "permissions.json"

        store = RuleStore(store_path)
        # Session-scope rule should raise ValueError when save_rule is called
        session_rule = make_rule(
            tool_id="kma_forecast_fetch", decision="allow", scope="session"
        )
        with pytest.raises(ValueError, match="user-scope"):
            store.save_rule(session_rule)

    def test_revoked_rule_absent_after_restart(self, tmp_path: Path) -> None:
        """A revoked user-scope rule is absent in the next session."""
        store_path = tmp_path / "permissions.json"

        store_before = RuleStore(store_path)
        store_before.save_rule(
            make_rule(tool_id="kma_forecast_fetch", decision="allow", scope="user")
        )
        assert store_before.revoke("kma_forecast_fetch", "user") is True

        # Restart
        boot_state = reset_session_state(store_path)
        assert boot_state.rules_loaded is True
        assert boot_state.user_rule_count == 0

        empty_ctx = ScopeContext()
        decision = boot_state.rule_store.resolve("kma_forecast_fetch", empty_ctx)
        assert decision is None  # Rule was revoked; R3 applies

    def test_r1_deny_wins_over_allow(self, tmp_path: Path) -> None:
        """Invariant R1: deny in any scope wins over allow in narrower scope."""
        store_path = tmp_path / "permissions.json"

        store = RuleStore(store_path)
        store.save_rule(
            make_rule(tool_id="koroad_accident_hazard_search", decision="allow", scope="user")
        )

        # Add a deny rule at session scope (in-memory)
        session_deny = make_rule(
            tool_id="koroad_accident_hazard_search", decision="deny", scope="session"
        )
        ctx = ScopeContext(session_rules=(session_deny,))

        # R1: deny-wins — session deny overrides user allow
        decision = store.resolve("koroad_accident_hazard_search", ctx)
        assert decision == "deny", (
            f"R1 violated: deny-wins should override allow, got {decision!r}"
        )

    def test_r2_narrower_wins_session_over_user(self, tmp_path: Path) -> None:
        """Invariant R2: narrower scope (session) wins over wider scope (user)."""
        store_path = tmp_path / "permissions.json"

        store = RuleStore(store_path)
        # User-scope deny
        store.save_rule(
            make_rule(tool_id="hira_hospital_search", decision="deny", scope="user")
        )

        # Session-scope allow (narrower)
        session_allow = make_rule(
            tool_id="hira_hospital_search", decision="allow", scope="session"
        )
        ctx = ScopeContext(session_rules=(session_allow,))

        # R1 deny-wins takes precedence over R2 narrower-wins.
        # When BOTH a deny (user) and allow (session) exist, R1 wins → deny.
        decision = store.resolve("hira_hospital_search", ctx)
        assert decision == "deny", (
            f"R1 should win over R2 when deny is present in any scope: got {decision!r}"
        )

    def test_r2_narrower_wins_without_deny(self, tmp_path: Path) -> None:
        """R2: without any deny, narrower session-scope allow beats user-scope ask."""
        store_path = tmp_path / "permissions.json"

        store = RuleStore(store_path)
        # User-scope ask
        store.save_rule(
            make_rule(tool_id="nmc_emergency_search", decision="ask", scope="user")
        )

        # Session-scope allow (narrower, no deny present anywhere)
        session_allow = make_rule(
            tool_id="nmc_emergency_search", decision="allow", scope="session"
        )
        ctx = ScopeContext(session_rules=(session_allow,))

        # R2: narrower session allow wins over user ask
        decision = store.resolve("nmc_emergency_search", ctx)
        assert decision == "allow", (
            f"R2: session allow should win over user ask, got {decision!r}"
        )
