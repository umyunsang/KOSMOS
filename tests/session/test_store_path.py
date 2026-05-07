# SPDX-License-Identifier: Apache-2.0
"""Tests for store._get_session_dir() path resolution.

Covers:
  1. Default path: ~/.ummaya/memdir/user/sessions
  2. UMMAYA_MEMDIR_USER env override
  3. Legacy UMMAYA_SESSION_DIR env override (backwards-compat)
  4. UMMAYA_MEMDIR_USER takes priority over UMMAYA_SESSION_DIR
"""

from __future__ import annotations

import os
from pathlib import Path

from ummaya.session.store import _get_default_session_dir, _get_session_dir

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_env(*keys: str) -> dict[str, str | None]:
    """Remove *keys* from os.environ, returning their previous values."""
    saved = {}
    for k in keys:
        saved[k] = os.environ.pop(k, None)
    return saved


def _restore_env(saved: dict[str, str | None]) -> None:
    """Restore env vars from a dict produced by _clear_env."""
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


# ---------------------------------------------------------------------------
# _get_default_session_dir
# ---------------------------------------------------------------------------


class TestGetDefaultSessionDir:
    def test_default_path_resolves_to_memdir(self) -> None:
        """When no env var is set, path is ~/.ummaya/memdir/user/sessions."""
        saved = _clear_env("UMMAYA_MEMDIR_USER", "UMMAYA_SESSION_DIR")
        try:
            result = _get_default_session_dir()
            expected = Path.home() / ".ummaya" / "memdir" / "user" / "sessions"
            assert result == expected
        finally:
            _restore_env(saved)

    def test_ummaya_memdir_user_override(self) -> None:
        """UMMAYA_MEMDIR_USER is honoured; sessions sub-dir is appended."""
        saved = _clear_env("UMMAYA_MEMDIR_USER", "UMMAYA_SESSION_DIR")
        try:
            os.environ["UMMAYA_MEMDIR_USER"] = "/tmp/test-memdir/user"  # noqa: S108
            result = _get_default_session_dir()
            assert result == Path("/tmp/test-memdir/user/sessions")  # noqa: S108
        finally:
            _restore_env(saved)


# ---------------------------------------------------------------------------
# _get_session_dir
# ---------------------------------------------------------------------------


class TestGetSessionDir:
    def test_default_path_no_env(self, tmp_path: Path) -> None:
        """When no env vars are set, the canonical memdir path is used."""
        saved = _clear_env("UMMAYA_MEMDIR_USER", "UMMAYA_SESSION_DIR")
        try:
            # We cannot write to ~ in CI, so we only test that the returned
            # path ends with the expected suffix.
            result = _get_default_session_dir()
            assert result.parts[-3:] == ("memdir", "user", "sessions")
        finally:
            _restore_env(saved)

    def test_ummaya_memdir_user_creates_dir(self, tmp_path: Path) -> None:
        """UMMAYA_MEMDIR_USER override causes directory creation."""
        saved = _clear_env("UMMAYA_MEMDIR_USER", "UMMAYA_SESSION_DIR")
        try:
            root = tmp_path / "memdir" / "user"
            os.environ["UMMAYA_MEMDIR_USER"] = str(root)
            result = _get_session_dir()
            expected = root / "sessions"
            assert result == expected
            assert expected.is_dir()
        finally:
            _restore_env(saved)

    def test_legacy_ummaya_session_dir_override(self, tmp_path: Path) -> None:
        """Legacy UMMAYA_SESSION_DIR is still respected for backwards-compat."""
        saved = _clear_env("UMMAYA_MEMDIR_USER", "UMMAYA_SESSION_DIR")
        try:
            legacy_dir = tmp_path / "legacy-sessions"
            os.environ["UMMAYA_SESSION_DIR"] = str(legacy_dir)
            result = _get_session_dir()
            assert result == legacy_dir
            assert legacy_dir.is_dir()
        finally:
            _restore_env(saved)

    def test_ummaya_memdir_user_takes_priority_over_legacy(self, tmp_path: Path) -> None:
        """UMMAYA_MEMDIR_USER wins when both env vars are set."""
        saved = _clear_env("UMMAYA_MEMDIR_USER", "UMMAYA_SESSION_DIR")
        try:
            root = tmp_path / "memdir" / "user"
            legacy_dir = tmp_path / "legacy"
            os.environ["UMMAYA_MEMDIR_USER"] = str(root)
            os.environ["UMMAYA_SESSION_DIR"] = str(legacy_dir)
            result = _get_session_dir()
            # UMMAYA_MEMDIR_USER takes priority; legacy dir never created
            assert result == root / "sessions"
            assert not legacy_dir.exists()
        finally:
            _restore_env(saved)

    def test_session_dir_is_created_if_absent(self, tmp_path: Path) -> None:
        """_get_session_dir() creates the directory if it does not exist."""
        saved = _clear_env("UMMAYA_MEMDIR_USER", "UMMAYA_SESSION_DIR")
        try:
            root = tmp_path / "new-memdir" / "user"
            assert not root.exists()
            os.environ["UMMAYA_MEMDIR_USER"] = str(root)
            result = _get_session_dir()
            assert result.is_dir()
        finally:
            _restore_env(saved)
