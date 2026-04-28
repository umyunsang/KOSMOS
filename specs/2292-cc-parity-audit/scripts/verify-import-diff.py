#!/usr/bin/env python3
"""
T013 — R3 SDK-import-only-diff verification.

For every entry in `data/enumerated-import-candidate.txt`, runs `diff` and
filters import-related lines (`import`, `from`, `export * from`,
`export { ... } from`). If the residual diff is empty, the file is confirmed
import-only; otherwise, it is flagged for reclassification to modified.

Outputs:
  - data/import-verify-results.json                (per-file ImportDiffEntry)
  - data/import-verify-reclassify-pending.json     (subset where body diff present)

Stdlib only (subprocess, json, re, pathlib, sys).
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
ENUM_IMPORT: Final = DATA_DIR / "enumerated-import-candidate.txt"
OUT_RESULTS: Final = DATA_DIR / "import-verify-results.json"
OUT_PENDING: Final = DATA_DIR / "import-verify-reclassify-pending.json"
CC_SRC_REL: Final = ".references/claude-code-sourcemap/restored-src/src"

IMPORT_LINE_RE: Final = re.compile(
    r"^[+\-]\s*(?:import|from|export\s+\*\s+from|export\s*\{[^}]*\}\s*from)\b"
)


def diff_pair(kosmos_abs: Path, cc_abs: Path) -> list[str]:
    proc = subprocess.run(
        ["diff", "-u", str(cc_abs), str(kosmos_abs)],
        capture_output=True,
        text=True,
        check=False,
    )
    # Skip the +++/--- header (first two lines) and `@@` hunk markers.
    out_lines = proc.stdout.splitlines()
    body = []
    for line in out_lines:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            continue
        body.append(line)
    return body


def split_diff(body: list[str]) -> tuple[list[str], list[str]]:
    """Return (import_changes, body_changes) — only +/- lines, no context."""
    imports = []
    bodies = []
    for line in body:
        if not (line.startswith("+") or line.startswith("-")):
            continue
        if IMPORT_LINE_RE.match(line):
            imports.append(line)
        else:
            bodies.append(line)
    return imports, bodies


def main() -> int:
    if not ENUM_IMPORT.exists():
        print(f"ERROR: {ENUM_IMPORT} missing — run T003 first", file=sys.stderr)
        return 1

    paths = [
        line.strip()
        for line in ENUM_IMPORT.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    entries = []
    pending = []
    for kosmos_path in paths:
        if not kosmos_path.startswith("tui/src/"):
            print(
                f"FATAL: unexpected prefix in candidate path {kosmos_path}; "
                f"enumeration manifest is stale — re-run T003/T004",
                file=sys.stderr,
            )
            return 2
        cc_path_rel = f"{CC_SRC_REL}/{kosmos_path[len('tui/src/'):]}"
        kosmos_abs = REPO_ROOT / kosmos_path
        cc_abs = REPO_ROOT / cc_path_rel
        if not kosmos_abs.exists():
            print(
                f"FATAL: candidate KOSMOS file missing: {kosmos_path}; "
                f"the enumeration manifest is stale or the working tree is "
                f"partial. Aborting — fix and re-run audit.",
                file=sys.stderr,
            )
            return 2
        if not cc_abs.exists():
            print(
                f"FATAL: candidate CC file missing: {cc_path_rel}; "
                f"`.references/claude-code-sourcemap/restored-src/src/` is "
                f"incomplete. Aborting — fix and re-run audit.",
                file=sys.stderr,
            )
            return 2

        body = diff_pair(kosmos_abs, cc_abs)
        imports, bodies = split_diff(body)
        body_diff_present = bool(bodies)
        reclassified = body_diff_present
        entry = {
            "kosmos_path": kosmos_path,
            "cc_source_path": cc_path_rel,
            "import_lines_changed": imports[:20],  # cap for JSON brevity
            "body_diff_present": body_diff_present,
            "reclassified_to_modified": reclassified,
        }
        entries.append(entry)
        if reclassified:
            pending.append(entry)

    if len(entries) != len(paths):
        # Defensive — every input row must produce exactly one entry.
        # Without this guard, stale-manifest paths could be silently dropped
        # while the report still claims complete coverage (Codex P1 fail-closed
        # gate).
        print(
            f"FATAL: processed {len(entries)} entries but input had "
            f"{len(paths)} candidates; refusing to write partial verify "
            f"manifest.",
            file=sys.stderr,
        )
        return 2

    OUT_RESULTS.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    confirmed = sum(1 for e in entries if not e["body_diff_present"])
    print(
        f"[R3] verified {len(entries)} files: {confirmed} import-only confirmed, "
        f"{len(pending)} reclassified to modified"
    )

    if pending:
        OUT_PENDING.write_text(
            json.dumps(pending, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[R3] staging at {OUT_PENDING.relative_to(REPO_ROOT)}")
    else:
        if OUT_PENDING.exists():
            OUT_PENDING.unlink()
        print("[R3] no reclassifications — staging file cleared")

    print(f"[R3] wrote {OUT_RESULTS.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
