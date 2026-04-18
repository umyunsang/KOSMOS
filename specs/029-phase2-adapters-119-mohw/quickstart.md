# Quickstart — 029 Phase 2 Adapters (NFA 119 + MOHW)

**Audience**: a developer (or Teammate agent) picking up the tasks emitted by
`/speckit-tasks` for this spec.

**Prerequisites**:

- `uv >= 0.5`
- Python 3.12+ (provided by `uv python install 3.12`)
- Git worktree at `/Users/um-yunsang/KOSMOS-15`, branch
  `feat/15-phase2-adapters-119-mohw`
- `.env` populated with `KOSMOS_DATA_GO_KR_API_KEY` (already present from earlier
  specs; **do NOT** exercise live SSIS or NFA calls in CI per Constitution §IV)
- Read `specs/029-phase2-adapters-119-mohw/data-model.md` first — it holds the
  normative Pydantic v2 schemas

---

## 1. Sync dependencies

```bash
cd /Users/um-yunsang/KOSMOS-15
uv sync
```

No new runtime dependency is introduced by this spec. `uv sync` should report no
lockfile changes; if it does, **STOP** — you or a sibling task has drifted the
dependency graph.

---

## 2. Create the new packages and their stubs

Paths listed in `data-model.md §10`:

```bash
mkdir -p src/kosmos/tools/nfa119 src/kosmos/tools/ssis
mkdir -p tests/tools/nfa119 tests/tools/ssis
mkdir -p tests/fixtures/nfa119 tests/fixtures/ssis
mkdir -p docs/security/dpa
touch src/kosmos/tools/nfa119/__init__.py \
      src/kosmos/tools/ssis/__init__.py \
      tests/tools/nfa119/__init__.py \
      tests/tools/ssis/__init__.py
```

Then author the four module files verbatim from `data-model.md`:

- `src/kosmos/tools/ssis/codes.py` — §1
- `src/kosmos/tools/nfa119/emergency_info_service.py` — §§2, 3, 4
- `src/kosmos/tools/ssis/welfare_eligibility_search.py` — §§5, 6, 7
- `docs/security/dpa/dpa-ssis-welfare-v1.md` — §9

---

## 3. Wire up `register_all.py` and `TOOL_MIN_AAL`

```bash
# Add register() calls to src/kosmos/tools/register_all.py.
# Modify src/kosmos/security/audit.py — apply the TOOL_MIN_AAL diff from
# data-model.md §8 (two new rows: nfa_emergency_info_service AAL1,
# mohw_welfare_eligibility_search AAL2).
```

Verify with:

```bash
uv run python -c "
from kosmos.tools.registry import ToolRegistry
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.register_all import register_all

registry, executor = ToolRegistry(), ToolExecutor()
register_all(registry, executor)
assert 'nfa_emergency_info_service' in registry._tools
assert 'mohw_welfare_eligibility_search' in registry._tools
print('OK — both tools registered')
"
```

If this prints `OK`, V1–V6 validators have accepted both `GovAPITool`
constructions and the `TOOL_MIN_AAL` V3 drift gate is green.

---

## 4. Create synthetic fixtures

Synthetic values drawn from spec §4.1 / §4.2:

```json
// tests/fixtures/nfa119/nfa_emergency_info_service.json
{
  "response": {
    "header": { "resultCode": "00", "resultMsg": "NORMAL SERVICE" },
    "body": {
      "pageNo": 1, "numOfRows": 10, "totalCount": 1,
      "items": [{
        "sidoHqOgidNm": "충청남도소방본부",
        "rsacGutFsttOgidNm": "천안동남소방서",
        "gutYm": "202112",
        "gutHh": "14",
        "sptMvmnDtc": "3200",
        "ptntAge": "60~69세",
        "ruptSptmCdNm": "기침"
      }]
    }
  }
}
```

```json
// tests/fixtures/ssis/mohw_welfare_eligibility_search.json
{
  "result_code": "0",
  "result_message": "SUCCESS",
  "page_no": 1, "num_of_rows": 10, "total_count": 1,
  "items": [{
    "servId": "WLF0000001188",
    "servNm": "출산가정 방문서비스",
    "jurMnofNm": "보건복지부",
    "jurOrgNm": "출산정책과",
    "servDgst": "출산 가정을 방문하여 산모와 신생아 건강을 지원",
    "lifeArray": "임신·출산",
    "intrsThemaArray": "임신·출산",
    "onapPsbltYn": "Y"
  }]
}
```

**No real PII.** Service IDs and names are published on `bokjiro.go.kr` /
NFA docs.

---

## 5. Run the test suite

```bash
uv run pytest tests/tools/nfa119 tests/tools/ssis -v
```

Expected outcomes (before implementation):

- All tests fail with `ModuleNotFoundError` until steps 2–4 complete.

Expected outcomes (after implementation):

- Input schema happy-path tests pass.
- `extra="forbid"` rejects unknown field tests pass.
- `Layer3GateViolation` is raised when `handle()` is called directly.
- Executor returns `LookupError(reason="auth_required")` with zero upstream
  HTTP calls when `session_identity=None`.
- BM25 top-5 includes both new tool IDs on the bilingual query terms from
  `search_hint`.

Run the full project suite to confirm zero regression:

```bash
uv run pytest
```

---

## 6. Commit discipline

Conventional Commits, `feat/` branch, no `--force`, no `--no-verify`:

```bash
git -C /Users/um-yunsang/KOSMOS-15 add \
    src/kosmos/tools/nfa119 \
    src/kosmos/tools/ssis \
    src/kosmos/security/audit.py \
    src/kosmos/tools/register_all.py \
    tests/tools/nfa119 \
    tests/tools/ssis \
    tests/fixtures/nfa119 \
    tests/fixtures/ssis \
    docs/tools/nfa119.md \
    docs/tools/ssis.md \
    docs/security/dpa/dpa-ssis-welfare-v1.md \
    specs/029-phase2-adapters-119-mohw
git -C /Users/um-yunsang/KOSMOS-15 commit -m "feat(029): nfa_emergency_info_service + mohw_welfare_eligibility_search (interface-only)"
```

Never `git add .` — always by path (AGENTS.md).

---

## 7. What is intentionally NOT in this spec

- Real HTTP calls to NFA or SSIS. `handle()` raises `Layer3GateViolation` until
  Epic #16 / #20 ships the Layer 3 auth-gate.
- XML parser implementation for SSIS. Stdlib `xml.etree.ElementTree` is the
  chosen future parser (zero new deps); implementation lands with Layer 3.
- DPA template content. The placeholder stub reserves the identifier for
  validator V2 traceability; drafting happens under Epic #16 / #20.
- `nfa_safety_center_lookup` (CSV-backed nearest-station tool). Tracked in the
  spec's Deferred Items table as item #8 (NEEDS TRACKING — `/speckit-taskstoissues`
  back-fills).

If your task looks like it needs any of the above, stop and check whether your
task belongs to this spec at all — it may belong to Epic #16 / #18 / #19 / #20.
