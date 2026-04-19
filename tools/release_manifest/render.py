# SPDX-License-Identifier: Apache-2.0
"""CLI entry point: python -m tools.release_manifest.render

Renders a ReleaseManifest as canonical YAML and writes it to --out.

Usage (see quickstart.md § C.2):
    python -m tools.release_manifest.render \\
        --commit-sha <40-hex> \\
        --uv-lock-hash sha256:<64-hex> \\
        --docker-digest sha256:<64-hex> \\
        --prompt-hashes-file <path-to-json> \\
        --friendli-model-id <org/repo> \\
        --litellm-proxy-version <semver|unknown> \\
        --out <output-path>

Exit codes:
    0  — success; YAML written to --out.
    1  — validation failure (Pydantic ValidationError or malformed input).
    2  — CLI argument error (argparse default).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml
from pydantic import ValidationError
from tools.release_manifest.models import ReleaseManifest

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.release_manifest.render",
        description="Render a ReleaseManifest YAML from CI inputs.",
    )
    parser.add_argument(
        "--commit-sha",
        required=True,
        metavar="SHA",
        help="40-char lowercase hex git commit SHA (e.g. $(git rev-parse HEAD)).",
    )
    parser.add_argument(
        "--uv-lock-hash",
        required=True,
        metavar="HASH",
        help="sha256:<64-hex> digest of uv.lock bytes.",
    )
    parser.add_argument(
        "--docker-digest",
        required=True,
        metavar="DIGEST",
        help="sha256:<64-hex> digest of the published Docker image manifest.",
    )
    parser.add_argument(
        "--prompt-hashes-file",
        required=True,
        metavar="FILE",
        help=(
            "Path to a JSON file containing a dict[prompt_id, sha256_hex] mapping "
            "(emitted by: python -m kosmos.context.prompt_loader --emit-hashes)."
        ),
    )
    parser.add_argument(
        "--friendli-model-id",
        required=True,
        metavar="MODEL_ID",
        help="FriendliAI-hosted model identifier (e.g. LGAI-EXAONE/exaone-3.5-32b-instruct).",
    )
    parser.add_argument(
        "--litellm-proxy-version",
        required=True,
        metavar="VERSION",
        help='LiteLLM proxy version (semver or "unknown").',
    )
    parser.add_argument(
        "--out",
        required=True,
        metavar="PATH",
        help="Destination YAML file path. Parent directory must already exist.",
    )
    return parser


def _load_prompt_hashes(file_path: str) -> dict[str, str]:
    """Load and validate the prompt-hashes JSON file.

    Expected format: a flat JSON object mapping prompt_id strings to
    64-char lowercase hex SHA-256 digest strings.

    Exits with code 1 on any read or parse error.
    """
    path = Path(file_path)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to read --prompt-hashes-file %r: %s", file_path, exc)
        sys.stderr.write(f"ERROR: cannot read --prompt-hashes-file {file_path!r}: {exc}\n")
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("--prompt-hashes-file %r is not valid JSON: %s", file_path, exc)
        sys.stderr.write(f"ERROR: --prompt-hashes-file {file_path!r} is not valid JSON: {exc}\n")
        sys.exit(1)

    if not isinstance(data, dict):
        msg = f"--prompt-hashes-file must contain a JSON object, got {type(data).__name__}"
        logger.error(msg)
        sys.stderr.write(f"ERROR: {msg}\n")
        sys.exit(1)

    # Verify all values are strings (basic shape guard before Pydantic validates patterns).
    for key, value in data.items():
        if not isinstance(key, str) or not isinstance(value, str):
            msg = (
                f"--prompt-hashes-file entries must be string → string mappings; "
                f"got key={key!r} ({type(key).__name__}), value={value!r} ({type(value).__name__})"
            )
            logger.error(msg)
            sys.stderr.write(f"ERROR: {msg}\n")
            sys.exit(1)

    return data  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    parser = _build_parser()
    args = parser.parse_args(argv)

    logger.debug("Parsed CLI args: %s", args)

    # Load and validate the prompt-hashes JSON file.
    prompt_hashes = _load_prompt_hashes(args.prompt_hashes_file)

    # Construct and validate the ReleaseManifest (enforces RM1-RM4).
    try:
        manifest = ReleaseManifest(
            commit_sha=args.commit_sha,
            uv_lock_hash=args.uv_lock_hash,
            docker_digest=args.docker_digest,
            prompt_hashes=prompt_hashes,
            friendli_model_id=args.friendli_model_id,
            litellm_proxy_version=args.litellm_proxy_version,
        )
    except ValidationError as exc:
        logger.error("ReleaseManifest validation failed:\n%s", exc)
        sys.stderr.write(f"ERROR: validation failed:\n{exc}\n")
        sys.exit(1)

    logger.info(
        "ReleaseManifest validated: commit_sha=%s prompt_hashes_count=%d",
        manifest.commit_sha,
        len(manifest.prompt_hashes),
    )

    # Serialise to canonical YAML: sorted keys, block style, no anchors/aliases, UTF-8.
    data = manifest.model_dump()
    yaml_text = yaml.safe_dump(data, sort_keys=True, default_flow_style=False, allow_unicode=True)

    # Write output — parent directory must already exist (per spec; do not auto-mkdir).
    out_path = Path(args.out)
    try:
        out_path.write_text(yaml_text, encoding="utf-8")
    except OSError as exc:
        logger.error("Failed to write output to %r: %s", args.out, exc)
        sys.stderr.write(f"ERROR: cannot write output to {args.out!r}: {exc}\n")
        sys.exit(1)

    logger.info("Release manifest written to %s", out_path)


if __name__ == "__main__":
    main()
