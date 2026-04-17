# Implementation Plan: Safety Rails — PII Redaction, Guardrails, Indirect Injection Defense

**Branch**: `feat/466-safety-rails` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: `/Users/um-yunsang/KOSMOS-466/specs/026-safety-rails/spec.md`
**Epic**: [#466 — Safety Rails](https://github.com/umyunsang/KOSMOS/issues/466)

---

## Summary

Ship a four-layer safety pipeline around the existing Tool System and LLM Client
(Claude Code harness analogue) without touching authz semantics or span transport:

- **Layer A** — PII redactor on LLM-ingress path, backed by a shared `_patterns.py`
  module lifted out of `step3_params.py` (single source of truth; Luhn upgrade
  for credit-card recognition).
- **Layer B** — LiteLLM pre/post-call callbacks dispatching to OpenAI Moderation API
  (primary guardrail; Apache-2.0 compatible; Llama Guard 3 explicitly deferred).
- **Layer C** — Indirect prompt-injection detector in `tools/executor.py` run *before*
  redaction, short-circuiting via `LookupError(reason=injection_detected)`.
- **Layer D** — Trust-hierarchy block inserted between Sections 3 and 4 of the system
  prompt; Section 5 (session guidance) remains strictly last for NFR-003 cache
  prefix stability.

Cross-Epic boundary: enum extension → PR-A (`Refs #507`); env registry → follow-up
on #468; LiteLLM config → follow-up on #465; span transport → unchanged (only a
new bounded attribute key on existing spans for #501).

---

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline — no version bump).

**Primary Dependencies** (new):

- `presidio-analyzer` (MIT) — PatternRecognizer-only deployment, spaCy NLP backend bypassed via a custom `NlpEngineProvider` that returns an empty recognizer set. Confirmed viable by Presidio docs (Analyzer supports running without an NLP engine when only pattern recognizers are configured).
- `openai` (Apache-2.0) — **confirmed absent** from `pyproject.toml` as of this plan (verified via `grep "openai" pyproject.toml` returned nothing matching the literal package name). Adding it is part of PR-B, consistent with AGENTS.md § Hard rules (dependency additions in spec-driven PRs only). Alternative rejected: hand-rolled `httpx` POST to `/v1/moderations` — rejected because moderation response shape is versioned by OpenAI and the SDK pins that for us.

**Primary Dependencies** (existing, exercised by this spec):

- `httpx >=0.27` — already used by `llm/client.py` and all tool adapters.
- `pydantic >=2.13` — all new models use `ConfigDict(frozen=True, strict=True)`.
- `pydantic-settings >=2.13` — `SafetySettings` follows the same idiom as `TracingSettings` already in `settings.py`.
- `opentelemetry-sdk`, `opentelemetry-semantic-conventions` — span attribute emission only; no new instrumentation surface.
- `pytest`, `pytest-asyncio`, `respx` — the 10+10+5+5 fixture set is implemented as unit tests with `respx`-mocked OpenAI Moderation calls for Layer B.

**Storage**: N/A — redaction, detection, and moderation are stateless. `SafetySettings` lives in process memory only (pydantic-settings loads from env at startup).

**Testing**:

- Unit tests: `tests/safety/test_redactor.py`, `test_injection.py`, `test_litellm_callbacks.py`, `test_patterns.py`, `test_system_prompt_trust_hierarchy.py`.
- Integration tests: `tests/safety/test_executor_wiring.py` exercises the full `detector → redactor → normalizer` chain through `ToolExecutor.invoke()` with a recorded fixture adapter.
- Regression tests: the existing Step 3 test suite `tests/permissions/test_step3_params.py` MUST pass byte-unchanged (FR-002 acceptance gate).
- No `@pytest.mark.live` markers added — moderation tests mock the OpenAI endpoint; CI never calls live.

**Target Platform**: Linux server (CI) and developer laptops (macOS/Linux). No platform-specific code.

**Project Type**: Single library (KOSMOS backend). TUI (`kosmos-ink`) is not touched by this spec — safety decisions surface via existing envelope + span channels.

**Performance Goals**:

- Redaction latency: p95 < 50 ms for tool outputs up to 100 KB. Presidio pattern-matching is O(n) in output size.
- Injection detector latency: p95 < 10 ms for tool outputs up to 100 KB (regex + entropy, no model invocation).
- OpenAI Moderation round-trip: subject to network — spec sets fail-open on outage (FR-011), no local SLO bound.
- System prompt assembly: unchanged — the trust-hierarchy block is a constant string; no regression in NFR-003 (SC-006 verifies).

**Constraints**:

- **Apache-2.0 purity**: no Llama Guard 3 in MVP. OpenAI Moderation only.
- **No hardcoding (3x rule)**: no static keyword blocklist, no static salvage regex, no hand-rolled PII tokenizer. Presidio `PatternRecognizer` + `_patterns.py` is the only pattern surface.
- **Pydantic v2 strict**: all new models use `ConfigDict(frozen=True, strict=True)`; no `Any`.
- **FriendliAI cache stability (NFR-003)**: Section 5 stays last. Trust-hierarchy sits between 3 and 4.
- **Defense-in-depth preserved**: commit 50e2c17's per-file redactions remain in place; `_redactor.py` is a layer on top.
- **Zero raw data in spans**: only bounded-enum `gen_ai.safety.event` values leave the process.

**Scale/Scope**: MVP-scale — student portfolio, single-node deployment expected. No horizontal-scale concerns for safety components (all stateless).

---

## Constitution Check

*GATE: Must pass before Phase 0. Re-check after Phase 1 design.*

Verified against `.specify/memory/constitution.md` v1.1.0:

| Principle | Status | Evidence |
|---|---|---|
| I. Reference-Driven Development | ✅ PASS | Every design decision below maps to a concrete reference. See "Phase 0 — Reference Mapping" section. |
| II. Fail-Closed Security | ✅ PASS | Redactor on by default; detector on by default; moderation off by default only because #465 proxy wiring is upstream-dependent. Missing `KOSMOS_OPENAI_MODERATION_API_KEY` with moderation enabled fails closed at startup (FR-022). |
| III. Pydantic v2 Strict Typing | ✅ PASS | All 5 Key Entities (RedactionResult, SafetyEvent, SafetyDecision, InjectionSignalSet, SafetySettings) are strict, frozen, discriminated where applicable. No `Any` introduced. |
| IV. Government API Compliance | ✅ PASS | No adapter changes. `@pytest.mark.live` not added — moderation tests mock via `respx`. |
| V. Policy Alignment | ✅ PASS | PIPA §26(4) processor-role honored (tool outputs redacted before LLM synthesis, where controller-level responsibility engages); AI Action Plan 원칙8 (single conversational window) preserved by keeping the harness shape unchanged. |
| VI. Deferred Work Accountability | ✅ PASS | 6 deferred items in spec.md, each with Target Epic + tracking marker. `/speckit-taskstoissues` will back-fill issue numbers. |

**Gate result**: PASS. Proceed to Phase 0.

---

## Phase 0 — Reference Mapping (mandatory per Constitution § I)

Each design decision below is anchored to at least one reference from
`docs/vision.md § Reference materials` or an external authority cited in the spec.

| Decision | Primary Reference | Secondary Reference | Why this reference |
|---|---|---|---|
| Four-layer safety pipeline (ingress redactor → detector → moderation → trust hierarchy) | **OpenAI Agents SDK** (guardrail pipeline) | **Claude Agent SDK** (permission types) | OpenAI Agents SDK's guardrail abstraction is the cleanest open-source precedent for composable safety stages; we adapt but do not copy line-for-line. |
| Redactor position in `tools/executor.py` (between raw output and `normalize()`) | **Claude Code reconstructed sourcemap** (tool loop internals) | **Pydantic AI** (schema-driven registry) | The tool loop's natural boundary for payload sanitization is post-adapter, pre-normalization — matches Claude Code's envelope-assembly hook point. |
| Detector runs *before* redactor (ordering: detector → redactor → normalizer) | **OWASP LLM Top 10 2025 — LLM01** (Prompt Injection) | **Simon Willison "lethal trifecta" essay** | Blocking the untrusted-input leg must happen before any payload transformation so the detector operates on the attacker's byte sequence; Willison's trifecta frames this as "untrusted input + access + exfiltration" with untrusted input as the kill-switch. |
| PII pattern library = Presidio `PatternRecognizer` with regexes from `_patterns.py` | **Microsoft Presidio docs** (MIT) | **Constitution § III** (Pydantic v2 strict) | Presidio is the most widely-audited MIT-licensed PII framework; pattern-only mode satisfies the 3x no-hardcoding rule without introducing a spaCy dependency. |
| Luhn checksum (ISO/IEC 7812) for credit-card recognizer | **ISO/IEC 7812** standard | Presidio's own credit-card recognizer | Luhn is the industry checksum; upgrade over `step3_params.py`'s unvalidated 16-digit regex eliminates false positives on order numbers, case numbers, and long identifiers. |
| OpenAI Moderation as sole moderation provider | **OpenAI Moderation API docs** | **LICENSE** (Apache-2.0) | Network API carries no local-license obligation; the only tractable Apache-2.0-compatible path for MVP. |
| Llama Guard 3 deferral | **Llama 3.2 Community License** §5(c), attribution clause | **LICENSE** (Apache-2.0) | Incompatibility is fact of license text, not preference. Option B in spec § Dependency License Posture documents the post-MVP ADR path. |
| Injection detector: structural + entropy + length (no static keyword list) | **arXiv 2504.11168** (Hackett et al., 2025-04-15) | **AGENTS.md § No hardcoding** | The paper documents 100% evasion rates against static-keyword classifiers (Azure Prompt Shield, Meta Prompt Guard); multi-signal scoring is the literature-supported mitigation. |
| `LookupError(reason=injection_detected)` as refusal envelope | **Claude Agent SDK** (permission types) | **Existing `LookupErrorReason` enum in `errors.py`** | The existing refusal channel already flows through the LLM context correctly; extending the enum is the smallest change that compose with every adapter without a branching surface. |
| Trust-hierarchy block between Sections 3 and 4 of system prompt | **Claude Code sourcemap — context assembly** | **NFR-003 FriendliAI cache stability** | Section 5 (session guidance) was deliberately placed last to protect the FriendliAI prompt-cache prefix; inserting before it preserves that property. |
| Moderation callbacks via LiteLLM pre/post hooks | **LiteLLM docs** (callback contract) | Epic **#465** (proxy + budget) | LiteLLM's callback slot is the sanctioned extension point; calling it directly from our code avoids forking LiteLLM. |
| Single span attribute `gen_ai.safety.event` | **OpenTelemetry GenAI semantic conventions** (experimental v1.40) | Epic **#501** (OTLP collector policy) | Minimal footprint on #501's schema; bounded enum value avoids any raw-payload leak through span export. |
| PIPA §26(4) carve-out for LLM synthesis step | **개인정보 보호법 §23, §26** | **MEMORY.md — project_pipa_role.md** | KOSMOS's default posture is processor (수탁자); the LLM synthesis step is the only carve-out where controller-level obligations engage, which is precisely where the redactor sits. |
| AI Action Plan 원칙8/9 alignment | **대한민국 AI 행동계획 2026–2028** | **MEMORY.md — reference_ai_action_plan.md** | 원칙8 mandates single-conversational-window for cross-ministry citizen services; safety that breaks the conversational surface would regress the mission. |

All 14 design decisions traceable. No gap flagged.

---

## Project Structure

### Documentation (this feature)

```text
specs/026-safety-rails/
├── spec.md                 # Feature spec (already written)
├── plan.md                 # This file (/speckit-plan output)
├── tasks.md                # Phase 2 output (/speckit-tasks, NOT created by plan)
├── checklists/
│   └── requirements.md     # Spec quality checklist (already written, PASS)
└── contracts/              # Phase 1 output below — see "Phase 1 Artifacts"
    ├── SafetyEvent.schema.md
    ├── RedactionResult.schema.md
    ├── SafetyDecision.schema.md
    ├── InjectionSignalSet.schema.md
    └── SafetySettings.schema.md
```

### Source Code (repository root)

```text
src/kosmos/
├── safety/                              # NEW package
│   ├── __init__.py                      # public re-exports (RedactionResult, SafetyEvent, run_redactor, run_detector)
│   ├── _patterns.py                     # NEW — canonical _PII_PATTERNS + PII_ACCEPTING_PARAMS (lifted from step3_params.py)
│   ├── _redactor.py                     # NEW — Presidio PatternRecognizer wrapper + Luhn validator
│   ├── _injection.py                    # NEW — structural + entropy detector
│   ├── _litellm_callbacks.py            # NEW — pre_call / post_call hook functions
│   ├── _models.py                       # NEW — RedactionResult, SafetyEvent (discriminated union), SafetyDecision, InjectionSignalSet
│   ├── _settings.py                     # NEW — pydantic-settings SafetySettings (4 KOSMOS_SAFETY_* env vars)
│   └── _span.py                         # NEW — emit_safety_event(kind, ...) helper that writes gen_ai.safety.event
├── permissions/
│   └── steps/
│       └── step3_params.py              # MODIFIED — replace local _PII_PATTERNS + PII_ACCEPTING_PARAMS with imports from kosmos.safety._patterns
├── tools/
│   ├── errors.py                        # MODIFIED (PR-A) — extend LookupErrorReason with content_blocked + injection_detected
│   └── executor.py                      # MODIFIED (PR-B) — wire detector → redactor before normalize() at invoke() ~L222 and dispatch() ~L394
├── context/
│   └── system_prompt.py                 # MODIFIED — insert trust-hierarchy section between _tool_use_policy_section and _personal_data_reminder_section
└── settings.py                          # MODIFIED — include SafetySettings() in the top-level Settings aggregate

tests/
├── safety/                              # NEW test package
│   ├── test_patterns.py                 # SoT verification: _PII_PATTERNS defined only in _patterns.py
│   ├── test_redactor.py                 # 10 PII fixtures (incl. Luhn-valid/invalid card pair)
│   ├── test_injection.py                # 10 indirect-injection fixtures (arXiv 2504.11168 taxonomy)
│   ├── test_litellm_callbacks.py        # 5 block + 5 pass moderation fixtures (OpenAI Moderation mocked via respx)
│   ├── test_executor_wiring.py          # end-to-end detector → redactor → normalize() through ToolExecutor.invoke()
│   ├── test_system_prompt_trust_hierarchy.py  # cache-prefix stability (SC-006) + section ordering
│   └── test_settings.py                 # SafetySettings defaults + fail-closed on missing moderation key
├── permissions/
│   └── test_step3_params.py             # UNCHANGED — regression gate for FR-002
└── fixtures/
    └── safety/                          # NEW fixtures for the 30-sample plan
        ├── pii_samples.json
        ├── injection_samples.json
        ├── moderation_block_samples.json
        ├── moderation_pass_samples.json
        └── recorded_tool_outputs/       # 500-turn corpus for SC-004 false-positive measurement (sampled from existing tests/fixtures/)

docs/
└── security/
    └── safety-rails-v1.md               # NEW — user-facing overview linked from spec.md (light, non-normative; the spec is normative)

# UNCHANGED (explicitly NOT modified by this epic):
#   docs/configuration.md                ← owned by #468
#   infra/litellm/config.yaml            ← owned by #465
#   LICENSE, NOTICE                      ← Apache-2.0 purity preserved
```

**Structure Decision**: Single library extension. New `kosmos.safety` subpackage isolates the four-layer pipeline; three existing modules (`errors.py`, `executor.py`, `system_prompt.py`) receive small surgical edits; one module (`step3_params.py`) drops literals in favor of imports. This matches KOSMOS's existing subpackage layout (`kosmos.permissions`, `kosmos.observability`, `kosmos.security`) — safety is the next sibling.

---

## Phase 1 Artifacts

### Data Model (inline summary — full schemas live in `contracts/`)

```python
# kosmos.safety._models

class RedactionResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    original_length: int
    redacted_length: int
    matches: tuple[RedactionMatch, ...]   # each: category, start, end (no raw value)
    redacted_text: str                     # used by executor to replace raw output

class RedactionMatch(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    category: Literal["rrn","phone_kr","email","passport_kr","credit_card"]
    start: int
    end: int

# Discriminated union on `kind`
class RedactedEvent(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    kind: Literal["redacted"] = "redacted"
    match_count: int

class InjectionBlockedEvent(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    kind: Literal["injection_blocked"] = "injection_blocked"
    signal_summary: InjectionSignalSet

class ModerationBlockedEvent(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    kind: Literal["moderation_blocked"] = "moderation_blocked"
    categories: tuple[str, ...]            # OpenAI's bounded taxonomy labels only

class ModerationWarnedEvent(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    kind: Literal["moderation_warned"] = "moderation_warned"
    detail: Literal["outage","partial_error"]

SafetyEvent = Annotated[
    RedactedEvent | InjectionBlockedEvent | ModerationBlockedEvent | ModerationWarnedEvent,
    Field(discriminator="kind"),
]

class SafetyDecision(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    flagged: bool
    categories: tuple[str, ...]
    decision: Literal["allow","block","warn"]

class InjectionSignalSet(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    structural_score: float          # 0..1 role-override / system-prompt heuristic
    entropy_score: float             # 0..1 base64/hex density heuristic
    length_deviation: float          # abs(log(len(output)/expected_len))
    decision: Literal["allow","block"]

class SafetySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KOSMOS_SAFETY_", frozen=True)
    redact_tool_output: bool = True
    injection_detector_enabled: bool = True
    moderation_enabled: bool = False                              # gated on #465
    # OPENAI key does NOT follow the KOSMOS_SAFETY_ prefix; use explicit field.
    openai_moderation_api_key: SecretStr | None = Field(default=None, alias="KOSMOS_OPENAI_MODERATION_API_KEY")
```

Full JSON Schemas go in `specs/026-safety-rails/contracts/*.schema.md` during implementation; the spec + plan fix the semantics so the schemas are mechanical.

### Quickstart (what a developer does to try this locally)

```bash
# 1. Install new deps
uv add presidio-analyzer openai

# 2. Env setup (temporary — real registry is #468's job)
export KOSMOS_SAFETY_REDACT_TOOL_OUTPUT=true
export KOSMOS_SAFETY_INJECTION_DETECTOR_ENABLED=true
export KOSMOS_SAFETY_MODERATION_ENABLED=false   # default; set true only after #465 lands

# 3. Run the safety test suite only
uv run pytest tests/safety/ -q

# 4. Run the full suite to verify no regression
uv run pytest -q
```

### Contracts (Phase 1 — NOT created by plan, but enumerated)

The five `contracts/*.schema.md` files produced at Phase 1 time match the Key
Entities. Each file contains: JSON Schema draft 2020-12, a Pydantic class
signature, and one positive + one negative validation example. Mechanical work
once spec + plan are merged.

---

## Agent / Task Breakdown Preview

(Produced by `/speckit-tasks`; summarized here for Plan completeness.)

**PR-A — `feat(safety): extend LookupErrorReason with content_blocked and injection_detected (Refs #507)`**

- T01 Extend `LookupErrorReason` enum in `src/kosmos/tools/errors.py` with `content_blocked`, `injection_detected`.
- T02 Add envelope-normalization tests covering the two new reasons (round-trip serialization).
- T03 Update any docstrings in `errors.py` that enumerate reasons.

**PR-B — `feat(safety): PII redaction + OpenAI Moderation + indirect-injection defense (Closes #466)`**

Layer A:

- T04 Create `kosmos/safety/_patterns.py` lifting `_PII_PATTERNS` + `PII_ACCEPTING_PARAMS` from `step3_params.py`.
- T05 Refactor `step3_params.py` to import from `_patterns.py`. Step 3 regression test MUST pass unchanged.
- T06 Create `kosmos/safety/_models.py` (RedactionResult, RedactionMatch, SafetyEvent union, SafetyDecision, InjectionSignalSet).
- T07 Create `kosmos/safety/_redactor.py` (Presidio PatternRecognizer + Luhn validator + `run_redactor()` API).
- T08 Write `tests/safety/test_redactor.py` — 10 PII fixtures incl. Luhn-valid/invalid pair.
- T09 Write `tests/safety/test_patterns.py` — SoT check (`_PII_PATTERNS` defined exactly once).

Layer B:

- T10 Create `kosmos/safety/_settings.py` (SafetySettings).
- T11 Create `kosmos/safety/_litellm_callbacks.py` (pre_call, post_call, 1393/1366 Korean hotlines in refusal).
- T12 Write `tests/safety/test_litellm_callbacks.py` — 5 block + 5 pass fixtures (OpenAI Moderation mocked via respx).
- T13 Write `tests/safety/test_settings.py` — defaults + fail-closed on missing moderation key when moderation enabled.

Layer C:

- T14 Create `kosmos/safety/_injection.py` (structural + entropy + length-deviation detector, `run_detector()`).
- T15 Write `tests/safety/test_injection.py` — 10 arXiv 2504.11168 fixtures.

Layer D:

- T16 Modify `src/kosmos/context/system_prompt.py` — insert `_trust_hierarchy_section()` between sections 3 and 4; Section 5 stays last.
- T17 Write `tests/safety/test_system_prompt_trust_hierarchy.py` — section ordering + cache-prefix stability (SC-006).

Wiring & Observability:

- T18 Wire detector → redactor in `src/kosmos/tools/executor.py` `invoke()` (~L222) and `dispatch()` (~L394) before `normalize()`.
- T19 Create `kosmos/safety/_span.py` (`emit_safety_event(kind, ...)` helper) and emit `gen_ai.safety.event` on every decision.
- T20 Write `tests/safety/test_executor_wiring.py` — end-to-end through ToolExecutor.invoke().

Dependencies & Docs:

- T21 Add `presidio-analyzer` and `openai` to `pyproject.toml` dependencies. Run `uv lock`.
- T22 Create `docs/security/safety-rails-v1.md` (non-normative overview linking back to spec.md).

Follow-up (NOT in this PR — comments on upstream Epics):

- T23 File follow-up comment on #465 describing the LiteLLM callback entrypoint.
- T24 File follow-up comment on #468 listing the four `KOSMOS_SAFETY_*` + one `KOSMOS_OPENAI_MODERATION_API_KEY` env keys.
- T25 File follow-up comment on #501 listing `gen_ai.safety.event` and its bounded enum values.

**Parallelism**: Layer A, B, C tasks are largely independent until wiring (T18). Agent Teams can take `Backend Architect` on A, `Security Engineer` on B, `API Tester` on C in parallel.

---

## Complexity Tracking

> Filled only if Constitution Check has violations to justify.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| (none) | — | — |

All principles satisfied without justified deviations. No complexity deficit to track.

---

## Re-check Gate (post-Phase 1)

After Phase 1 artifact creation (the five `contracts/*.schema.md` files during
implementation), run the Constitution Check a second time. If the schemas
introduce any `Any` fields, un-frozen models, or unbounded enum variants, STOP
and revise — do not proceed to `/speckit-tasks` issue creation.

---

## References

- Spec: [`spec.md`](./spec.md)
- Checklist: [`checklists/requirements.md`](./checklists/requirements.md)
- Constitution: `.specify/memory/constitution.md` v1.1.0
- Vision: `docs/vision.md` § Reference materials, § Permission pipeline, § Context assembly
- Prior security specs: `specs/024-tool-security-v1/`, `specs/025-tool-security-v6/`
- External: OWASP LLM Top 10 (2025) LLM01/LLM02; Microsoft Presidio Analyzer docs (MIT); OpenAI Moderation API docs; arXiv 2504.11168; Simon Willison "lethal trifecta" essay; ISO/IEC 7812.
- Korean legal: 주민등록법 시행령 제2조 별표 1; 전기통신번호관리세칙; 여권법 시행령 제7조; 개인정보 보호법 §23, §26.
- AI Action Plan: 대한민국 AI 행동계획 2026–2028 원칙8/9.
