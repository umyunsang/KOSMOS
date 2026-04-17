"""Shared fixtures for tests/context/.

Factoring decision: `valid_prompt_tree` is defined here (not duplicated in each
file) so all four TDD files share a single, authoritative tree builder.
test_prompt_loader_happy_path.py and test_prompt_loader_fail_closed.py both
import from this conftest via the standard pytest fixture mechanism.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml


def _write_valid_prompt_tree(tmp_path: Path) -> Path:
    """Write three prompt files + a matching manifest.yaml under tmp_path/prompts/.

    Returns the Path to prompts/manifest.yaml.

    Layout:
        <tmp_path>/
            prompts/
                system_v1.md
                session_guidance_v1.md
                compact_v1.md
                manifest.yaml
    """
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Distinct content per prompt so SHA-256 values differ.
    contents: dict[str, bytes] = {
        "system_v1.md": b"# System Prompt v1\nYou are KOSMOS, a Korean public-service assistant.\n",
        "session_guidance_v1.md": (
            b"# Session Guidance v1\n"
            b"Use resolve_location for address-to-region conversion.\n"
        ),
        "compact_v1.md": b"# Compact v1\nSummarise the session for context compaction.\n",
    }

    entries: list[dict] = []
    for filename, raw in contents.items():
        fpath = prompts_dir / filename
        fpath.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        prompt_id = filename.replace(".md", "")  # e.g. "system_v1"
        entries.append(
            {
                "prompt_id": prompt_id,
                "version": 1,
                "sha256": digest,
                "path": filename,
            }
        )

    manifest_data = {"version": 1, "entries": entries}
    manifest_path = prompts_dir / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(manifest_data, default_flow_style=False), encoding="utf-8"
    )

    return manifest_path


@pytest.fixture()
def valid_prompt_tree(tmp_path: Path) -> Path:
    """Pytest fixture: build a valid prompt tree, return manifest Path."""
    return _write_valid_prompt_tree(tmp_path)
