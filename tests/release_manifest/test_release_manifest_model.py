# SPDX-License-Identifier: Apache-2.0
"""Failing RED tests for the ReleaseManifest Pydantic model (T016).

The module under test — tools.release_manifest.models — does not exist yet
(it will be authored in T033). Every test in this file is expected to fail
with ModuleNotFoundError until T033 is complete.

Invariants covered:
- RM1: prompt_hashes includes system_v1, session_guidance_v1, compact_v1 at minimum.
- RM2: commit_sha is 40-char lowercase hex.
- RM3: uv_lock_hash and docker_digest are sha256:-prefixed 64-hex strings.
- RM4: extra="forbid" blocks unknown fields (NFR-03 enforcement).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from tools.release_manifest.models import ReleaseManifest

# ---------------------------------------------------------------------------
# Shared valid field values (used across happy-path and mutation tests)
# ---------------------------------------------------------------------------

_COMMIT_SHA = "0123456789abcdef0123456789abcdef01234567"
_SHA256_PREFIXED = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_PROMPT_HASHES = {
    "system_v1": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "session_guidance_v1": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "compact_v1": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
}
_FRIENDLI_MODEL_ID = "LGAI-EXAONE/exaone-3.5-32b-instruct"
_LITELLM_PROXY_VERSION = "unknown"


def _valid_kwargs(**overrides: object) -> dict:
    """Return a complete set of valid ReleaseManifest constructor kwargs."""
    base = {
        "commit_sha": _COMMIT_SHA,
        "uv_lock_hash": _SHA256_PREFIXED,
        "docker_digest": _SHA256_PREFIXED,
        "prompt_hashes": dict(_PROMPT_HASHES),
        "friendli_model_id": _FRIENDLI_MODEL_ID,
        "litellm_proxy_version": _LITELLM_PROXY_VERSION,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


class TestReleaseManifestHappyPath:
    def test_valid_manifest_constructs(self) -> None:
        """All six required fields with valid values must produce a frozen model instance."""
        manifest = ReleaseManifest(**_valid_kwargs())
        assert manifest.commit_sha == _COMMIT_SHA
        assert manifest.uv_lock_hash == _SHA256_PREFIXED
        assert manifest.docker_digest == _SHA256_PREFIXED
        assert manifest.prompt_hashes["system_v1"] == _PROMPT_HASHES["system_v1"]
        assert manifest.friendli_model_id == _FRIENDLI_MODEL_ID
        assert manifest.litellm_proxy_version == "unknown"

    def test_litellm_proxy_version_accepts_unknown(self) -> None:
        """The placeholder value 'unknown' must be accepted."""
        manifest = ReleaseManifest(**_valid_kwargs(litellm_proxy_version="unknown"))
        assert manifest.litellm_proxy_version == "unknown"

    def test_litellm_proxy_version_accepts_semver(self) -> None:
        """A full semver string (MAJOR.MINOR.PATCH) must be accepted."""
        manifest = ReleaseManifest(**_valid_kwargs(litellm_proxy_version="1.72.4"))
        assert manifest.litellm_proxy_version == "1.72.4"

    def test_model_is_frozen(self) -> None:
        """Mutation after construction must raise (frozen=True enforcement)."""
        manifest = ReleaseManifest(**_valid_kwargs())
        with pytest.raises(Exception):  # noqa: B017  — pydantic raises ValidationError or TypeError
            manifest.commit_sha = "deadbeef" * 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RM1 — prompt_hashes required keys
# ---------------------------------------------------------------------------


class TestReleaseManifestRM1PromptHashes:
    def test_missing_system_v1_prompt_hash_rejected(self) -> None:
        """prompt_hashes without system_v1 must raise ValidationError (RM1)."""
        incomplete = {
            "session_guidance_v1": _PROMPT_HASHES["session_guidance_v1"],
            "compact_v1": _PROMPT_HASHES["compact_v1"],
        }
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(prompt_hashes=incomplete))

    def test_missing_session_guidance_v1_prompt_hash_rejected(self) -> None:
        """prompt_hashes without session_guidance_v1 must raise ValidationError (RM1)."""
        incomplete = {
            "system_v1": _PROMPT_HASHES["system_v1"],
            "compact_v1": _PROMPT_HASHES["compact_v1"],
        }
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(prompt_hashes=incomplete))

    def test_missing_compact_v1_prompt_hash_rejected(self) -> None:
        """prompt_hashes without compact_v1 must raise ValidationError (RM1)."""
        incomplete = {
            "system_v1": _PROMPT_HASHES["system_v1"],
            "session_guidance_v1": _PROMPT_HASHES["session_guidance_v1"],
        }
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(prompt_hashes=incomplete))

    def test_extra_prompt_hash_alongside_required_accepted(self) -> None:
        """Additional prompt_id keys beyond the three required ones must be accepted."""
        extended = dict(_PROMPT_HASHES)
        extended["tool_guide_v1"] = _PROMPT_HASHES["system_v1"]
        manifest = ReleaseManifest(**_valid_kwargs(prompt_hashes=extended))
        assert "tool_guide_v1" in manifest.prompt_hashes


# ---------------------------------------------------------------------------
# RM2 — commit_sha format
# ---------------------------------------------------------------------------


class TestReleaseManifestRM2CommitSha:
    def test_commit_sha_wrong_length_rejected(self) -> None:
        """A 39-character commit_sha must raise ValidationError (RM2)."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(commit_sha="0123456789abcdef0123456789abcdef0123456"))

    def test_commit_sha_uppercase_rejected(self) -> None:
        """A 40-char commit_sha containing uppercase letters must raise ValidationError (RM2)."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(commit_sha="0123456789ABCDEF0123456789abcdef01234567"))

    def test_commit_sha_too_long_rejected(self) -> None:
        """A 41-character commit_sha must raise ValidationError (RM2)."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(commit_sha="0123456789abcdef0123456789abcdef012345678"))

    def test_commit_sha_non_hex_rejected(self) -> None:
        """A 40-char string containing non-hex characters must raise ValidationError (RM2)."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(commit_sha="gggggggggggggggggggggggggggggggggggggggg"))


# ---------------------------------------------------------------------------
# RM3 — sha256:-prefixed hashes
# ---------------------------------------------------------------------------


class TestReleaseManifestRM3PrefixedHashes:
    def test_docker_digest_without_sha256_prefix_rejected(self) -> None:
        """A bare 64-hex docker_digest without the sha256: prefix must raise (RM3)."""
        bare_hex = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(docker_digest=bare_hex))

    def test_uv_lock_hash_without_sha256_prefix_rejected(self) -> None:
        """A bare 64-hex uv_lock_hash without the sha256: prefix must raise (RM3)."""
        bare_hex = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(uv_lock_hash=bare_hex))

    def test_docker_digest_wrong_prefix_rejected(self) -> None:
        """A docker_digest with 'md5:' prefix must raise (RM3)."""
        with pytest.raises(ValidationError):
            ReleaseManifest(
                **_valid_kwargs(
                    docker_digest="md5:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
                )
            )

    def test_uv_lock_hash_uppercase_hex_rejected(self) -> None:
        """A uv_lock_hash with sha256: prefix but uppercase hex must raise (RM3)."""
        with pytest.raises(ValidationError):
            ReleaseManifest(
                **_valid_kwargs(
                    uv_lock_hash="sha256:E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855"
                )
            )


# ---------------------------------------------------------------------------
# RM4 — extra="forbid"
# ---------------------------------------------------------------------------


class TestReleaseManifestRM4ExtraForbid:
    def test_extra_field_rejected(self) -> None:
        """An unknown field (slack_webhook) must raise ValidationError (RM4, extra='forbid')."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(slack_webhook="https://hooks.slack.com/services/T000/B000/secret"))

    def test_extra_credential_field_rejected(self) -> None:
        """A credential-bearing extra field (api_key) must raise ValidationError (RM4)."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(api_key="sk-secret-key"))


# ---------------------------------------------------------------------------
# litellm_proxy_version format
# ---------------------------------------------------------------------------


class TestLiteLlmProxyVersion:
    def test_litellm_proxy_version_rejects_non_semver(self) -> None:
        """The string 'latest' (not semver, not 'unknown') must raise ValidationError."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(litellm_proxy_version="latest"))

    def test_litellm_proxy_version_rejects_partial_semver(self) -> None:
        """A two-part version '1.72' (missing PATCH) must raise ValidationError."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(litellm_proxy_version="1.72"))

    def test_litellm_proxy_version_rejects_empty(self) -> None:
        """An empty string must raise ValidationError."""
        with pytest.raises(ValidationError):
            ReleaseManifest(**_valid_kwargs(litellm_proxy_version=""))
