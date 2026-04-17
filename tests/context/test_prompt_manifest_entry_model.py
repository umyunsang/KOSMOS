# SPDX-License-Identifier: Apache-2.0
"""Tests for PromptManifestEntry — Pydantic v2 model (spec 026, data-model.md § 1).

RED phase (T006): the target module does not exist yet.
Pytest will collect these tests but fail at import with ModuleNotFoundError.
That is the expected state until T024 creates the model.

Invariants under test:
- I1  prompt_id matches ^[a-z][a-z0-9_]*_v[0-9]+$
- I2  version integer equals the _v{N} numeric suffix of prompt_id
- I3  sha256 is exactly 64 lowercase hex characters (0-9a-f)
- I4  path must not contain '..' traversal segments
- I4b model is frozen=True; mutation after construction raises ValidationError
- extra="forbid" blocks unknown constructor kwargs
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.context.prompt_models import PromptManifestEntry

# ---------------------------------------------------------------------------
# Shared valid fixture values — all invariants satisfied simultaneously.
# ---------------------------------------------------------------------------
_VALID_SHA256 = "a" * 64  # 64 lowercase hex chars (a is valid hex)
_VALID_PROMPT_ID = "system_v1"
_VALID_VERSION = 1
_VALID_PATH = "system_v1.md"


def _valid_entry(**overrides: object) -> PromptManifestEntry:
    """Construct a fully-valid PromptManifestEntry, optionally overriding fields."""
    kwargs: dict[str, object] = {
        "prompt_id": _VALID_PROMPT_ID,
        "version": _VALID_VERSION,
        "sha256": _VALID_SHA256,
        "path": _VALID_PATH,
    }
    kwargs.update(overrides)
    return PromptManifestEntry(**kwargs)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidEntryConstruction:
    """A well-formed entry must construct without error."""

    def test_valid_entry_constructs_successfully(self) -> None:
        entry = _valid_entry()
        assert entry.prompt_id == _VALID_PROMPT_ID
        assert entry.version == _VALID_VERSION
        assert entry.sha256 == _VALID_SHA256
        assert entry.path == _VALID_PATH

    def test_another_valid_prompt_id_family(self) -> None:
        """session_guidance_v1 is a well-formed prompt_id with version=1."""
        entry = _valid_entry(
            prompt_id="session_guidance_v1",
            version=1,
            path="session_guidance_v1.md",
        )
        assert entry.prompt_id == "session_guidance_v1"

    def test_version_two_entry_constructs_successfully(self) -> None:
        """_v2 suffix with version=2 must be accepted."""
        entry = _valid_entry(
            prompt_id="compact_v2",
            version=2,
            path="compact_v2.md",
        )
        assert entry.version == 2


# ---------------------------------------------------------------------------
# I2 — version must match _v{N} suffix in prompt_id
# ---------------------------------------------------------------------------


class TestVersionMustMatchPromptIdSuffix:
    """Invariant I2: version field value must equal the suffix integer in prompt_id."""

    def test_version_must_match_prompt_id_suffix(self) -> None:
        """prompt_id ends in _v1 but version=2; model_validator must reject this."""
        with pytest.raises(ValidationError):
            _valid_entry(prompt_id="system_v1", version=2)

    def test_version_zero_with_v0_suffix_rejected(self) -> None:
        """version must be >= 1 (Field(ge=1)), so even a matching v0 is invalid."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id="system_v0",  # pattern allows v0 but version ge=1 blocks it
                version=0,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
            )

    def test_suffix_three_with_version_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _valid_entry(prompt_id="compact_v3", version=1)


# ---------------------------------------------------------------------------
# I4 — path must not contain '..' traversal segments
# ---------------------------------------------------------------------------


class TestPathWithParentTraversalRejected:
    """Invariant I4: paths containing '..' must be rejected."""

    def test_path_with_parent_traversal_rejected(self) -> None:
        """'../x.md' uses a parent traversal segment — must raise."""
        with pytest.raises(ValidationError):
            _valid_entry(path="../x.md")

    def test_path_with_embedded_traversal_rejected(self) -> None:
        """'prompts/../../secret.md' must also raise."""
        with pytest.raises(ValidationError):
            _valid_entry(path="prompts/../../secret.md")

    def test_absolute_path_rejected(self) -> None:
        """Absolute paths ('/etc/passwd') are not relative POSIX paths and must raise."""
        with pytest.raises(ValidationError):
            _valid_entry(path="/etc/passwd")


# ---------------------------------------------------------------------------
# I3 — sha256 must be exactly 64 lowercase hex characters
# ---------------------------------------------------------------------------


class TestSha256MustBeLowercaseHex:
    """Invariant I3: sha256 must match ^[0-9a-f]{64}$."""

    def test_sha256_must_be_lowercase_hex(self) -> None:
        """'Z'*64 contains uppercase letters — must raise."""
        with pytest.raises(ValidationError):
            _valid_entry(sha256="Z" * 64)

    def test_sha256_with_non_hex_chars_rejected(self) -> None:
        """'g'*64 contains chars outside 0-9a-f — must raise."""
        with pytest.raises(ValidationError):
            _valid_entry(sha256="g" * 64)

    def test_sha256_uppercase_hex_rejected(self) -> None:
        """'A'*64 is uppercase hex — the pattern requires lowercase — must raise."""
        with pytest.raises(ValidationError):
            _valid_entry(sha256="A" * 64)


class TestSha256MustBeExactly64Chars:
    """sha256 length boundary enforcement."""

    def test_sha256_must_be_exactly_64_chars(self) -> None:
        """63-char hex string is one char short — must raise."""
        with pytest.raises(ValidationError):
            _valid_entry(sha256="a" * 63)

    def test_sha256_65_chars_rejected(self) -> None:
        """65-char hex string is one char too long — must raise."""
        with pytest.raises(ValidationError):
            _valid_entry(sha256="a" * 65)

    def test_sha256_empty_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _valid_entry(sha256="")


# ---------------------------------------------------------------------------
# I1 — prompt_id pattern ^[a-z][a-z0-9_]*_v[0-9]+$
# ---------------------------------------------------------------------------


class TestPromptIdPatternEnforced:
    """Invariant I1: prompt_id must match the snake_case + _v{N} pattern."""

    def test_prompt_id_pattern_enforced(self) -> None:
        """'System_V1' starts with uppercase — must raise."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id="System_V1",
                version=1,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
            )

    def test_prompt_id_missing_version_suffix_rejected(self) -> None:
        """'system' has no _v{N} suffix — must raise."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id="system",
                version=1,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
            )

    def test_prompt_id_uppercase_mid_rejected(self) -> None:
        """'system_Prompt_v1' contains uppercase — must raise."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id="system_Prompt_v1",
                version=1,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
            )

    def test_prompt_id_starting_with_digit_rejected(self) -> None:
        """'1system_v1' starts with a digit — must raise (pattern: ^[a-z])."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id="1system_v1",
                version=1,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
            )

    def test_prompt_id_with_hyphen_rejected(self) -> None:
        """'system-v1' uses a hyphen — the pattern only allows underscores — must raise."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id="system-v1",
                version=1,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
            )


# ---------------------------------------------------------------------------
# Frozen — mutation after construction must raise
# ---------------------------------------------------------------------------


class TestEntryIsFrozen:
    """model_config.frozen=True; any attribute assignment raises ValidationError."""

    def test_entry_is_frozen(self) -> None:
        """Assigning to entry.version after construction must raise ValidationError."""
        entry = _valid_entry()
        with pytest.raises(ValidationError):
            entry.version = 99  # type: ignore[misc]

    def test_sha256_mutation_raises(self) -> None:
        entry = _valid_entry()
        with pytest.raises(ValidationError):
            entry.sha256 = "b" * 64  # type: ignore[misc]

    def test_path_mutation_raises(self) -> None:
        entry = _valid_entry()
        with pytest.raises(ValidationError):
            entry.path = "other_v1.md"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# extra="forbid" — unknown constructor kwargs must raise
# ---------------------------------------------------------------------------


class TestExtraFieldForbidden:
    """model_config.extra='forbid'; unexpected kwargs at construction must raise."""

    def test_extra_field_forbidden(self) -> None:
        """Passing an unknown field must raise ValidationError, not silently ignore it."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id=_VALID_PROMPT_ID,
                version=_VALID_VERSION,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
                unknown_field="should_not_be_accepted",  # type: ignore[call-arg]
            )

    def test_credential_like_field_rejected(self) -> None:
        """A field named 'api_key' must not sneak through — extra='forbid' defence."""
        with pytest.raises(ValidationError):
            PromptManifestEntry(
                prompt_id=_VALID_PROMPT_ID,
                version=_VALID_VERSION,
                sha256=_VALID_SHA256,
                path=_VALID_PATH,
                api_key="secret-value",  # type: ignore[call-arg]
            )
