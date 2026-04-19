# Phase 0 Research — Spec 031 Five-Primitive Harness Redesign

**Branch**: `031-five-primitive-harness` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md) | **Discussion**: [#1051](https://github.com/umyunsang/KOSMOS/discussions/1051)

> Per Constitution v1.1.1 §I and AGENTS.md, every design decision below maps first to the **restored-src primary reference** (`.references/claude-code-sourcemap/restored-src/src/`, Claude Code 2.1.88) and escalates to a secondary reference only when restored-src does not cover the need.

---

## 1. Reference Map — Primitive ↔ Claude Code analogue

| KOSMOS primitive | Claude Code analogue (primary, restored-src) | Shape carried over | Escalation reason (if any) |
|---|---|---|---|
| `lookup` (mode=`search`) | `src/tools/GrepTool/` (content search) + `src/tools/ToolSearchTool/` (registry self-search) | BM25 over `search_hint`, no side effects, idempotent | Spec 022 already shipped; re-cite for continuity |
| `lookup` (mode=`fetch`) | `src/tools/FileReadTool/` + `src/tools/WebFetchTool/` (read-only byte retrieval) | Deterministic output, cache-friendly, idempotent | — |
| `resolve_location` | `src/tools/GlobTool/` (pattern → concrete path list) | Deterministic resolver, one-shot, no side effects | — |
| `submit` | `src/tools/BashTool/` (the single "execute side-effecting action" tool, with `bashPermissions.ts` + `bashSecurity.ts` gauntlet) | Envelope `{tool_id, params}` → `{transaction_id, status, adapter_receipt}`; permission-gated side effects | Escalate to **Pydantic AI** for schema-driven per-adapter model, **OpenAI Agents SDK** guardrail pipeline for fail-closed gate composition |
| `subscribe` | No byte-for-byte analog in CC tools; closest is `src/services/SessionMemory/` (long-lived state observation) + `src/tools/shared/` (async generator streaming) | `AsyncIterator[Event]` with `lifetime`; back-pressure native | Escalate to **AutoGen AgentRuntime mailbox** (streaming delivery semantics) + **stamina/aiobreaker** (back-pressure + circuit breaker); **3GPP TS 23.041** for CBS Message ID 4370–4385; **RSS 2.0** spec for `guid` de-duplication |
| `verify` | `src/services/oauth/` + `src/tools/McpAuthTool/` (credential delegation — CC never mints tokens, always delegates) | Discriminated union over external credential families, delegation-only | Escalate to **OpenAI Agents SDK guardrail pipeline** for family-family mismatch detection; **Pydantic v2 discriminated union** for family variants. Korean tier enum is domain extension — no CC analog |

**Verdict**: Three of five primitives (`lookup`, `resolve_location`, `submit`) are structural ports of CC tools. Two (`subscribe`, `verify`) are KOSMOS-net-new that use CC's **architecture** (async generator streaming, delegation-not-minting) but carry Korean-domain **data shape** that CC has no concept of.

---

## 2. `submit` envelope design

**Decision**: Envelope is `{tool_id: str, params: dict[str, Any_forbidden_use_model]}` in / `{transaction_id: str, status: Literal["pending","succeeded","failed","rejected"], adapter_receipt: dict}` out. No domain fields on the main model.

**Rationale**:
- Mirrors `BashTool`'s single `{command, description, timeout}` surface where `command` is an opaque string dispatched to the shell — `params` is the same shape, opaque to the main surface, typed by the adapter's own Pydantic model.
- Pydantic AI's tool registry pattern lets each adapter own `input_schema: type[BaseModel]` while the harness only sees the shared envelope — this is exactly what `src/kosmos/tools/registry.py` already does for Spec 022's 4 adapters.
- Per Constitution §III, the adapter's `params` is typed by its Pydantic model even though the main surface sees `dict`. This is enforced by the `ToolRegistry.register()` backstop — adapter parses its own params at invocation time, registers its model at boot.

**Alternatives considered**:
- **5 separate verbs** (the rejected 8-verb design): Leaks ministry knowledge to main surface (FR-002 violation); duplicates audit/permission plumbing 5×; contradicts harness-not-reimplementation.
- **Envelope carries `ministry: Literal[...]` discriminator**: Still leaks. Rejected.
- **`params: BaseModel` at the main surface via generic**: Pydantic v2 generics over discriminated unions work but require every adapter schema to be imported at main-surface definition time — breaks lazy tool discovery (Layer 2 principle in `docs/vision.md`). Rejected.

**Reference citations**:
- Primary: `.references/claude-code-sourcemap/restored-src/src/tools/BashTool/BashTool.tsx` (opaque command dispatch)
- Primary: `.references/claude-code-sourcemap/restored-src/src/tools/BashTool/bashPermissions.ts` (per-invocation permission gate)
- Secondary (Pydantic AI): per-adapter schema pattern
- Secondary (OpenAI Agents SDK): guardrail pipeline composition pre-invocation

---

## 3. `verify` — 6-family discriminated union + dual-axis tier schema

**Decision**: `AuthContext` is a Pydantic v2 discriminated union over 6 family literals, each variant carrying `published_tier: Literal[<subset of the 18-label enum applicable to that family>]` (primary) + `nist_aal_hint: Literal["AAL1","AAL2","AAL3"]` (advisory) + family-specific session metadata fields.

### 3.1 Ratified `published_tier` enum — 18 labels

The spec defers the exact label strings to this plan (Assumption: *"The 18 `published_tier` labels are enumerated in the Spec 031 plan document … The plan will ratify the exact label strings."*). Ratified labels grouped by family:

| Family | Ratified `published_tier` labels | `nist_aal_hint` (advisory) |
|---|---|---|
| `gongdong_injeungseo` (공동인증서, 구 공인인증서) | `gongdong_injeungseo_personal_aal3`, `gongdong_injeungseo_corporate_aal3`, `gongdong_injeungseo_bank_only_aal2` | AAL2/3 |
| `geumyung_injeungseo` (금융인증서, 금융결제원 클라우드) | `geumyung_injeungseo_personal_aal2`, `geumyung_injeungseo_business_aal3` | AAL2/3 |
| `ganpyeon_injeung` (간편인증, PASS·카카오·네이버·토스·KB·삼성·페이코) | `ganpyeon_injeung_pass_aal2`, `ganpyeon_injeung_kakao_aal2`, `ganpyeon_injeung_naver_aal2`, `ganpyeon_injeung_toss_aal2`, `ganpyeon_injeung_bank_aal2`, `ganpyeon_injeung_samsung_aal2`, `ganpyeon_injeung_payco_aal2` | AAL2 |
| `digital_onepass` (디지털원패스, 행정안전부) | `digital_onepass_level1_aal1`, `digital_onepass_level2_aal2`, `digital_onepass_level3_aal3` | AAL1/2/3 |
| `mobile_id` (모바일 신분증 — 운전면허·주민등록·국가보훈등록·공무원증) | `mobile_id_mdl_aal2`, `mobile_id_resident_aal2` | AAL2 |
| `mydata` (마이데이터 사업자, 금융위 v240930) | `mydata_individual_aal2` | AAL2 |

**Total**: 18 labels. Enum is **closed** in v1; expansion requires a spec amendment (per Edge Case "`published_tier` value not in the 18-label enum") and per the Deferred Items entry *"`published_tier` enum expansion beyond the ratified 18 labels"*.

**Rationale**:
- **Dual-axis over single-axis NIST AAL**: The rejected 8-verb design used AAL-only and lost distinctions like `공동인증서` vs `금융인증서` (both AAL3 but governed by different bodies — 금융결제원 vs 전자서명법). Dual-axis preserves the Korean-public-infrastructure fidelity while giving international interop an advisory hint.
- **Harness-not-reimplementation**: Each variant delegates to the relevant external operator (금융결제원, PASS providers, 행정안전부, 모바일 운전면허 발급기관, 마이데이터 사업자). KOSMOS holds no signing keys, runs no CA, issues no VCs.

**Alternatives considered**:
- **NIST AAL primary, Korean tier optional**: Rejected (original 8-verb pattern).
- **Flat `published_tier: str` without discriminator**: Loses family-level metadata (e.g., `ganpyeon_injeung_kakao_aal2` vs `ganpyeon_injeung_pass_aal2` carry different session-state schemas). Rejected.
- **Open enum**: Rejected (Edge Case mandates closed enum in v1).

**Reference citations**:
- Primary: `.references/claude-code-sourcemap/restored-src/src/services/oauth/` (CC delegates to OAuth providers; never mints)
- Primary: `.references/claude-code-sourcemap/restored-src/src/tools/McpAuthTool/` (per-family auth tool pattern)
- Secondary (OpenAI Agents SDK): guardrail mismatch detection
- Domain sources: `docs/vision.md § Reference materials` → PublicDataReader (auth patterns); external Korean sources (금융결제원·PASS providers·행정안전부·마이데이터 사업자) documented only — no code lift.

---

## 4. `subscribe` — 3 delivery modalities, no webhook

**Decision**: Input `{tool_id: str, params: dict, lifetime: Duration}`; output `AsyncIterator[SubscriptionEvent]`. `SubscriptionEvent` discriminated on `kind: Literal["cbs_broadcast", "rest_pull_tick", "rss_item"]`. No `webhook_url` field anywhere in the schema (FR-013).

**Rationale**:
- **Async-generator streaming over callback**: Matches CC's loop-level async generator idiom (`services/shared/*`) — back-pressure comes free from Python/TS async iteration, cancellation propagates on `lifetime` expiry.
- **3 modalities unified under one iterator**: Each adapter internally handles its own protocol (CBS radio bearer, REST `httpx.AsyncClient` polling, RSS feed tail via stored `guid`). The harness only sees `Event`s on the iterator.
- **Webhook forbidden**: KOSMOS is a client-side harness — adding a webhook receiver means running an HTTP server, which contradicts the harness principle and expands blast radius (public endpoint = new attack surface).

**Modality specifics**:
- **3GPP CBS broadcast**: Message ID range `4370–4385` (ATIS-0700007 CMAS categories, adopted by KCS CBS profile). Adapter consumes CBS messages from a mock radio-layer fixture (real-device CBS requires UE access, out of v1 scope).
- **REST pull**: Adapter declares `polling_interval: Duration`. Harness enforces minimum interval (e.g., 10s) to protect data.go.kr quota. `ToolCallAuditRecord` emitted per tick.
- **RSS 2.0**: `<guid isPermaLink="false">` tracked in subscription state; duplicates suppressed. Reset `guid`s treated as new items (Edge Case: "System MUST treat reset `guid`s as new items — delivery is the safer default").

**Alternatives considered**:
- **Webhook receiver**: Rejected (FR-013).
- **Server-sent events (SSE)**: Some data.go.kr APIs support SSE but not uniformly; falls back to REST pull.
- **Long-polling**: Covered by REST pull with `polling_interval=0`.

**Reference citations**:
- Primary: `.references/claude-code-sourcemap/restored-src/src/services/SessionMemory/` (long-lived observation state)
- Secondary (AutoGen): AgentRuntime mailbox streaming semantics
- Secondary (stamina): enforced jitter + capped backoff for REST pull
- Secondary (aiobreaker): per-adapter circuit breaker for burst protection
- Domain sources: 3GPP TS 23.041; RSS 2.0 spec (Harvard Berkman Center)

---

## 5. Mock scope — 6 mirror-able systems, 3 scenario-only

**Decision**: `docs/mock/` contains **exactly 6** system subdirectory trees. `docs/scenarios/` contains **exactly 3** OPAQUE journeys with no mock adapter.

### 5.1 `docs/mock/` — 6 mirror-able systems

| System | Public-spec URL | Mirror axis | License / basis |
|---|---|---|---|
| `data.go.kr` (16 domains, incl. KOROAD / KMA / HIRA / NMC / NFA119) | openapi.data.go.kr per-service OpenAPI | **byte** mirror via serviceKey fixture recording | Public OpenAPI |
| `omnione` (K-DIDF DID `did:omn`) | OpenDID reference stack | **byte** mirror via Apache-2.0 full stack | Apache-2.0 |
| `barocert` | developers.barocert.com SDK docs | **shape** mirror via SDK schema | SDK docs public |
| `mydata` (금융위 v240930) | KFTC 마이데이터 표준 v240930 | **shape** mirror (mTLS + OAuth 2.0) | Public standard |
| `npki_crypto` (crypto layer only: PKCS#7 / #12) | `PyPinkSign` reference | **byte** mirror via PKCS#7 / #12 parser | PyPinkSign (reference impl, MIT-style open) |
| `cbs` (긴급재난문자, 3GPP TS 23.041 Message IDs 4370–4385) | 3GPP TS 23.041 | **byte** mirror via message-ID + payload | 3GPP public |

### 5.2 `docs/scenarios/` — 3 OPAQUE journeys (no mock adapter)

| Journey | Why OPAQUE | KOSMOS ↔ real-system handoff point |
|---|---|---|
| 정부24 민원 제출 | Submission API withheld from public disclosure | Harness hands user to `gov24.go.kr` browser flow |
| KEC 전자세금계산서 XML 서명부 | XSD + public signing key not disclosed | Harness renders draft XML, user signs in NETS-KEC portal |
| NPKI 포털별 challenge-response | Portal-proprietary session handshake | Harness shows guidance; user authenticates directly on portal |

**Rationale**:
- Encoding fake contracts for OPAQUE systems teaches the harness to fail in novel ways when institutions contribute the real spec (learned failure = regression). Better: document the journey and block at the handoff point.
- Per feedback memory `feedback_mock_vs_scenario.md`, this split is the ratified mock-vs-scenario boundary — honored verbatim here.

**Promotion path** (FR-025): When `data.go.kr` publishes (e.g.) the 정부24 submission API, the scenario `.md` moves into `docs/mock/gov24/`, a real fixture + adapter stub is added, and the scenario file records the promotion in a "Promoted to mock on <date>, tracked by #<issue>" footer.

**Reference citations**:
- Primary: restored-src has no analog — CC has no government-integration layer. Escalation documented.
- Secondary: PublicDataReader (`docs/vision.md § Reference materials`) — proves `data.go.kr` byte-mirrorability
- Decision authority: feedback memory `feedback_mock_vs_scenario.md` (2026-04-19 ratification)

---

## 6. Security Spec v1.2 cutover

**Decision**: `docs/security/tool-template-security-spec-v1.md` bumps to v1.2. The `TOOL_MIN_AAL` single-axis table is replaced with a dual-axis `(published_tier_minimum, nist_aal_hint)` schema. Spec 024 V1–V4 invariants and Spec 025 V6 invariant + canonical `auth_type`↔`auth_level` allow-list are preserved verbatim until v1.2 GA; at v1.2 GA they are either re-stated or explicitly superseded (with migration note).

**Enforcement shape at v1.2 GA**:
- `AdapterRegistration` gains `published_tier_minimum: <one of the 18 labels> | None` and `nist_aal_hint: AAL1|AAL2|AAL3 | None`.
- `ToolRegistry.register()` backstop enforces **both** fields must be set on or after v1.2 GA (FR-030).
- Pre-v1.2 registrations (Spec 022's 4 adapters, 8 legacy tool IDs in `src/kosmos/security/audit.py`) retain their current shape via a one-release compatibility window; compatibility window closes at v1.2 GA.

**Current legacy state** (discovered during research):
- `src/kosmos/security/audit.py::TOOL_MIN_AAL` currently lists 8 legacy tool IDs + 2 Phase-2 API adapters — confirms that the legacy 8-verb AAL-only shape is still encoded. v1.2 migration MUST delete the legacy 8-verb entries and migrate the 4 existing Spec 022 adapters + 2 Phase-2 adapters to the dual-axis shape.
- `ToolCallAuditRecord` v1 I1–I5 invariants (Spec 024) and V1–V6 invariants (Spec 025) are enforced via Pydantic `@model_validator(mode="after")` + `ToolRegistry.register()` backstop. This pattern is preserved verbatim.

**Reference citations**:
- Primary: restored-src has no policy-language analog. Escalation documented.
- Secondary (NeMo Guardrails): Colang 2.0 policy language as a model for auditable dual-axis rails
- Secondary (OpenAI Agents SDK): guardrail pipeline composition at registration time

---

## 7. Deferred Items validation (Constitution §VI gate)

The spec's "Scope Boundaries & Deferred Items" section lists 9 rows. Validation result per Constitution §VI:

| Row | Tracking Issue | Validation result |
|---|---|---|
| Full Ink + React + Bun TUI renderers for submit/subscribe/verify outputs | #287 | ✅ Open epic confirmed |
| #287 body rewrite removing references to deleted 8-verb Epic #994 | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |
| Spec 027 agent-swarm integration of submit/subscribe/verify | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |
| `docs/mock/` 6-system stub build-out | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |
| `docs/scenarios/` content authoring for 3 OPAQUE journeys | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |
| `docs/security/tool-template-security-spec-v1.md` v1.2 bump | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |
| Scenario→mock promotion automation | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |
| CI lint rule rejecting re-introduction of legacy 8-verb names | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |
| `published_tier` enum expansion beyond 18 labels | NEEDS TRACKING | ⏳ To be resolved by `/speckit-taskstoissues` |

**Unregistered deferral scan**: Spec text was grepped for "separate epic", "future epic", "Phase [2+]", "v2", "deferred to", "later release", "out of scope for v1". All occurrences resolve to the table above except one benign usage: *"Spec 031 v1"* appears as a release-tag reference, not a deferral. No unregistered deferrals.

**Verdict**: Deferred Items table is compliant. 7 "NEEDS TRACKING" entries are expected and will be backfilled by `/speckit-taskstoissues` creating placeholder issues.

---

## 8. Unresolved NEEDS CLARIFICATION

None. The spec contained zero `[NEEDS CLARIFICATION: ...]` markers. The only open enumeration — the 18 `published_tier` labels — was intentionally deferred by the spec to this plan; Section 3.1 ratifies the enum.

---

## 9. Reference-mapping summary

| Layer | Primary (restored-src) | Secondary | Section |
|---|---|---|---|
| `lookup` / `resolve_location` | GrepTool + FileReadTool + WebFetchTool + GlobTool | Spec 022 shipped | §1 |
| `submit` envelope | BashTool + bashPermissions.ts + bashSecurity.ts | Pydantic AI, OpenAI Agents SDK | §2 |
| `verify` 6-family union | oauth/ + McpAuthTool | OpenAI Agents SDK | §3 |
| `published_tier` enum | — (domain extension) | Korean public-infra docs | §3.1 |
| `subscribe` streaming | services/SessionMemory + tools/shared/ | AutoGen mailbox, stamina, aiobreaker | §4 |
| `subscribe` data formats | — (domain extension) | 3GPP TS 23.041; RSS 2.0 | §4 |
| Mock scope | — (net-new) | feedback memory ratification | §5 |
| Security v1.2 | — (net-new) | NeMo Guardrails | §6 |

**Every non-`—` primary citation** is a concrete path under `.references/claude-code-sourcemap/restored-src/src/`. **Every `—` primary** is accompanied by an explicit escalation reason and a domain-source citation per Constitution §I rule *"only escalate to the secondary references below when restored-src does not cover the need (document the escalation in research.md)."*

---

## Phase 0 exit gate

- [x] All NEEDS CLARIFICATION resolved (§8)
- [x] Every design decision mapped to a concrete reference (§1–6, §9)
- [x] Deferred Items table validated against Constitution §VI (§7)
- [x] 18 `published_tier` labels ratified (§3.1)
- [x] Mock-vs-scenario split ratified (§5)
- [x] Security v1.2 cutover plan established (§6)

Proceed to Phase 1 (data-model.md + contracts/ + quickstart.md).
