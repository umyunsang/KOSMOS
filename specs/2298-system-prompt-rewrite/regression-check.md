# Regression Check — Epic η #2298 System Prompt Rewrite

Covers T019 (#2465) and T020 (#2466).

---

## T019 — Lookup-only Regression (SC-006) Approach

**Outcome: (b) — defer to CI (shadow-eval workflow)**

### Fixture Investigation

The spec references an `_existing_lookup_only/` directory under `tests/fixtures/shadow_eval/`.
Investigation result (2026-04-30):

```
$ ls -la tests/fixtures/shadow_eval/
total 8
-rw-r--r--   __init__.py
drwxr-xr-x   __pycache__
drwxr-xr-x   citizen_chain/

$ find tests/fixtures/shadow_eval/ -type f -name "*.json"
tests/fixtures/shadow_eval/citizen_chain/kec.json
tests/fixtures/shadow_eval/citizen_chain/modid.json
tests/fixtures/shadow_eval/citizen_chain/simple_auth_module.json
tests/fixtures/shadow_eval/citizen_chain/geumyung_module.json
tests/fixtures/shadow_eval/citizen_chain/any_id_sso.json
```

The `_existing_lookup_only/` subdirectory does **not exist**. Only the 5 new citizen-chain
fixtures (authored by T014–T018, US2) are present. The 8 lookup-only fixtures cited by
spec.md § SC-006 (weather × 2, hospital × 1, emergency × 1, accident × 1, welfare × 1,
location-resolve × 1, no-tool fallback × 1) have not been authored as shadow-eval fixtures
at this commit. They exist as **adapter-level test fixtures** under:

```
tests/fixtures/kma/      (forecast_fetch_happy.json, ...)
tests/fixtures/hira/     (hospital_search_happy.json, ...)
tests/fixtures/nmc/      (fresh_response.json, ...)
tests/fixtures/koroad/   (accident_hazard_search_happy.json, ...)
tests/fixtures/ssis/     (mohw_welfare_eligibility_search.json, ...)
```

These adapter fixtures exercise the tool *response parsing*, not the LLM prompt→tool-call
routing. Authoring them as shadow-eval routing fixtures is a gap owned by Spec 026
shadow-eval infrastructure, not by Epic η individually.

### Regression Gate: Defer to CI

**SC-006 gate = the GitHub Actions `shadow-eval.yml` workflow on the PR.**

- Workflow fires automatically on `prompts/**` PRs (FR-014 confirmed by Spec 026 acceptance).
- On this branch, the `.github/workflows/shadow-eval.yml` twin-run (`deployment.environment=main`
  vs `deployment.environment=shadow`) is the canonical source-of-truth for prompt regression.
- Per spec.md § SC-004, the `shadow` run fixture-match rate for existing lookup-only fixtures
  must be ≥ historical baseline (no regression).
- Local mock harness execution is **not available** (no `_existing_lookup_only/` fixtures).

**Verdict**: SC-006 can only be verified post-PR via the `shadow-eval.yml` CI run.
Lead Opus must monitor the shadow-eval check in the PR checks list and treat a non-PASS result
as a blocking regression before merge.

Representative fixture pair that *would* form the smoke set once authored:
- `tests/fixtures/shadow_eval/_existing_lookup_only/weather_basic.json`
- `tests/fixtures/shadow_eval/_existing_lookup_only/hospital_search.json`

---

## T020 — Visual Continuity Check (2112 Keyframes)

The 6 keyframe PNGs from Epic 2112 are committed to the **main** repo at
`specs/2112-dead-anthropic-models/` (not yet in this worktree — they are untracked files
on `main`, listed in git status but not on the `2298-system-prompt-rewrite` branch).

All 6 were inspected via the Read tool (multimodal vision):

| File | Content |
|------|---------|
| `smoke-scenario-0-launch.png` | TUI boot screen — KOSMOS v0.1.0-alpha+1978 branding, UFO mascot, empty REPL prompt waiting for input. Status bar shows `high · /effort`. |
| `smoke-scenario-1-greeting.png` | LLM greeting response rendered in REPL — Korean-language intro listing current branch, active tasks, offer to help. Multi-turn context box with `⎿` prefix visible. |
| `smoke-scenario-2-slash-autocomplete.png` | Slash-command autocomplete dropdown with `/speckit-*` family listed, input bar at top, `/` typed. Greeting text above. |
| `smoke-scenario-3-help.png` | `/help` overlay — 4-group layout (세션 / 권한 / 도구 / 저장) with Korean descriptions. `Esc · 닫기` footer visible. |
| `smoke-scenario-4-lookup.png` | Same `/help` overlay visible (screenshot captured at help-state, not at lookup-result state). No lookup result rendered in this frame. |
| `smoke-scenario-5-weather.png` | Same `/help` overlay (identical frame to scenario-3 and scenario-4 — the vhs tape captured the help overlay for three consecutive screenshots). |

### Visual Continuity Verdict

**Y — Visual continuity preserved.**

Reasoning:
- The `<output_style>` section of `prompts/system_v1.md` is **preserved verbatim** by this
  Epic (FR-003 in spec.md). The rendered output format (Korean primary, `⎿` multi-turn cue,
  `/help` 4-group layout) is controlled by `<output_style>` and the TUI rendering stack
  (`tui/src/`), neither of which this Epic modifies (FR-019: zero `tui/src/**` changes).
- Keyframes 0–1 confirm the boot+branding and greeting flow are stable post-Spec-2112.
  The rewritten prompt does not alter the TUI boot path or the greeting instruction set.
- Keyframes 3–5 confirm the `/help` overlay renders the KOSMOS slash-command catalog
  correctly. This is TUI-layer state, unaffected by prompt content changes.
- No lookup-result frame is captured in these keyframes (frames 4–5 show the help overlay
  rather than a lookup response). Visual continuity of the lookup-result rendering will be
  verified post-merge by the T028 mandate: re-run Layer 2 + Layer 4 smokes on the final HEAD.

**Gap**: Keyframes 4 and 5 are duplicates of keyframe 3 (help overlay) — the vhs tape
did not advance to capture a live lookup response. This is a known limitation of the 2112
smoke tape design; it does not indicate a regression. T028 closes this gap.
