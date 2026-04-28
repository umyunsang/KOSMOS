#!/usr/bin/env python3
"""
T005 — R4 modified-file classification.

Classifies every entry in `data/enumerated-modified.txt` into exactly one of
{Legitimate, Cleanup-needed, Suspicious} using three signals defined in
`research.md § R-4`:

  (a) directory pattern  — known KOSMOS infra dirs vs known Spec 1633 residue
                           paths
  (b) git history        — `git log` first / last commits of the file
                           grep'd for KOSMOS spec ids (`feat/NNNN-...`)
  (c) import scan        — body grep for known residue tokens
                           (`@anthropic-ai/`, `claude.ts`,
                            `verifyApiKey`, etc.)

Decision matrix (first match wins):

  - Both (a) Legitimate dir AND (c) no residue token  → Legitimate
  - (a) Cleanup-needed dir OR (c) any residue token   → Cleanup-needed
  - (b) git log mentions known spec id + (c) clean    → Legitimate
  - else                                              → Suspicious

The script writes:
  - data/modified-218-classification.json   (one AuditEntry per row of
                                              enumerated-modified.txt)

Read-only outside specs/2292-cc-parity-audit/.
Stdlib only (json, pathlib, subprocess, re, sys).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
AUDIT_DIR: Final = REPO_ROOT / "specs" / "2292-cc-parity-audit"
DATA_DIR: Final = AUDIT_DIR / "data"
ENUM_MODIFIED: Final = DATA_DIR / "enumerated-modified.txt"
OUT_JSON: Final = DATA_DIR / "modified-218-classification.json"
CC_SRC_REL: Final = ".references/claude-code-sourcemap/restored-src/src"

# (a) Directory patterns ---------------------------------------------------
LEGITIMATE_DIR_PREFIXES: Final = (
    "tui/src/i18n/",
    "tui/src/ipc/",
    "tui/src/observability/",
    "tui/src/ssh/",
    "tui/src/theme/",
    "tui/src/bridge/",
)
CLEANUP_DIR_PREFIXES: Final = (
    "tui/src/services/api/",          # Spec 1633 closure pending (claude.ts etc.)
    "tui/src/utils/permissions/",     # Spec 033 KOSMOS-invented residue
    "tui/src/commands/permissions/",  # ditto
)

# (c) Import / body residue tokens ----------------------------------------
RESIDUE_TOKENS: Final = (
    "@anthropic-ai/",
    "anthropic-sdk",
    "verifyApiKey",
    "queryHaiku",
    "queryWithModel",
    "PermissionDecisionT",
    "PermissionLayerT",
    "pipa_class",
    "auth_level",
    "permission_tier",
    "is_personal_data",
    "is_irreversible",
    "requires_auth",
    "dpa_reference",
    "5-mode spectrum",
)

# KOSMOS-specific tokens that strongly imply legitimate change
KOSMOS_TOKENS: Final = (
    "KOSMOS",
    "kosmos",
    "@kosmos/",
    "EXAONE",
    "FriendliAI",
    "friendli",
    "한국어",
    "i18n",
    "ko_KR",
)

SPEC_ID_RE: Final = re.compile(r"\b(?:feat|fix|docs|chore|refactor)[\(/]?\s*(\d{3,4})\b")


def run(cmd: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
        check=False,
    )
    return proc.stdout


def collect_signals(kosmos_path: str) -> dict:
    """Compute the 3 signals for one file."""
    abs_path = REPO_ROOT / kosmos_path
    cc_path = REPO_ROOT / CC_SRC_REL / kosmos_path[len("tui/src/"):]
    sig = {
        "directory_match": None,
        "git_history_match": None,
        "import_scan_match": None,
    }

    # (a) directory match
    for pref in LEGITIMATE_DIR_PREFIXES:
        if kosmos_path.startswith(pref):
            sig["directory_match"] = f"legitimate:{pref}"
            break
    if sig["directory_match"] is None:
        for pref in CLEANUP_DIR_PREFIXES:
            if kosmos_path.startswith(pref):
                sig["directory_match"] = f"cleanup:{pref}"
                break

    # (b) git history — extract spec id mentions from last 5 commits.
    log_out = run(
        [
            "git",
            "log",
            "-n",
            "5",
            "--pretty=%s",
            "--",
            kosmos_path,
        ],
        cwd=REPO_ROOT,
    )
    spec_ids = set()
    for line in log_out.splitlines():
        for match in SPEC_ID_RE.finditer(line):
            spec_ids.add(match.group(1))
    if spec_ids:
        sig["git_history_match"] = "spec:" + ",".join(sorted(spec_ids))

    # (c) import / body residue scan
    body = ""
    if abs_path.exists():
        try:
            body = abs_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = ""
    residue_hits = [tok for tok in RESIDUE_TOKENS if tok in body]
    kosmos_hits = [tok for tok in KOSMOS_TOKENS if tok in body]
    if residue_hits:
        sig["import_scan_match"] = "residue:" + "|".join(residue_hits[:3])
    elif kosmos_hits:
        sig["import_scan_match"] = "kosmos:" + "|".join(kosmos_hits[:3])

    sig["_residue_hits"] = residue_hits
    sig["_kosmos_hits"] = kosmos_hits
    sig["_spec_ids"] = sorted(spec_ids)
    return sig


def classify(sig: dict) -> tuple[str, str, str]:
    """Return (classification, change_summary, reference_citation)."""
    dir_match = sig.get("directory_match") or ""
    residue_hits = sig.get("_residue_hits") or []
    kosmos_hits = sig.get("_kosmos_hits") or []
    spec_ids = sig.get("_spec_ids") or []

    # Decision tree (first hit wins).
    if dir_match.startswith("cleanup:") or residue_hits:
        if residue_hits:
            summary = f"Anthropic / Spec 033 잔재 토큰 감지: {', '.join(residue_hits[:3])}"
            ref = "Spec 1633 closure pending"
        else:
            summary = f"Spec 1633 cleanup 디렉토리: {dir_match.split(':', 1)[1]}"
            ref = "Spec 1633 closure pending"
        return "Cleanup-needed", summary, ref

    if dir_match.startswith("legitimate:"):
        prefix = dir_match.split(":", 1)[1]
        summary = f"KOSMOS 인프라 디렉토리 ({prefix}) — 정당 변경"
        ref = "Spec 287 (TUI Ink+React+Bun) 또는 Spec 032 (IPC stdio hardening)"
        return "Legitimate", summary, ref

    if kosmos_hits:
        summary = f"KOSMOS-only 토큰 ({', '.join(kosmos_hits[:3])}) 식별 — 정당 변경"
        ref = (
            f"Spec ids in git log: {', '.join(spec_ids)}"
            if spec_ids
            else "KOSMOS i18n / branding"
        )
        return "Legitimate", summary, ref

    if spec_ids:
        summary = f"Spec id 인용 ({', '.join(spec_ids)}) — git 기록 기반 정당 변경"
        ref = f"Specs: {', '.join('#' + s for s in spec_ids)}"
        return "Legitimate", summary, ref

    # No signals produced a verdict.
    summary = "휴리스틱 미분류 — 추가 audit 필요"
    ref = (
        f".references/claude-code-sourcemap/restored-src/src/"
        f"{Path('').joinpath(*Path('tui/src').parts).as_posix()}"
    )
    return "Suspicious", summary, ref


def main() -> int:
    if not ENUM_MODIFIED.exists():
        print(f"ERROR: {ENUM_MODIFIED} missing — run T003/T004 first", file=sys.stderr)
        return 1

    paths = [
        line.strip()
        for line in ENUM_MODIFIED.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    entries = []
    for kosmos_path in paths:
        sig = collect_signals(kosmos_path)
        classification, change_summary, reference_citation = classify(sig)
        cc_source_path = (
            f"{CC_SRC_REL}/{kosmos_path[len('tui/src/'):]}"
            if kosmos_path.startswith("tui/src/")
            else None
        )
        entries.append(
            {
                "kosmos_path": kosmos_path,
                "cc_source_path": cc_source_path,
                "classification": classification,
                "change_summary": change_summary,
                "reference_citation": reference_citation,
                "signals": {
                    "directory_match": sig.get("directory_match"),
                    "git_history_match": sig.get("git_history_match"),
                    "import_scan_match": sig.get("import_scan_match"),
                },
                "notes": None,
            }
        )

    OUT_JSON.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Summary.
    counts = {"Legitimate": 0, "Cleanup-needed": 0, "Suspicious": 0}
    for e in entries:
        counts[e["classification"]] += 1
    total = sum(counts.values())
    print(f"[R4] classified {total} files:")
    for k, v in counts.items():
        pct = (v * 100 / total) if total else 0
        print(f"  {k:<16} {v:>4} ({pct:5.1f}%)")
    print(f"[R4] wrote {OUT_JSON.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
