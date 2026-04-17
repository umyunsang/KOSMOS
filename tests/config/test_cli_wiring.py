# SPDX-License-Identifier: Apache-2.0
"""Integration test: verify the guard is wired into the CLI main entry."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from kosmos.cli import app as cli_app


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch):
    for key in list(os.environ):
        if key.startswith(("KOSMOS_", "LANGFUSE_")):
            monkeypatch.delenv(key, raising=False)
    yield


def test_main_invokes_verify_startup_between_dotenv_and_tracing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """main() must call the three bootstrap hooks in the exact contract order."""
    call_order: list[str] = []

    def _record(name: str):
        def _fn(*_a, **_kw):
            call_order.append(name)
        return _fn

    monkeypatch.setattr(cli_app, "load_repo_dotenv", _record("dotenv"))
    monkeypatch.setattr(cli_app, "verify_startup", _record("guard"))
    monkeypatch.setattr(cli_app, "setup_tracing", _record("tracing"))
    monkeypatch.setattr(cli_app, "_app", _record("app"))

    cli_app.main()

    assert call_order == ["dotenv", "guard", "tracing", "app"]


def test_main_exits_78_when_required_var_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """End-to-end: empty env → guard trips → process exits 78 before tracing."""
    tracing_called = {"hit": False}

    def _mark_tracing(*_a, **_kw) -> None:
        tracing_called["hit"] = True

    monkeypatch.setattr(cli_app, "load_repo_dotenv", lambda: None)
    monkeypatch.setattr(cli_app, "setup_tracing", _mark_tracing)
    monkeypatch.setattr(cli_app, "_app", lambda: None)

    with pytest.raises(SystemExit) as excinfo:
        cli_app.main()
    assert excinfo.value.code == 78
    assert tracing_called["hit"] is False, "setup_tracing must not run after guard fails"
    captured = capsys.readouterr()
    assert captured.err.startswith("KOSMOS config error [env=")
