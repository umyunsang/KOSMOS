# SPDX-License-Identifier: Apache-2.0
"""Tests for kosax.config.guard — fail-fast startup guard.

Test matrix mirrors contracts/guard.md T-G01..T-G10.
Written before guard.py implementation (TDD).
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator

import pytest

from kosax.config import guard

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Full-required set keeps dev/ci/prod all green. Guard inspects KOSAX_ENV at
# call time, so pop fixture isolates each test from ambient shell state.
ALL_REQUIRED_SET: dict[str, str] = {
    "LANGFUSE_PUBLIC_KEY": "pk-lf-<redacted>",
    "LANGFUSE_SECRET_KEY": "sk-lf-<redacted>",
    "KOSAX_OTEL_ENDPOINT": "http://localhost:4318",
}


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Strip every KOSAX_*/LANGFUSE_* var plus KOSAX_ENV before each test."""
    for key in list(os.environ):
        if key.startswith(("KOSAX_", "LANGFUSE_")):
            monkeypatch.delenv(key, raising=False)
    yield


def _set_all(monkeypatch: pytest.MonkeyPatch, overrides: dict[str, str] | None = None) -> None:
    for name, value in ALL_REQUIRED_SET.items():
        monkeypatch.setenv(name, value)
    if overrides:
        for name, value in overrides.items():
            if value is None:
                monkeypatch.delenv(name, raising=False)
            else:
                monkeypatch.setenv(name, value)


# ---------------------------------------------------------------------------
# T-G01..T-G10
# ---------------------------------------------------------------------------


def test_t_g01_empty_env_defaults_to_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """KOSAX_ENV unset defaults to dev and has no Infisical-required user key."""
    diag = guard.check_required()
    assert diag is None


def test_t_g02_all_required_set_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """All required vars populated → check_required returns None."""
    _set_all(monkeypatch)
    monkeypatch.setenv("KOSAX_ENV", "prod")
    assert guard.check_required() is None


def test_t_g03_prod_requires_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """KOSAX_ENV=prod with LANGFUSE_PUBLIC_KEY missing → diagnostic lists it."""
    _set_all(monkeypatch, overrides={"LANGFUSE_PUBLIC_KEY": None})
    monkeypatch.setenv("KOSAX_ENV", "prod")
    diag = guard.check_required()
    assert diag is not None
    assert diag.env == "prod"
    assert "LANGFUSE_PUBLIC_KEY" in diag.missing


def test_t_g04_dev_does_not_require_langfuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same state as T-G03 but KOSAX_ENV=dev → LANGFUSE not in missing list."""
    _set_all(monkeypatch, overrides={"LANGFUSE_PUBLIC_KEY": None})
    monkeypatch.setenv("KOSAX_ENV", "dev")
    diag = guard.check_required()
    # LANGFUSE must NOT be flagged in dev even though it's missing.
    if diag is not None:
        assert "LANGFUSE_PUBLIC_KEY" not in diag.missing


def test_t_g05_whitespace_value_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only value counts as missing (FR-006)."""
    _set_all(monkeypatch, overrides={"KOSAX_OTEL_ENDPOINT": "   \t "})
    monkeypatch.setenv("KOSAX_ENV", "prod")
    diag = guard.check_required()
    assert diag is not None
    assert "KOSAX_OTEL_ENDPOINT" in diag.missing


def test_t_g06_unknown_env_falls_through_to_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """KOSAX_ENV=staging (unknown) → classified as dev, no prod-only vars flagged."""
    _set_all(monkeypatch, overrides={"LANGFUSE_PUBLIC_KEY": None})
    monkeypatch.setenv("KOSAX_ENV", "staging")
    diag = guard.check_required()
    assert guard.current_env() == "dev"
    if diag is not None:
        assert diag.env == "dev"
        assert "LANGFUSE_PUBLIC_KEY" not in diag.missing


def test_t_g07_hundred_ms_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """Worst-case (all-missing) guard path MUST complete under 100 ms."""
    # Empty env — worst case produces the longest missing list.
    monkeypatch.setenv("KOSAX_ENV", "prod")
    start = time.monotonic()
    diag = guard.check_required()
    elapsed = time.monotonic() - start
    assert diag is not None
    assert elapsed < 0.1, f"guard took {elapsed * 1000:.1f} ms; budget is 100 ms"


def test_t_g08_missing_list_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same env state → identical missing tuple across calls."""
    monkeypatch.setenv("KOSAX_ENV", "prod")
    first = guard.check_required()
    second = guard.check_required()
    assert first is not None and second is not None
    assert first.missing == second.missing
    # Alphabetically sorted (contracts/guard.md stderr grammar).
    assert list(first.missing) == sorted(first.missing)


def test_t_g09_verify_startup_does_not_write_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """verify_startup MUST NOT touch .env file (FR-042)."""
    env_file = tmp_path / ".env"
    env_file.write_text("SENTINEL=value\n", encoding="utf-8")
    original_mtime = env_file.stat().st_mtime
    _set_all(monkeypatch)
    monkeypatch.setenv("KOSAX_ENV", "dev")
    guard.verify_startup()  # no-op on success path
    assert env_file.stat().st_mtime == original_mtime
    assert env_file.read_text(encoding="utf-8") == "SENTINEL=value\n"


def test_t_g10_verify_startup_emits_no_otel_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Guard runs before setup_tracing; must not import/init OTel."""
    _set_all(monkeypatch)
    monkeypatch.setenv("KOSAX_ENV", "dev")
    # Scrub any OTel modules loaded by other tests to prove the guard doesn't re-import.
    modules = __import__("sys").modules
    preloaded = {name for name in list(modules) if name.startswith("opentelemetry")}
    guard.verify_startup()
    after = {name for name in list(modules) if name.startswith("opentelemetry")}
    # The guard itself must introduce zero new opentelemetry.* modules.
    assert after <= preloaded


# ---------------------------------------------------------------------------
# verify_startup exit-code + stderr grammar
# ---------------------------------------------------------------------------


def test_verify_startup_exits_78_on_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("KOSAX_ENV", "prod")
    with pytest.raises(SystemExit) as excinfo:
        guard.verify_startup()
    assert excinfo.value.code == 78
    captured = capsys.readouterr()
    assert captured.out == ""
    line = captured.err.rstrip("\n")
    # Single-line grammar check.
    assert "\n" not in line
    assert line.startswith("KOSAX config error [env=")
    assert "missing required variables:" in line
    assert "See https://github.com/umyunsang/KOSAX/blob/main/docs/configuration.md" in line


def test_verify_startup_silent_on_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_all(monkeypatch)
    monkeypatch.setenv("KOSAX_ENV", "dev")
    result = guard.verify_startup()
    assert result is None
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_current_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KOSAX_ENV", raising=False)
    assert guard.current_env() == "dev"
    monkeypatch.setenv("KOSAX_ENV", "ci")
    assert guard.current_env() == "ci"
    monkeypatch.setenv("KOSAX_ENV", "prod")
    assert guard.current_env() == "prod"
    monkeypatch.setenv("KOSAX_ENV", "")
    assert guard.current_env() == "dev"
    monkeypatch.setenv("KOSAX_ENV", "production")
    assert guard.current_env() == "dev"


def test_guard_diagnostic_frozen() -> None:
    """GuardDiagnostic is immutable — dataclass frozen=True."""
    diag = guard.GuardDiagnostic(
        missing=("KOSAX_X",),
        env="dev",
        doc_url="https://example.invalid/docs",
    )
    with pytest.raises((AttributeError, Exception)):
        diag.missing = ("KOSAX_Y",)  # type: ignore[misc]
