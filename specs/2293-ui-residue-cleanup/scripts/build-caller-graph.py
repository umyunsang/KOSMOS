#!/usr/bin/env python3
"""Build caller graph for 30 Cleanup-needed files (Epic β #2293).

For each file in modified-218-classification.json with classification='Cleanup-needed':
- count + list importers (`from '...<module-path>(.js)?'`)
- inspect file contents for Anthropic-token signal (queryHaiku/queryWithModel/verifyApiKey/@anthropic-ai/)
- emit JSON to specs/2293-ui-residue-cleanup/data/caller-graph.json

Run from repo root (worktree at /Users/um-yunsang/KOSAX-w-2293/).
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # KOSAX-w-2293
SPEC_DIR = REPO_ROOT / "specs" / "2293-ui-residue-cleanup"
EPIC_ALPHA_JSON = REPO_ROOT / "specs" / "2292-cc-parity-audit" / "data" / "modified-218-classification.json"
OUTPUT_JSON = SPEC_DIR / "data" / "caller-graph.json"

ANTHROPIC_TOKENS = ["queryHaiku", "queryWithModel", "verifyApiKey", "@anthropic-ai/"]
DEPENDENCY_TOKENS = [
    "sdk-compat",
    "@aws-sdk/client-bedrock-runtime",
    "claude.ai",
    "isClaudeAISubscriber",
    "getClaudeCodeUserAgent",
    "growthbook",
    "from 'bun:bundle'",
    "feature(",
]


def module_path(kosax_path: str) -> str:
    """Strip leading tui/src/ and trailing .ts(x) to get import-path stem."""
    p = kosax_path
    if p.startswith("tui/src/"):
        p = p[len("tui/src/"):]
    for suffix in (".tsx", ".ts"):
        if p.endswith(suffix):
            p = p[: -len(suffix)]
            break
    return p


def list_importers(mod: str, exclude_self: str) -> list[str]:
    """grep -rE 'from \"[^\"]*<mod>(\\.js)?\"' tui/src/ — return importer file paths."""
    pattern = rf"from\s+['\"][^'\"]*{re.escape(mod)}(\.js)?['\"]"
    proc = subprocess.run(
        ["grep", "-rE", pattern, "tui/src/", "-l"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    files = [f for f in proc.stdout.strip().splitlines() if f and f != exclude_self]
    return sorted(set(files))


def file_token_matches(kosax_path: str) -> dict[str, int]:
    """Count occurrences of each Anthropic token in the file content."""
    fpath = REPO_ROOT / kosax_path
    if not fpath.exists():
        return dict.fromkeys(ANTHROPIC_TOKENS, 0)
    text = fpath.read_text(encoding="utf-8", errors="replace")
    return {tok: text.count(tok) for tok in ANTHROPIC_TOKENS}


def file_dependency_signals(kosax_path: str) -> dict:
    """Extract line count + dependency token hits + first-line summary."""
    fpath = REPO_ROOT / kosax_path
    if not fpath.exists():
        return {"line_count": 0, "dependency_hits": {}, "first_lines": ""}
    text = fpath.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    deps = {tok: text.count(tok) for tok in DEPENDENCY_TOKENS}
    return {
        "line_count": len(lines),
        "dependency_hits": deps,
        "first_lines": "\n".join(lines[:5]),
    }


def main() -> int:
    classification = json.loads(EPIC_ALPHA_JSON.read_text())
    cleanup = [f for f in classification if f.get("classification") == "Cleanup-needed"]

    rows: list[dict] = []
    for entry in cleanup:
        kosax = entry["kosax_path"]
        mod = module_path(kosax)
        importers = list_importers(mod, exclude_self=kosax)
        tokens = file_token_matches(kosax)
        deps = file_dependency_signals(kosax)
        rows.append({
            "kosax_path": kosax,
            "module_path": mod,
            "line_count": deps["line_count"],
            "importer_count": len(importers),
            "importers": importers,
            "internal_anthropic_tokens": tokens,
            "dependency_hits": deps["dependency_hits"],
            "first_lines": deps["first_lines"],
            "epic_alpha_signal": entry.get("signals", {}),
            "epic_alpha_summary": entry.get("change_summary", ""),
        })

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Print summary table to stdout
    for _i, r in enumerate(rows, 1):
        sum(r["internal_anthropic_tokens"].values())

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
