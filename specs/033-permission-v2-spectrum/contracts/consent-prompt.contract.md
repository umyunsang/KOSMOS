# Contract — PIPA §15(2) Consent Prompt Builder

**Feature**: 033-permission-v2-spectrum
**Artifact**: Behavioral contract for `src/kosmos/permissions/prompt.py::PIPAConsentPrompt`
**Date**: 2026-04-20

> References: PIPA §15(2) 4-tuple, §22(1) individual consent, Kantara CR v1.1.0 §5.1 notice elements, ISO/IEC 29184:2020 §5.3 plain-language binding.

## 1. Prompt Structure (required)

Every consent prompt presented to the citizen MUST contain, in this order, these 5 sections:

1. **Title** — `[{tool_id}] 개인정보 처리 동의`
2. **목적** (purpose) — single paragraph
3. **항목** (data_items) — bullet list, one item per line
4. **보유기간** (retention_period) — single line
5. **거부권 및 불이익** (refusal_right) — single paragraph explicitly stating what functionality is lost on refusal

## 2. Individual-consent invariants (PIPA §22(1))

| `pipa_class` | Prompt grouping rule |
|--------------|----------------------|
| `일반` | May be bundled with other `일반` items from the same adapter call. |
| `민감` | **Individual prompt.** No bundling — even within the same call. |
| `고유식별` | **Individual prompt.** Re-authentication (AAL2+) may be required per Spec 025 V6 backstop. |
| `특수` | **Individual prompt.** Killswitch override ALWAYS asks (Invariant K3). |

**Builder contract**: `PIPAConsentPrompt.build(decisions: list[ConsentDecision])` MUST raise `ValidationError` if any decision with `pipa_class ∈ {민감, 고유식별, 특수}` is bundled alongside another decision.

## 3. AAL-consent coupling (Spec 025 V6 backstop)

When `auth_level ∈ {AAL2, AAL3}`, the prompt MUST include a visible line:

> **인증 수준**: {AAL2|AAL3} — 추가 본인확인이 필요할 수 있습니다.

Rationale: citizen must understand that consent + re-authentication are two separate barriers.

## 4. Test Matrix (required — at `/speckit-taskstoissues` time)

| # | Input pipa_class | Input auth_level | Input mode | Expected behavior |
|---|------------------|------------------|------------|-------------------|
| T01 | `일반` | `public` | `default` | Bundle OK. Single prompt. |
| T02 | `일반` | `AAL1` | `default` | Bundle OK. Single prompt with AAL1 label. |
| T03 | `민감` | `AAL1` | `default` | **Individual prompt required.** Bundling raises `ValidationError`. |
| T04 | `고유식별` | `AAL2` | `default` | Individual prompt + AAL2 label visible. |
| T05 | `특수` | `AAL3` | `default` | Individual prompt + AAL3 label + mandatory refusal-right paragraph. |
| T06 | `일반` | `public` | `plan` | **No prompt.** `plan` mode is observation-only. |
| T07 | `일반` | `public` | `acceptEdits` | **No prompt if tool is reversible.** (Auto-allow per mode contract.) |
| T08 | `특수` | `AAL3` | `bypassPermissions` | **Prompt EVERY call** (Killswitch K3 + K4 + K5). No caching. |
| T09 | `민감` | `AAL2` | `dontAsk` | If in allow-list: no prompt. If not: fall back to `default` prompt flow. |
| T10 | `일반` | `public` | `default` | `refusal_right` missing → builder raises `ValidationError` (C1). |
| T11 | `일반` | `public` | `default` | `data_items` empty → builder raises `ValidationError` (C1). |
| T12 | `일반` | `public` | `default` | `purpose` is `""` → builder raises `ValidationError` (C1). |
| T13 | `민감` | `AAL1` | `default` | Granted → ledger append granted=True; record_hash chains. |
| T14 | `민감` | `AAL1` | `default` | Refused → ledger append granted=False; record_hash chains. |
| T15 | `일반` | `public` | `default` | Retention period = `P30D` → prompt renders "보유기간: 30일 (P30D)". |
| T16 | `일반` | `public` | `default` | Retention period = `일회성` → prompt renders "보유기간: 일회성 (호출 완료 시 즉시 폐기)". |

## 5. Rendering contract

- Prompt MUST render via TUI (Ink) — NO web/mobile rendering.
- Prompt MUST be keyboard-navigable: `Y` (동의), `N` (거부), `ESC` (취소, = 거부).
- Prompt MUST NOT allow `Enter` to default to allow when focus is on a destructive action. Default focus = "거부".
- For `pipa_class ∈ {민감, 고유식별, 특수}`, initial focus MUST be "거부" and require explicit keystroke to allow (defensive UI).

## 6. Telemetry (Spec 021 OTEL)

Every prompt emits:

- `consent.prompt.shown` span — attrs: `tool_id`, `pipa_class`, `auth_level`, `mode`, `session_id`, `correlation_id`
- `consent.prompt.decided` span — attrs: `granted: bool`, `response_latency_ms`

## 7. Exit Criteria

- [ ] All 16 test-matrix rows covered by `tests/permissions/test_prompt_contract.py`.
- [ ] `PIPAConsentPrompt.__init__` enforces PIPA §15(2) 4-tuple completeness (C1).
- [ ] `PIPAConsentPrompt.build()` enforces individual-consent rule (C2).
- [ ] Rendering contract verified via TUI snapshot tests (Ink test harness).
- [ ] OTEL spans emitted per §6.
