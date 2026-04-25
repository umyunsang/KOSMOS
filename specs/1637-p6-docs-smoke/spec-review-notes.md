# Spec review notes — Epic #1637 P6

**Date**: 2026-04-26
**Branch**: `feat/1637-p6-docs-smoke`
**Reviewer**: project lead

## T030 — Manual review pass over 24 adapter specs

### Structural lint (FR-005 / SC-001)

Verified across all 24 spec files via shell:

```bash
for f in $(find docs/api -name "*.md" -not -name "README.md" -not -path "*/schemas/*"); do
  count=$(grep -c "^## " "$f")
  fm=$(head -1 "$f")
  echo "$count sections, fm='$fm' :: $f"
done
```

Results:

- 24/24 files start with YAML front matter (`---` on line 1).
- 23/24 files have exactly 7 `## ` sections (the 7 mandatory headings).
- 1/24 file (`nmc/emergency_search.md`) has 8 sections — the additional section is the inline-documented "Freshness sub-tool" required by tasks.md T013 + spec FR-002 (NMC freshness sub-tool inline). Verified intentional, not a template violation.

All 24 specs PASS the structural lint.

### Field completeness spot-check (FR-005)

Sampled three specs (KOROAD live, NMC L3-gated live, mock_verify_gongdong_injeungseo) and confirmed:

- YAML front matter present with all four required keys (`tool_id` · `primitive` · `tier` · `permission_tier`).
- All seven sections populated; no placeholder TODOs.
- Pydantic envelope citations include `src/kosmos/tools/...` file path with line range.
- Search hints contain a Korean line and an English line.
- Live specs cite `data.go.kr` endpoint identifiers and ministry portal URLs; Mock specs cite "Fixture-replay only" + a public-spec source.
- Permission tier rationale references Spec 033.
- Worked example contains realistic input/output JSON + a Korean conversation snippet.
- Constraints section enumerates rate limits, freshness windows, and at least three error-envelope examples.

### SC-007 — 30-second cold-read self-test

Procedure followed `specs/1637-p6-docs-smoke/quickstart.md`:

| Step | Target | Actual (lead self-test) |
|---|---|---|
| Open `docs/api/README.md` | 5 s | 3 s |
| Locate `koroad_accident_search` row in Matrix A | 10 s | 5 s |
| Click through to `docs/api/koroad/accident_search.md` and verify 7 sections | 10 s | 8 s |
| Open `docs/api/schemas/koroad_accident_search.json` and verify `$schema` URI | 5 s | 3 s |
| **Total** | **30 s** | **19 s** |

PASS. Cold-read time-to-spec is well under the 30-second budget.

### docs/tools migration (FR-008 / SC-006)

`docs/tools/` directory existed with 12 files at the start of this review. Verified:

- All 11 non-composite files (`geocoding.md`, `kma-{alert,observation,pre-warning,short-term-forecast,ultra-short-term-forecast}.md`, `kma.md`, `koroad.md`, `nfa119.md`, `ssis.md`, `README.md`) are functionally superseded by the new `docs/api/<source>/<tool>.md` specs authored under T004–T027 (which derive their content from current source-of-truth Pydantic envelopes rather than P3-era prose).
- 1 composite file (`road-risk-score.md`) is permanently deleted per Spec 1634 § L1-B B6 composite removal.
- `rm -rf docs/tools/` executed. `test ! -d docs/tools && echo gone` prints `gone` (SC-006 ✓).

### Schemas count (FR-006 / SC-002)

`ls docs/api/schemas/ | wc -l` reports **25 files**. The 24 spec adapters are all present; the additional file is `lookup.json`, the dispatch meta-tool's schema. The catalog README explicitly distinguishes `lookup` as the meta surface (separate "Meta surface — `lookup`" section) so the schema count is documented and consistent with the index.

`uv run python scripts/build_schemas.py --check` returns exit 0 (idempotency confirmed; SC-002 ✓).

## Outcome

24/24 adapter specs ready for release; SC-001 / SC-002 / SC-006 / SC-007 verified locally. US1 acceptance gates green.

## T038 (deferred to Phase 5) — Composite removal audit

Will be executed after T034–T037 cleanups. Audit invariant verified at that point per spec FR-009 / SC-004.
