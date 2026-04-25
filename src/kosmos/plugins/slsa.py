# SPDX-License-Identifier: Apache-2.0
"""SLSA provenance verification wrapper around the vendored ``slsa-verifier`` binary.

Plugin install (per ``contracts/plugin-install.cli.md`` Phase 3) shells
out to ``slsa-verifier verify-artifact`` to confirm the bundle's
SLSA v1.0 provenance was signed by the same GitHub-Actions workflow
named in ``manifest.slsa_provenance_url``. This module owns:

* The exact ``subprocess`` invocation (no shell, list-form argv,
  bounded timeout, captured output).
* Mapping the binary's exit code + stderr to a closed enum of
  :class:`SLSAFailureKind` values so the installer surfaces the
  correct exit code and citizen-facing error message
  (per the contract's "SLSA verification — failure modes (R-3)" table).
* The vendored-binary discovery rule: ``--vendor-slsa-from <path>``
  override → ``KOSMOS_PLUGIN_VENDOR_ROOT/slsa-verifier/<platform>/slsa-verifier``
  default. Missing binary maps to a distinct ``binary_not_found`` kind so
  the caller can shell out to ``scripts/bootstrap_slsa_verifier.sh``.

The module never raises out of the verification path — failures are
returned as :class:`SLSAVerificationResult` records so the installer
can surface them through the IPC envelope without exception plumbing.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from kosmos.settings import settings

logger = logging.getLogger(__name__)


_DEFAULT_TIMEOUT_SEC = 60.0
"""Bounded timeout for the slsa-verifier subprocess (per contract)."""

_PLATFORM_DIR_OVERRIDES: dict[str, str] = {
    # Map (Python sys.platform style ‑‑ already returned by platform.system())
    # to the slsa-verifier release naming convention. The matrix below covers
    # the four platforms vendored per T063: darwin-amd64 / darwin-arm64 /
    # linux-amd64 / linux-arm64.
    "Darwin": "darwin",
    "Linux": "linux",
}


class SLSAFailureKind(StrEnum):
    """Closed enum of SLSA verification failure subtypes.

    Mirrors the contract's "SLSA verification — failure modes" table and
    the installer's exit-code mapping: kinds prefixed ``provenance_*`` and
    ``source_uri_*`` map to exit 3 (provenance reject); ``binary_not_found``
    maps to exit 7 (backend prerequisite missing); ``timeout`` and
    ``unknown`` are catch-alls also routed to exit 3.
    """

    PROVENANCE_NOT_SIGNED = "provenance_not_signed"
    """slsa-verifier reports the provenance is not OIDC-signed by GH Actions."""

    SOURCE_URI_MISMATCH = "source_uri_mismatch"
    """slsa-verifier rejects the source-uri claim."""

    BINARY_NOT_FOUND = "binary_not_found"
    """Vendored slsa-verifier binary missing for this platform."""

    TIMEOUT = "timeout"
    """slsa-verifier exceeded :data:`_DEFAULT_TIMEOUT_SEC`."""

    UNKNOWN = "unknown"
    """Any other non-zero exit (kept open so new release tags don't break us)."""


@dataclass(frozen=True, slots=True)
class SLSAVerificationResult:
    """Outcome record returned from :func:`verify_artifact`.

    ``passed=True`` ⇔ exit code 0; otherwise exactly one of
    :class:`SLSAFailureKind` is set in :attr:`failure_kind`. ``stderr_tail``
    is the last ~2 KB of the verifier's stderr, retained verbatim so the
    citizen-facing error overlay can show the upstream message without
    re-running the subprocess.
    """

    passed: bool
    failure_kind: SLSAFailureKind | None
    stderr_tail: str
    exit_code: int


def _detect_platform_dir() -> str:
    system = platform.system()
    machine = platform.machine().lower()

    base = _PLATFORM_DIR_OVERRIDES.get(system)
    if base is None:
        # Fall through to a literal — ``binary_not_found`` will route the
        # missing-binary failure cleanly from the call site.
        base = system.lower()

    # slsa-verifier release naming: amd64 / arm64.
    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"arm64", "aarch64"}:
        arch = "arm64"
    else:
        arch = machine

    return f"{base}-{arch}"


def default_verifier_path() -> Path:
    """Return the configured-default path to the vendored slsa-verifier binary."""
    return settings.plugin_vendor_root / "slsa-verifier" / _detect_platform_dir() / "slsa-verifier"


def _classify_failure(stderr: str, exit_code: int) -> SLSAFailureKind:
    """Map an slsa-verifier failure to a :class:`SLSAFailureKind`.

    Heuristic: slsa-verifier writes well-known phrases to stderr for the two
    failure modes the contract calls out by name. Anything else falls back to
    :attr:`SLSAFailureKind.UNKNOWN` so the caller still surfaces exit 3
    rather than crashing on an unmapped substring.
    """
    haystack = stderr.lower()
    if "not signed by" in haystack or "no matching signatures" in haystack:
        return SLSAFailureKind.PROVENANCE_NOT_SIGNED
    if "source uri" in haystack and "mismatch" in haystack:
        return SLSAFailureKind.SOURCE_URI_MISMATCH
    return SLSAFailureKind.UNKNOWN


def _tail(text: str, *, max_bytes: int = 2048) -> str:
    if len(text) <= max_bytes:
        return text
    return "…" + text[-max_bytes:]


def verify_artifact(
    *,
    bundle_path: Path,
    provenance_path: Path,
    source_uri: str,
    verifier_path: Path | None = None,
    timeout_sec: float = _DEFAULT_TIMEOUT_SEC,
) -> SLSAVerificationResult:
    """Verify a plugin bundle's SLSA v1.0 provenance.

    Equivalent to::

        slsa-verifier verify-artifact \\
            --provenance-path <provenance_path> \\
            --source-uri <source_uri> \\
            <bundle_path>

    Args:
        bundle_path: Path to the downloaded plugin bundle (.tar.gz).
        provenance_path: Path to the .intoto.jsonl provenance attestation.
        source_uri: Expected source URI claim
            (e.g. ``github.com/kosmos-plugin-store/kosmos-plugin-<name>``).
        verifier_path: Override the slsa-verifier binary location. Defaults
            to :func:`default_verifier_path`.
        timeout_sec: Subprocess timeout. Defaults to 60s per contract.

    Returns:
        A frozen :class:`SLSAVerificationResult` describing the outcome.
        ``passed=True`` means the upstream binary exited 0; any other path
        sets ``failure_kind`` to a :class:`SLSAFailureKind` value.
    """
    binary = verifier_path or default_verifier_path()
    if not binary.is_file():
        logger.warning(
            "slsa-verifier binary missing at %s — install will report binary_not_found",
            binary,
        )
        return SLSAVerificationResult(
            passed=False,
            failure_kind=SLSAFailureKind.BINARY_NOT_FOUND,
            stderr_tail=(
                f"slsa-verifier binary not found at {binary}. "
                "Run scripts/bootstrap_slsa_verifier.sh to vendor the "
                "platform-specific binary into KOSMOS_PLUGIN_VENDOR_ROOT."
            ),
            exit_code=-1,
        )

    cmd = [
        str(binary),
        "verify-artifact",
        "--provenance-path",
        str(provenance_path),
        "--source-uri",
        source_uri,
        str(bundle_path),
    ]

    try:
        completed = subprocess.run(  # noqa: S603 — argv list, no shell.
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("slsa-verifier timeout after %ss for %s", timeout_sec, bundle_path)
        return SLSAVerificationResult(
            passed=False,
            failure_kind=SLSAFailureKind.TIMEOUT,
            stderr_tail=_tail(
                exc.stderr.decode("utf-8", errors="replace")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            ),
            exit_code=-1,
        )

    if completed.returncode == 0:
        return SLSAVerificationResult(
            passed=True,
            failure_kind=None,
            stderr_tail=_tail(completed.stderr),
            exit_code=0,
        )

    failure = _classify_failure(completed.stderr, completed.returncode)
    logger.warning(
        "slsa-verifier exit=%s failure_kind=%s for %s",
        completed.returncode,
        failure,
        bundle_path,
    )
    return SLSAVerificationResult(
        passed=False,
        failure_kind=failure,
        stderr_tail=_tail(completed.stderr),
        exit_code=completed.returncode,
    )


__all__ = [
    "SLSAFailureKind",
    "SLSAVerificationResult",
    "default_verifier_path",
    "verify_artifact",
]
