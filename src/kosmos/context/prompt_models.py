# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 models for the Prompt Registry manifest.

Implements PromptManifestEntry and PromptManifest as specified in
specs/026-cicd-prompt-registry/data-model.md §§ 1–2.

Invariants enforced at construction time:
  PromptManifestEntry:
    I1 — prompt_id matches ^[a-z][a-z0-9_]*_v[0-9]+$  (enforced by PromptId alias)
    I2 — version integer equals the _v{N} suffix in prompt_id
    I3 — sha256 is exactly 64 lowercase hex chars      (enforced by Sha256Hex alias)
    I4 — path must not contain '..' traversal segments

  PromptManifest:
    M1 — prompt_id is unique across all entries
    M2 — within each prompt family (prompt_id sans _v{N}), versions form
         the dense sequence 1, 2, 3, … with no gaps or missing v1
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typed string aliases
# ---------------------------------------------------------------------------

# 64 lowercase hex characters — SHA-256 digest canonical form.
Sha256Hex = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64),
]

# snake_case prompt identifier with mandatory _v{N} suffix (N >= 0 per pattern;
# version ge=1 rejects v0 at the field level).
PromptId = Annotated[
    str,
    StringConstraints(
        pattern=r"^[a-z][a-z0-9_]*_v[0-9]+$",
        min_length=3,
        max_length=64,
    ),
]

# Relative POSIX path (forward-slash only), no parent traversal.
RelPath = Annotated[
    str,
    StringConstraints(
        pattern=r"^[A-Za-z0-9_\-./]+$",
        min_length=1,
        max_length=256,
    ),
]


# ---------------------------------------------------------------------------
# PromptManifestEntry
# ---------------------------------------------------------------------------


class PromptManifestEntry(BaseModel):
    """One row in prompts/manifest.yaml. Immutable once constructed."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    prompt_id: PromptId = Field(
        description="Stable identifier for this prompt. The numeric suffix after _v is the version.",
    )
    version: int = Field(
        ge=1,
        description="Monotonic integer version. MUST match the numeric suffix of prompt_id.",
    )
    sha256: Sha256Hex = Field(
        description="Lowercase hex SHA-256 digest of the file bytes at path.",
    )
    path: RelPath = Field(
        description="Path relative to the prompts/ directory. Must not contain '..' segments.",
    )

    @model_validator(mode="after")
    def _check_version_matches_id_suffix(self) -> PromptManifestEntry:
        """I2: version field must equal the _v{N} suffix integer in prompt_id."""
        suffix_match = re.search(r"_v([0-9]+)$", self.prompt_id)
        if suffix_match is None:
            raise ValueError(f"I2 violation: prompt_id {self.prompt_id!r} missing _v{{N}} suffix")
        suffix_version = int(suffix_match.group(1))
        if suffix_version != self.version:
            raise ValueError(
                f"I2 violation: prompt_id {self.prompt_id!r} suffix version {suffix_version}"
                f" != field version {self.version}"
            )
        return self

    @model_validator(mode="after")
    def _check_path_safe(self) -> PromptManifestEntry:
        """I4: path must not be absolute and must not contain '..' traversal segments."""
        p = Path(self.path)
        if p.is_absolute():
            raise ValueError(f"I4 violation: path {self.path!r} is absolute; only relative paths are accepted")
        if ".." in p.parts:
            raise ValueError(f"I4 violation: path {self.path!r} contains forbidden '..' segment")
        return self


# ---------------------------------------------------------------------------
# PromptManifest
# ---------------------------------------------------------------------------


class PromptManifest(BaseModel):
    """The whole prompts/manifest.yaml document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: int = Field(
        ge=1,
        description="Manifest schema version. Currently 1.",
    )
    entries: tuple[PromptManifestEntry, ...] = Field(
        min_length=1,
        description="Ordered tuple of prompt entries. Use tuple (not list) for immutability.",
    )

    @model_validator(mode="after")
    def _check_prompt_ids_unique(self) -> PromptManifest:
        """M1: prompt_id values are unique across entries."""
        seen: set[str] = set()
        for entry in self.entries:
            if entry.prompt_id in seen:
                raise ValueError(f"M1 violation: duplicate prompt_id: {entry.prompt_id!r}")
            seen.add(entry.prompt_id)
        return self

    @model_validator(mode="after")
    def _check_versions_monotonic_per_family(self) -> PromptManifest:
        """M2: for a given prompt family (prompt_id sans _v{N}), versions are a dense
        sequence starting at 1 — i.e. exactly 1, 2, 3, … with no gaps or duplicates.

        Trivially satisfied for a v1-only manifest (one entry per family), but enforced
        now so future multi-version adoption cannot skip versions.
        """
        families: dict[str, list[int]] = {}
        for entry in self.entries:
            family = re.sub(r"_v[0-9]+$", "", entry.prompt_id)
            families.setdefault(family, []).append(entry.version)
        for family, versions in families.items():
            sorted_versions = sorted(versions)
            if sorted_versions != list(range(1, len(sorted_versions) + 1)):
                raise ValueError(
                    f"M2 violation: prompt family {family!r} versions must be a dense sequence"
                    f" starting at 1; got {sorted_versions!r}"
                )
        return self
