# Contract — `scripts/audit-env-registry.py`

**Purpose**: Cross-check the in-code `KOSMOS_*` surface against `docs/configuration.md` registry. Fail CI on drift.
**Related FR**: FR-020, FR-022, FR-023 · **SC**: SC-003 · **NFR**: NFR-006 (10 s budget)

---

## CLI

```
usage: audit-env-registry.py [--repo-root PATH] [--registry PATH]

Cross-check KOSMOS_* env-var surface vs. the registry in docs/configuration.md.
Always emits a JSON report on stdout (see §"Drift report shape").

options:
  --repo-root PATH   repo root to scan (default: current working dir ancestor
                     containing pyproject.toml).
  --registry PATH    registry markdown file (default: docs/configuration.md).
```

Stdlib-only: `argparse`, `re`, `pathlib`, `json`, `sys`. No third-party imports.

## Scan scope

- **Code scan**: `src/**/*.py` + `.github/workflows/ci.yml` + `.env.example`.
- **Registry scan**: `docs/configuration.md` (single file).

## Name extraction regex

```python
_NAME_RE = re.compile(r"\bKOSMOS_[A-Z][A-Z0-9_]*\b")
_LANGFUSE_RE = re.compile(r"\bLANGFUSE_[A-Z][A-Z0-9_]*\b")
```

Allowlisted prefixes: `KOSMOS_`, `LANGFUSE_`. Any other all-caps identifier matched via a broader `[A-Z_]{3,}` sweep is flagged as a `prefix_violation` only if it lives in an assignment / `env_prefix` / `validation_alias` context (contextual filter to suppress trivial constants).

## OverrideFamily suppression

Per-tool `KOSMOS_<TOOL_ID>_API_KEY` expansions (e.g., `KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY`) are detected via `permissions/credentials.py::_tool_specific_var`. The audit recognises the family pattern via a registry row with exact variable literal `KOSMOS_{TOOL_ID}_API_KEY` (literal, not regex) and suppresses "undocumented" findings that match the expansion rule.

## Parsing contract — registry Markdown

The registry table MUST satisfy:
- Exactly one Markdown table whose header row begins with `| Variable | Required |` (case-sensitive).
- Each data row's first cell MUST be a backtick-wrapped variable name: `` `KOSMOS_X` `` or `` `LANGFUSE_X` `` or the literal override-family placeholder.
- Data rows are any lines matching `^\| ` that follow the header (up to the next blank line or next `##` heading).

Parse algorithm:
1. Read file as UTF-8.
2. Locate header line via the literal prefix match.
3. Skip the header-separator line (`| --- | ...`).
4. Collect subsequent `| ... |` lines until blank or heading.
5. For each row: `row.split("|")[1].strip()` — the first non-empty cell; strip backticks → variable name.
6. Classify by the `Required` cell: `yes (all envs)`, `yes (prod only, …)`, `yes (ci+prod)`, `conditional (…)`, `no (opt-in)`, `**deprecated**`.

Malformed table → exit 2 (see §Exit codes) with a single-line error identifying the offending line number.

## Drift report shape

```json
{
  "schema_version": "1",
  "generated_at": "2026-04-17T12:34:56Z",
  "verdict": "clean" | "drift" | "malformed",
  "scan_stats": {
    "code_files_scanned": 142,
    "unique_names_in_code": 18,
    "registry_rows": 21,
    "duration_seconds": 0.42
  },
  "findings": {
    "in_code_not_in_registry": [
      {"name": "KOSMOS_NEW_THING", "source_files": ["src/kosmos/foo.py:42"]}
    ],
    "in_registry_not_in_code": [
      {"name": "KOSMOS_OLD_THING", "registry_line": 87}
    ],
    "prefix_violations": [
      {"name": "MY_BAD_VAR",
       "source_files": ["src/kosmos/bar.py:10"],
       "reason": "not KOSMOS_-prefixed and not in LANGFUSE_ allowlist"}
    ],
    "override_family_unmatched": []
  }
}
```

The JSON report is the sole output format; there is no human-readable alternative mode.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Clean — no drift, no violations. |
| `1` | Drift detected (one or more findings non-empty). |
| `2` | Malformed registry or scan error (e.g., registry missing, unreadable file). |

Exit code 1 blocks CI; exit 2 is a configuration error in the audit pipeline itself.

## Performance contract

- **Budget**: 10 s wall-clock on the full repo tree (NFR-006).
- **Measurement**: self-timed, reported in `scan_stats.duration_seconds`.
- Current repo size (~140 `*.py` files, ~10k lines) → expected ~0.5 s; 20× headroom.

## Determinism

- Findings arrays MUST be sorted: by `name` ascending.
- `source_files` arrays MUST be sorted: by path string, then line number.
- `generated_at` uses UTC ISO-8601 with `Z` suffix.
- Same input tree → identical JSON output byte-for-byte.

## CI integration

Invoked as a pre-test step (see `contracts/ci-workflow.md §Pre-test gates`):

```yaml
- name: Env registry drift check
  run: uv run python scripts/audit-env-registry.py
```

Non-zero exit fails the CI job.

## Test matrix (self-test fixture)

| Test ID | Input | Expected |
|---------|-------|----------|
| T-AR01 | Clean repo + registry matching 1:1 | exit 0, `verdict=clean` |
| T-AR02 | Code has `KOSMOS_X` not in registry | exit 1, `in_code_not_in_registry` contains `KOSMOS_X` |
| T-AR03 | Registry has `KOSMOS_X` not in code | exit 1, `in_registry_not_in_code` contains `KOSMOS_X` |
| T-AR04 | Malformed registry (missing header) | exit 2 |
| T-AR05 | `LANGFUSE_PUBLIC_KEY` in code, in registry | exit 0 (allowlisted prefix) |
| T-AR06 | `KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY` in code, family pattern in registry | exit 0 (family match) |
| T-AR07 | Performance: 10 s wall-clock on full repo | `duration_seconds < 10.0` |

## Non-goals

- Not a static type checker. Doesn't verify that variables are consumed by a `pydantic-settings` field — only that names exist in code and registry.
- Not a secret scanner. Value inspection is `scripts/audit-secrets.sh`'s job.
- Doesn't auto-generate the registry. Registry updates are human PRs; this script is the drift gate.
