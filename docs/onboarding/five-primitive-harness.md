# Onboarding: Five-Primitive Harness

KOSMOS replaced an earlier eight-verb surface (`pay`, `issue_certificate`, `submit_application`, `reserve_slot`, `subscribe_alert`, `check_eligibility`, and two others) with five canonical primitives: `lookup`, `resolve_location`, `submit`, `subscribe`, and `verify`. The change mirrors how Claude Code distilled developer work to roughly five always-loaded verbs — not by copying Claude Code's exact verb names, but by applying the same empirical discovery method to citizen-government interaction. Domain specialisation now lives entirely in adapter modules (`src/kosmos/tools/<ministry>/<adapter>.py`), keeping the main LLM-visible surface ministry-agnostic. The rationale and six-layer architecture that motivates this design are in [`docs/vision.md`](../vision.md).

---

## Hands-on start

The single source for step-by-step commands, environment setup, and smoke tests is:

**[`specs/031-five-primitive-harness/quickstart.md`](../../specs/031-five-primitive-harness/quickstart.md)**

Do not replicate those steps here. If the quickstart is broken, fix it there.

---

## Primitive → Claude Code analog

The table below is transcribed from [`specs/031-five-primitive-harness/research.md § 1`](../../specs/031-five-primitive-harness/research.md#1-reference-map--primitive--claude-code-analogue). Read that section for full rationale and escalation notes.

| KOSMOS primitive | Claude Code analogue (restored-src) | Shape carried over | Port type |
|---|---|---|---|
| `lookup` (mode=`search`) | `src/tools/GrepTool/` + `src/tools/ToolSearchTool/` | BM25 over `search_hint`, no side effects, idempotent | Structural port |
| `lookup` (mode=`fetch`) | `src/tools/FileReadTool/` + `src/tools/WebFetchTool/` | Deterministic output, cache-friendly, idempotent | Structural port |
| `resolve_location` | `src/tools/GlobTool/` | Deterministic resolver, one-shot, no side effects | Structural port |
| `submit` | `src/tools/BashTool/` + `bashPermissions.ts` + `bashSecurity.ts` | Envelope `{tool_id, params}` → `{transaction_id, status, adapter_receipt}`; permission-gated side effects | Structural port (escalates to Pydantic AI + OpenAI Agents SDK guardrail for per-adapter schema) |
| `subscribe` | `src/services/SessionMemory/` + `src/tools/shared/` async generator | `AsyncIterator[Event]` with `lifetime`; back-pressure native | Architecture port, Korean-domain data shape (escalates to AutoGen mailbox; 3GPP TS 23.041; RSS 2.0) |
| `verify` | `src/services/oauth/` + `src/tools/McpAuthTool/` | Discriminated union over external credential families, delegation-only | Architecture port, Korean-domain tiers (escalates to OpenAI Agents SDK guardrail; Pydantic v2 discriminated union) |

**Verdict from research.md**: `lookup`, `resolve_location`, `submit` are structural ports of CC tools. `subscribe` and `verify` are KOSMOS-net-new: they use CC's async-generator and delegation architecture but carry Korean-domain data shapes that CC has no concept of.

---

## Dual-axis security model

Spec 031 introduced a dual-axis security model documented in [`docs/security/tool-template-security-spec-v1.md`](../security/tool-template-security-spec-v1.md) v1.2. Key points for new engineers:

- **Two axes, not one.** Every adapter registration declares both `published_tier_minimum` (one of 18 closed Korean-auth-tier labels) and `nist_aal_hint` (advisory `AAL1` / `AAL2` / `AAL3`). Using NIST AAL alone loses distinctions between Korean credential families that share an AAL level but are governed by different authorities.
- **18-label closed enum.** The `published_tier` enum is closed in v1; expansion requires a spec amendment. The 18 labels are grouped across six families: `gongdong_injeungseo`, `geumyung_injeungseo`, `ganpyeon_injeung`, `digital_onepass`, `mobile_id`, `mydata`.
- **V1–V6 invariants preserved.** Pydantic `@model_validator(mode="after")` enforces Spec 024 I1–I5 and Spec 025 V6 invariants; `ToolRegistry.register()` is the backstop against `model_construct` bypass.
- **Legacy 8-verb entries must not be re-introduced.** `src/kosmos/security/audit.py::TOOL_MIN_AAL` had 8 legacy IDs — they were removed at v1.2 GA. A lint test (T082) enforces this at CI time.
- **Fail-closed default.** New adapter registrations that omit `published_tier_minimum` or `nist_aal_hint` are rejected by the registry. The safe default is deny, not allow.

---

## Before your first PR

- [ ] Run `uv sync` and confirm `uv run pytest` exits 0.
- [ ] Read the full quickstart: [`specs/031-five-primitive-harness/quickstart.md`](../../specs/031-five-primitive-harness/quickstart.md).
- [ ] Understand the five-primitive surface from the spec: [`specs/031-five-primitive-harness/spec.md`](../../specs/031-five-primitive-harness/spec.md).
- [ ] When adding an adapter, follow the fail-closed defaults checklist in [`AGENTS.md § New tool adapter`](../../AGENTS.md).
- [ ] PRs close the Epic issue (`Closes #EPIC`), not individual task sub-issues. See [`docs/conventions.md`](../conventions.md).

---

## What to read next

- [`AGENTS.md`](../../AGENTS.md) — hard rules, stack, issue hierarchy, PR and commit conventions
- [`docs/conventions.md`](../conventions.md) — branch naming, commit format, task linking, PR closing
- [`specs/031-five-primitive-harness/spec.md`](../../specs/031-five-primitive-harness/spec.md) — normative spec for this harness layer
