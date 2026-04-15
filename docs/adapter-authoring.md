# Adapter Authoring Guide

How to add a new government API adapter to KOSMOS. This guide covers everything from directory layout to fixture capture. See `docs/design/mvp-tools.md` for the canonical architectural decisions.

## Design authority

All architectural decisions (D1–D7, Q1–Q5) are frozen in `docs/design/mvp-tools.md`. If a new adapter seems to require a structural change to `lookup`, `resolve_location`, `executor.py`, `envelope.py`, or `registry.py`, open a GitHub issue before proceeding — those files are closed for modification by new adapters.

---

## 1. Directory structure

```
src/kosmos/tools/<provider>/
    __init__.py           # empty — namespace package marker
    <noun>_<verb>.py      # adapter module (e.g. hospital_search.py)

tests/tools/<provider>/
    __init__.py           # empty
    test_<noun>_<verb>.py           # unit + integration tests (T051 style)
    test_<noun>_<verb>_search_rank.py  # BM25 rank tests (T053 style)

tests/fixtures/<provider>/
    <noun>_<verb>_happy.json          # happy-path recorded fixture
    <noun>_<verb>_error_<case>.json   # error-path fixture
```

Canonical examples:
- KOROAD: `src/kosmos/tools/koroad/accident_hazard_search.py`
- HIRA: `src/kosmos/tools/hira/hospital_search.py`

---

## 2. Pydantic schema conventions

All I/O schemas use **Pydantic v2** (`pydantic>=2.0`). `Any` is forbidden.

```python
from pydantic import BaseModel, ConfigDict, Field

class MyAdapterInput(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    location_code: str = Field(
        pattern=r"^[0-9]{10}$",
        description=(
            "10-digit 행정동 administrative code. "
            "Obtain from resolve_location(want='adm_cd'). Never guess."
        ),
    )
    year: int = Field(
        ge=2019,
        le=2100,
        description="Calendar year for the dataset query.",
    )
```

Key rules:
- `extra="forbid"` — rejects unknown fields at validation time.
- `frozen=True` — makes input instances immutable (safe for async use).
- Every field needs a `description` that tells the LLM **where to get the value** (e.g., "Obtain from resolve_location") and explicitly forbids model memory for derived parameters ("Never guess").
- Use `ge`, `le`, `pattern` constraints to catch bad params at the schema boundary before the upstream call.
- For coordinate fields, include the valid range (e.g., Korean longitude 124–132).

---

## 3. Envelope return shape

The `handle()` function returns a plain `dict` that the executor passes to `envelope.normalize()`. The dict must include a `kind` field matching one of the frozen `LookupOutput` variants:

```python
# Collection (list of records)
return {
    "kind": "collection",
    "items": [{"field_a": ..., "field_b": ...}, ...],
    "total_count": 42,          # optional but recommended
    "next_cursor": None,        # opaque string for pagination, or None
}

# Single record
return {
    "kind": "record",
    "item": {"field_a": ..., "field_b": ...},
}

# Time series
return {
    "kind": "timeseries",
    "points": [{"ts": "2026-04-16T12:00:00Z", "temperature_c": 15.2, ...}, ...],
    "interval": "hour",         # "minute" | "hour" | "day"
}
```

The `meta` block (`source`, `fetched_at`, `request_id`, `elapsed_ms`) is injected automatically by `envelope.normalize()` — do **not** include it in the handler return value.

For errors, raise a `RuntimeError` or `httpx.HTTPStatusError` — the executor converts exceptions to `LookupError(reason="upstream_unavailable", retryable=True)`. Do not return an error dict; let exceptions propagate to the executor boundary (FR-017).

---

## 4. `register()` function pattern

Every adapter module exposes a `register(registry, executor)` function:

```python
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from kosmos.tools.models import GovAPITool

MY_TOOL = GovAPITool(
    id="provider_noun_verb",
    ...
)

def register(registry: object, executor: object) -> None:
    """Register this adapter into a ToolRegistry + ToolExecutor.

    Called from register_all.py. Do NOT call from this module directly.
    """
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.registry import ToolRegistry
    import logging

    logger = logging.getLogger(__name__)

    assert isinstance(registry, ToolRegistry)
    assert isinstance(executor, ToolExecutor)

    async def _adapter(inp: BaseModel) -> dict[str, Any]:
        assert isinstance(inp, MyAdapterInput)
        return await handle(inp)

    registry.register(MY_TOOL)
    executor.register_adapter(MY_TOOL.id, _adapter)
    logger.info("Registered tool: %s", MY_TOOL.id)
```

The `register()` function must **not** be called from `register_all.py` until the Stage 3 integration task for that adapter. This keeps individual adapters testable in isolation with a fresh test-local registry.

---

## 5. `search_hint` — bilingual requirement

Every adapter must include both Korean and English keywords in one `search_hint` string (FR-011). The BM25 retrieval gate (`kiwipiepy` + `rank_bm25`) tokenizes this field at index time.

```python
search_hint=(
    "병원 검색 진료과목 의료기관 정보 근처 병원 내과 외과 소아과 "
    "hospital search medical specialty clinic nearby HIRA healthcare Korea"
),
```

Guidelines:
- Korean first (they are the primary query language), English after.
- Include synonyms the LLM might use (e.g., both "병원" and "의료기관").
- Include the provider acronym in both languages (e.g., "HIRA", "건강보험심사평가원").
- Aim for 10–25 meaningful tokens; padding with noise words hurts precision.

---

## 6. Fail-closed defaults

Declare all four security fields explicitly (FR-024). Default to the most restrictive value; only relax when the API actually warrants it.

```python
GovAPITool(
    ...
    requires_auth=False,        # True = requires session identity (NMC pattern)
    is_personal_data=False,     # True = response may contain PII (triggers auth gate)
    is_concurrency_safe=True,   # False if rate-limiter state makes parallel calls unsafe
    cache_ttl_seconds=0,        # 0 = no caching; set >0 only for stable reference data
)
```

Invariant (FR-038): `is_personal_data=True` requires `requires_auth=True`. Registration fails at startup otherwise. See `nmc_emergency_search` for the canonical example of an auth-gated stub.

---

## 7. Fixture capture convention

Fixtures live under `tests/fixtures/<provider>/`. Every adapter ships at least two fixtures:

| Fixture | Purpose |
|---|---|
| `<noun>_<verb>_happy.json` | 2–3 real items, success response (resultCode=00) |
| `<noun>_<verb>_error_<case>.json` | Upstream error or provider error |

If live capture is not possible (e.g., missing env keys in CI), synthesize from the published API docs and add a `_provenance` comment at the top of the JSON:

```json
{
  "_provenance": "Synthesized from published <PROVIDER> API docs (<URL>). Field names, envelope shape, and resultCode semantics sourced from <document>. Captured: YYYY-MM-DD.",
  "response": { ... }
}
```

Fixture format mirrors the raw API response exactly — the adapter's `handle()` function parses it. Do not pre-process fixtures.

To capture a live fixture (only when `KOSMOS_DATA_GO_KR_API_KEY` is set):

```bash
KOSMOS_DATA_GO_KR_API_KEY=<key> uv run pytest -m live tests/tools/<provider>/
```

Live tests are marked `@pytest.mark.live` and skipped in CI (never call live endpoints in CI per constitution §IV).

---

## 8. Test checklist

Every adapter must have:

- `test_handle_returns_collection_dict` — happy path via mocked httpx.
- `test_handle_items_have_expected_fields` — key fields present in items.
- `test_lookup_fetch_returns_lookup_collection` — end-to-end via `lookup(mode='fetch')`.
- `test_upstream_500_returns_lookup_error` — HTTP 500 → `LookupError`.
- `test_provider_error_*_returns_lookup_error` — non-00 resultCode → `LookupError`.
- `test_invalid_*_returns_invalid_params` — bad input → `LookupError(reason='invalid_params')`.
- `test_register` — `register()` wires tool into registry and executor.
- Search rank test: `lookup(mode='search', query='<matching hint>')` returns this tool as top candidate.

All tests must use mocked httpx or recorded fixtures. No live `data.go.kr` calls in CI.

---

## 9. Registering in `register_all.py`

Once the adapter, fixtures, and tests are green:

```python
# src/kosmos/tools/register_all.py

from kosmos.tools.hira.hospital_search import register as register_hira_hospital_search

def register_all_tools(registry: ToolRegistry, executor: ToolExecutor) -> None:
    ...
    register_hira_hospital_search(registry, executor)
```

Only add this call in a dedicated Stage 3 task. Do not include it during the adapter implementation task — this keeps registration gated behind a deliberate merge step.

---

## 10. Quick reference

| Step | File(s) | Key requirement |
|---|---|---|
| Input schema | `src/.../hospital_search.py` | `ConfigDict(extra="forbid", frozen=True)`, no `Any`, all fields have `description` |
| Handler | same | async coroutine, returns dict with `kind` field, raises on error |
| Tool metadata | same | bilingual `search_hint`, explicit fail-closed flags |
| `register()` | same | assert types, register tool + adapter, log |
| Happy fixture | `tests/fixtures/<provider>/` | 2–3 items, raw API envelope |
| Error fixture | same | non-00 resultCode or HTTP error |
| Unit tests | `tests/tools/<provider>/test_*.py` | mock httpx, cover happy + error + validation |
| Search rank test | `tests/tools/<provider>/test_*_search_rank.py` | top-k query returns this tool |
| `register_all.py` | **Stage 3 only** | import + call in `register_all_tools()` |
