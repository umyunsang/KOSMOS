#!/usr/bin/env -S uv run python
# SPDX-License-Identifier: Apache-2.0
"""Render docs/plugins/review-checklist.md from checklist_manifest.yaml.

Usage:
    uv run python scripts/render_checklist.py            # write
    uv run python scripts/render_checklist.py --check    # CI drift gate

The Markdown rendering is the human-readable face of the canonical YAML
manifest at ``tests/fixtures/plugin_validation/checklist_manifest.yaml``.
The 50-row YAML is the source-of-truth; this script keeps the docs page
in sync.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from kosmos.plugins.checks.framework import ChecklistRow, load_checklist_rows

REPO_ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = REPO_ROOT / "tests" / "fixtures" / "plugin_validation" / "checklist_manifest.yaml"
DOC_PATH = REPO_ROOT / "docs" / "plugins" / "review-checklist.md"

GROUP_TITLES = {
    "Q1": "Q1 — Schema integrity (10)",
    "Q2": "Q2 — Fail-closed defaults (6)",
    "Q3": "Q3 — Security V1–V6 invariants (5)",
    "Q4": "Q4 — Discovery & docs (8)",
    "Q5": "Q5 — Permission tier (3)",
    "Q6": "Q6 — PIPA §26 trustee (4)",
    "Q7": "Q7 — Tier classification + mocking discipline (5)",
    "Q8": "Q8 — Reserved-name & namespace (3)",
    "Q9": "Q9 — OTEL emission (2)",
    "Q10": "Q10 — Tests & fixtures (4)",
}


def render(rows: list[ChecklistRow]) -> str:
    grouped: dict[str, list[ChecklistRow]] = defaultdict(list)
    for r in rows:
        grouped[r.id.split("-")[0]].append(r)

    lines: list[str] = [
        "# 50-Item Plugin Review Checklist",
        "",
        "> Auto-generated from [`tests/fixtures/plugin_validation/checklist_manifest.yaml`]"
        "(../../tests/fixtures/plugin_validation/checklist_manifest.yaml).",
        "> 수동 편집하지 말고, YAML 을 갱신한 뒤 `uv run python scripts/render_checklist.py` 로 재생성하세요.",
        "",
        f"Total: **{len(rows)}** items.",
        "",
    ]

    for group_key in sorted(grouped.keys(), key=lambda k: int(k[1:])):
        title = GROUP_TITLES.get(group_key, group_key)
        items = grouped[group_key]
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| ID | Korean | English | Source | Check type | Implementation |")
        lines.append("|---|---|---|---|---|---|")
        for r in items:
            lines.append(
                f"| `{r.id}` | {r.description_ko} | {r.description_en} | "
                f"{r.source_rule} | {r.check_type} | "
                f"`{r.check_implementation}` |"
            )
        lines.append("")

    lines.extend(
        [
            "## Failure messages",
            "",
            "When a check fails the workflow surfaces both Korean and English failure",
            "messages on the PR comment + step summary. The bilingual messages live in",
            "the YAML rows below — see `failure_message_ko` / `failure_message_en`.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    rows = load_checklist_rows(YAML_PATH)
    rendered = render(rows)
    if "--check" in argv:
        existing = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.exists() else ""
        if existing != rendered:
            print(
                "review-checklist.md drift detected — run "
                "`uv run python scripts/render_checklist.py` to regenerate.",
                file=sys.stderr,
            )
            return 1
        return 0
    DOC_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {DOC_PATH} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
