# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for KOSMOS permission receipt ledger tests (Spec 035).

Spec 033 KOSMOS-invented residue fixtures removed in Epic δ #2295.
Only Spec 035 receipt-ledger tmp-path fixtures are retained here.

References:
- specs/2295-backend-permissions-cleanup/spec.md § FR-001, FR-002
- .specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Spec 035 receipt ledger tmp-path fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_permission_dir(tmp_path: Path) -> Path:
    """Return a temporary directory tree for Spec 035 receipt ledger files.

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
    empty_store = '{"schema_version": "1.0.0", "rules": []}\n'
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
    fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        os.write(fd, b"\x00" * 32)
    finally:
        os.close(fd)
    return key_path
