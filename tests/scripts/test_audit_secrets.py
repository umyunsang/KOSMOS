# SPDX-License-Identifier: Apache-2.0
"""
Pytest harness for scripts/audit-secrets.sh.

Tests T-AS01..T-AS08 per contracts/audit-secrets.md §Test matrix.
Fixtures build synthetic .github/workflows/ci.yml under tmp_path so the real
workflow is never touched.  No token values — only <redacted> placeholders and
synthetic test strings.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "audit-secrets.sh"


def _run(repo_root: Path) -> subprocess.CompletedProcess[str]:
    """Run audit-secrets.sh pointing at the synthetic repo root."""
    return subprocess.run(
        [str(SCRIPT), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
    )


def _write_workflow(repo_root: Path, content: str) -> None:
    """Create .github/workflows/ci.yml inside tmp repo root."""
    wf_dir = repo_root / ".github" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "ci.yml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# T-AS01: clean workflow containing only ${{ secrets.GITHUB_TOKEN }} → exit 0
# ---------------------------------------------------------------------------
def test_as01_github_token_only_is_clean(tmp_path: Path) -> None:
    """T-AS01: GITHUB_TOKEN alone is allowlisted; no violation."""
    _write_workflow(
        tmp_path,
        "token: ${{ secrets.GITHUB_TOKEN }}\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert result.stderr.strip().endswith("clean — no forbidden patterns found.")


# ---------------------------------------------------------------------------
# T-AS02: ${{ secrets.FRIENDLI_TOKEN }} → exit 1, violation reported
# ---------------------------------------------------------------------------
def test_as02_friendli_token_is_forbidden(tmp_path: Path) -> None:
    """T-AS02: FRIENDLI_TOKEN matches DENY-TOKEN and DENY-FRIENDLI; exit 1."""
    _write_workflow(
        tmp_path,
        "env:\n  KOSMOS_FRIENDLI_TOKEN: ${{ secrets.FRIENDLI_TOKEN }}\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 1, f"stderr: {result.stderr}"
    assert "FORBIDDEN" in result.stderr
    # Summary line must be present
    assert "violation(s) found" in result.stderr


# ---------------------------------------------------------------------------
# T-AS03: ${{ secrets.KOSMOS_KAKAO_API_KEY }} → exit 1
# ---------------------------------------------------------------------------
def test_as03_kosmos_api_key_is_forbidden(tmp_path: Path) -> None:
    """T-AS03: Any KOSMOS_* secret reference triggers DENY-KOSMOS; exit 1."""
    _write_workflow(
        tmp_path,
        "env:\n  KEY: ${{ secrets.KOSMOS_KAKAO_API_KEY }}\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 1, f"stderr: {result.stderr}"
    assert "FORBIDDEN" in result.stderr


# ---------------------------------------------------------------------------
# T-AS04: YAML comment containing secrets.FOO_TOKEN → exit 0
# ---------------------------------------------------------------------------
def test_as04_comment_line_suppressed(tmp_path: Path) -> None:
    """T-AS04: Lines starting with # are suppressed; comment does not trigger."""
    _write_workflow(
        tmp_path,
        "# rotate this token: ${{ secrets.KOSMOS_FRIENDLI_TOKEN }} quarterly\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"


# ---------------------------------------------------------------------------
# T-AS05: uses: some/action@v1-token-helper → exit 0
# ---------------------------------------------------------------------------
def test_as05_uses_line_suppressed(tmp_path: Path) -> None:
    """T-AS05: Lines beginning with 'uses:' are suppressed."""
    _write_workflow(
        tmp_path,
        "      uses: some/action@v1-token-helper\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"


# ---------------------------------------------------------------------------
# T-AS06: .github/workflows/ directory missing → exit 2
# ---------------------------------------------------------------------------
def test_as06_missing_workflow_dir_exits_2(tmp_path: Path) -> None:
    """T-AS06: Scanned file absent → scan error, exit 2."""
    # Deliberately do NOT create .github/workflows/ci.yml
    result = _run(tmp_path)
    assert result.returncode == 2, f"stderr: {result.stderr}"
    assert "ERROR" in result.stderr


# ---------------------------------------------------------------------------
# T-AS07: ${{ vars.INFISICAL_CLIENT_ID }} → exit 0 (not a secrets.* reference)
# ---------------------------------------------------------------------------
def test_as07_vars_reference_is_clean(tmp_path: Path) -> None:
    """T-AS07: vars.* references are not secrets; no violation."""
    _write_workflow(
        tmp_path,
        "env:\n  CLIENT_ID: ${{ vars.INFISICAL_CLIENT_ID }}\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 0, f"stderr: {result.stderr}"


# ---------------------------------------------------------------------------
# T-AS08: ${{ secrets.INFISICAL_CLIENT_SECRET }} → exit 1
# ---------------------------------------------------------------------------
def test_as08_infisical_client_secret_is_forbidden(tmp_path: Path) -> None:
    """T-AS08: INFISICAL_CLIENT_SECRET matches DENY-SECRET; exit 1."""
    _write_workflow(
        tmp_path,
        "env:\n  SECRET: ${{ secrets.INFISICAL_CLIENT_SECRET }}\n",
    )
    result = _run(tmp_path)
    assert result.returncode == 1, f"stderr: {result.stderr}"
    assert "FORBIDDEN" in result.stderr
