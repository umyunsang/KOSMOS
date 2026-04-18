# Quickstart: Scenario 1 E2E — Route Safety (Re-baseline)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Contracts**: [`contracts/`](./contracts/)

This guide shows how to run, extend, and debug the Scenario 1 (route safety) end-to-end test suite. All commands assume you are in the repository root and `uv` is installed.

---

## 1. Run the full suite (default)

```
uv run pytest tests/e2e/ -k route_safety -v
```

Expected: **green in < 5 seconds** (SC-8). No network I/O. No artifacts written to disk.

---

## 2. Run a single variant

```
# Happy path only
uv run pytest tests/e2e/test_route_safety_happy.py -v

# Degraded path — KMA down, retryable
KOSMOS_E2E_SCENARIO=degraded_kma_retry \
  uv run pytest tests/e2e/test_route_safety_degraded.py -v

# KOROAD 2023 year-code quirk (강원 42 → 51)
KOSMOS_E2E_SCENARIO=quirk_2023_gangwon \
  uv run pytest tests/e2e/test_route_safety_quirk.py -v

# Observability assertions only
uv run pytest tests/e2e/test_route_safety_spans.py -v
```

---

## 3. Emit a `RunReport` artifact

For debugging or for a future DeepEval consumer:

```
mkdir -p .run-reports
KOSMOS_E2E_DUMP_DIR=$(pwd)/.run-reports \
  uv run pytest tests/e2e/test_route_safety_happy.py -v

ls .run-reports
# 030-happy-1713456789012.json
```

The file conforms to [`contracts/eval-output.schema.json`](./contracts/eval-output.schema.json). Validate it:

```
uv run python -c "
import json, pathlib, jsonschema
schema = json.loads(pathlib.Path('specs/030-scenario1-route-safety-rebase/contracts/eval-output.schema.json').read_text())
report = json.loads(next(pathlib.Path('.run-reports').glob('030-happy-*.json')).read_text())
jsonschema.validate(report, schema)
print('ok')
"
```

(`jsonschema` is a transitive test dep via `pytest`; if unavailable, add it only under a `dev` extra — do **not** add it to the runtime.)

---

## 4. Observability assertion — what it checks

`tests/e2e/test_route_safety_spans.py` asserts the following on every tool call in the happy-path run:

| Assertion | Source |
|---|---|
| `gen_ai.operation.name == "execute_tool"` exists on every `execute_tool` span | FR-017 |
| `kosmos.tool.outcome ∈ {"ok", "error"}` on every `execute_tool` span | FR-017 |
| `kosmos.tool.adapter == tool_id` **only** on `lookup(mode="fetch")` spans | FR-018 |
| No Korean citizen query string appears in any span attribute value | FR-019 |
| When `OTEL_SDK_DISABLED=true` is set, the test is skipped (not failed) | FR-020 |

To exercise the FR-020 graceful-skip path locally:

```
OTEL_SDK_DISABLED=true \
  uv run pytest tests/e2e/test_route_safety_spans.py -v
# Expected: SKIPPED, not FAILED.
```

---

## 5. Adding a new fixture tape

All HTTP is intercepted by patching `httpx.AsyncClient.get`. To add a new recorded response (e.g., a different `adm_cd`):

1. Capture the live response **outside CI**, behind `@pytest.mark.live`. Never check in live responses from the happy-path runner.
2. Store the JSON under the matching provider directory:
   - Kakao: `tests/fixtures/kakao/`
   - KOROAD: `tests/fixtures/koroad/`
   - KMA: `tests/fixtures/kma/`
3. Name the file by the request shape, e.g. `koroad/accident_hazard_siDo=51_guGun=680_year=2023.json` — readable at a glance.
4. Add a URL-pattern → file mapping in `tests/e2e/conftest.py` so the `AsyncMock` picks it up.
5. Reference the tape from a `ScenarioScript` entry in the test.

**Never** commit a real `data.go.kr` or Kakao response that contains citizen PII. The recorded tapes are government-level data only.

---

## 6. Debugging a failing scenario

1. Re-run with `-v --tb=short` to see the assertion message.
2. If the failure is on `tool_call_order` or `fetched_adapter_ids`, dump the `RunReport` (see §3) — it contains the exact executed sequence.
3. If the failure is on a span assertion, inspect `RunReport.observability.spans` in the JSON artifact.
4. If the failure is a schema-envelope error (`LookupCollection` vs `LookupTimeseries`), cross-reference with `src/kosmos/tools/envelope.py` and `src/kosmos/tools/models.py`.

---

## 7. What this suite does NOT do

- **No live API calls.** Ever. Neither in CI nor in local default runs. Live paths are gated behind `@pytest.mark.live` which is skipped unless `--run-live` is passed (and the real keys are present).
- **No LLM quality assertions.** `final_response` is checked for string presence of ≥ 1 KOROAD hazard spot name and ≥ 1 KMA weather field reference (FR-023), nothing more.
- **No DeepEval, no BLEU, no ROUGE.** Deferred — see `plan.md §Deferred-Item Dispositions`.
- **No multi-turn follow-up.** Deferred — same.

---

## 8. Cross-references

- Plan: [plan.md](./plan.md)
- Research (Phase 0 decisions): [research.md](./research.md)
- Data model: [data-model.md](./data-model.md)
- Contracts: [`contracts/`](./contracts/)
- Prior spec (superseded): [`specs/012-scenario1-e2e-route-safety/`](../012-scenario1-e2e-route-safety/)
- MVP main-tool design: [`docs/design/mvp-tools.md`](../../docs/design/mvp-tools.md)
- Vision: [`docs/vision.md`](../../docs/vision.md)
