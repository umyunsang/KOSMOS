# Contract — KOROAD accident-search tool input schema

**Feature**: 019-phase1-hardening
**Target file**: `src/kosmos/tools/koroad/koroad_accident_search.py`

## Contract scope

Only the Pydantic v2 `Field(description=...)` text on two fields changes. Runtime validation, adapter behavior, and upstream API calls are unchanged (Out of Scope).

## Required description content

### `KoroadAccidentSearchInput.si_do`

The description MUST contain, in English:

1. A statement that the value MUST be derived from a prior `address_to_region` tool call on a user-provided location string.
2. A statement that the value MUST NEVER be filled from model memory, with a reference to the empirical counter-example where a Korean-centric LLM produced a wrong district code for "강남역".
3. A pointer to the `SidoCode` enumeration as the authoritative set of valid codes.

### `KoroadAccidentSearchInput.gu_gun`

The description MUST contain, in English:

1. Same MUST-be-derived-from-`address_to_region` statement, scoped to gugun-level codes.
2. Same NEVER-fill-from-memory statement with the Gangnam counter-example.
3. A pointer to the `GugunCode` enumeration as the authoritative set of valid codes.

## Verification

- Unit test in `tests/tools/koroad/test_koroad_accident_search.py` asserts that `KoroadAccidentSearchInput.model_json_schema()` contains the phrases "address_to_region" and "never" (case-insensitive) on both fields, and references `SidoCode` / `GugunCode` by name.
- Existing mocked unit tests for the adapter remain green without assertion rewrites.

## Explicitly not changed

- No runtime validator added. The upstream API remains the authority for `(si_do, gu_gun)` pair validity (spec Out of Scope).
- No new fields. No schema ordering change.
- No behavior change in the adapter's `search_hint`, output schema, or fixtures.
