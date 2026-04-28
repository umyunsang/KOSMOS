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
        print(f"ERROR: {ENUM_KEEP} missing — run T003/T004 first", file=sys.stderr)
        return 1

    population = [
        line.strip()
        for line in ENUM_KEEP.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(population) < SAMPLE_SIZE:
        print(
            f"ERROR: population ({len(population)}) < sample size ({SAMPLE_SIZE})",
            file=sys.stderr,
        )
        return 1

    rng = random.Random(SEED)
    sample = rng.sample(population, SAMPLE_SIZE)

    entries = []
    mismatches = []
    for idx, kosmos_path in enumerate(sample):
        if not kosmos_path.startswith("tui/src/"):
            print(
                f"FATAL: unexpected prefix in sampled path {kosmos_path}; "
                f"enumeration manifest is stale — re-run T003/T004",
                file=sys.stderr,
            )
            return 2
        cc_path_rel = f"{CC_SRC_REL}/{kosmos_path[len('tui/src/'):]}"
        kosmos_abs = REPO_ROOT / kosmos_path
        cc_abs = REPO_ROOT / cc_path_rel
        if not kosmos_abs.exists():
            print(
                f"FATAL: sampled KOSMOS file missing: {kosmos_path}; "
                f"the enumeration manifest is stale or the working tree "
                f"is partial. Aborting — fix and re-run audit.",
                file=sys.stderr,
            )
            return 2
        if not cc_abs.exists():
            print(
                f"FATAL: sampled CC file missing: {cc_path_rel}; "
                f"`.references/claude-code-sourcemap/restored-src/src/` is "
                f"incomplete. Aborting — fix and re-run audit.",
                file=sys.stderr,
            )
            return 2
        kosmos_sha = sha256_file(kosmos_abs)
        cc_sha = sha256_file(cc_abs)
        match = kosmos_sha == cc_sha
        entry = {
            "kosmos_path": kosmos_path,
            "cc_source_path": cc_path_rel,
            "kosmos_sha256": kosmos_sha,
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
        print(
            f"FATAL: produced {len(entries)} entries but SAMPLE_SIZE={SAMPLE_SIZE}; "
            f"refusing to write incomplete spot-check manifest.",
            file=sys.stderr,
        )
        return 2

    OUT_RESULTS.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    matched = sum(1 for e in entries if e["hash_match"])
    print(f"[R2] sampled {len(entries)} files (seed={SEED}); {matched}/{len(entries)} match")

    if mismatches:
        OUT_PENDING.write_text(
            json.dumps(mismatches, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"[R2] {len(mismatches)} mismatch(es) → staging at {OUT_PENDING.relative_to(REPO_ROOT)}")
    else:
        # Ensure stale staging from a prior run is removed.
        if OUT_PENDING.exists():
            OUT_PENDING.unlink()
        print("[R2] no mismatches — staging file cleared")

    print(f"[R2] wrote {OUT_RESULTS.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
