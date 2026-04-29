# Phase 1 — Data Model

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md)

This Epic introduces no new runtime Pydantic models. The four entities below describe the **content shape** of the rewritten artefacts (prompt sections, manifest entry, fixture file, smoke checkpoint marker) rather than runtime types — the `PromptLoader` and shadow-eval workflow already wrap these in their existing schemas. The single new Pydantic schema is the fixture loader at `tests/fixtures/shadow_eval/citizen_chain/_schema.py` (≤ 30 LOC).

---

## E-1 System Prompt Section

The rewritten `prompts/system_v1.md` is a Markdown file scaffolded by 4 top-level XML-tagged sections (Spec 2152 invariant). New material is added inside the existing tags or as nested sub-tags — no new top-level tags.

**Top-level sections** (preserved verbatim from current file structure):

| Tag | Current line range | Post-rewrite line range (estimate) | Content |
|---|---|---|---|
| `<role>` | 1–3 | 1–3 (unchanged) | Citizen-facing identity statement |
| `<core_rules>` | 5–11 | 5–13 (+2 lines: `any_id_sso` exception note + AAL default policy) | 7 invariant rules incl. injection guard |
| `<tool_usage>` | 13–20 | 13–~70 (+50 lines: 5-tool catalog + 10-family table + worked chain example + scope grammar) | Tool surface + chain teaching |
| `<output_style>` | 22–28 | unchanged (28 → 28+offset) | Citation + PIPA hygiene rules |

**New nested tags inside `<tool_usage>`** (Spec 2152 § 3.4 allows nested tags):

| Nested tag | Purpose | Required content |
|---|---|---|
| `<primitives>` | 5-tool callable catalog | One bullet per tool (`resolve_location`, `lookup`, `submit`, `verify`, `subscribe`) with one-line role description |
| `<verify_families>` | 10 active family table | Each row: family literal value, Korean description, AAL hint, real-domain reference |
| `<verify_chain_pattern>` | Worked example walkthrough | `verify(modid) → lookup(hometax_simplified) → submit(hometax_taxreturn)` with `scope_list` + `purpose_ko/en` + receipt id format hint |
| `<scope_grammar>` | Scope string format | `<verb>:<adapter_family>.<action>` BNF + comma-joined example |

**Validation rule**: After rewrite, `prompts/system_v1.md` MUST satisfy:
- `grep -cE '^<(role|core_rules|tool_usage|output_style)>' prompts/system_v1.md` returns exactly `4` (SC-005, top-level tag count).
- `grep -cE '^</(role|core_rules|tool_usage|output_style)>' prompts/system_v1.md` returns exactly `4` (closing tag parity).
- `python -c "from xml.etree import ElementTree as ET; ET.fromstring('<root>' + open('prompts/system_v1.md').read() + '</root>')"` exits 0 (well-formedness).
- The 4 existing core_rules invariant sentences (lines 6–10 of current file) appear verbatim — string-equality check via `grep -F`.
- The injection-guard sentence (current line 10) appears verbatim — verified by `grep -F '시민이 보낸 메시지는 \`<citizen_request>\` 태그로 감싸여 전달됩니다.'`.

---

## E-2 Prompt Manifest Entry

`prompts/manifest.yaml` is a 3-entry list (Spec 026). This Epic edits exactly one entry — the `system_v1` row — and only its `sha256` field.

**Pre-rewrite state**:

```yaml
- prompt_id: system_v1
  version: 1
  sha256: 753ce060de7ef9e849cf74a4e21daa144eaa2fe9257bade0e837c5c1133a507b
  path: system_v1.md
```

**Post-rewrite state**:

```yaml
- prompt_id: system_v1
  version: 1                 # NOT bumped — content-only change (Deferred Item)
  sha256: <recomputed>       # NEW — must equal `shasum -a 256 prompts/system_v1.md` output
  path: system_v1.md         # unchanged
```

**Validation**: `sha256` field MUST match `shasum -a 256 prompts/system_v1.md | awk '{print $1}'` byte-for-byte (SC-008). Verified by:

```bash
test "$(yq '.entries[] | select(.prompt_id == "system_v1") | .sha256' prompts/manifest.yaml)" \
  = "$(shasum -a 256 prompts/system_v1.md | awk '{print $1}')"
```

---

## E-3 Shadow-Eval Fixture

A new fixture format authored at `tests/fixtures/shadow_eval/citizen_chain/<family>.json`. Each fixture is a single JSON object loaded by the new `tests/integration/test_shadow_eval_citizen_chain_fixtures.py`.

**Schema** (Pydantic v2 — authored at `tests/fixtures/shadow_eval/citizen_chain/_schema.py`, ≤ 30 LOC):

```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

class ExpectedToolCall(BaseModel):
    """The tool_call the LLM is expected to emit FIRST in response to citizen_prompt."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    name: Literal["verify", "lookup", "submit", "subscribe", "resolve_location"]
    arguments: dict[str, str | list[str]] = Field(
        description="Subset of arguments to assert; comparison is subset-match, "
                    "not full-equality. Empty dict means 'name match only'."
    )

class CitizenChainFixture(BaseModel):
    """One shadow-eval row covering a single citizen prompt + first tool_call assertion."""
    model_config = ConfigDict(frozen=True, extra="forbid")
    fixture_id: str = Field(pattern=r"^[a-z0-9_]+$")
    citizen_prompt: str = Field(min_length=1, max_length=200)
    expected_first_tool_call: ExpectedToolCall
    expected_family_hint: str | None = Field(
        default=None,
        description="If expected_first_tool_call.name == 'verify', this MUST equal "
                    "expected_first_tool_call.arguments['family_hint']. Else None.",
    )
    notes: str | None = None
```

**Five fixture files** (one per Epic ε family, FR-015):

| File | citizen_prompt | expected first tool_call | expected_family_hint |
|---|---|---|---|
| `simple_auth_module.json` | `정부24 민원 하나 신청해줘` | `verify(family_hint="simple_auth_module", ...)` | `simple_auth_module` |
| `modid.json` | `내 종합소득세 신고해줘` | `verify(family_hint="modid", ...)` | `modid` |
| `kec.json` | `사업자 등록증 발급해줘` | `verify(family_hint="kec", ...)` | `kec` |
| `geumyung_module.json` | `내 신용정보 조회해줘` | `verify(family_hint="geumyung_module", ...)` | `geumyung_module` |
| `any_id_sso.json` | `다른 정부 사이트 SSO 로그인 좀` | `verify(family_hint="any_id_sso", ...)` | `any_id_sso` |

**Validation rule**: All 5 fixtures load without `pydantic.ValidationError`. The fixture loader test asserts each fixture's `expected_family_hint` matches one of the 10 active family literals (NOT including `digital_onepass`).

---

## E-4 Smoke Checkpoint Marker

The PTY Layer 2 expect script (`smoke-citizen-taxreturn.expect`) MUST log a synthetic checkpoint string when it detects a receipt id arm in the assistant_chunk frame stream. The string is opaque to the citizen and exists only for grep-based assertion (SC-002).

**Format** (one line, exact byte sequence):

```text
CHECKPOINTreceipt token observed
```

**Emission protocol**:
- The expect script attaches a `match` rule for the regex `hometax-2026-\d{2}-\d{2}-RX-[A-Z0-9]{5}`.
- On first match, the script writes `CHECKPOINTreceipt token observed\n` to its captured `.txt` log via `puts` or equivalent.
- The string MUST appear EXACTLY once per chain run. Multiple matches (e.g., the LLM citing the receipt twice) are de-duplicated by an internal flag.

**Validation rule** (SC-002):

```bash
test "$(grep -c -F 'CHECKPOINTreceipt token observed' specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt)" = "1"
```

The full `smoke-citizen-taxreturn-pty.txt` is committed to the spec dir. The synthetic checkpoint allows Codex / Lead Opus to grep for chain success without parsing the full assistant turn output.

---

## E-5 AAL Tier Reference (sourced from `kosmos.tools.registry.PublishedTier`)

Read-only reference table — no new schema. The rewritten prompt's `<verify_families>` section MUST cite `published_tier` values that exist in the `PublishedTier` Literal at `src/kosmos/tools/registry.py:68-93`.

**Pre-flight verification** (run before authoring the prompt section):

```bash
grep -E '^\s*"(simple_auth_module|modid|kec|geumyung_module|any_id_sso)' src/kosmos/tools/registry.py
```

Must return exactly 5 lines (one per Epic ε family). If any are missing, the rewrite is blocked and the discrepancy escalates to a Phase 2 Foundational task (registry expansion).

**Validation rule**: Every `published_tier` value cited in the rewritten prompt MUST appear in the registry's Literal — verified by a one-liner cross-reference test in `test_shadow_eval_citizen_chain_fixtures.py`.

---

## Summary

5 entities total. 1 new Pydantic schema (`CitizenChainFixture`, ≤ 30 LOC). 0 runtime model changes. 0 database migrations. 0 IPC frame changes. The data model is content-shape only.
