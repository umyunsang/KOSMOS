# SPDX-License-Identifier: Apache-2.0
"""Tests for PromptManifest and PromptManifestEntry Pydantic models (prompt_models.py).

Covers:
- M1: prompt_id uniqueness across all manifest entries (ValidationError on duplicate)
- M2: per-family version density — versions must be a 1..N sequence with no gaps or missing v1
- Frozen (immutable) behaviour on PromptManifest
- extra="forbid" enforcement at manifest root
- min_length=1 enforcement on entries

RED phase: src/kosmos/context/prompt_models.py does not exist yet (T024).
A ModuleNotFoundError on collection is the expected RED signal.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.context.prompt_models import PromptManifest, PromptManifestEntry

# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

# Valid 64-character lowercase hex SHA-256 digest (sha256("") canonical form).
_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

# Alternative digest for entries that need a distinct sha256 value.
_SHA2 = "ba7816bf8f01cfea414140de5dae2ec73b00361bbef0469348423f656b6418f4"
_SHA3 = "2c624232cdd221771294dfbb310acbc8f21f97b7b0b9e96d1a3a6a29b9faa8df"


def _entry(
    prompt_id: str,
    version: int,
    sha256: str = _SHA,
    path: str | None = None,
) -> PromptManifestEntry:
    """Build a valid PromptManifestEntry, defaulting path to prompts/<prompt_id>.md."""
    return PromptManifestEntry(
        prompt_id=prompt_id,
        version=version,
        sha256=sha256,
        path=path or f"prompts/{prompt_id}.md",
    )


# ---------------------------------------------------------------------------
# T1 — Happy path: three distinct families each at v1
# ---------------------------------------------------------------------------


class TestValidManifestWithThreeEntries:
    """A manifest with three distinct v1 families constructs without error."""

    def test_version_field_must_match_suffix(self) -> None:
        """Negative: version field mismatching _v{N} suffix must raise."""
        with pytest.raises(ValidationError, match="version"):
            PromptManifest(
                version=1,
                entries=(
                    _entry("system_v1", 1, _SHA),
                    _entry("session_guidance_v1", 2, _SHA2),  # version must match _v suffix
                    _entry("compact_v1", 1, _SHA3),
                ),
            )

    def test_valid_manifest_correct_versions(self) -> None:
        """Proper happy path: each entry's version field matches its _v{N} suffix."""
        manifest = PromptManifest(
            version=1,
            entries=(
                _entry("system_v1", 1, _SHA),
                _entry("session_guidance_v1", 1, _SHA2),
                _entry("compact_v1", 1, _SHA3),
            ),
        )
        assert len(manifest.entries) == 3
        assert manifest.version == 1


# ---------------------------------------------------------------------------
# T2 — M1: duplicate prompt_id raises
# ---------------------------------------------------------------------------


class TestDuplicatePromptIdRejected:
    """M1: two entries with the same prompt_id must raise ValidationError."""

    def test_duplicate_prompt_id_rejected(self) -> None:
        with pytest.raises(ValidationError, match="duplicate prompt_id"):
            PromptManifest(
                version=1,
                entries=(
                    _entry("system_v1", 1, _SHA),
                    _entry("system_v1", 1, _SHA2),  # duplicate
                ),
            )

    def test_duplicate_across_different_positions(self) -> None:
        """Duplicate detected even when non-adjacent."""
        with pytest.raises(ValidationError, match="duplicate prompt_id"):
            PromptManifest(
                version=1,
                entries=(
                    _entry("system_v1", 1, _SHA),
                    _entry("session_guidance_v1", 1, _SHA2),
                    _entry("system_v1", 1, _SHA3),  # duplicate of first
                ),
            )


# ---------------------------------------------------------------------------
# T3 — M2: version gap within a family raises
# ---------------------------------------------------------------------------


class TestVersionGapRejected:
    """M2: a family with v1 and v3 but no v2 must raise ValidationError."""

    def test_version_gap_rejected(self) -> None:
        with pytest.raises(ValidationError, match="dense sequence"):
            PromptManifest(
                version=1,
                entries=(
                    _entry("system_v1", 1, _SHA),
                    _entry("system_v3", 3, _SHA2),  # gap: v2 is missing
                ),
            )


# ---------------------------------------------------------------------------
# T4 — M2: family with only v2 (no v1) raises
# ---------------------------------------------------------------------------


class TestFamilyMissingV1Rejected:
    """M2: a family that starts at v2 with no v1 entry must raise ValidationError."""

    def test_family_missing_v1_rejected(self) -> None:
        with pytest.raises(ValidationError, match="dense sequence"):
            PromptManifest(
                version=1,
                entries=(
                    _entry("system_v2", 2, _SHA),  # no system_v1 sibling
                ),
            )

    def test_family_starting_at_v3_rejected(self) -> None:
        with pytest.raises(ValidationError, match="dense sequence"):
            PromptManifest(
                version=1,
                entries=(
                    _entry("compact_v3", 3, _SHA),  # no v1 or v2
                ),
            )


# ---------------------------------------------------------------------------
# T5 — M2: [v1, v2] dense sequence passes
# ---------------------------------------------------------------------------


class TestMultiVersionFamilyPasses:
    """M2: a family with exactly [v1, v2] must not raise."""

    def test_multi_version_family_passes(self) -> None:
        manifest = PromptManifest(
            version=1,
            entries=(
                _entry("system_v1", 1, _SHA),
                _entry("system_v2", 2, _SHA2),
            ),
        )
        assert len(manifest.entries) == 2

    def test_three_version_dense_family_passes(self) -> None:
        manifest = PromptManifest(
            version=1,
            entries=(
                _entry("system_v1", 1, _SHA),
                _entry("system_v2", 2, _SHA2),
                _entry("system_v3", 3, _SHA3),
            ),
        )
        assert len(manifest.entries) == 3

    def test_mixed_families_multi_version_passes(self) -> None:
        """Two families, one at v1, one at [v1, v2] — both valid."""
        manifest = PromptManifest(
            version=1,
            entries=(
                _entry("system_v1", 1, _SHA),
                _entry("system_v2", 2, _SHA2),
                _entry("compact_v1", 1, _SHA3),
            ),
        )
        assert len(manifest.entries) == 3


# ---------------------------------------------------------------------------
# T6 — Frozen: mutation of entries raises
# ---------------------------------------------------------------------------


class TestManifestIsFrozen:
    """PromptManifest is frozen=True; any attribute mutation must raise."""

    def test_manifest_is_frozen(self) -> None:
        manifest = PromptManifest(
            version=1,
            entries=(_entry("system_v1", 1, _SHA),),
        )
        with pytest.raises((ValidationError, TypeError)):
            manifest.entries = ()  # type: ignore[misc]

    def test_manifest_version_is_frozen(self) -> None:
        manifest = PromptManifest(
            version=1,
            entries=(_entry("system_v1", 1, _SHA),),
        )
        with pytest.raises((ValidationError, TypeError)):
            manifest.version = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T7 — extra="forbid": unknown field at manifest root raises
# ---------------------------------------------------------------------------


class TestExtraFieldForbidden:
    """PromptManifest must reject unrecognised top-level fields."""

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            PromptManifest(
                version=1,
                entries=(_entry("system_v1", 1, _SHA),),
                unknown_field="should_be_rejected",  # type: ignore[call-arg]
            )

    def test_extra_nested_field_on_entry_forbidden(self) -> None:
        """PromptManifestEntry also enforces extra='forbid'."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id="system_v1",
                version=1,
                sha256=_SHA,
                path="prompts/system_v1.md",
                surprise="not_allowed",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# T8 — min_length=1: zero entries rejected
# ---------------------------------------------------------------------------


class TestEmptyEntriesRejected:
    """entries tuple must contain at least one entry (min_length=1)."""

    def test_empty_entries_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PromptManifest(
                version=1,
                entries=(),
            )

    def test_empty_list_entries_rejected(self) -> None:
        """Passing a list (coerced to tuple by Pydantic) with zero items also raises."""
        with pytest.raises(ValidationError):
            PromptManifest(
                version=1,
                entries=[],  # type: ignore[arg-type]
            )
