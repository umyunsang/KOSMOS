# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/audit-env-registry.py — T-AR01 through T-AR07 (contract) + extras.

Test IDs T-AR01..T-AR07 mirror
`specs/026-secrets-infisical-oidc/contracts/audit-env-registry.md §Test matrix`
exactly. Additional cases (T-AR08, T-AR09) cover behaviour documented in the
contract body (§Allowlisted prefixes, §OverrideFamily suppression) but not
listed in the matrix — they are regression guards, not contract assertions.

Uses subprocess to invoke the script so it remains stdlib-only at runtime.
All fixtures are synthetic; no real credentials or secret values.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "audit-env-registry.py"

# Minimal valid registry table header + separator
_REGISTRY_HEADER = "| Variable | Required | Default | Range / Format | Consumed by | Source doc |"
_REGISTRY_SEP = "|----------|----------|---------|----------------|-------------|------------|"


def _make_registry(rows: list[str]) -> str:
    """Build a minimal valid registry Markdown string."""
    lines = [
        "# Configuration",
        "",
        _REGISTRY_HEADER,
        _REGISTRY_SEP,
    ]
    lines.extend(rows)
    lines.append("")
    return "\n".join(lines)


def _make_py_source(vars_: list[str]) -> str:
    """Build minimal Python source that references the given env var names."""
    lines = ["import os\n"]
    for v in vars_:
        lines.append(f'x_{v} = os.environ.get("{v}")\n')
    return "".join(lines)


def _run(repo_root: Path, registry_path: Path | None = None) -> tuple[int, dict]:
    """Run the audit script against a synthetic repo.  Returns (exit_code, report)."""
    cmd = [
        sys.executable,
        str(_SCRIPT),
        "--repo-root",
        str(repo_root),
    ]
    if registry_path is not None:
        cmd += ["--registry", str(registry_path)]

    result = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        report = {}
    return result.returncode, report


def _write_src_py(repo_root: Path, content: str, name: str = "module.py") -> None:
    src = repo_root / "src" / "kosmos"
    src.mkdir(parents=True, exist_ok=True)
    (src / name).write_text(content, encoding="utf-8")


def _write_registry(repo_root: Path, rows: list[str]) -> Path:
    docs = repo_root / "docs"
    docs.mkdir(exist_ok=True)
    reg = docs / "configuration.md"
    reg.write_text(_make_registry(rows), encoding="utf-8")
    return reg


# ---------------------------------------------------------------------------
# T-AR01 (contract): Clean state — every code var in registry → exit 0, verdict clean
# ---------------------------------------------------------------------------


def test_ar01_clean_state(tmp_path: Path) -> None:
    """T-AR01: 1:1 code↔registry match → exit 0, verdict=clean."""
    _write_src_py(
        tmp_path,
        _make_py_source(["KOSMOS_SYNTHETIC_FOO", "KOSMOS_SYNTHETIC_BAR"]),
    )
    _write_registry(
        tmp_path,
        [
            "| `KOSMOS_SYNTHETIC_FOO` | yes (all envs) | — | string | `kosmos.test` | — |",
            "| `KOSMOS_SYNTHETIC_BAR` | yes (all envs) | — | string | `kosmos.test` | — |",
        ],
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 0, f"Expected exit 0, got {exit_code}. Report: {report}"
    assert report.get("verdict") == "clean", f"Expected clean, got: {report.get('verdict')}"
    findings = report.get("findings", {})
    assert findings.get("in_code_not_in_registry") == []
    assert findings.get("in_registry_not_in_code") == []
    assert findings.get("prefix_violations") == []
    assert findings.get("override_family_unmatched") == []


# ---------------------------------------------------------------------------
# T-AR02 (contract): Code var not in registry → exit 1, in_code_not_in_registry
# ---------------------------------------------------------------------------


def test_ar02_code_var_not_in_registry(tmp_path: Path) -> None:
    """T-AR02: KOSMOS_SYNTHETIC_NEW in code but not in registry → exit 1."""
    _write_src_py(
        tmp_path,
        _make_py_source(["KOSMOS_SYNTHETIC_KNOWN", "KOSMOS_SYNTHETIC_NEW"]),
    )
    _write_registry(
        tmp_path,
        [
            "| `KOSMOS_SYNTHETIC_KNOWN` | yes (all envs) | — | string | `kosmos.test` | — |",
        ],
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 1, f"Expected exit 1, got {exit_code}"
    assert report.get("verdict") == "drift"
    missing = [f["name"] for f in report["findings"]["in_code_not_in_registry"]]
    assert "KOSMOS_SYNTHETIC_NEW" in missing, f"Missing not flagged: {missing}"


# ---------------------------------------------------------------------------
# T-AR03 (contract): Registry var not in code → exit 1, in_registry_not_in_code
# ---------------------------------------------------------------------------


def test_ar03_registry_var_not_in_code(tmp_path: Path) -> None:
    """T-AR03: KOSMOS_SYNTHETIC_STALE in registry but not in code → exit 1."""
    _write_src_py(
        tmp_path,
        _make_py_source(["KOSMOS_SYNTHETIC_ACTIVE"]),
    )
    _write_registry(
        tmp_path,
        [
            "| `KOSMOS_SYNTHETIC_ACTIVE` | yes (all envs) | — | string | `kosmos.test` | — |",
            "| `KOSMOS_SYNTHETIC_STALE` | yes (all envs) | — | string | `kosmos.test` | — |",
        ],
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 1, f"Expected exit 1, got {exit_code}"
    assert report.get("verdict") == "drift"
    stale = [f["name"] for f in report["findings"]["in_registry_not_in_code"]]
    assert "KOSMOS_SYNTHETIC_STALE" in stale, f"Stale not flagged: {stale}"


# ---------------------------------------------------------------------------
# T-AR04 (contract): Malformed registry (missing header) → exit 2
# ---------------------------------------------------------------------------


def test_ar04_malformed_registry_missing_header(tmp_path: Path) -> None:
    """T-AR04: Registry with no `| Variable | Required |` header → exit 2."""
    _write_src_py(tmp_path, _make_py_source(["KOSMOS_SYNTHETIC_OK"]))

    # Write a registry file that has no recognisable header.
    docs = tmp_path / "docs"
    docs.mkdir(exist_ok=True)
    reg = docs / "configuration.md"
    reg.write_text(
        textwrap.dedent("""\
            # Configuration

            This registry is intentionally malformed — no table header.
            Random prose goes here with no `|` table markers.
        """),
        encoding="utf-8",
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 2, f"Expected exit 2 (malformed), got {exit_code}. Report: {report}"
    assert report.get("verdict") == "malformed", f"Expected malformed, got: {report.get('verdict')}"


# ---------------------------------------------------------------------------
# T-AR05 (contract): LANGFUSE_ in code + in registry → exit 0 (allowlisted prefix)
# ---------------------------------------------------------------------------


def test_ar05_langfuse_allowlist_clean(tmp_path: Path) -> None:
    """T-AR05: LANGFUSE_PUBLIC_KEY in code + registry → exit 0 (allowlist)."""
    _write_src_py(
        tmp_path,
        _make_py_source(["KOSMOS_SYNTHETIC_BASE", "LANGFUSE_PUBLIC_KEY"]),
    )
    _write_registry(
        tmp_path,
        [
            "| `KOSMOS_SYNTHETIC_BASE` | yes (all envs) | — | string | `kosmos.test` | — |",
            "| `LANGFUSE_PUBLIC_KEY` | yes (prod only) | — | string "
            "| `kosmos.observability.langfuse` | — |",
        ],
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 0, (
        f"Expected exit 0 (LANGFUSE_ allowlisted), got {exit_code}. "
        f"Findings: {report.get('findings')}"
    )
    assert report.get("verdict") == "clean"
    # LANGFUSE_ must NOT trigger a prefix_violation (it's in the allowlist).
    violations = [f["name"] for f in report["findings"]["prefix_violations"]]
    assert "LANGFUSE_PUBLIC_KEY" not in violations, (
        f"LANGFUSE_PUBLIC_KEY wrongly flagged as prefix violation: {violations}"
    )


# ---------------------------------------------------------------------------
# T-AR06 (contract): Override-family member + pattern row in registry → clean
# ---------------------------------------------------------------------------


def test_ar06_override_family_clean(tmp_path: Path) -> None:
    """T-AR06: KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY in code + family row → exit 0."""
    _write_src_py(
        tmp_path,
        _make_py_source(["KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY", "KOSMOS_SYNTHETIC_BASE"]),
    )
    _write_registry(
        tmp_path,
        [
            "| `KOSMOS_SYNTHETIC_BASE` | yes (all envs) | — | string | `kosmos.test` | — |",
            "| `KOSMOS_{TOOL_ID}_API_KEY` | conditional (see note) | — | string "
            "| `kosmos.permissions.credentials` | — |",
        ],
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 0, (
        f"Expected exit 0 (family suppressed), got {exit_code}. Findings: {report.get('findings')}"
    )
    assert report.get("verdict") == "clean"
    assert report["findings"]["override_family_unmatched"] == []


# ---------------------------------------------------------------------------
# T-AR07 (contract): Performance — >1000 synthetic Python files, duration < 10 s
# ---------------------------------------------------------------------------


def test_ar07_performance(tmp_path: Path) -> None:
    """T-AR07: >1000 code files scanned within 10 s wall-clock (NFR-006)."""
    src_dir = tmp_path / "src" / "kosmos" / "generated"
    src_dir.mkdir(parents=True)

    # Generate 1100 Python files each referencing one known var.
    var_name = "KOSMOS_SYNTHETIC_PERF"
    content = _make_py_source([var_name])
    for i in range(1100):
        (src_dir / f"module_{i:04d}.py").write_text(content, encoding="utf-8")

    _write_registry(
        tmp_path,
        [
            f"| `{var_name}` | yes (all envs) | — | string | `kosmos.test` | — |",
        ],
    )

    exit_code, report = _run(tmp_path)

    # Clean or drift both acceptable here — we only care about timing.
    duration = report.get("scan_stats", {}).get("duration_seconds", 9999)
    assert duration < 10.0, f"Performance budget exceeded: {duration:.3f}s >= 10s"
    # Should be clean since all vars are registered.
    assert exit_code == 0, (
        f"Expected clean run in perf test, got exit {exit_code}. Findings: {report.get('findings')}"
    )


# ---------------------------------------------------------------------------
# T-AR08 (beyond contract): Prefix violation — non-KOSMOS_/non-LANGFUSE_ in .env.example
#
# Contract matrix does not list this as a numbered test, but §Allowlisted
# prefixes mandates `prefix_violations` reporting. This is a regression guard.
# ---------------------------------------------------------------------------


def test_ar08_prefix_violation(tmp_path: Path) -> None:
    """T-AR08: NON_KOSMOS_VAR in .env.example → exit 1, prefix_violations."""
    # Populate registry with one known var so the code scan won't drift.
    _write_src_py(tmp_path, _make_py_source(["KOSMOS_SYNTHETIC_OK"]))
    _write_registry(
        tmp_path,
        [
            "| `KOSMOS_SYNTHETIC_OK` | yes (all envs) | — | string | `kosmos.test` | — |",
        ],
    )

    # Write .env.example with a non-KOSMOS_, non-LANGFUSE_ assignment.
    env_example = tmp_path / ".env.example"
    env_example.write_text(
        textwrap.dedent("""\
            # Example env
            KOSMOS_SYNTHETIC_OK=
            MY_TOTALLY_DIFFERENT_VAR=secret
        """),
        encoding="utf-8",
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 1, f"Expected exit 1, got {exit_code}"
    violations = [f["name"] for f in report["findings"]["prefix_violations"]]
    assert "MY_TOTALLY_DIFFERENT_VAR" in violations, f"Violation not flagged: {violations}"


# ---------------------------------------------------------------------------
# T-AR09 (beyond contract): Override-family member WITHOUT pattern row →
#                           override_family_unmatched
#
# Contract §OverrideFamily suppression mandates this behaviour; matrix does
# not assign it a numbered test. Regression guard for the negative path.
# ---------------------------------------------------------------------------


def test_ar09_override_family_unmatched(tmp_path: Path) -> None:
    """T-AR09: KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY in code, NO family row → exit 1."""
    _write_src_py(
        tmp_path,
        _make_py_source(["KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY", "KOSMOS_SYNTHETIC_BASE"]),
    )
    # Registry has no family row.
    _write_registry(
        tmp_path,
        [
            "| `KOSMOS_SYNTHETIC_BASE` | yes (all envs) | — | string | `kosmos.test` | — |",
        ],
    )

    exit_code, report = _run(tmp_path)

    assert exit_code == 1, f"Expected exit 1, got {exit_code}"
    unmatched = [f["name"] for f in report["findings"]["override_family_unmatched"]]
    assert "KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY" in unmatched, (
        f"Expected override_family_unmatched entry; got: {unmatched}"
    )
