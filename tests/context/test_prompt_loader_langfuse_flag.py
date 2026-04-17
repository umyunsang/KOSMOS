"""T011 — PromptLoader Langfuse opt-in flag tests (FR-C08, FR-C09).

All tests are intentionally RED until src/kosmos/context/prompt_loader.py exists (T025).

TEST-COMMENT: test_flag_true_with_mock_client_hash_disagreement_fails_closed is
intentionally brittle.  It encodes FR-C09's requirement that any disagreement between
the repo-side SHA-256 and the Langfuse-returned hash MUST cause PromptLoader to
fail-closed (raise PromptRegistryError).  The mock surface approximates the narrowest
viable Langfuse v2+ SDK call:

    langfuse.Langfuse(public_key=..., secret_key=..., host=...).get_prompt(name, version)

...which returns an object with a `.hash` or `.prompt` attribute.  The exact import
path PromptLoader will use is unknown at TDD time (Task T025 decides it); this test
may need adjustment once T025 chooses the import surface.  The structural plausibility
of the mock is sufficient to force the loader into the fail-closed branch.

Uses the shared `valid_prompt_tree` fixture from tests/context/conftest.py.
"""

from __future__ import annotations

import sys
import types

import pytest

from kosmos.context.prompt_loader import (  # noqa: F401 — RED import
    PromptLoader,
    PromptRegistryError,
)

# ---------------------------------------------------------------------------
# Test 1: flag unset — langfuse must NEVER be imported
# ---------------------------------------------------------------------------


def test_flag_unset_never_imports_langfuse(valid_prompt_tree, monkeypatch):
    """With KOSMOS_PROMPT_REGISTRY_LANGFUSE unset, PromptLoader must not import langfuse."""
    monkeypatch.delenv("KOSMOS_PROMPT_REGISTRY_LANGFUSE", raising=False)
    # Ensure langfuse is not already cached from a previous test.
    sys.modules.pop("langfuse", None)

    _loader = PromptLoader(manifest_path=valid_prompt_tree)

    assert "langfuse" not in sys.modules, (
        "PromptLoader imported 'langfuse' even though KOSMOS_PROMPT_REGISTRY_LANGFUSE is unset"
    )


# ---------------------------------------------------------------------------
# Test 2: flag true, extras absent -> PromptRegistryError with install hint
# ---------------------------------------------------------------------------


def test_flag_true_without_extras_raises_with_install_hint(valid_prompt_tree, monkeypatch):
    """FR-C08: with flag=true and langfuse extras absent, PromptLoader must raise
    PromptRegistryError with a message pointing at 'uv sync --extra langfuse'."""
    monkeypatch.setenv("KOSMOS_PROMPT_REGISTRY_LANGFUSE", "true")
    # Make langfuse unimportable by setting its sys.modules entry to None.
    # Per importlib convention, None means "import was tried and failed" (absent module).
    sys.modules.pop("langfuse", None)
    monkeypatch.setitem(sys.modules, "langfuse", None)  # type: ignore[arg-type]

    with pytest.raises(PromptRegistryError) as exc_info:
        PromptLoader(manifest_path=valid_prompt_tree)

    msg = str(exc_info.value)
    assert "uv sync --extra langfuse" in msg, (
        f"Expected install hint 'uv sync --extra langfuse' in error message, got: {msg!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: flag true, mock client returns mismatched hash -> fail-closed (FR-C09)
# ---------------------------------------------------------------------------


def _make_fake_langfuse_module(disagreeing_hash: str) -> types.ModuleType:
    """Build a minimal fake 'langfuse' module whose Client.get_prompt returns an
    object with a .hash field set to a value that disagrees with the repo hash.

    The fake mirrors the narrowest viable Langfuse v2+ surface:
        langfuse.Langfuse(public_key=..., secret_key=..., host=...).get_prompt(name, version)
    and returns a prompt object with .hash != <repo sha256>.
    """
    fake_mod = types.ModuleType("langfuse")

    class _FakePromptResult:
        def __init__(self, bad_hash: str) -> None:
            # Expose both .hash and .prompt so the loader can detect either surface.
            self.hash = bad_hash
            self.prompt = "# Fake system prompt from Langfuse\n"
            self.version = 1

    class _FakeLangfuse:
        def __init__(self, *args, **kwargs) -> None:  # noqa: ANN001
            pass

        def get_prompt(self, name: str, version: int | None = None) -> _FakePromptResult:  # noqa: ANN001
            return _FakePromptResult(bad_hash=disagreeing_hash)

    fake_mod.Langfuse = _FakeLangfuse  # type: ignore[attr-defined]
    return fake_mod


def test_flag_true_with_mock_client_hash_disagreement_fails_closed(valid_prompt_tree, monkeypatch):
    """FR-C09: with flag=true and a Langfuse client returning a hash that disagrees
    with the repo hash for 'system_v1', PromptLoader must raise PromptRegistryError
    naming 'system_v1' and indicating a hash mismatch between sources."""
    monkeypatch.setenv("KOSMOS_PROMPT_REGISTRY_LANGFUSE", "true")

    # Inject fake langfuse module with a deliberately wrong hash.
    bad_hash = "a" * 64  # 64-char hex string that won't match the real file SHA-256.
    fake_langfuse = _make_fake_langfuse_module(disagreeing_hash=bad_hash)
    sys.modules.pop("langfuse", None)
    monkeypatch.setitem(sys.modules, "langfuse", fake_langfuse)

    with pytest.raises(PromptRegistryError) as exc_info:
        PromptLoader(manifest_path=valid_prompt_tree)

    msg = str(exc_info.value)
    assert "system_v1" in msg, f"Expected error message to name 'system_v1', got: {msg!r}"
    # Accept any phrasing that indicates a two-source hash disagreement.
    assert any(kw in msg.lower() for kw in ("mismatch", "disagree", "langfuse", "hash")), (
        f"Expected error message to indicate a hash mismatch between repo and Langfuse, "
        f"got: {msg!r}"
    )
