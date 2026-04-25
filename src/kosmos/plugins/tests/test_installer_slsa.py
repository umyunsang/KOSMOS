# SPDX-License-Identifier: Apache-2.0
"""Tests for ``kosmos.plugins.slsa.verify_artifact``.

The wrapper shells out to ``slsa-verifier``; tests use a tiny shell-script
stub on disk so we exercise the real :mod:`subprocess` plumbing — argv
list construction, exit-code parsing, stderr classification, timeout
handling — without depending on the actual binary being vendored. The
contract's three failure modes (R-3) are each covered with a stub that
prints the exact phrase :func:`_classify_failure` matches against.
"""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from kosmos.plugins.slsa import (
    SLSAFailureKind,
    SLSAVerificationResult,
    default_verifier_path,
    verify_artifact,
)


def _make_stub_verifier(
    tmp_path: Path,
    *,
    exit_code: int,
    stderr: str = "",
    stdout: str = "",
    sleep_sec: float = 0.0,
) -> Path:
    """Build an executable shell stub that mimics slsa-verifier output.

    The stub ignores its argv beyond returning the requested exit code so
    each test can assert behaviour for one outcome at a time.
    """
    stub = tmp_path / "slsa-verifier-stub"
    body_lines = ["#!/bin/sh"]
    if sleep_sec:
        body_lines.append(f"sleep {sleep_sec}")
    if stdout:
        body_lines.append(f"printf %s {stdout!r}")
    if stderr:
        body_lines.append(f"printf %s {stderr!r} 1>&2")
    body_lines.append(f"exit {exit_code}")
    stub.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return stub


@pytest.fixture
def bundle_files(tmp_path: Path) -> tuple[Path, Path]:
    """Empty placeholder bundle + provenance files; the stub does not read them."""
    bundle = tmp_path / "demo.tar.gz"
    provenance = tmp_path / "demo.intoto.jsonl"
    bundle.write_bytes(b"")
    provenance.write_bytes(b"")
    return bundle, provenance


class TestVerifyArtifactSuccess:
    def test_exit_zero_passes(self, tmp_path: Path, bundle_files: tuple[Path, Path]) -> None:
        bundle, provenance = bundle_files
        stub = _make_stub_verifier(tmp_path, exit_code=0)

        result = verify_artifact(
            bundle_path=bundle,
            provenance_path=provenance,
            source_uri="github.com/kosmos-plugin-store/kosmos-plugin-demo",
            verifier_path=stub,
        )
        assert isinstance(result, SLSAVerificationResult)
        assert result.passed is True
        assert result.failure_kind is None
        assert result.exit_code == 0


class TestVerifyArtifactFailureModes:
    def test_provenance_not_signed_classified(
        self, tmp_path: Path, bundle_files: tuple[Path, Path]
    ) -> None:
        bundle, provenance = bundle_files
        stub = _make_stub_verifier(
            tmp_path,
            exit_code=1,
            stderr="FAILED: provenance not signed by GitHub Actions OIDC issuer.",
        )

        result = verify_artifact(
            bundle_path=bundle,
            provenance_path=provenance,
            source_uri="github.com/kosmos-plugin-store/kosmos-plugin-demo",
            verifier_path=stub,
        )
        assert result.passed is False
        assert result.failure_kind is SLSAFailureKind.PROVENANCE_NOT_SIGNED
        assert "not signed" in result.stderr_tail.lower()
        assert result.exit_code == 1

    def test_source_uri_mismatch_classified(
        self, tmp_path: Path, bundle_files: tuple[Path, Path]
    ) -> None:
        bundle, provenance = bundle_files
        stub = _make_stub_verifier(
            tmp_path,
            exit_code=1,
            stderr=("FAILED: source URI mismatch: expected github.com/x/y, got github.com/x/z"),
        )

        result = verify_artifact(
            bundle_path=bundle,
            provenance_path=provenance,
            source_uri="github.com/x/y",
            verifier_path=stub,
        )
        assert result.passed is False
        assert result.failure_kind is SLSAFailureKind.SOURCE_URI_MISMATCH
        assert result.exit_code == 1

    def test_unknown_failure_falls_back(
        self, tmp_path: Path, bundle_files: tuple[Path, Path]
    ) -> None:
        bundle, provenance = bundle_files
        stub = _make_stub_verifier(
            tmp_path,
            exit_code=2,
            stderr="some unmapped error message",
        )

        result = verify_artifact(
            bundle_path=bundle,
            provenance_path=provenance,
            source_uri="github.com/x/y",
            verifier_path=stub,
        )
        assert result.passed is False
        assert result.failure_kind is SLSAFailureKind.UNKNOWN
        assert result.exit_code == 2

    def test_timeout_classified(self, tmp_path: Path, bundle_files: tuple[Path, Path]) -> None:
        bundle, provenance = bundle_files
        stub = _make_stub_verifier(tmp_path, exit_code=0, sleep_sec=0.4)

        result = verify_artifact(
            bundle_path=bundle,
            provenance_path=provenance,
            source_uri="github.com/x/y",
            verifier_path=stub,
            timeout_sec=0.05,
        )
        assert result.passed is False
        assert result.failure_kind is SLSAFailureKind.TIMEOUT


class TestVerifyArtifactBinaryDiscovery:
    def test_missing_binary_yields_binary_not_found(
        self, tmp_path: Path, bundle_files: tuple[Path, Path]
    ) -> None:
        bundle, provenance = bundle_files
        missing = tmp_path / "does-not-exist"

        result = verify_artifact(
            bundle_path=bundle,
            provenance_path=provenance,
            source_uri="github.com/x/y",
            verifier_path=missing,
        )
        assert result.passed is False
        assert result.failure_kind is SLSAFailureKind.BINARY_NOT_FOUND
        assert "bootstrap_slsa_verifier" in result.stderr_tail

    def test_default_path_resolves_under_vendor_root(self) -> None:
        path = default_verifier_path()
        # Last two segments are the platform-dir + binary name; full path
        # depends on the host (KOSMOS_PLUGIN_VENDOR_ROOT may be overridden
        # in the developer environment).
        assert path.name == "slsa-verifier"
        assert path.parent.parent.name == "slsa-verifier"


class TestVerifyArtifactArgvShape:
    def test_argv_includes_required_flags(
        self,
        tmp_path: Path,
        bundle_files: tuple[Path, Path],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The contract pins three argv flags. Capture argv via a shell stub."""
        bundle, provenance = bundle_files
        # Stub writes its argv to a sibling file then exits 0.
        argv_log = tmp_path / "argv.log"
        stub_body = f'#!/bin/sh\nprintf "%s\\n" "$@" > {argv_log}\nexit 0\n'
        stub = tmp_path / "stub"
        stub.write_text(stub_body, encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)

        result = verify_artifact(
            bundle_path=bundle,
            provenance_path=provenance,
            source_uri="github.com/kosmos-plugin-store/kosmos-plugin-demo",
            verifier_path=stub,
        )
        assert result.passed is True
        argv = argv_log.read_text(encoding="utf-8").splitlines()
        assert argv[0] == "verify-artifact"
        assert "--provenance-path" in argv
        assert "--source-uri" in argv
        assert str(bundle) in argv
        assert "github.com/kosmos-plugin-store/kosmos-plugin-demo" in argv
