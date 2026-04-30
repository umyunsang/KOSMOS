# SPDX-License-Identifier: Apache-2.0
"""Canonical map: ``tool_id`` → ``family_hint`` for the verify primitive.

The mapping is the single source-of-truth in ``prompts/system_v1.md``
``<verify_families>`` … ``</verify_families>`` block.  The module reads that
block exactly once at first use (``lru_cache``) and returns a frozen mapping.

Public API
----------
``resolve_family(tool_id)``  → ``str | None``
    Return the ``family_hint`` string for the given verify tool_id, or ``None``
    if the tool_id is not recognised.

``get_canonical_map()``  → ``Mapping[str, str]``
    Return the full frozen ``{tool_id: family_hint}`` mapping.

Design
------
- Decision 2 in ``specs/2297-zeta-e2e-smoke/research.md``: parse markdown at
  boot, no Python duplication, no drift between code and prompt.
- FR-008b: raises ``RuntimeError`` if fewer than 10 entries are parsed.
- Path resolution: ``KOSMOS_PROMPTS_DIR`` env var → ``<repo_root>/prompts``.
  Repo root is detected by walking up from this file's location.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_BLOCK_RE = re.compile(
    r"<verify_families>(.*?)</verify_families>",
    re.DOTALL,
)

# Match table rows: | ... | `mock_verify_*` | ...
# The second column contains the tool_id in backticks.
_ROW_RE = re.compile(
    r"^\|\s*[^|]+\|\s*`(mock_verify_[a-z0-9_]+)`\s*\|",
    re.MULTILINE,
)

# Explicit overrides for tool_ids whose family_hint differs from the simple
# prefix-stripped value.  These two entries have the canonical ``_module``
# suffix in the family_hint even though it is absent from the tool_id suffix.
# Source: data-model.md § 2 + src/kosmos/primitives/verify.py
# (Literal["simple_auth_module"] / Literal["geumyung_module"]).
_FAMILY_OVERRIDES: dict[str, str] = {
    "mock_verify_module_simple_auth": "simple_auth_module",
    "mock_verify_module_geumyung": "geumyung_module",
}

_MODULE_PREFIX = "mock_verify_module_"
_PLAIN_PREFIX = "mock_verify_"


def _tool_id_to_family(tool_id: str) -> str:
    """Derive the family_hint from a tool_id string.

    Checks the override table first, then falls back to prefix stripping:
    - ``mock_verify_module_<suffix>`` → ``<suffix>``
    - ``mock_verify_<suffix>``        → ``<suffix>``
    """
    if tool_id in _FAMILY_OVERRIDES:
        return _FAMILY_OVERRIDES[tool_id]
    if tool_id.startswith(_MODULE_PREFIX):
        return tool_id[len(_MODULE_PREFIX) :]
    if tool_id.startswith(_PLAIN_PREFIX):
        return tool_id[len(_PLAIN_PREFIX) :]
    return tool_id


def _locate_prompts_dir() -> Path:
    """Return the ``prompts/`` directory path.

    Resolution order:
    1. ``KOSMOS_PROMPTS_DIR`` environment variable (if set and non-empty).
    2. Walk up from this file's location until a ``prompts/`` sibling of the
       package root is found (handles editable installs).
    3. Fall back to ``<repo_root>/prompts`` where repo_root is three levels up
       from this file (``src/kosmos/tools/verify_canonical_map.py``).
    """
    env_dir = os.environ.get("KOSMOS_PROMPTS_DIR", "").strip()
    if env_dir:
        return Path(env_dir)

    # Walk upward looking for the repo root (contains prompts/ directory).
    current = Path(__file__).resolve().parent
    for _ in range(10):
        candidate = current / "prompts"
        if candidate.is_dir() and (candidate / "system_v1.md").exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent

    # Explicit fallback: three parent dirs up from this file is the repo root
    # src/kosmos/tools/ → src/kosmos/ → src/ → repo_root
    return Path(__file__).resolve().parent.parent.parent.parent / "prompts"


@lru_cache(maxsize=1)
def _load_map() -> Mapping[str, str]:
    """Parse the ``<verify_families>`` block and return a frozen mapping.

    Raises
    ------
    RuntimeError
        If the block is missing or fewer than 10 entries are found (FR-008b).
    """
    prompts_dir = _locate_prompts_dir()
    system_md = prompts_dir / "system_v1.md"

    try:
        text = system_md.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"verify_canonical_map: cannot read {system_md}: {exc}") from exc

    match = _BLOCK_RE.search(text)
    if not match:
        raise RuntimeError(
            f"verify_canonical_map: <verify_families> block not found in {system_md}"
        )

    block = match.group(1)
    tool_ids = _ROW_RE.findall(block)

    mapping: dict[str, str] = {tid: _tool_id_to_family(tid) for tid in tool_ids}

    if len(mapping) < 10:
        raise RuntimeError(f"verify_canonical_map: expected ≥10 entries, got {len(mapping)}")

    return MappingProxyType(mapping)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_family(tool_id: str) -> str | None:
    """Return the ``family_hint`` for *tool_id*, or ``None`` if unknown.

    The mapping is loaded once from ``prompts/system_v1.md``
    ``<verify_families>`` block at first call (``lru_cache``).  Subsequent
    calls return the cached mapping without re-reading the file.
    """
    return _load_map().get(tool_id)


def get_canonical_map() -> Mapping[str, str]:
    """Return the full ``{tool_id: family_hint}`` frozen mapping (read-only)."""
    return _load_map()
