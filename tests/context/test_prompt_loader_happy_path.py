"""T008 — PromptLoader happy-path tests (FR-C10).

Uses the shared `valid_prompt_tree` fixture from tests/context/conftest.py.
All tests are intentionally RED until src/kosmos/context/prompt_loader.py exists (T025).
"""

from __future__ import annotations

import collections.abc
import hashlib
import logging

import pytest

from kosmos.context.prompt_loader import PromptLoader, PromptRegistryError  # noqa: F401 — RED import


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_returns_str(valid_prompt_tree):
    """PromptLoader.load() must return a non-empty str."""
    loader = PromptLoader(manifest_path=valid_prompt_tree)
    result = loader.load("system_v1")
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_hash_returns_64_hex_matching_bytes(valid_prompt_tree):
    """get_hash() must return 64-char lowercase hex equal to the file's SHA-256."""
    prompts_dir = valid_prompt_tree.parent
    file_bytes = (prompts_dir / "system_v1.md").read_bytes()
    expected = _sha256_bytes(file_bytes)

    loader = PromptLoader(manifest_path=valid_prompt_tree)
    digest = loader.get_hash("system_v1")

    assert isinstance(digest, str)
    assert len(digest) == 64
    assert digest == digest.lower()
    assert digest == expected


def test_all_hashes_returns_exactly_three_entries(valid_prompt_tree):
    """all_hashes() must return a Mapping with exactly three prompt_id keys."""
    loader = PromptLoader(manifest_path=valid_prompt_tree)
    hashes = loader.all_hashes()

    assert isinstance(hashes, collections.abc.Mapping)
    assert set(hashes.keys()) == {"system_v1", "session_guidance_v1", "compact_v1"}
    assert len(hashes) == 3


def test_info_log_emitted_per_resolved_prompt(valid_prompt_tree, caplog):
    """FR-C10: at least one INFO record per resolved prompt must be emitted
    on the kosmos.context.prompt_loader logger during PromptLoader construction."""
    with caplog.at_level(logging.INFO, logger="kosmos.context.prompt_loader"):
        _loader = PromptLoader(manifest_path=valid_prompt_tree)

    loader_records = [
        r for r in caplog.records if r.name == "kosmos.context.prompt_loader"
    ]
    assert len(loader_records) >= 3, (
        f"Expected >= 3 INFO records from 'kosmos.context.prompt_loader', "
        f"got {len(loader_records)}: {[r.message for r in loader_records]}"
    )
