"""Contract validation tests for prompts-manifest.schema.json (JSON Schema Draft 2020-12).

These tests assert that the schema correctly accepts well-formed manifests and rejects
malformed ones. This is a RED-phase contract test; no implementation code is exercised.
"""

import json
import logging
from pathlib import Path

import jsonschema
import pytest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema fixture
# ---------------------------------------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "026-cicd-prompt-registry"
    / "contracts"
    / "prompts-manifest.schema.json"
)

_VALID_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
_VALID_SHA256_B = "a" * 64
_VALID_SHA256_C = "b" * 63 + "0"


@pytest.fixture(scope="module")
def schema() -> dict:
    """Load the JSON Schema document from the specs directory."""
    assert _SCHEMA_PATH.exists(), f"Schema not found at {_SCHEMA_PATH}"
    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        loaded = json.load(fh)
    logger.debug("Loaded schema from %s", _SCHEMA_PATH)
    return loaded


@pytest.fixture()
def valid_manifest() -> dict:
    """Return a well-formed manifest with the three canonical prompt entries."""
    return {
        "version": 1,
        "entries": [
            {
                "prompt_id": "system_v1",
                "version": 1,
                "sha256": _VALID_SHA256,
                "path": "system_v1.md",
            },
            {
                "prompt_id": "session_guidance_v1",
                "version": 1,
                "sha256": _VALID_SHA256_B,
                "path": "session_guidance_v1.md",
            },
            {
                "prompt_id": "compact_v1",
                "version": 1,
                "sha256": _VALID_SHA256_C,
                "path": "compact_v1.md",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


def test_valid_manifest_passes_schema(schema: dict, valid_manifest: dict) -> None:
    """A well-formed manifest with three entries must pass schema validation without error.

    Covers: version=1 (integer >= 1), three entries with lowercase snake_case prompt_ids
    ending in _v{N}, 64-hex sha256 values, and relative .md paths.
    """
    result = jsonschema.validate(instance=valid_manifest, schema=schema)
    # jsonschema.validate returns None on success
    assert result is None


def test_bad_prompt_id_pattern_raises_validation_error(schema: dict, valid_manifest: dict) -> None:
    """An entry whose prompt_id violates the pattern ^[a-z][a-z0-9_]*_v[0-9]+$ must be rejected.

    'System_V1' contains uppercase letters and does not match the required pattern, so
    jsonschema must raise ValidationError.
    """
    manifest = valid_manifest.copy()
    manifest["entries"] = list(manifest["entries"])  # shallow copy the list
    # Replace first entry with a bad prompt_id (uppercase, missing _v suffix pattern)
    manifest["entries"][0] = {
        "prompt_id": "System_V1",  # uppercase — violates ^[a-z][a-z0-9_]*_v[0-9]+$
        "version": 1,
        "sha256": _VALID_SHA256,
        "path": "system_v1.md",
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)


def test_missing_sha256_raises_validation_error(schema: dict, valid_manifest: dict) -> None:
    """An entry that omits the required 'sha256' field must be rejected by the schema.

    The schema marks sha256 as required in promptManifestEntry, so its absence must
    trigger a ValidationError.
    """
    manifest = valid_manifest.copy()
    manifest["entries"] = list(manifest["entries"])
    entry_without_sha256 = {
        "prompt_id": "compact_v1",
        "version": 1,
        # sha256 intentionally omitted
        "path": "compact_v1.md",
    }
    manifest["entries"][2] = entry_without_sha256
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)


def test_extra_top_level_field_raises_validation_error(schema: dict, valid_manifest: dict) -> None:
    """A manifest with an unexpected top-level key must be rejected.

    The schema sets 'additionalProperties: false' at the root object level, so any key
    beyond 'version' and 'entries' (e.g. 'api_key') must trigger a ValidationError.
    """
    manifest = dict(valid_manifest)
    manifest["api_key"] = "supersecret-token-that-should-not-be-here"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=manifest, schema=schema)
