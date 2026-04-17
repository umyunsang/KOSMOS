"""Black-box CLI contract tests for tools/release_manifest/render.py (T017, Epic #467).

These tests invoke the render CLI via subprocess so that import errors surface
as clean RED failures before the implementation exists.  No import of the
module under test is performed here.

Expected RED state (pre-implementation):
  subprocess returns returncode == 1 with stderr containing
  "No module named 'tools.release_manifest.render'"

Once tools/release_manifest/render.py is implemented (Phase 3.3), all four
tests should turn GREEN without modification.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import validate

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = (
    REPO_ROOT
    / "specs"
    / "026-cicd-prompt-registry"
    / "contracts"
    / "release-manifest.schema.json"
)

# Fixed synthetic values — all match their respective schema patterns.
_COMMIT_SHA = "1" * 40                    # ^[0-9a-f]{40}$
_UV_LOCK_HASH = "sha256:" + "a" * 64     # ^sha256:[0-9a-f]{64}$
_DOCKER_DIGEST = "sha256:" + "b" * 64   # ^sha256:[0-9a-f]{64}$
_PROMPT_HASHES = {
    "system_v1": "a" * 64,
    "session_guidance_v1": "b" * 64,
    "compact_v1": "c" * 64,
}
# Schema pattern: ^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$
_FRIENDLI_MODEL_ID = "LGAI-EXAONE/exaone-3.5-32b-instruct"
_LITELLM_PROXY_VERSION = "unknown"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_prompt_hashes_file(tmp_path: Path) -> Path:
    """Write the canonical prompt-hashes JSON fixture and return its path."""
    fpath = tmp_path / "prompt-hashes.json"
    fpath.write_text(json.dumps(_PROMPT_HASHES), encoding="utf-8")
    return fpath


def _run_render_cli(*extra_args: str, tmp_path: Path) -> subprocess.CompletedProcess:
    """Invoke tools.release_manifest.render as a module via the current interpreter.

    ``extra_args`` are appended after the fixed --out flag so individual tests
    can override or omit required arguments.
    """
    out_path = tmp_path / "release-manifest.yaml"
    cmd = [
        sys.executable,
        "-m",
        "tools.release_manifest.render",
        *extra_args,
        "--out",
        str(out_path),
    ]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# T017a: happy path — valid YAML output validates against JSON Schema
# ---------------------------------------------------------------------------


def test_happy_path_emits_schema_valid_yaml(tmp_path: Path) -> None:
    """Passing all six CLI args produces a YAML file that validates against the schema.

    CLI args per quickstart.md § C.2:
      --commit-sha <40-hex>
      --uv-lock-hash sha256:<64-hex>
      --docker-digest sha256:<64-hex>
      --prompt-hashes-file <JSON file>
      --friendli-model-id <model-id>
      --litellm-proxy-version unknown
      --out <output path>
    """
    import yaml  # PyYAML — already a project dependency

    prompt_hashes_file = _write_prompt_hashes_file(tmp_path)
    out_path = tmp_path / "release-manifest.yaml"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.release_manifest.render",
            "--commit-sha", _COMMIT_SHA,
            "--uv-lock-hash", _UV_LOCK_HASH,
            "--docker-digest", _DOCKER_DIGEST,
            "--prompt-hashes-file", str(prompt_hashes_file),
            "--friendli-model-id", _FRIENDLI_MODEL_ID,
            "--litellm-proxy-version", _LITELLM_PROXY_VERSION,
            "--out", str(out_path),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode == 0, (
        f"CLI exited {proc.returncode}.\nstdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert out_path.exists(), f"Output file not created at {out_path}"

    with _SCHEMA_PATH.open(encoding="utf-8") as fh:
        schema = json.load(fh)

    with out_path.open(encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    # Raises jsonschema.ValidationError if the output is malformed.
    validate(manifest, schema)


# ---------------------------------------------------------------------------
# T017b: --uv-lock-hash without sha256: prefix must exit non-zero
# ---------------------------------------------------------------------------


def test_uv_lock_hash_without_sha256_prefix_exits_nonzero(tmp_path: Path) -> None:
    """Passing a bare 64-hex uv-lock-hash (no 'sha256:' prefix) must be rejected.

    The CLI is expected to validate the format before writing any output and
    emit a diagnostic on stderr.
    """
    prompt_hashes_file = _write_prompt_hashes_file(tmp_path)
    raw_hex_no_prefix = "a" * 64  # missing "sha256:" prefix

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.release_manifest.render",
            "--commit-sha", _COMMIT_SHA,
            "--uv-lock-hash", raw_hex_no_prefix,   # ← invalid: no prefix
            "--docker-digest", _DOCKER_DIGEST,
            "--prompt-hashes-file", str(prompt_hashes_file),
            "--friendli-model-id", _FRIENDLI_MODEL_ID,
            "--litellm-proxy-version", _LITELLM_PROXY_VERSION,
            "--out", str(tmp_path / "out.yaml"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode != 0, (
        "CLI should have exited non-zero for a uv-lock-hash without 'sha256:' prefix, "
        f"but got returncode={proc.returncode}."
    )
    assert proc.stderr, (
        "CLI produced no stderr output; a diagnostic message is required."
    )


# ---------------------------------------------------------------------------
# T017c: omitting --prompt-hashes-file must exit non-zero
# ---------------------------------------------------------------------------


def test_omitting_prompt_hashes_file_exits_nonzero(tmp_path: Path) -> None:
    """Running the CLI without --prompt-hashes-file must fail with a diagnostic.

    The prompt-hashes file is a required argument per tasks.md T017c.
    The CLI must reject the invocation and write a helpful error to stderr.
    """
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.release_manifest.render",
            "--commit-sha", _COMMIT_SHA,
            "--uv-lock-hash", _UV_LOCK_HASH,
            "--docker-digest", _DOCKER_DIGEST,
            # --prompt-hashes-file intentionally omitted
            "--friendli-model-id", _FRIENDLI_MODEL_ID,
            "--litellm-proxy-version", _LITELLM_PROXY_VERSION,
            "--out", str(tmp_path / "out.yaml"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode != 0, (
        "CLI should have exited non-zero when --prompt-hashes-file is omitted, "
        f"but got returncode={proc.returncode}."
    )
    assert proc.stderr, (
        "CLI produced no stderr output; a diagnostic message is required."
    )


# ---------------------------------------------------------------------------
# T017d: uv.lock drift surrogate — malformed lock hash must exit non-zero
# ---------------------------------------------------------------------------


def test_uv_lock_drift_surrogate_exits_nonzero(tmp_path: Path) -> None:
    """FR-E04 drift-check surrogate: a malformed --uv-lock-hash is rejected.

    TEST-COMMENT (brittleness note):
    -----------------------------------------------------------------------
    This test encodes FR-E04's drift guardrail as a CLI-level check.
    The *ideal* drift test would pass two mismatching lock hashes —
    e.g. ``--uv-lock-hash sha256:<A>`` alongside a ``--verify-lock-hash
    sha256:<B>`` flag — so the CLI can detect a mismatch between the hash
    supplied on the command line and a second source (e.g. a freshly
    computed hash of the checked-out uv.lock).

    However, the exact CLI surface for the drift check has NOT been pinned
    by any accepted spec section as of 2026-04-17.  T034 (FR-E04 full
    implementation) will define whether a ``--verify-lock-hash`` flag, an
    environment variable, or an implicit file-read is used.

    Until T034 lands, this test approximates the drift guardrail by
    supplying a syntactically INVALID lock hash (correct prefix, wrong
    length: 63 hex chars instead of 64).  Any compliant implementation of
    the CLI must reject this and surface a non-zero exit, which is the
    minimum observable signal that the drift-check path is wired up.

    ADJUSTMENT REQUIRED: once T034 pins the drift-check surface, replace
    the malformed-hash approach here with a genuine two-hash mismatch test
    that directly exercises FR-E04's "uv.lock computed hash != supplied
    hash → fail" branch.
    -----------------------------------------------------------------------
    """
    prompt_hashes_file = _write_prompt_hashes_file(tmp_path)
    # sha256: prefix present but only 63 hex chars — wrong length, pattern mismatch.
    malformed_hash = "sha256:" + "a" * 63  # one char short of the required 64

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.release_manifest.render",
            "--commit-sha", _COMMIT_SHA,
            "--uv-lock-hash", malformed_hash,   # ← drift-check surrogate
            "--docker-digest", _DOCKER_DIGEST,
            "--prompt-hashes-file", str(prompt_hashes_file),
            "--friendli-model-id", _FRIENDLI_MODEL_ID,
            "--litellm-proxy-version", _LITELLM_PROXY_VERSION,
            "--out", str(tmp_path / "out.yaml"),
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert proc.returncode != 0, (
        "CLI should have exited non-zero for a malformed uv-lock-hash "
        f"(FR-E04 surrogate), but got returncode={proc.returncode}."
    )
