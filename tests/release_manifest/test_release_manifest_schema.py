"""Contract tests for release-manifest.schema.json (T015, Epic #467).

Validates that the JSON Schema correctly accepts the canonical example and
rejects every malformed variant specified in tasks.md.  No implementation
code is exercised here — this is a pure schema-contract test.
"""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate

# ---------------------------------------------------------------------------
# Fixture: load schema once for the module
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "026-cicd-prompt-registry"
    / "contracts"
    / "release-manifest.schema.json"
)


@pytest.fixture(scope="module")
def schema() -> dict:
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def valid_example(schema: dict) -> dict:
    """Return a deep copy of examples[0] so tests cannot contaminate each other."""
    return copy.deepcopy(schema["examples"][0])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _mutate(base: dict, **kwargs) -> dict:
    """Return a deep copy of *base* with top-level keys updated from *kwargs*.

    Pass a value of ``_DELETE`` sentinel to remove a key instead of setting it.
    """
    obj = copy.deepcopy(base)
    for key, value in kwargs.items():
        if value is _DELETE:
            obj.pop(key, None)
        else:
            obj[key] = value
    return obj


_DELETE = object()


# ---------------------------------------------------------------------------
# 1. Valid baseline
# ---------------------------------------------------------------------------


def test_valid_example_validates(schema: dict, valid_example: dict) -> None:
    """examples[0] from the schema must validate without raising."""
    result = validate(valid_example, schema)
    assert result is None


# ---------------------------------------------------------------------------
# 2. Missing required prompt hash key
# ---------------------------------------------------------------------------


def test_missing_system_v1_prompt_hash_rejected(schema: dict, valid_example: dict) -> None:
    """Removing prompt_hashes.system_v1 must raise ValidationError.

    The schema declares ``required: [system_v1, session_guidance_v1, compact_v1]``
    inside the ``prompt_hashes`` object.
    """
    bad = copy.deepcopy(valid_example)
    del bad["prompt_hashes"]["system_v1"]

    with pytest.raises(ValidationError):
        validate(bad, schema)


# ---------------------------------------------------------------------------
# 3. commit_sha wrong length (39 chars instead of 40)
# ---------------------------------------------------------------------------


def test_commit_sha_wrong_length_rejected(schema: dict, valid_example: dict) -> None:
    """A 39-character hex commit_sha must fail the minLength/pattern constraint."""
    bad = _mutate(valid_example, commit_sha="0123456789abcdef0123456789abcdef0123456")
    assert len(bad["commit_sha"]) == 39  # guard

    with pytest.raises(ValidationError):
        validate(bad, schema)


# ---------------------------------------------------------------------------
# 4. docker_digest without sha256: prefix
# ---------------------------------------------------------------------------


def test_docker_digest_without_sha256_prefix_rejected(schema: dict, valid_example: dict) -> None:
    """A bare 64-char hex docker_digest (no ``sha256:`` prefix) must be rejected.

    The schema pattern is ``^sha256:[0-9a-f]{64}$``.
    """
    raw_hex = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert len(raw_hex) == 64  # guard
    bad = _mutate(valid_example, docker_digest=raw_hex)

    with pytest.raises(ValidationError):
        validate(bad, schema)


# ---------------------------------------------------------------------------
# 5. Extra top-level field (additionalProperties: false)
# ---------------------------------------------------------------------------


def test_extra_top_level_field_rejected(schema: dict, valid_example: dict) -> None:
    """An unexpected top-level field ``api_key`` must be rejected.

    The schema has ``additionalProperties: false``.
    """
    bad = copy.deepcopy(valid_example)
    bad["api_key"] = "sk-super-secret"

    with pytest.raises(ValidationError):
        validate(bad, schema)


# ---------------------------------------------------------------------------
# Bonus 6. uv_lock_hash without sha256: prefix
# ---------------------------------------------------------------------------


def test_uv_lock_hash_without_sha256_prefix_rejected(schema: dict, valid_example: dict) -> None:
    """Parallel structure to docker_digest: bare hex must be rejected for uv_lock_hash."""
    raw_hex = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    bad = _mutate(valid_example, uv_lock_hash=raw_hex)

    with pytest.raises(ValidationError):
        validate(bad, schema)


# ---------------------------------------------------------------------------
# Bonus 7. litellm_proxy_version allows "unknown" placeholder
# ---------------------------------------------------------------------------


def test_litellm_proxy_version_allows_unknown_placeholder(
    schema: dict, valid_example: dict
) -> None:
    """The literal string ``"unknown"`` must pass validation.

    The schema pattern is ``^(unknown|[0-9]+\\.[0-9]+\\.[0-9]+)$``, explicitly
    allowing this placeholder until Epic #465 ships.
    """
    example_with_unknown = _mutate(valid_example, litellm_proxy_version="unknown")
    result = validate(example_with_unknown, schema)
    assert result is None
