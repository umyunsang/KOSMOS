# Contract: Scenario Runner CLI

**Spec**: `specs/030-scenario1-route-safety-rebase/spec.md`
**Status**: Draft (Phase 1 output of `/speckit-plan`)
**Schema version**: `030-runreport-v1`

This document specifies the command-line entry point that runs the Scenario 1 (route safety) end-to-end suite against recorded fixtures and optionally writes a `RunReport` artifact to disk. The runner is thin — it is a wrapper around `pytest` with deterministic knobs.

No new binary is shipped. The contract here pins the **invocation shape** that tests, CI, and future eval harnesses rely on.

---

## 1. Invocation shape

```
uv run pytest tests/e2e/ -k route_safety [--dump-dir PATH] [--scenario-id ID] [--otel-disabled]
```

The underlying `pytest` entry points accept these environment variables (preferred over CLI flags for CI stability):

| Env var | Type | Default | Purpose |
|---|---|---|---|
| `KOSMOS_E2E_DUMP_DIR` | `PATH \| None` | unset | When set, each scenario test writes its `RunReport` as JSON to `$KOSMOS_E2E_DUMP_DIR/030-<scenario_id>-<unix_ts>.json`. When unset, nothing is written to disk. |
| `KOSMOS_E2E_SCENARIO` | `str \| None` | unset | When set, only the matching `ScenarioScript.scenario_id` runs. Accepts one of `happy`, `degraded_kma_retry`, `degraded_koroad_no_retry`, `both_down`, `quirk_2023_gangwon`, `quirk_2023_jeonbuk`, `quirk_2022_control`. Unset ⇒ all scenarios run. |
| `OTEL_SDK_DISABLED` | `str` | unset | When `"true"`, the FR-020 graceful-skip path activates for `tests/e2e/test_route_safety_spans.py`. All other scenario tests continue to run. |
| `KOSMOS_DATA_GO_KR_API_KEY` | `str` | (set by fixture) | Startup-guard input. Tests inject `"test-dummy"` via `monkeypatch.setenv` (FR-011/012). |
| `KOSMOS_KAKAO_REST_KEY` | `str` | (set by fixture) | Startup-guard input. Tests inject `"test-dummy"` via `monkeypatch.setenv` (FR-011/012). |

---

## 2. Exit codes

| Code | Meaning |
|---|---|
| `0` | All selected scenarios passed. |
| `1` | One or more scenarios failed — standard `pytest` failure. |
| `2` | Collection error (fixture missing, `RunReport` schema version drift, guard rejected dummy keys). |
| `3` | `KOSMOS_E2E_DUMP_DIR` provided but not writable. |

Exit codes `0` and `1` are inherited from `pytest`. Codes `2` and `3` are emitted by an early `conftest.py` check.

---

## 3. Output: `RunReport` JSON (when `KOSMOS_E2E_DUMP_DIR` is set)

Each scenario writes exactly one file on green. The file path template:

```
$KOSMOS_E2E_DUMP_DIR/030-<scenario_id>-<unix_epoch_ms>.json
```

Contents conform to [`eval-output.schema.json`](./eval-output.schema.json). The writer **never** includes:
- Raw citizen query strings beyond `trigger_query` (the top-level field; a future DeepEval consumer intentionally needs it, and it is not written to span attributes — see FR-019).
- Real API keys (guaranteed by FR-011; dummy values are not sensitive).
- Raw HTTP response bodies from the tapes — only the parsed envelope.

On red (test failure), no file is written — `pytest`'s failure output is the only artifact.

---

## 4. CI invocation

The GitHub Actions workflow invokes:

```
uv run pytest tests/e2e/ --maxfail=1 --durations=10 -q
```

No environment variables are set beyond the two startup-guard dummies injected by the `autouse` fixture. CI does **not** set `KOSMOS_E2E_DUMP_DIR` — no artifacts leave the runner.

---

## 5. Developer invocation (quickstart)

See [`../quickstart.md`](../quickstart.md) for local-dev recipes. The most common:

```
uv run pytest tests/e2e/test_route_safety_happy.py -v
KOSMOS_E2E_DUMP_DIR=$(pwd)/.run-reports uv run pytest tests/e2e/ -k route_safety -v
```

---

## 6. Non-goals

- This CLI does **not** call FriendliAI or any live LLM — the scripted `MockLLMClient` is always used.
- This CLI does **not** run DeepEval or any semantic quality harness — that is deferred (see plan.md §Deferred-Item Dispositions).
- This CLI is **not** a standalone console script (`pyproject.toml` does not register a `kosmos-e2e` entry point). Adding one would be a separate spec-driven change.
