#!/usr/bin/env python3
"""
T010 — R2 byte-identical parity spot-check.

Selects 50 files from `data/enumerated-keep-byte-identical.txt` using
`random.Random(2292).sample(...)` (seed = Epic number, Mersenne Twister
guaranteed stable across Python 3.x), then sha256-compares each pair.

Outputs:
  - data/spot-check-results.json                 (50 entries)
  - data/spot-check-reclassify-pending.json      (only when mismatches found)

Reproducibility: seed `2292` is hardcoded; this script + result JSON together
are the canonical record.

Stdlib only (random, hashlib, json, pathlib, sys).
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
AUDIT_DIR: Final = REPO_ROOT / "specs" / "2292-cc-parity-audit"
DATA_DIR: Final = AUDIT_DIR / "data"
ENUM_KEEP: Final = DATA_DIR / "enumerated-keep-byte-identical.txt"
OUT_RESULTS: Final = DATA_DIR / "spot-check-results.json"
OUT_PENDING: Final = DATA_DIR / "spot-check-reclassify-pending.json"
CC_SRC_REL: Final = ".references/claude-code-sourcemap/restored-src/src"

SEED: Final = 2292
SAMPLE_SIZE: Final = 50


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not ENUM_KEEP.exists():
        return 1

    population = [
        line.strip()
        for line in ENUM_KEEP.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(population) < SAMPLE_SIZE:
        return 1

    rng = random.Random(SEED)
    sample = rng.sample(population, SAMPLE_SIZE)

    entries = []
    mismatches = []
    for idx, ummaya_path in enumerate(sample):
        if not ummaya_path.startswith("tui/src/"):
            return 2
        cc_path_rel = f"{CC_SRC_REL}/{ummaya_path[len('tui/src/'):]}"
        ummaya_abs = REPO_ROOT / ummaya_path
        cc_abs = REPO_ROOT / cc_path_rel
        if not ummaya_abs.exists():
            return 2
        if not cc_abs.exists():
            return 2
        ummaya_sha = sha256_file(ummaya_abs)
        cc_sha = sha256_file(cc_abs)
        match = ummaya_sha == cc_sha
        entry = {
            "ummaya_path": ummaya_path,
            "cc_source_path": cc_path_rel,
            "ummaya_sha256": ummaya_sha,
            "cc_sha256": cc_sha,
            "hash_match": match,
            "sampling_seed": SEED,
            "sampling_index": idx,
        }
        entries.append(entry)
        if not match:
            mismatches.append(entry)

    if len(entries) != SAMPLE_SIZE:
        # Defensive — should be unreachable given the FATAL early-returns above,
        # but enforce the invariant explicitly so the JSON downstream is never
        # written with a short denominator (Codex P1 fail-closed gate).
        return 2

    OUT_RESULTS.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    sum(1 for e in entries if e["hash_match"])

    if mismatches:
        OUT_PENDING.write_text(
            json.dumps(mismatches, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    else:
        # Ensure stale staging from a prior run is removed.
        if OUT_PENDING.exists():
            OUT_PENDING.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
