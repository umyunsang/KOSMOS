# Contract — `.github/workflows/plugin-validation.yml`

**Type**: GitHub Actions reusable workflow (`workflow_call`) + on-PR trigger.
**Purpose**: Enforce all 50 review-checklist items mechanically (FR-012, FR-015, FR-016).
**Trigger**: PR opened/updated touching `manifest.yaml`, `adapter.py`, `schema.py`, `tests/**`, or `README.ko.md` in any plugin repo (template + 4 examples + future contributor plugins).

## Workflow inputs (when called via `workflow_call`)

| Input | Type | Required | Default | Description |
|---|---|---|---|---|
| `kosmos-ref` | string | false | `main` | Pin the umyunsang/KOSMOS commit the validator code comes from. |
| `python-version` | string | false | `3.12` | Python version for tests. |
| `bun-version` | string | false | `1.2` | Bun version (for any TS lint steps). |

## Job: `validate`

Runs on `ubuntu-latest`. Steps execute strictly sequentially; any failure aborts the rest and posts the Korean summary comment.

### Step matrix (driven by `tests/fixtures/plugin_validation/checklist_manifest.yaml`)

```
1.  Checkout PR HEAD
2.  Setup Python 3.12 + uv
3.  Setup Bun 1.2 (only needed if TS lint enabled)
4.  Install KOSMOS validator package (uv add git+https://github.com/umyunsang/KOSMOS@<kosmos-ref>#subdirectory=src/kosmos/plugins)
5.  Load checklist manifest from KOSMOS repo
    (tests/fixtures/plugin_validation/checklist_manifest.yaml — 50 items)
6.  For each item in manifest, run check_implementation:
    - check_type=static  → AST/regex check via Python helper
    - check_type=unit    → pytest selection of dotted-path test
    - check_type=workflow → run a workflow-step shell command
    Collect (item_id, status, message_ko, message_en) tuples.
7.  Sandbox enforcement (FR-016):
    - All checks run inside a network-blocked container (--network=none)
      to guarantee no live data.go.kr egress.
    - pytest fixtures get block_network autouse=True.
8.  Emit summary comment on PR:
    "✓ N/50 통과 · ✗ M/50 실패 — 실패 항목: [Q1-PYV2: ..., Q3-V2-DPA: ...]"
    Korean by default; English mirror underneath.
9.  Set check status:
    - N == 50 → success (green)
    - N < 50  → failure (red), block merge
```

## Output: PR comment shape

```markdown
## KOSMOS plugin-validation — 검증 결과 (commit `<sha>`)

**✓ 47 / 50 통과**
**✗ 3 / 50 실패**

### 실패 항목 (수정 필요)

| ID | 한국어 | English | 수정 가이드 |
|---|---|---|---|
| Q1-NOANY | `Any` 타입 금지 | No `Any` types | `schema.py:42` 의 `Any` 를 명시적 타입으로 교체 |
| Q3-V2-DPA | V2 dpa_reference non-null when pipa_class != non_personal | dpa_reference required for non-public PIPA classes | `manifest.yaml` 의 `dpa_reference` 비어 있음 |
| Q6-PIPA-HASH | acknowledgment_sha256 == canonical SHA-256 | Acknowledgment hash mismatch | `docs/plugins/security-review.md` 의 canonical 텍스트 다시 읽고 SHA-256 갱신 |

### 통과 항목

48 of 50 items passed (Q1-PYV2, Q1-FIELD-DESC, Q1-INPUT-MODEL, Q1-OUTPUT-MODEL, Q1-MANIFEST-VALID, ...).

상세 로그: <link to GHA run>
참조: `docs/plugins/review-checklist.md`
```

## SLA / runtime budget (Plan Performance Goals)

- End-to-end < 5 minutes per PR.
- Phase breakdown (target):
  - Setup (steps 1–4): ≤ 90 s
  - Static checks (step 6 / `static`): ≤ 30 s
  - Unit checks (step 6 / `unit`): ≤ 120 s
  - Workflow checks (step 6 / `workflow`): ≤ 30 s
  - Comment + status (steps 8–9): ≤ 10 s

## Self-test obligation (SC-006)

Every example plugin's repo MUST run this workflow against itself in CI. The `kosmos-plugin-template` repo has a meta-test that scaffolds a fresh plugin via `kosmos plugin init demo` and runs the workflow against it; expects 50/50 pass. This is CI-gated on every PR to the template.

## Negative-path matrix (verifies FR-015)

The validator's own test suite (in this repo, `src/kosmos/plugins/tests/test_validation_workflow.py`) drives the workflow with synthetic manifests:

| Synthetic input | Expected outcome |
|---|---|
| 50/50 valid manifest | success, comment shows ✓ 50/50 |
| Manifest missing description on one Field | failure on Q1-FIELD-DESC |
| Manifest with `Any` in schema | failure on Q1-NOANY |
| `tier=mock` without `mock_source_spec` | failure on Q7-MOCK-SOURCE |
| `processes_pii=True` without acknowledgment | failure on Q6-PIPA-PRESENT |
| Acknowledgment with wrong hash | failure on Q6-PIPA-HASH |
| `tool_id` not namespaced | failure on Q8-NAMESPACE |
| `tool_id` overriding root primitive (`lookup`) | failure on Q8-NO-ROOT-OVERRIDE |
| `otel_attributes` missing `kosmos.plugin.id` | failure on Q9-OTEL-ATTR |

≥ 5 negative cases per SC-003.

## Drift prevention

The workflow file itself (`.github/workflows/plugin-validation.yml`) MUST NOT contain hand-coded check logic. All check semantics live in:
1. `tests/fixtures/plugin_validation/checklist_manifest.yaml` (the 50 rows)
2. `src/kosmos/plugins/checks/q*_*.py` (one helper per item)
3. `docs/plugins/review-checklist.md` (the human-readable rendering)

A meta-CI step verifies the YAML row count is exactly 50 and that every `check_implementation` reference resolves to an existing function. Drift between Markdown / YAML / Python is caught at this step.
