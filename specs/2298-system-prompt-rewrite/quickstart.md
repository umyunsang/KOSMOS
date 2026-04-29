# Quickstart — Epic η #2298 Implementation Walkthrough

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)
**Audience**: Lead Opus + Sonnet teammates picking up `tasks.md` items.

---

## TL;DR

Rewrite `prompts/system_v1.md` to teach the LLM the 4 reserved primitives + 10 active verify families + citizen verify→lookup→submit chain pattern. Recompute the manifest SHA-256. Add 5 shadow-eval fixtures. Capture vhs Layer 4 + PTY Layer 2 smoke. Open the PR with `Closes #2298`.

**No source-code edits.** No new dependencies. Touch only:

- `prompts/system_v1.md` (rewrite)
- `prompts/manifest.yaml` (1-line SHA-256 update)
- `tests/fixtures/shadow_eval/citizen_chain/` (5 new JSON + 1 schema.py)
- `tests/integration/test_shadow_eval_citizen_chain_fixtures.py` (new)
- `specs/2298-system-prompt-rewrite/scripts/lint-prompt.sh` (new)
- `specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.{tape,expect}` (new)
- `specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-{pty.txt,keyframe-{1,2,3}.png,*.gif}` (captured)

---

## Step 0 — Worktree confirmation

```bash
cd /Users/um-yunsang/KOSMOS-w-2298
git status                    # On branch 2298-system-prompt-rewrite, clean
git log --oneline -3          # Spec / plan commits visible
```

If you are NOT in the worktree, set it up:

```bash
cd /Users/um-yunsang/KOSMOS && git pull --ff-only
git worktree add ../KOSMOS-w-2298 2298-system-prompt-rewrite
cd ../KOSMOS-w-2298
uv sync --quiet
uv run pytest -q --tb=no      # Baseline expected: clean
```

---

## Step 1 — Pre-flight invariant checks

Verify Epic ε infrastructure is intact before authoring the prompt:

```bash
# 10 active verify mocks register correctly
uv run pytest tests/integration/test_verify_module_dispatch.py -q

# Citizen tax-return chain happy-path passes (Mock-only)
uv run pytest tests/integration/test_e2e_citizen_taxreturn_chain.py::test_happy_chain_verify_lookup_submit -q

# 5 Epic ε families exist in PublishedTier
grep -E '"(simple_auth_module|modid|kec|geumyung_module|any_id_sso)' src/kosmos/tools/registry.py | wc -l
# Expected: 5

# 11-arm AuthContext union present
grep -A12 'AuthContext = Annotated\[' src/kosmos/primitives/verify.py | grep -cE 'Context\b'
# Expected: 11

# Current manifest SHA matches file
shasum -a 256 prompts/system_v1.md
yq '.entries[] | select(.prompt_id == "system_v1") | .sha256' prompts/manifest.yaml
# Both must match
```

If any pre-flight fails, STOP and triage — Epic η is not the right place to fix Epic ε regression.

---

## Step 2 — Author the rewritten `prompts/system_v1.md`

Follow [`contracts/system-prompt-section-grammar.md`](./contracts/system-prompt-section-grammar.md) exactly. The new file structure:

```text
<role>
  ... (line 2 unchanged) ...
</role>

<core_rules>
  ... (existing 5 sentences) ...
  - any_id_sso 예외 (FR-008 짧은 한 줄)
  - AAL 기본값: "stated purpose 를 만족하는 가장 낮은 tier" (FR-003 한 줄)
</core_rules>

<tool_usage>
  <primitives>
    - 5 callable surface tools 설명
  </primitives>

  <verify_families>
    | 10-row Markdown table |
  </verify_families>

  <verify_chain_pattern>
    Worked example: modid → hometax_simplified → hometax_taxreturn
  </verify_chain_pattern>

  <scope_grammar>
    BNF + comma-joined example
  </scope_grammar>

  ... (existing OPAQUE-forever fallback paragraph + tool_calls discipline) ...
</tool_usage>

<output_style>
  ... unchanged ...
</output_style>
```

After authoring, run the lint script:

```bash
bash specs/2298-system-prompt-rewrite/scripts/lint-prompt.sh prompts/system_v1.md
```

Expected: exit 0. The script checks all 7 invariants from `contracts/system-prompt-section-grammar.md § 5`.

---

## Step 3 — Recompute manifest SHA

```bash
NEW_SHA="$(shasum -a 256 prompts/system_v1.md | awk '{print $1}')"
echo "New SHA: $NEW_SHA"

# Patch the manifest with yq (already a project dependency? if not, fall back to sed)
yq -i ".entries |= map(if .prompt_id == \"system_v1\" then .sha256 = \"$NEW_SHA\" else . end)" prompts/manifest.yaml

# Or with sed:
# sed -i "/prompt_id: system_v1/{n;n;s/sha256: .*/sha256: $NEW_SHA/;}" prompts/manifest.yaml

# Verify
test "$(yq '.entries[] | select(.prompt_id == "system_v1") | .sha256' prompts/manifest.yaml)" = "$NEW_SHA"
```

Verify boot validation passes:

```bash
uv run python -c "from pathlib import Path; from kosmos.context.prompt_loader import PromptLoader; PromptLoader(manifest_path=Path('prompts/manifest.yaml')); print('OK')"
# Expected: OK (no PromptRegistryError)
```

---

## Step 4 — Add 5 shadow-eval fixtures

```bash
mkdir -p tests/fixtures/shadow_eval/citizen_chain
```

Author `_schema.py` (≤ 30 LOC) per [`contracts/shadow-eval-fixture-schema.md § 2`](./contracts/shadow-eval-fixture-schema.md).

Author the 5 JSON fixtures per [§ 3.1–3.5](./contracts/shadow-eval-fixture-schema.md). Verify count:

```bash
ls tests/fixtures/shadow_eval/citizen_chain/*.json | wc -l
# Expected: 5
```

Author `tests/integration/test_shadow_eval_citizen_chain_fixtures.py` per [§ 4](./contracts/shadow-eval-fixture-schema.md). Run:

```bash
uv run pytest tests/integration/test_shadow_eval_citizen_chain_fixtures.py -q
# Expected: 6 tests pass (5 parametrized + 1 count check)
```

---

## Step 5 — Capture Layer 2 PTY smoke

Author `specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.expect` per [`contracts/smoke-checkpoint-protocol.md § 1`](./contracts/smoke-checkpoint-protocol.md).

Run:

```bash
expect specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.expect \
  > specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt 2>&1

# Verify SC-002
grep -F 'CHECKPOINTreceipt token observed' \
  specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt
# Expected: exactly 1 line of output (the checkpoint)
```

If the checkpoint is missing:
1. Read the PTY log — did the LLM emit `verify`?
2. If no — the rewritten prompt is not teaching effectively. Strengthen `<verify_chain_pattern>`.
3. If yes but no receipt — the chain failed mid-flight. Check Mock adapter health (Epic ε regression).

---

## Step 6 — Capture Layer 4 vhs smoke

Author `specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.tape` per [`contracts/smoke-checkpoint-protocol.md § 2`](./contracts/smoke-checkpoint-protocol.md).

Run:

```bash
vhs specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.tape

# Verify keyframe outputs
ls specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-{1,2,3}.png
# Expected: 3 files

ls specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn.gif
# Expected: present
```

**Lead Opus visual verification step** (mandatory per AGENTS.md):

For each PNG, use the Read tool to inspect the rendered TUI:
1. Keyframe 1 — must show `KOSMOS` brand text.
2. Keyframe 2 — must show citizen Korean prompt typed in input field.
3. Keyframe 3 — must show `접수번호: hometax-2026-MM-DD-RX-XXXXX` text.

If any keyframe fails inspection, regenerate (Sleep duration may need extension).

---

## Step 7 — Pytest sweep

```bash
uv run pytest -q --tb=short
```

Expected: same pass count as `main` HEAD (no regression). The 6 new tests from Step 4 are added.

`bun test` is exempt (TUI no-change per FR-019).

---

## Step 8 — Commit + Push + PR

```bash
git add prompts/system_v1.md prompts/manifest.yaml \
        tests/fixtures/shadow_eval/citizen_chain/ \
        tests/integration/test_shadow_eval_citizen_chain_fixtures.py \
        specs/2298-system-prompt-rewrite/

git commit -m "feat(2298): rewrite system_v1 — 4-primitive vocabulary + citizen chain teaching"

git push -u origin 2298-system-prompt-rewrite

gh pr create --title "feat(2298): system prompt rewrite — infinite-spinner fix" --body "$(cat <<'EOF'
## Summary

Rewrites prompts/system_v1.md to teach the LLM the 4 reserved primitives + 10 active verify families + citizen verify→lookup→submit chain pattern. Closes the post-Epic-ε infinite spinner on OPAQUE-domain submit-class requests.

## References

- specs/2298-system-prompt-rewrite/spec.md
- specs/2298-system-prompt-rewrite/plan.md
- specs/2298-system-prompt-rewrite/research.md
- specs/2298-system-prompt-rewrite/contracts/{system-prompt-section-grammar,shadow-eval-fixture-schema,smoke-checkpoint-protocol}.md
- specs/2152-system-prompt-redesign/spec.md (XML scaffolding invariant)
- specs/2296-ax-mock-adapters/contracts/delegation-token-envelope.md (scope grammar)
- specs/1979-plugin-dx-tui-integration/delegation-flow-design.md § 12.4 (canonical citizen chain)

## Verification

- ✅ specs/2298-system-prompt-rewrite/scripts/lint-prompt.sh prompts/system_v1.md
- ✅ uv run pytest tests/integration/test_shadow_eval_citizen_chain_fixtures.py -q
- ✅ uv run pytest tests/integration/test_e2e_citizen_taxreturn_chain.py -q
- ✅ Layer 2 PTY smoke: specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt (CHECKPOINTreceipt token observed × 1)
- ✅ Layer 4 vhs smoke: specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-{1,2,3}.png + .gif (Lead Opus Read-tool verified)
- ✅ Spec 026 boot fail-closed: PromptLoader(manifest_path=...) exits 0
- ✅ shadow-eval workflow: pending CI

Closes #2298
EOF
)"

# Monitor CI
gh pr checks --watch --interval 10
```

---

## Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Forgot to recompute manifest SHA | `PromptRegistryError: digest mismatch` at boot | Re-run Step 3 |
| Authored 11-row family table including `digital_onepass` | `lint-prompt.sh` exits 1 on FR-002 negative invariant | Remove the `digital_onepass` row |
| `<verify_chain_pattern>` chain example uses non-existing tool_id | LLM emits the wrong tool_id → IPC `unknown_tool_id` error | Use `mock_lookup_module_hometax_simplified` and `mock_submit_module_hometax_taxreturn` exactly (verify via `grep -r mock_lookup_module_hometax_simplified src/kosmos/tools/`) |
| vhs Sleep too short | Keyframe 3 shows spinner | Extend Sleep at line "Sleep 12s" to 18s |
| Forgot the `any_id_sso` exception note | Shadow-eval fails for `any_id_sso.json` because LLM chains submit | Add the FR-008 sentence to `<verify_chain_pattern>` |
| Adding new top-level XML tag | XML well-formedness or section-count check fails | Spec 2152 invariant — nest inside existing tags |
| Adding new dependency | `git diff main..HEAD -- pyproject.toml tui/package.json` shows `+` | AGENTS.md hard rule — find a stdlib path |

---

## Rollback

If CI rejects the PR or shadow-eval fails:

```bash
git revert HEAD          # If the rewrite is fundamentally broken
# OR
# Iterate on prompts/system_v1.md, re-recompute manifest SHA, re-capture smoke, re-push
```

The Epic is single-file at the heart — iteration is fast.
