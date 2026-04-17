# SPDX-License-Identifier: Apache-2.0
"""PromptLoader — Prompt Registry for the KOSMOS platform.

Loads prompts/manifest.yaml at startup, verifies SHA-256 integrity for every
listed prompt file, and serves immutable prompt strings to the Context Assembly
layer (FR-C03, FR-C04, FR-C08, FR-C09, FR-C10).

Fail-closed invariants (raised as PromptRegistryError at construction time):
  R1 — a manifest-listed file is absent from disk.
  R2 — a file's computed SHA-256 does not match the manifest entry.
  R3 — a .md file exists under the prompts directory that is not listed in the
       manifest (orphan-file detection).

Usage::

    from kosmos.context.prompt_loader import PromptLoader

    loader = PromptLoader(manifest_path=Path("prompts/manifest.yaml"))
    text   = loader.load("system_v1")
    digest = loader.get_hash("system_v1")
    hashes = loader.all_hashes()          # dict[prompt_id, sha256_hex]

CLI::

    python -m kosmos.context.prompt_loader --regenerate-manifest
    python -m kosmos.context.prompt_loader --emit-hashes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import yaml

from kosmos.context.prompt_models import PromptManifest

__all__ = ["PromptLoader", "PromptRegistryError"]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class PromptRegistryError(RuntimeError):
    """Raised on any integrity or configuration failure in the Prompt Registry.

    Covers R1 (missing file), R2 (hash mismatch), R3 (orphan file), and
    Langfuse opt-in failures (FR-C09).
    """


# ---------------------------------------------------------------------------
# PromptLoader
# ---------------------------------------------------------------------------


class PromptLoader:
    """Reads prompts/manifest.yaml at construction time and exposes immutable
    prompt strings and their SHA-256 digests to callers.

    Parameters
    ----------
    manifest_path:
        Path to the manifest YAML file (typically ``prompts/manifest.yaml``).
        The prompt files are resolved relative to the directory that contains
        this file (i.e. ``manifest_path.parent``).
    langfuse_enabled:
        Override for the Langfuse opt-in flag.  If ``None`` (default), the
        value is read from the environment variable
        ``KOSMOS_PROMPT_REGISTRY_LANGFUSE``.  Passing an explicit bool is
        intended for tests that need deterministic behaviour.

    Raises
    ------
    PromptRegistryError
        On any R1/R2/R3 violation or on Langfuse opt-in failures (FR-C09).
    """

    def __init__(
        self,
        manifest_path: Path,
        langfuse_enabled: bool | None = None,
    ) -> None:
        self._manifest_path = manifest_path
        self._prompts_dir = manifest_path.parent

        # Resolve the Langfuse flag once so we don't repeatedly touch os.environ.
        if langfuse_enabled is None:
            langfuse_enabled = (
                os.environ.get("KOSMOS_PROMPT_REGISTRY_LANGFUSE", "").strip().lower() == "true"
            )
        self._langfuse_enabled = langfuse_enabled

        # Internal caches — populated during _load_and_verify().
        self._texts: dict[str, str] = {}
        self._hashes: dict[str, str] = {}

        self._load_and_verify()

        if self._langfuse_enabled:
            self._verify_langfuse()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, prompt_id: str) -> str:
        """Return the immutable prompt text for *prompt_id*.

        The returned string is the exact bytes of the file decoded as UTF-8,
        cached on first access.

        Raises
        ------
        KeyError
            If *prompt_id* is not registered in the manifest.
        """
        return self._texts[prompt_id]

    def get_hash(self, prompt_id: str) -> str:
        """Return the SHA-256 hex digest that was verified at load time.

        Used by the Context Assembly layer to stamp ``kosmos.prompt.hash`` on
        every LLM span (FR-C07).

        Raises
        ------
        KeyError
            If *prompt_id* is not registered.
        """
        return self._hashes[prompt_id]

    def all_hashes(self) -> Mapping[str, str]:
        """Return an immutable mapping of *prompt_id* → sha256 hex.

        Used by the release-manifest job to populate ``prompt_hashes``.
        """
        return MappingProxyType(self._hashes)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_and_verify(self) -> None:
        """Parse manifest.yaml, verify file integrity, enforce R1/R2/R3."""
        # --- Parse YAML -------------------------------------------------------
        try:
            raw = yaml.safe_load(self._manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PromptRegistryError(f"Prompt manifest not found: {self._manifest_path}") from exc

        # --- Validate with Pydantic model (M1, M2, I1–I4) --------------------
        try:
            manifest = PromptManifest.model_validate(raw)
        except Exception as exc:
            raise PromptRegistryError(f"Invalid manifest at {self._manifest_path}: {exc}") from exc

        # --- R3: detect orphan .md files not listed in the manifest -----------
        listed_paths: set[str] = {entry.path for entry in manifest.entries}
        for candidate in sorted(self._prompts_dir.glob("*.md")):
            if candidate.name not in listed_paths:
                raise PromptRegistryError(
                    f"R3 violation: orphan prompt file not listed in manifest: "
                    f"{candidate.name!r} (full path: {candidate}). "
                    f"Add an entry to {self._manifest_path} or remove the file."
                )

        # --- R1 + R2: verify each manifest entry ------------------------------
        for entry in manifest.entries:
            file_path = self._prompts_dir / entry.path

            # R1: file must exist.
            if not file_path.exists():
                raise PromptRegistryError(
                    f"R1 violation: manifest entry {entry.prompt_id!r} references "
                    f"file {entry.path!r} which does not exist on disk "
                    f"(resolved to {file_path})."
                )

            # R2: computed SHA-256 must match manifest sha256.
            file_bytes = file_path.read_bytes()
            computed = hashlib.sha256(file_bytes).hexdigest()
            if computed != entry.sha256:
                raise PromptRegistryError(
                    f"R2 violation: SHA-256 mismatch for prompt_id={entry.prompt_id!r}. "
                    f"Manifest has {entry.sha256!r}, computed {computed!r} "
                    f"from {file_path}. "
                    f"File may have been tampered with or the manifest entry is stale."
                )

            # Cache the text and hash.
            text = file_bytes.decode("utf-8")
            self._texts[entry.prompt_id] = text
            self._hashes[entry.prompt_id] = computed

            logger.info(
                "Resolved prompt: prompt_id=%r version=%d sha256=%s",
                entry.prompt_id,
                entry.version,
                computed,
            )

    def _verify_langfuse(self) -> None:
        """When KOSMOS_PROMPT_REGISTRY_LANGFUSE=true, lazily import langfuse and
        perform a two-source consistency check (FR-C09).

        Raises PromptRegistryError if:
        - the langfuse extras are absent (import fails),
        - Langfuse is unreachable or returns an unknown prompt_id, or
        - the hash returned by Langfuse disagrees with the repo hash.
        """
        # Lazy import — must NOT happen at module load time (FR-C08).
        try:
            import langfuse as _langfuse_mod  # type: ignore[import-untyped]  # noqa: PLC0415
        except (ImportError, TypeError) as exc:
            raise PromptRegistryError(
                "KOSMOS_PROMPT_REGISTRY_LANGFUSE=true but the langfuse package is "
                "not installed. Install it with: uv sync --extra langfuse"
            ) from exc

        host = os.environ.get("KOSMOS_LANGFUSE_HOST", "")
        public_key = os.environ.get("KOSMOS_LANGFUSE_PUBLIC_KEY", "")
        secret_key = os.environ.get("KOSMOS_LANGFUSE_SECRET_KEY", "")

        try:
            client = _langfuse_mod.Langfuse(
                public_key=public_key or None,
                secret_key=secret_key or None,
                host=host or None,
            )
        except Exception as exc:
            raise PromptRegistryError(f"Failed to initialise Langfuse client: {exc}") from exc

        for prompt_id, repo_hash in self._hashes.items():
            try:
                result = client.get_prompt(prompt_id, version=1)
            except Exception as exc:
                raise PromptRegistryError(
                    f"R-LF: Langfuse.get_prompt({prompt_id!r}) failed: {exc}. "
                    f"Failing closed — cannot verify cross-source hash for {prompt_id!r}."
                ) from exc

            lf_hash: str | None = getattr(result, "hash", None)
            if lf_hash is None:
                # Langfuse returned an object without a .hash attribute;
                # fall back to hashing the .prompt text if available.
                lf_text: str | None = getattr(result, "prompt", None)
                if lf_text is not None:
                    lf_hash = hashlib.sha256(lf_text.encode("utf-8")).hexdigest()

            if lf_hash != repo_hash:
                raise PromptRegistryError(
                    f"FR-C09 Langfuse hash mismatch for prompt_id={prompt_id!r}: "
                    f"repo sha256={repo_hash!r}, langfuse hash={lf_hash!r}. "
                    f"The two sources disagree — failing closed to prevent serving "
                    f"a mismatched prompt version."
                )

            logger.info(
                "Langfuse cross-source hash verified: prompt_id=%r sha256=%s",
                prompt_id,
                repo_hash,
            )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _cli_regenerate_manifest(prompts_dir: Path, manifest_path: Path) -> None:
    """Scan prompts_dir for *_v*.md files, compute SHA-256 for each, and write
    a valid manifest.yaml consumable by PromptLoader.

    The entry ``prompt_id`` is derived from the filename stem (e.g.
    ``system_v1.md`` → ``system_v1``).  The ``version`` integer is extracted
    from the ``_v{N}`` suffix.  The ``path`` field is relative to prompts_dir.
    """
    import re  # noqa: PLC0415

    entries = []
    for md_file in sorted(prompts_dir.glob("*_v*.md")):
        stem = md_file.stem  # e.g. "system_v1"
        match = re.search(r"_v([0-9]+)$", stem)
        if match is None:
            logger.warning("Skipping %s — no _v{N} suffix found", md_file.name)
            continue
        version = int(match.group(1))
        file_bytes = md_file.read_bytes()
        digest = hashlib.sha256(file_bytes).hexdigest()
        entries.append(
            {
                "prompt_id": stem,
                "version": version,
                "sha256": digest,
                "path": md_file.name,
            }
        )
        print(f"  {stem}: {digest}")  # noqa: T201 — CLI stdout output

    manifest_data = {"version": 1, "entries": entries}
    manifest_path.write_text(
        yaml.safe_dump(manifest_data, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )
    print(f"Manifest written to {manifest_path}")  # noqa: T201 — CLI stdout output


def _cli_emit_hashes(manifest_path: Path) -> None:
    """Emit a JSON object ``{prompt_id: sha256_hex}`` for every manifest entry.

    Output is consumed by ``tools.release_manifest.render`` via
    ``--prompt-hashes-file``, which requires a JSON ``dict[str, str]`` payload.
    """
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest = PromptManifest.model_validate(raw)
    payload = {entry.prompt_id: entry.sha256 for entry in manifest.entries}
    print(json.dumps(payload, indent=2, sort_keys=True))  # noqa: T201 — CLI stdout output


def main(argv: list[str] | None = None) -> None:
    """CLI entry point: python -m kosmos.context.prompt_loader [options]."""
    parser = argparse.ArgumentParser(
        prog="python -m kosmos.context.prompt_loader",
        description="KOSMOS Prompt Registry CLI utilities.",
    )
    parser.add_argument(
        "--regenerate-manifest",
        action="store_true",
        help="Scan prompts/ for *_v*.md files, compute SHA-256 for each, and "
        "write prompts/manifest.yaml.",
    )
    parser.add_argument(
        "--emit-hashes",
        action="store_true",
        help="Emit a JSON object '{prompt_id: sha256_hex}' on stdout for every "
        "entry in prompts/manifest.yaml (consumed by tools.release_manifest.render).",
    )
    parser.add_argument(
        "--prompts-dir",
        type=Path,
        default=Path("prompts"),
        help="Path to the prompts directory (default: ./prompts).",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Path to the manifest YAML file (default: <prompts-dir>/manifest.yaml).",
    )

    args = parser.parse_args(argv)

    prompts_dir: Path = args.prompts_dir
    manifest_path: Path = args.manifest or (prompts_dir / "manifest.yaml")

    if args.regenerate_manifest:
        _cli_regenerate_manifest(prompts_dir=prompts_dir, manifest_path=manifest_path)
    elif args.emit_hashes:
        _cli_emit_hashes(manifest_path=manifest_path)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
