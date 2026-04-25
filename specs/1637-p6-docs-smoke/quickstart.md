# Quickstart — `docs/api/` cold-read time-to-spec test

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-04-26

This quickstart validates spec User Story 1 (Priority P1) and Success Criterion SC-007. It documents the exact procedure a contributor follows when discovering a KOSMOS adapter from a cold start.

## Goal

A first-time reader (no prior KOSMOS knowledge) locates an arbitrary tool spec, verifies its envelope, and consumes its JSON Schema in **under 30 seconds**.

## Pre-requisites

- The merged feat/1637 branch (or main after merge).
- A Markdown viewer (terminal `bat`, GitHub web, or any IDE preview).
- A generic JSON Schema Draft 2020-12 validator (any).

## Procedure

### Step 1 — open the catalog (target: 5 seconds)

```bash
$ bat docs/api/README.md      # or open in GitHub
```

Expected: a one-paragraph introduction followed by Matrix A (by source) and Matrix B (by primitive). Both matrices fit on a single screen at 100-column width.

### Step 2 — find the target adapter (target: 10 seconds)

Suppose the target is `koroad_accident_search`. Either:

- **Path A — by source**: scan Matrix A → "KOROAD" row → first column shows `koroad_accident_search`.
- **Path B — by primitive**: scan Matrix B → "lookup" section → find the row with `koroad_accident_search`.

Either way, the matrix entry hyperlinks to `docs/api/koroad/accident_search.md`.

### Step 3 — read the spec (target: 10 seconds)

```bash
$ bat docs/api/koroad/accident_search.md
```

Expected: the seven mandatory sections in this order — Overview · Envelope · Search hints · Endpoint · Permission tier rationale · Worked example · Constraints. The YAML front matter at the top exposes `tool_id`, `primitive`, `tier`, `permission_tier` for machine readers.

The Worked Example section shows an input JSON, an output JSON, and a Korean conversation snippet. A reader can copy the input JSON directly into a `lookup(mode="fetch", tool_id=..., params=...)` call.

### Step 4 — consume the schema (target: 5 seconds)

```bash
$ bat docs/api/schemas/koroad_accident_search.json
```

Expected: a Draft 2020-12 JSON Schema with `$schema` URI, `$id`, `title`, `properties`, `required`, and `$defs` for nested envelope models. The schema validates against any generic Draft 2020-12 validator.

### Step 5 — verify (optional)

```bash
$ python -c "
import json
schema = json.loads(open('docs/api/schemas/koroad_accident_search.json').read())
assert schema['\$schema'] == 'https://json-schema.org/draft/2020-12/schema'
print('OK')
"
```

Expected output: `OK`.

## Total elapsed time

Measured during the smoke checklist run (step ID `quickstart-cold-read`):

| Step | Target | Actual (validator self-test) |
|---|---|---|
| 1. open catalog | 5 s | (filled at run) |
| 2. find adapter | 10 s | |
| 3. read spec | 10 s | |
| 4. consume schema | 5 s | |
| **Total** | **30 s** | |

If the actual elapsed time exceeds 30 seconds, the AdapterIndex matrix layout or the AdapterSpec heading order is at fault — re-evaluate Phase 1 contracts, not this quickstart.

## Validation against acceptance scenarios

This quickstart maps directly to:

- **Spec US1 Acceptance Scenario 1** (matrix scan finds adapter).
- **Spec US1 Acceptance Scenario 2** (seven mandatory fields populated).
- **Spec US1 Acceptance Scenario 3** (JSON Schema validates).
- **Spec SC-007** (30-second target).

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Step 2 takes more than 10 s | matrix has too many columns or unsorted rows | Reduce to the 5 columns in data-model.md § 2; sort alphabetically by tool_id within each source group. |
| Step 3 reader cannot identify primitive | primitive missing from front matter or Overview | Verify YAML front matter present; add primitive label to Overview classification table. |
| Step 4 schema fails Draft 2020-12 validation | `$schema` URI wrong or `$defs` malformed | Re-run `python scripts/build_schemas.py`; the script must produce a valid schema by construction (research.md § R4). |

## Cross-reference

- AdapterIndex contract → data-model.md § 2.
- AdapterSpec template → contracts/adapter-spec-template.md.
- JSON Schema generation → contracts/build-schemas-cli.md.
- Visual-evidence capture for this quickstart → smoke-checklist row `quickstart-cold-read`.
