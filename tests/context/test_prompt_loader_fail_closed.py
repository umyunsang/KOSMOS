"""T009 — PromptLoader fail-closed tests (R1, R2, R3).

Uses the shared `valid_prompt_tree` fixture from tests/context/conftest.py.
All tests are intentionally RED until src/kosmos/context/prompt_loader.py exists (T025).

Fixture note: `valid_prompt_tree` is defined in conftest.py and returns the
Path to prompts/manifest.yaml inside a fresh tmp_path per test.
"""

from __future__ import annotations

import pytest

from kosmos.context.prompt_loader import (  # noqa: F401 — RED import
    PromptLoader,
    PromptRegistryError,
)

# ---------------------------------------------------------------------------
# R1: manifest lists a path whose file is missing -> PromptRegistryError
# ---------------------------------------------------------------------------

def test_r1_missing_file_raises_prompt_registry_error(valid_prompt_tree):
    """R1: PromptLoader must raise PromptRegistryError when a manifest-listed file
    is absent from disk.  The error message must reference the missing prompt_id or path."""
    prompts_dir = valid_prompt_tree.parent
    (prompts_dir / "system_v1.md").unlink()

    with pytest.raises(PromptRegistryError) as exc_info:
        PromptLoader(manifest_path=valid_prompt_tree)

    msg = str(exc_info.value)
    assert "system_v1" in msg or "system_v1.md" in msg, (
        f"Expected error message to reference 'system_v1' or 'system_v1.md', got: {msg!r}"
    )


# ---------------------------------------------------------------------------
# R2: sha256 in manifest doesn't match file bytes -> PromptRegistryError naming prompt_id
# ---------------------------------------------------------------------------

def test_r2_hash_mismatch_raises_naming_prompt_id(valid_prompt_tree):
    """R2: PromptLoader must raise PromptRegistryError when a file's SHA-256 does not
    match the manifest entry.  The error message must name the mismatching prompt_id."""
    prompts_dir = valid_prompt_tree.parent
    compact_path = prompts_dir / "compact_v1.md"
    # Append one byte to corrupt the digest.
    compact_path.write_bytes(compact_path.read_bytes() + b"\x00")

    with pytest.raises(PromptRegistryError) as exc_info:
        PromptLoader(manifest_path=valid_prompt_tree)

    msg = str(exc_info.value)
    assert "compact_v1" in msg, (
        f"Expected error message to name 'compact_v1', got: {msg!r}"
    )


# ---------------------------------------------------------------------------
# R3: orphan .md file not listed in manifest -> PromptRegistryError naming orphan
# ---------------------------------------------------------------------------

def test_r3_orphan_file_raises_naming_orphan(valid_prompt_tree):
    """R3: PromptLoader must raise PromptRegistryError when an unlisted .md file
    exists under prompts/.  The error message must reference the orphan filename."""
    prompts_dir = valid_prompt_tree.parent
    orphan = prompts_dir / "leaked_v1.md"
    orphan.write_bytes(b"# Leaked secret prompt\n")

    with pytest.raises(PromptRegistryError) as exc_info:
        PromptLoader(manifest_path=valid_prompt_tree)

    msg = str(exc_info.value)
    assert "leaked_v1" in msg or "leaked_v1.md" in msg, (
        f"Expected error message to reference 'leaked_v1' or 'leaked_v1.md', got: {msg!r}"
    )
