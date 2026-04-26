# Contract — `scripts/build_schemas.py` CLI

**Purpose**: defines the command-line surface of the new builder script. Validates spec FR-006 / FR-007 / FR-022 and SC-002.

---

## Synopsis

```bash
python scripts/build_schemas.py [--check] [--output-dir DIR] [--quiet]
```

## Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--check` | flag | false | Validate that on-disk schemas match what the script would produce. Exit code 0 if match; non-zero if drift. Used by CI / pre-commit. |
| `--output-dir DIR` | path | `docs/api/schemas/` | Override output directory (used by tests). |
| `--quiet` | flag | false | Suppress per-file progress output; only print final summary. |
| `-h`, `--help` | flag | — | Print usage and exit. |

## Behavior

1. **Resolve repository root**: ascend from the script's own location until a `pyproject.toml` is found. ERROR if not found.
2. **Import the registry**: `from kosmos.tools import register_all` (or equivalent — confirm the canonical entry point during implement). The import populates `kosmos.tools.registry.ToolRegistry._tools` per Spec 1634.
3. **Iterate adapters in alphabetical order by tool_id** (deterministic sort).
4. **For each adapter**:
   1. Locate input model class and output model class (per AdapterRegistration data structure).
   2. Call `Model.model_json_schema(mode='validation', ref_template='#/$defs/{model}')` for each.
   3. Wrap into the JSONSchema entity from data-model.md § 3.
   4. Render with `json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False)` plus a trailing newline.
   5. If `--check`: compare against on-disk file; record drift.
   6. Else: write to `<output-dir>/<tool_id>.json`, but only if content changed (preserve mtime when unchanged).
5. **Print summary**:
   - Without `--check`: `wrote <N>, unchanged <M>` to stdout.
   - With `--check`: `OK` and exit 0 if no drift; `DRIFT: <list of files>` and exit 1 otherwise.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (or `--check` with no drift) |
| 1 | Drift detected with `--check` |
| 2 | Registry import failed |
| 3 | Output write failed (permission, IO) |
| 4 | Pydantic schema generation failed for at least one model |

## Stdin / Stdout / Stderr

- Stdin: not used.
- Stdout: progress + summary (suppressed under `--quiet` except the final summary).
- Stderr: errors and warnings only.

## Determinism guarantees

- Iteration order: alphabetical by tool_id (Python `sorted()` on string keys).
- JSON output: `sort_keys=True` ensures property order is deterministic.
- Indentation: fixed at 2 spaces (`indent=2`).
- Trailing newline: always present (POSIX convention; helps git diff).
- Encoding: UTF-8 (`ensure_ascii=False` preserves Korean field descriptions verbatim).

Re-running the script on an unchanged tree MUST produce zero filesystem changes (mtime preserved by the "only-if-changed" write step).

## Dependencies

- Stdlib only: `argparse`, `pathlib`, `json`, `sys`.
- Pydantic v2 (existing project dependency; via the registry).

**No new dependencies introduced**. AGENTS.md hard rule + spec FR-022 satisfied.

## Implementation budget

- Approximate LOC: 100–150.
- File location: `scripts/build_schemas.py`.
- Test coverage: a `tests/scripts/test_build_schemas.py` (under existing pytest setup) verifies idempotency by running the script twice and asserting zero diff.

## Out-of-scope (this contract)

- Validating the produced JSON Schema against a meta-schema (delegated to a separate CI step using existing testing libraries).
- Generating OpenAPI 3.0 — explicitly deferred per spec FR-020 and Deferred-Items table.
