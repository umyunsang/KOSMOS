# Wave 4 Execution — Leader Prompt

> This prompt is for a Lead agent (Opus) to execute Wave 4 (final wave) of the Phase 1 roadmap.
> Read `AGENTS.md`, `docs/vision.md`, and `.specify/memory/constitution.md` first.

---

## Context

You are the Lead agent for KOSMOS Phase 1 Wave 4 — the final integration wave. All prior waves are complete:
- Wave 1: Epic #4 (LLM Client), Epic #6 (Tool System) — DONE
- Wave 2: Epic #5 (Query Engine), Epic #7 (API Adapters) — DONE
- Wave 3: Epic #8 (Permission Pipeline), Epic #9 (Context Assembly), Epic #10 (Error Recovery), Epic #11 (CLI) — DONE

The codebase now has all 6 architectural layers implemented at v1 level:
- `src/kosmos/llm/` — LLM Client (Layer 1 dependency)
- `src/kosmos/engine/` — Query Engine (Layer 1)
- `src/kosmos/tools/` — Tool System + Adapters (Layer 2)
- `src/kosmos/permission/` — Permission Pipeline v1 (Layer 3)
- `src/kosmos/context/` — Context Assembly v1 (Layer 5)
- `src/kosmos/recovery/` — Error Recovery v1 (Layer 6)
- `src/kosmos/cli/` — CLI Interface (typer + rich)

## Wave 4 goal

One Epic — the acceptance test for the entire Phase 1:

```
Wave 4
  └── Epic #12  Scenario 1 E2E — Route Safety
```

### Target interaction
```
Citizen:  "내일 부산에서 서울 가는데, 안전한 경로 추천해줘"
KOSMOS:   fuses KOROAD accident data + KMA weather alerts + road-risk index
          → "경부고속도로 대전-천안 구간 위험 등급, 안개 주의보.
             중부내륙 우회를 추천합니다."
```

This is NOT a new feature — it is an **integration test** that proves all layers work together end-to-end.

## Workflow

### Step 1: Verify Epic #12 exists
```bash
gh issue view 12 --repo umyunsang/KOSMOS
```

### Step 2: `/speckit-specify` → spec.md
- This spec describes the E2E scenario, not a new architectural component
- Define:
  - Input: natural-language route safety question (Korean)
  - Expected flow: Query Engine → tool discovery → KOROAD adapter → KMA adapter → road risk calculation → synthesis → response
  - Expected output: actionable route recommendation with cited data sources
  - Edge cases: API down, no data for region, ambiguous location, rate limit hit
  - Success criteria: citizen gets a useful answer within 30 seconds
- **STOP and wait for user approval**

### Step 3: `/speckit-plan` → plan.md
- Map the data flow through all 6 layers:
  1. CLI receives input → passes to Query Engine
  2. Query Engine calls LLM for intent analysis
  3. LLM requests tools via tool_use → Tool System resolves adapters
  4. Permission Pipeline gates each API call
  5. Context Assembly provides session context to LLM
  6. Error Recovery handles any API failures
  7. LLM synthesizes results → CLI displays response
- Identify integration points that need glue code
- Define test fixtures: recorded KOROAD + KMA responses for the scenario
- **STOP and wait for user approval**

### Step 4: `/speckit-tasks` → tasks.md
- Expected tasks:
  - Integration glue: wire CLI → Engine → Tools → Permission → Context
  - Scenario test fixtures: recorded API responses for Busan→Seoul route
  - E2E test: `test_scenario1_route_safety.py` with `@pytest.mark.live` variant
  - CLI smoke test: interactive session can complete the scenario
  - Documentation: update README with usage example
- **STOP and wait for user approval**

### Step 5: `/speckit-analyze` → constitution compliance check

### Step 6: `/speckit-taskstoissues` → create Task issues, link to Epic #12
- **STOP and wait for user approval**

### Step 7: Implementation
- Create feature branch: `feat/scenario1-e2e`
- This wave is integration-focused — Lead may handle solo (few tasks, high coupling)
- Key implementation:
  - Wire all layers together in the correct dependency order
  - Create recorded fixtures from actual API responses (use `@pytest.mark.live` for recording)
  - Write E2E test that runs entirely on fixtures (no live APIs in CI)
  - Verify the CLI can complete the full scenario interactively

#### Step 7a: Internal code review
- Focus on integration correctness: are all layer interfaces used correctly?
- Check error propagation: does a KOROAD 503 trigger Error Recovery → fallback?
- Check permission flow: does the pipeline correctly gate each API call?

#### Step 7b: Integration verification
```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv run pytest
uv run pytest tests/e2e/ -v  # E2E tests specifically
```

### Step 8: PR and CI
- Branch: `feat/scenario1-e2e`
- PR body: `Closes #12` + all Task issue numbers
- Monitor CI until all checks pass

### Step 9: Copilot Code Review response
- Read and triage Copilot comments
- Fix valid issues, push, verify CI

### Step 10: Final report — Phase 1 completion
Report to user:
- PR link and CI status
- Copilot review summary
- **Scenario 1 test result**: PASS or FAIL with details
- **Phase 1 completion status**:
  - [ ] All 9 Epics (#4-#12) merged
  - [ ] All Task issues closed
  - [ ] Scenario 1 E2E test passes on fixtures
  - [ ] CLI can complete the route safety scenario interactively
  - [ ] `uv run pytest` passes with full coverage
- **Readiness for Phase 2**: what's next (Agent Swarms, more adapters, Ministry specialists)
- **STOP and wait for user to merge**

## Hard constraints

- All source text in English. Korean only in domain data.
- Pydantic v2 for all tool I/O. Never `Any`.
- `KOSMOS_` prefix for all env vars. Never commit secrets.
- `@pytest.mark.live` on real API tests — never run in CI.
- Conventional Commits. Branch: `feat/<slug>`.
- `uv run pytest` must pass before every PR.
- Never advance to the next spec step without user approval.
- E2E tests in CI MUST use recorded fixtures, never live APIs.

## Starting the work

Begin now:
1. `git checkout main && git pull origin main`
2. Read ALL source code under `src/kosmos/` to understand the full codebase
3. Verify Epic #12 exists on GitHub
4. Begin `/speckit-specify` for Epic #12
5. Present the spec to the user for approval
