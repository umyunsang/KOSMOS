# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for permission pipeline tests.

Includes both v1 gauntlet fixtures (unchanged) and Spec 033 v2 fixtures
(additive, T002 — new tmp-path fixtures for rule store, ledger, and HMAC key).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from kosmos.permissions.models import AccessTier, PermissionCheckRequest, SessionContext

# ---------------------------------------------------------------------------
# v1 gauntlet fixtures (unchanged)
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_session_context():
    """Factory fixture for creating SessionContext instances."""

    def _make(
        *,
        session_id: str = "test-session-001",
        citizen_id: str | None = None,
        auth_level: int = 0,
        consented_providers: list[str] | None = None,
    ) -> SessionContext:
        return SessionContext(
            session_id=session_id,
            citizen_id=citizen_id,
            auth_level=auth_level,
            consented_providers=consented_providers or [],
        )

    return _make


@pytest.fixture()
def make_permission_request(make_session_context):
    """Factory fixture for creating PermissionCheckRequest instances."""

    def _make(
        *,
        tool_id: str = "test_tool",
        access_tier: AccessTier = AccessTier.public,
        arguments_json: str = "{}",
        session_context: SessionContext | None = None,
        is_personal_data: bool = False,
        is_bypass_mode: bool = False,
    ) -> PermissionCheckRequest:
        return PermissionCheckRequest(
            tool_id=tool_id,
            access_tier=access_tier,
            arguments_json=arguments_json,
            session_context=session_context or make_session_context(),
            is_personal_data=is_personal_data,
            is_bypass_mode=is_bypass_mode,
        )

    return _make


# ---------------------------------------------------------------------------
# Spec 033 v2 fixtures (T002 — additive)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_permission_dir(tmp_path: Path) -> Path:
    """Return a temporary directory tree for all v2 permission files.

    Layout::

        tmp_permission_dir/
        ├── permissions.json          (rule store)
        ├── consent_ledger.jsonl      (consent ledger)
        └── keys/
            └── ledger.key            (HMAC key placeholder, mode 0o400)

    The directory is cleaned up automatically by pytest's ``tmp_path`` fixture.
    """
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir(mode=0o700, parents=True)
    return tmp_path


@pytest.fixture()
def tmp_rule_store(tmp_permission_dir: Path) -> Path:
    """Return path to an empty rule store JSON file under ``tmp_permission_dir``."""
    rule_store = tmp_permission_dir / "permissions.json"
    # Write an empty but valid schema-versioned rule store.
    empty_store = '{"$schema": "kosmos://permissions-store/v1", "version": 1, "rules": []}\n'
    rule_store.write_text(empty_store)
    return rule_store


@pytest.fixture()
def tmp_consent_ledger(tmp_permission_dir: Path) -> Path:
    """Return path to an empty consent ledger JSONL file under ``tmp_permission_dir``."""
    ledger = tmp_permission_dir / "consent_ledger.jsonl"
    ledger.touch()
    return ledger


@pytest.fixture()
def tmp_hmac_key(tmp_permission_dir: Path) -> Path:
    """Return path to a freshly-generated 32-byte HMAC key with mode 0o400.

    The file is created with a deterministic test key (32 zero bytes) to make
    tests reproducible.  Mode is set to ``0o400`` (owner-read only) as required
    by Invariant C3 from data-model.md § 2.2.
    """
    key_path = tmp_permission_dir / "keys" / "ledger.key"
    # Write 32 bytes of deterministic test key material.
    fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        os.write(fd, b"\x00" * 32)
    finally:
        os.close(fd)
    return key_path
