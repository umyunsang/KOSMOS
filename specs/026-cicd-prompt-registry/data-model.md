# Phase 1 — Data Model: CI/CD & Prompt Registry

**Feature**: Spec 026 — CI/CD & Prompt Registry
**Date**: 2026-04-17
**Scope**: Pydantic v2 models for the Prompt Registry manifest and the Release Manifest. All models are `frozen=True`, `extra="forbid"`, no `typing.Any`, stdlib + `pydantic >= 2.13` only.

The schema contracts (JSON Schema Draft 2020-12) that mirror these models live under `contracts/`. The Pydantic models are the single source of truth at runtime; the JSON Schemas are for CI validation of the YAML files themselves (pre-load check in GitHub Actions).

## 1. Prompt Registry — `PromptManifestEntry`

```python
# src/kosmos/context/prompt_loader.py (Phase 1 contract; implementation in /speckit-implement)

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

# 64 lowercase hex characters — SHA-256 digest canonical form.
Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64)]

# snake_case prompt identifier with mandatory _v{N} suffix (N >= 1).
PromptId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*_v[0-9]+$", min_length=3, max_length=64)]

# Relative POSIX path (forward-slash only), no parent traversal.
RelPath = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_\-./]+$", min_length=1, max_length=256)]


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
        """Invariant: version field must equal the _v{N} suffix in prompt_id."""
        suffix_match = re.search(r"_v([0-9]+)$", self.prompt_id)
        if suffix_match is None:
            raise ValueError(f"prompt_id {self.prompt_id!r} missing _v{{N}} suffix")
        suffix_version = int(suffix_match.group(1))
        if suffix_version != self.version:
            raise ValueError(
                f"prompt_id {self.prompt_id!r} suffix version {suffix_version} != field version {self.version}"
            )
        return self

    @model_validator(mode="after")
    def _check_path_safe(self) -> PromptManifestEntry:
        """Invariant: path must not escape the prompts/ directory via .. segments."""
        if ".." in Path(self.path).parts:
            raise ValueError(f"path {self.path!r} contains forbidden .. segment")
        return self
```

**Invariants enforced at model construction time**:

- I1 — `prompt_id` is snake_case + `_v{N}` suffix.
- I2 — `version` is a positive integer AND equals the `_v{N}` suffix in `prompt_id`.
- I3 — `sha256` is exactly 64 lowercase hex characters.
- I4 — `path` is a safe relative path (no `..`, no absolute prefix).

## 2. Prompt Registry — `PromptManifest`

```python
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
        """Invariant M1: prompt_id values are unique across entries."""
        seen: set[str] = set()
        for entry in self.entries:
            if entry.prompt_id in seen:
                raise ValueError(f"duplicate prompt_id: {entry.prompt_id!r}")
            seen.add(entry.prompt_id)
        return self

    @model_validator(mode="after")
    def _check_versions_monotonic_per_family(self) -> PromptManifest:
        """Invariant M2: for a given prompt family (prompt_id sans _v{N}),
        versions are strictly monotonic and start at 1.

        This invariant is trivially satisfied for the v1 manifest (one entry per family)
        but is enforced now so v2 adoption cannot skip versions or reuse them.
        """
        families: dict[str, list[int]] = {}
        for entry in self.entries:
            family = re.sub(r"_v[0-9]+$", "", entry.prompt_id)
            families.setdefault(family, []).append(entry.version)
        for family, versions in families.items():
            sorted_versions = sorted(versions)
            if sorted_versions != list(range(1, len(sorted_versions) + 1)):
                raise ValueError(
                    f"prompt family {family!r} versions must be a dense sequence starting at 1; got {sorted_versions!r}"
                )
        return self
```

**Invariants enforced at the manifest level**:

- M1 — `prompt_id` is unique across all entries.
- M2 — within a family (the substring before `_v{N}`), versions form `1, 2, 3, ...` with no gaps or duplicates.

**Runtime-only invariants (enforced by `PromptLoader`, not by the model)**:

- R1 — every file named in `entries[].path` exists on disk under `prompts/`.
- R2 — computed SHA-256 over each file's bytes equals the manifest `sha256`.
- R3 — no orphan `prompts/*.md` exists that is not listed in `entries` (fail-closed per spec.md Edge Cases).

## 3. Release Manifest — `ReleaseManifest`

```python
# Authored in .github/workflows/release-manifest.yml via a tiny helper module;
# lives under scripts/ or tools/ (final location chosen in /speckit-implement).

from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

CommitSha = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$", min_length=40, max_length=40)]
Sha256Prefixed = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$", min_length=71, max_length=71)]
# Model id follows HuggingFace convention: "<org>/<repo>[:<tag>]".
FriendliModelId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$", min_length=3, max_length=128)]
# litellm_proxy_version is either a semver (e.g. "1.72.4") or the placeholder "unknown".
LiteLlmProxyVersion = Annotated[str, StringConstraints(pattern=r"^(unknown|[0-9]+\.[0-9]+\.[0-9]+)$", min_length=3, max_length=32)]


class ReleaseManifest(BaseModel):
    """docs/release-manifests/<commit_sha>.yaml — one per release tag push."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    commit_sha: CommitSha = Field(description="40-char lowercase hex git commit sha this release was built from.")
    uv_lock_hash: Sha256Prefixed = Field(description="sha256:<hex> of uv.lock bytes at commit_sha.")
    docker_digest: Sha256Prefixed = Field(description="sha256:<hex> of the published Docker image manifest.")
    prompt_hashes: dict[PromptId, Sha256Hex] = Field(
        min_length=1,
        description="Mapping from prompt_id to sha256 hex for every prompt in prompts/manifest.yaml at commit_sha.",
    )
    friendli_model_id: FriendliModelId = Field(description="FriendliAI-hosted model identifier in use at release time.")
    litellm_proxy_version: LiteLlmProxyVersion = Field(
        description='Gateway proxy version. Placeholder "unknown" until Epic #465 ships.',
    )

    @model_validator(mode="after")
    def _check_prompt_hashes_non_empty(self) -> ReleaseManifest:
        """Invariant RM1: prompt_hashes must list at least three entries — system_v1,
        session_guidance_v1, and compact_v1 are required at the first release."""
        required = {"system_v1", "session_guidance_v1", "compact_v1"}
        missing = required - set(self.prompt_hashes.keys())
        if missing:
            raise ValueError(f"prompt_hashes is missing required entries: {sorted(missing)!r}")
        return self
```

**Invariants enforced**:

- RM1 — `prompt_hashes` includes at minimum `system_v1`, `session_guidance_v1`, `compact_v1`.
- RM2 — `commit_sha` is a 40-char lowercase hex string (git SHA-1 canonical form).
- RM3 — `uv_lock_hash` and `docker_digest` are both `sha256:`-prefixed 64-hex to disambiguate from bare commit shas.
- RM4 — `extra="forbid"` blocks accidental addition of credential-bearing fields — NFR-03 enforcement at schema level.

## 4. Cross-Model Relationships

```
                       ┌──────────────────────────┐
                       │  PromptManifestEntry     │
                       │  (prompt_id, version,    │
                       │   sha256, path)          │
                       └────────────┬─────────────┘
                                    │ 1..N (tuple, frozen)
                                    ▼
                       ┌──────────────────────────┐
                       │  PromptManifest          │
                       │  (version, entries)      │
                       └────────────┬─────────────┘
                                    │ loaded at startup by
                                    ▼
                       ┌──────────────────────────┐
                       │  PromptLoader            │
                       │  .load(prompt_id) -> str │
                       │  .get_hash(id) -> str    │◄── consumed by Context Assembly to stamp
                       │  .all_hashes() -> dict   │    kosmos.prompt.hash on every LLM span (FR-C07)
                       └────────────┬─────────────┘
                                    │ at release time, .all_hashes() is read by
                                    ▼
                       ┌──────────────────────────┐
                       │  build-manifest job      │
                       │  → ReleaseManifest       │
                       │    .prompt_hashes        │
                       └──────────────────────────┘
```

## 5. State Transitions

### 5.1 Prompt lifecycle

```
[file added under prompts/]
      │
      ▼
[manifest entry added to prompts/manifest.yaml] ──► CI schema check passes ──► PromptLoader loads it at boot
                                                                                         │
                                                                                         ▼
                                                                                 [published in release manifest]
```

A prompt is **never mutated in place**. A content change is a new `_v{N+1}` file with a new manifest entry; the old entry may be removed or retained depending on rollback needs. Phase 1 only delivers v1 entries.

### 5.2 Release-manifest lifecycle

```
[tag push v*.*.*] ──► build-manifest job ──► ReleaseManifest written to docs/release-manifests/<sha>.yaml
                                                                │
                                                                ▼
                                                        [commit-back to main]
                                                                │
                                                                ▼
                                                        [file is append-only;
                                                         never edited in place]
```

Manifest files are treated as an append-only log — historical entries are never rewritten. If a manifest field evolves (e.g., `litellm_proxy_version` becomes real once Epic #465 ships), the next tag's manifest reflects the new value; previous manifests keep the `"unknown"` placeholder for historical fidelity.

## 6. Forbidden Patterns

To keep this schema honest against Constitution Principle III and Spec 025 lessons:

- ❌ `typing.Any` — every field is concretely typed.
- ❌ `dict[str, object]` — concrete value types always.
- ❌ `Optional[...]` on identity fields (`commit_sha`, `prompt_id`, `sha256`) — these are required and have no meaningful null.
- ❌ `model_config = ConfigDict(frozen=False)` — every model is immutable.
- ❌ `extra="allow"` — every model forbids unknown keys (defends against typos + NFR-03 secret-leak class).
- ❌ Mutable default factories on list fields — use `tuple[...]` instead of `list[...]` for collections.
