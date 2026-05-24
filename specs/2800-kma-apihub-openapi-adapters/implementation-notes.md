# Implementation Notes

## Worktree Scope

This implementation is limited to the approved Spec 2800 paths:

- `src/ummaya/tools/kma/apihub_catalog.py`
- `src/ummaya/tools/kma/apihub_endpoint.py`
- `src/ummaya/tools/kma/apihub_structured_adapter.py`
- `src/ummaya/tools/kma/__init__.py`
- `src/ummaya/tools/register_all.py`
- `src/ummaya/permissions/credentials.py`
- `tests/tools/kma/test_apihub_*.py`
- `tests/tools/kma/fixtures/apihub/*`
- `tests/permissions/test_credentials.py`
- registration count guards that must change because the registry adds 78
  active tools and keeps 7 unavailable operations catalog-only
- `docs/api/kma/apihub_structured_adapters.md`

The repository already contains many unrelated dirty files. They are treated as
user or prior-session changes and are not reverted by this feature.

## Evidence Boundary

The generated catalog is based on KMA APIHub category pages captured on
2026-05-24. Only structured `typ02/openApi` sample URLs are wrapped in this
feature. Non-structured URL families and special industrial pages are tracked as
deferred issues #3037 and #3038. Full live validation across every structured
operation is tracked as #3039.

## Validation Evidence

Completed validation:

- `uv run ruff format ... && uv run ruff check ...` for touched Python files:
  passed.
- `uv run pytest tests/tools/kma/test_apihub_catalog.py tests/tools/kma/test_apihub_endpoint.py tests/tools/kma/test_apihub_structured_adapter.py tests/permissions/test_credentials.py tests/tools/test_registration.py tests/unit/tools/test_registry_count_breakdown.py tests/integration/test_discovery_bridge_path_b.py tests/integration/test_mcp_otel_spans.py`: 54 passed.
- `uv run pytest tests/tools/kma/test_kma_current_observation.py tests/tools/kma/test_kma_short_term_forecast.py tests/tools/kma/test_kma_ultra_short_term_forecast.py tests/tools/kma/test_vilage_fcst_endpoint.py`: 102 passed.
- `uv run pytest tests/tools/kma/test_forecast_fetch.py`: 29 passed.
- Combined focused regression run covering the APIHub tests, registry tests,
  specialized KMA tests, and forecast_fetch: 185 passed.
- `uv run mypy src`: passed.
- `OTEL_SDK_DISABLED=true uv run python -m ummaya.eval.retrieval eval/retrieval_queries.yaml`:
  passed with recall@5=100.00%.
- `uv run python scripts/docs_generate.py --check`: passed.
- `uv run python scripts/build_schemas.py --quiet`: generated schemas for the
  active `kma_apihub_*` registered adapters.
- `uv run python scripts/build_schemas.py --check --quiet`: passed with the
  existing duplicate primitive-registry warnings.

Approval evidence:

- The KMA APIHub My Page approval table was rechecked on 2026-05-24 after the
  portal submission pass. It showed 87 approved utilization entries across 18
  pages: all 85 structured `/openApi` operations plus two non-structured
  `/url` operations. The structured catalog now marks all wrapped operations
  `approved`.
- On 2026-05-24, the remaining APIHub utilization application forms were
  submitted from the user's logged-in Chrome session for `seqApi` pages 740,
  741, 748, 749, 878, 880, 881, 882, and 885-893.
- A representative direct curl probe for
  `/api/typ02/openApi/AmmIwxxmService/getMetar` using the official sample
  parameters returned HTTP 200, `resultCode=00`, and
  `resultMsg=NORMAL_SERVICE` after the portal submission pass. The auth key was
  sourced from the local environment and not recorded.
- The same representative operation was also invoked through UMMAYA's
  `call_operation()` adapter path and returned `resultCode=00`,
  `resultMsg=NORMAL_SERVICE`, `raw_format=json`, and one item.
- 2026-05-25 follow-up live probes removed seven non-working structured
  operations from the active callable surface while keeping them in the
  catalog: three `GtsInfoService` operations returned `resultCode=02`
  / `DB_ERROR`; four UM `NwpModelInfoService` operations returned
  `resultCode=99` after the official 2026-03-31 production stop.
