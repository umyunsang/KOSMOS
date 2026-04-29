#!/usr/bin/env python3
"""Validator for the 5 OPAQUE-domain scenario docs (Epic ζ T028 / SC-010).

Walks ``docs/scenarios/{hometax-tax-filing,gov24-minwon-submit,
mobile-id-issuance,kec-yessign-signing,mydata-live}.md`` and asserts each
has the structure mandated by FR-018:

1. Korean-primary first-level title (``# `` line containing Korean characters).
2. "Why no adapter" thesis paragraph (subsection or paragraph header
   matching ``어댑터를 만들지 않는 이유`` or ``Why no adapter``).
3. ≥5 numbered citizen narrative steps (lines starting with ``1.``..``5.``,
   anywhere in the doc).
4. ``## Hand-off URL`` footer section listing the canonical agency URL.

Exit code 0 on full PASS; non-zero with per-doc diagnostics on FAIL.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Path resolution — works from repo root or from this script's parent.
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent.parent  # specs/2297-../scripts/ → repo root
DOCS_DIR = REPO_ROOT / "docs" / "scenarios"

REQUIRED_DOCS = [
    "hometax-tax-filing.md",
    "gov24-minwon-submit.md",
    "mobile-id-issuance.md",
    "kec-yessign-signing.md",
    "mydata-live.md",
]

KOREAN_CHAR_RE = re.compile(r"[가-힣]")  # Hangul syllables block
WHY_NO_ADAPTER_RE = re.compile(
    r"(어댑터.*만들지.*않는.*이유|Why no adapter|왜 어댑터가 없)",
    re.IGNORECASE,
)
HANDOFF_HEADING_RE = re.compile(r"^##\s+Hand-off URL", re.MULTILINE)
NUMBERED_STEP_RE = re.compile(r"^\s*([1-9]|1[0-9])\.\s+\S", re.MULTILINE)
URL_RE = re.compile(r"https?://[^\s)\]]+")


def check_doc(path: Path) -> list[str]:
    """Return list of failure reasons; empty list = PASS."""
    failures: list[str] = []
    if not path.is_file():
        return [f"missing file: {path}"]

    text = path.read_text(encoding="utf-8")

    # 1. Korean-primary H1 title
    title_lines = [ln for ln in text.splitlines() if ln.startswith("# ")]
    if not title_lines:
        failures.append("no H1 (# ...) title found")
    elif not KOREAN_CHAR_RE.search(title_lines[0]):
        failures.append(f"H1 title is not Korean-primary: {title_lines[0]!r}")

    # 2. Why-no-adapter section
    if not WHY_NO_ADAPTER_RE.search(text):
        failures.append(
            "no 'Why no adapter' section "
            "(expected '어댑터를 만들지 않는 이유' or similar)"
        )

    # 3. ≥5 numbered narrative steps
    steps = NUMBERED_STEP_RE.findall(text)
    if len(steps) < 5:
        failures.append(
            f"only {len(steps)} numbered steps found; need ≥5 per FR-018"
        )

    # 4. Hand-off URL footer
    if not HANDOFF_HEADING_RE.search(text):
        failures.append("no '## Hand-off URL' footer section")
    else:
        # Pull the section body and assert at least one URL
        idx = HANDOFF_HEADING_RE.search(text).start()  # type: ignore[union-attr]
        footer = text[idx:]
        if not URL_RE.search(footer):
            failures.append("'## Hand-off URL' section has no URL")

    return failures


def main() -> int:
    if not DOCS_DIR.is_dir():
        sys.stderr.write(f"FATAL: {DOCS_DIR} does not exist\n")
        return 2

    overall_failures: dict[str, list[str]] = {}
    for filename in REQUIRED_DOCS:
        path = DOCS_DIR / filename
        failures = check_doc(path)
        if failures:
            overall_failures[filename] = failures

    if overall_failures:
        sys.stderr.write(
            f"check_scenario_docs FAIL — {len(overall_failures)}/"
            f"{len(REQUIRED_DOCS)} docs have issues:\n"
        )
        for filename, fails in overall_failures.items():
            sys.stderr.write(f"  {filename}:\n")
            for f in fails:
                sys.stderr.write(f"    - {f}\n")
        return 1

    sys.stdout.write(
        f"check_scenario_docs PASS — all {len(REQUIRED_DOCS)} docs match FR-018.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
