"""T010 — PromptLoader immutability and cache tests (FR-C04).

All tests are intentionally RED until src/kosmos/context/prompt_loader.py exists (T025).
Uses the shared `valid_prompt_tree` fixture from tests/context/conftest.py.
"""

from __future__ import annotations

import pytest

from kosmos.context.prompt_loader import PromptLoader, PromptRegistryError  # noqa: F401 — RED import


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_returns_str_type(valid_prompt_tree):
    """PromptLoader.load() must return exactly `str`, not a subclass or wrapper."""
    loader = PromptLoader(manifest_path=valid_prompt_tree)
    result = loader.load("system_v1")
    assert type(result) is str, (
        f"Expected type(result) is str, got {type(result)!r}"
    )


def test_load_returns_cached_object_identity(valid_prompt_tree):
    # FR-C04: single cached instance — intentional object identity check
    loader = PromptLoader(manifest_path=valid_prompt_tree)
    first = loader.load("system_v1")
    second = loader.load("system_v1")
    assert first is second, (
        "Expected two calls to .load('system_v1') to return the same cached object "
        "(object identity), but got distinct objects."
    )


def test_no_public_cache_setter(valid_prompt_tree):
    """No public setter-style attribute for the internal cache must exist on PromptLoader."""
    loader = PromptLoader(manifest_path=valid_prompt_tree)
    assert not hasattr(loader, "set_cache"), (
        "PromptLoader must not expose a 'set_cache' attribute"
    )
    assert not hasattr(loader, "clear_cache"), (
        "PromptLoader must not expose a 'clear_cache' attribute"
    )
    assert not hasattr(loader, "invalidate"), (
        "PromptLoader must not expose an 'invalidate' attribute"
    )
