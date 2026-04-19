# Phase 0 Research — Permission v2 (Spec 033)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-04-20

This document resolves the 5 open questions carried from `checklists/requirements.md § Next step`, maps every FR group to a primary + secondary reference, and re-validates deferred-item tracking per Constitution §VI.

---

## 1. Reference Mapping (Constitution §I)

Every FR cluster maps to at least one primary reference (preferred migration source per Constitution §I's Permission Pipeline row: **OpenAI Agents SDK** primary, **Claude Code reconstructed** secondary) plus supporting references for domain-specific concerns (PIPA, canonical JSON, hash-chain, file formats).

### 1.1 Group A — Mode Spectrum (FR-A01..A05)

| Decision | Primary reference | Secondary reference | Rationale |
|---|---|---|---|
| 5 external modes (`default` / `plan` / `acceptEdits` / `bypassPermissions` / `dontAsk`) | `.references/claude-code-sourcemap/restored-src/src/utils/permissions/PermissionMode.ts` (external modes enum) | Cursor Cascade "Ask/Edit/Agent" modes · Continue.dev `agent-modes` spec | CC's external modes are battle-tested, 1:1 1 match with user expectations from CC CLI users (a majority of our early adopters). Internal modes (`auto` / `bubble`) are gated on `TRANSCRIPT_CLASSIFIER` growth-book feature and tied to CC's transcript classifier — not applicable to citizen-API domain, explicitly out of scope per spec.md Assumption #8. |
| Shift+Tab cycle order `default → acceptEdits → plan → default` (high-risk excluded) | `.references/claude-code-sourcemap/restored-src/src/utils/permissions/getNextPermissionMode.ts` | Continue.dev Shift+Tab idiom | CC's `getNextPermissionMode` includes bypass in the cycle when `isBypassPermissionsModeAvailable`; we deliberately **deviate** — spec.md US5 requires high-risk modes to be slash-command-only for audit clarity (ledger `action=enter_high_risk_mode` vs a silent keychord toggle). Recorded in `data-model.md § 2.1` state diagram. |
| Slash commands `/permissions bypass`, `/permissions dontAsk`, `/permissions list`, `/permissions edit`, `/permissions verify` | `.references/claude-code-sourcemap/restored-src/src/commands/permissions/` (command surface) | Continue.dev slash-command style | CC's slash command registry pattern translates directly to our TUI (Spec 287) command surface. `verify` command is new — invokes WS3 `kosmos permissions verify` CLI. |
| High-risk auto-expire (default 30 min, configurable) | `.references/claude-code-sourcemap/restored-src/src/utils/permissions/permissionSetup.ts` (`stripDangerousPermissionsForAutoMode` + `restoreDangerousPermissions`) | OpenAI Agents SDK session-scoped guardrails | CC's pattern of stashing dangerous perms on auto-mode entry + restoring on exit is the reference for our timeout-based fallback — but we always fallback to `default` (not to a previous mode) per FR-A05 to keep audit semantics unambiguous. |
| `ToolPermissionContext` injection at every tool call | `.references/claude-code-sourcemap/restored-src/src/utils/permissions/permissions.ts` (`applyPermissionRulesToPermissionContext`) | OpenAI Agents SDK `input_guardrails` pipeline | CC's pattern of passing a context object through the tool loop rather than reading module-level globals keeps tests deterministic and makes the guardrail pipeline auditable. |

### 1.2 Group B — Killswitch (NON-NEGOTIABLE; FR-B01..B04)

| Decision | Primary reference | Secondary reference | Rationale |
|---|---|---|---|
| `is_irreversible=True` adapters are never silent under any mode | **OpenAI Agents SDK** `input_guardrails`/`output_guardrails` + `tripwire_triggered=True` pattern | `.references/claude-code-sourcemap/restored-src/src/utils/permissions/bypassPermissionsKillswitch.ts` (`checkAndDisableBypassPermissions` + `gracefulShutdown(1, 'bypass_permissions_disabled')`) | Agents SDK's guardrail pipeline is the Constitution §I primary reference for Permission Pipeline; its "tripwire" pattern maps cleanly to our killswitch (raises `RequireHumanOversight` error → TUI prompts). CC's bypass killswitch is the secondary reference for **runtime** disabling (Statsig gate `tengu_disable_bypass_permissions_mode`). We embed the killswitch **before** mode evaluation in the guard pipeline (data-model.md § 2.2 state diagram). |
| `is_personal_data=True` + `auth_level ∈ {AAL2, AAL3}` requires valid ledger receipt | Spec 025 V6 `auth_type` ↔ `auth_level` invariant | PIPA §15 / §22 (purpose-specific consent) | Spec 025 V6 already backstops the AAL invariant at `ToolRegistry.register()`; FR-B02 extends this to require **consent ledger lookup at call-time**. Pre-evaluated by killswitch module — if no valid ledger receipt exists for this adapter × purpose × session, the call is refused irrespective of persistent rule store `allow`. |
| Automation (ant user / swarm worker) on irreversible → `RequireHumanOversight` | Anthropic Cookbook "orchestrator-workers" pattern — worker agents escalate human-in-the-loop | Spec 027 mailbox IPC (error propagation path) | Agent swarms must not be able to commit irreversible civic actions without explicit human approval. Our `RequireHumanOversight` error type is propagated back through Spec 027 mailbox to coordinator, which surfaces it in TUI as a confirmation prompt. |
| Killswitch override attempts logged to ledger | Claude Code `bypassPermissionsKillswitch.ts` telemetry pattern | NIST SP 800-92 event-logging guidelines | CC logs bypass-disable events to its telemetry pipeline. We replicate by appending `action=killswitch_override_attempt` records to consent ledger — these become admissible evidence in ISMS-P audits. |

### 1.3 Group C — Persistent Rule Store (FR-C01..C05)

| Decision | Primary reference | Secondary reference | Rationale |
|---|---|---|---|
| Tri-state `allow | ask | deny` per adapter (optional ministry + purpose tuple keys) | **Continue.dev** `~/.continue/permissions.yaml` + `policies.permissions` schema | `.references/claude-code-sourcemap/restored-src/src/utils/permissions/permissionsLoader.ts` (`loadAllPermissionRulesFromDisk`) | Continue.dev is the cleanest single-user local-file tri-state reference. CC's rule loader pattern (multi-source: user / project / local / cli-arg) is more powerful but adds complexity we don't need for MVP. We adopt Continue.dev's JSON format for the file (not YAML — Python stdlib JSON is sufficient, no PyYAML dep), with CC's source-priority concept deferred to Permission v3 (spec.md Deferred item #1 — organization override). |
| Atomic writes via `tmpfile + os.rename` | POSIX `rename(2)` atomicity guarantee (same-filesystem) + CPython `pathlib.Path.replace()` | Git's `core.fsync` + `rename` pattern | POSIX mandates atomic rename within a filesystem. CPython's `pathlib.Path.replace()` wraps `os.replace()` which is atomic on both Linux/macOS. No new dep needed. |
| Schema validation at boot + fail-closed fallback to `default` + prompt-always | OpenAI Agents SDK "invalid config → tripwire" pattern | CC `permissionSetup.ts` `initializeToolPermissionContext` | Tripwire semantics apply to boot config just as to runtime calls. If we can't safely interpret the rule store, we can't safely exercise any non-default mode — so fall back to `default` with per-call prompts. |
| `/permissions` TUI editor with external-edit detection at boot | CC slash command + file-mtime snapshot idiom | Continue.dev CLI `continue permissions list` | Users editing JSON directly is expected (Continue.dev docs flag this as common). We snapshot file mtime after our writes and check at boot; if mtime differs (user edited externally), we re-validate schema + emit `action=rule_change` reconciliation ledger record. |

### 1.4 Group D — PIPA Consent Ledger (FR-D01..D10)

| Decision | Primary reference | Secondary reference | Rationale |
|---|---|---|---|
| Consent receipt record format | **Kantara Initiative Consent Receipt v1.1.0** (ANCR-WG-CRv1_1_0.json schema) | ISO/IEC 29184:2020 (Privacy notices & consent) + KAIO Initiative Notice & Consent Template | Kantara v1.1.0 is the canonical industry schema; ISO 29184 supplies the notice-binding requirement (`notice_hash` + `action_signifying_consent` extension fields). Neither is licensed in a way that blocks KOSMOS use (see § 3.1 below). |
| PIPA 4-tuple (목적·항목·보유기간·거부권) enforced at prompt UI | 개인정보보호법 §15(2) 각호 (1-4) | 개인정보보호위원회 표준 동의서 양식 (2024 개정) | 4-tuple is the statutory minimum. We upgrade to a schema invariant: prompt Pydantic model has `StrictStr(min_length=1)` for each of the 4 fields, so it's structurally impossible for the UI to render a prompt missing any of them (Hypothesis property test in SC-006). |
| Append-only WORM semantics (software-enforced) | PIPA 개인정보 안전성 확보조치 §8 (접속기록 보관·점검) + ISMS-P 2.9.4 | NIST SP 800-92 § 4.2.1 (append-only log discipline) | §8 mandates ≥ 2 years retention + tamper-evident. Our API surface exposes only `append()` / `iter()` / `verify()` — no update, no delete — so the spec-level WORM is enforced without requiring a WORM filesystem. |
| Hash chain: `prev_hash || canonical_json(record)` SHA-256 | **RFC 8785 JCS** (JSON Canonicalization Scheme) + NIST FIPS 180-4 SHA-256 | Hyperledger / W3C VC Data Integrity hash-chain precedents | RFC 8785 is the only standardized canonical JSON encoding; alternatives (OLPC canonical JSON, BSON, CBOR) either lack spec precision or introduce deps. See § 3.3 resolution. |
| HMAC-SHA-256 seal with 32-byte key at `~/.kosmos/keys/ledger.key` mode 0400 | NIST SP 800-107 / RFC 2104 HMAC | OWASP ASVS V9.1 (logging integrity controls) | Single-user MVP: one HMAC key, yearly manual rotation (see § 3.4 resolution). Key generation via stdlib `secrets.token_bytes(32)` on first boot; mode 0400 enforced on creation + boot-time check. |
| Individual-consent (§22(1)) — no bundled consent | PIPA §22(1) + 개인정보보호위원회 2024 해설서 §22 | Privacy by Design principle 2 (default privacy settings) | Each `purpose_category` gets its own ledger record; a single user interaction that grants multiple purposes produces N records (not 1 bundled). Enforced by `ConsentDecision` schema having `purpose_category: StrictStr` (single-valued), with prompt UI spawning N sequential 4-tuple prompts for N purposes. |
| Purpose-limitation (§18(2)) re-prompt trigger | PIPA §18(2) + 개인정보보호위원회 2024 해설서 §18 | GDPR Art. 5(1)(b) purpose-limitation (analogous) | When a call reuses an adapter with a different `purpose_category` than the one consented to, killswitch module detects mismatch and forces re-prompt. Implemented in `killswitch.py` + tested in `test_ledger_purpose_mismatch.py` (part of WS3). |
| Consent validity expiry + re-consent trigger | PIPA 해설서 §15 (동의 유효기간) + 표준 개인정보보호 지침 §13 | Adapter-level `consent_validity_period` metadata | Default validity is a policy constant (`CONSENT_DEFAULT_VALIDITY_DAYS = 180`), with per-adapter override via `AdapterPermissionMetadata.consent_validity_period`. Expiry checked at lookup time in `audit_coupling.py`. |
| 2-year+ retention | 개인정보 안전성 확보조치 §8 + ISMS-P 2.9.4 | KISA 2024 기술적·관리적 보호조치 가이드 | Module constant `LEDGER_MINIMUM_RETENTION_DAYS = 730`. WORM API surface (no delete) structurally guarantees retention; archival to cheaper storage after N days is deferred (spec.md Deferred #3 — Audit Archive Epic). |

### 1.5 Group E — LLM Synthesis Boundary (FR-E01, FR-E02)

| Decision | Primary reference | Secondary reference | Rationale |
|---|---|---|---|
| KOSMOS = 수탁자 default + LLM synthesis = controller-level carve-out | MEMORY `project_pipa_role` (PIPA §26 interpretation) | 개인정보보호위원회 2023 AI 개인정보보호 자율점검표 §4.3 (LLM 합성 단계) | The processor-default + controller-carve-out interpretation was validated with user in the pre-compact session. LLM synthesis is where raw personal data becomes inferences the user didn't explicitly consent to at source — hence controller-level obligations kick in for that stage only. |
| Pseudonymization failure → LLM call blocked | PIPA §28의2 (가명정보) + 2024 가명정보 처리 가이드 | GDPR Art. 25 privacy-by-default | Fail-closed: if the synthesis guard cannot produce a pseudonymized prompt, the LLM call is refused + ledger appends `action=synthesis_blocked_missing_pseudonym`. Automatic pseudonymization engine (beyond "detect presence") deferred to a separate Epic (spec.md Deferred #6). |
| AI 기본법 §27 high-impact AI safeguards (banner + `/escalate` + explainability) | 인공지능산업 진흥 및 신뢰 기반 조성 등에 관한 법률 §27 (2026 시행) | AI 행동계획 2026 과제 54 (공공 AI 영향평가) | Three safeguards wired into every session: (a) session-start banner declaring "고영향 AI 사용 세션" (always-on for KOSMOS since we touch personal data + irreversible actions), (b) `/escalate` slash command routes to human-operator mailbox (Spec 027), (c) explainability — `/why` command prints recent tool-call history + matched ledger receipts. |

### 1.6 Group F — Integration & Audit (FR-F01..F03)

| Decision | Primary reference | Secondary reference | Rationale |
|---|---|---|---|
| `consent_receipt_id` ↔ Spec 024 `ToolCallAuditRecord` coupling | Spec 024 `ToolCallAuditRecord.consent_receipt_id` field (already declared in Spec 024 v1) | Kantara CR `consentReceiptID` field | Field exists in Spec 024 but is currently optional/unvalidated; FR-F01 makes it a populated-required field whenever `is_personal_data=True`. Coupling is a **read** on Spec 024 schema, no modification. |
| Spec 025 V6 AAL invariant preservation | Spec 025 V6 `auth_type` ↔ `auth_level` invariant | Spec 024 v1 AAL classes | V6 backstop runs at `ToolRegistry.register()`; Permission v2 adds a **second** backstop at call-time (before mode/rule evaluation). A rule store `allow` for an AAL2 adapter is never honored if the session only has AAL1 — returns `AALInsufficientError`. |
| OpenTelemetry span attributes | Spec 021 GenAI v1.40 attribute set | OpenTelemetry semantic conventions for security events | Three new KOSMOS-namespaced attributes on each tool call span: `kosmos.permission.mode`, `kosmos.permission.decision` (∈ {`allow`, `deny`, `ask_prompted`, `ask_session_granted`, `ask_session_denied`, `killswitch_blocked`, `aal_insufficient`}), `kosmos.consent.receipt_id`. Emitted by `otel_spans.py` helper. |

---

## 2. Deferred-Item Validation (Constitution §VI)

Per spec.md § Scope Boundaries:

### 2.1 Out of Scope (Permanent) — 4 items, validated

| Item | Rationale | Check |
|---|---|---|
| 모바일 네이티브 권한 UI | KOSMOS is terminal platform | PASS — no prose references mobile inside spec body |
| Claude Code 내부 모드 (`auto`, `bubble`) | TRANSCRIPT_CLASSIFIER-gated CC-internal feature, citizen domain unaffected | PASS — FR-A01 explicitly excludes internal modes |
| 생체정보 기반 AAL3 획득 경로 | Session-layer concern, outside Permission v2 | PASS — spec.md Assumption #5 declares AAL as "trusted input" |
| AI 행동계획 §31 워터마킹 | Separate research Epic required | PASS — spec.md Assumption #6 scopes §31 to banner only |

### 2.2 Deferred to Future Work — 7 items, all NEEDS TRACKING

| # | Item | Target Epic | Tracking | Validation |
|---|---|---|---|---|
| 1 | Organization override (admin-level `permissions.json`) | Permission v3 (조직 배포) | NEEDS TRACKING | PASS — to be created at `/speckit-taskstoissues` |
| 2 | Multi-device consent sync | Sync Epic (세션 복원) | NEEDS TRACKING | PASS |
| 3 | Ledger long-term archival (≥ 2 years remote) | Audit Archive Epic | NEEDS TRACKING | PASS |
| 4 | Automatic re-consent expiry notifications | Notifications Epic | NEEDS TRACKING | PASS |
| 5 | GDPR / CCPA mapping for overseas residents | International Compliance Epic | NEEDS TRACKING | PASS |
| 6 | Automatic pseudonymization engine | Pseudonymization Engine Epic | NEEDS TRACKING | PASS |
| 7 | TUI `/permissions audit` interactive ledger browser | TUI Audit UX Epic | NEEDS TRACKING | PASS |

### 2.3 Scan for unregistered deferrals

Ripgrep sweep of spec.md for `"separate epic|future phase|v2|later release|deferred to|out of scope for v1"` — all hits appear inside the Deferred Items table or are in Constitution §VI citations. **No orphan deferrals.**

---

## 3. Open-Question Resolutions

### 3.1 Kantara Consent Receipt v1.1.0 licensing

**Question**: Is the Kantara Initiative CR v1.1.0 JSON schema usable by KOSMOS?

**Decision**: Yes — adopt Kantara CR v1.1.0 as the reference schema for `ConsentDecision` records.

**Rationale**:
- Kantara Initiative publishes the CR specification under the **Kantara Initiative IPR Policy — Non-Assertion Covenant** (effectively a patent non-assertion + copyright-permissive grant for interoperability implementations).
- The JSON schema itself is published in the Kantara WG repository at MIT / Apache-2.0-equivalent permissive terms (no royalty, no attribution copyleft).
- KOSMOS is Apache-2.0; no conflict.
- We do **not** claim Kantara compliance (that requires a separate certification); we cite the schema as "reference format derived from" to stay honest about our compliance posture.

**Alternatives considered**:
- **ISO/IEC 29184:2020 native schema** — rejected: ISO spec is behind a paywall, cannot be vendored; we still cite 29184 for notice-binding **concepts** (fields like `notice_hash`).
- **Custom KOSMOS schema, no reference** — rejected: violates Constitution §I (no concrete reference). Also harms interoperability with future external auditors who expect Kantara shape.

**Attribution**: Each ledger record carries a `$schema` field pointing to Kantara CR v1.1.0 URL; `docs/security/` gets a new ADR entry citing the IPR policy (to be created as part of WS3).

### 3.2 Continue.dev `permissions.yaml` schema compatibility

**Question**: Adopt Continue.dev's tri-state file format, or extend it, or roll our own?

**Decision**: **Adopt the tri-state concept but use JSON (not YAML) + KOSMOS-specific field names.**

**Rationale**:
- Continue.dev's `allow | ask | deny` × per-adapter granularity is exactly what we need.
- YAML requires PyYAML dep — violates AGENTS.md hard rule (no new deps in-spec).
- Field names in Continue.dev (`tool`, `policy`) don't match our domain (we use `adapter_id`, `decision`); renaming is cleaner than aliasing.
- Schema version tag (`$schema`) lets us version-migrate later without a format switch.

**Concrete format** (data-model.md § 1.3):
```json
{
  "$schema": "kosmos://permissions-store/v1",
  "version": 1,
  "rules": [
    {"adapter_id": "hira_hospital_search", "decision": "allow", "source": "user", "created_at": "...", "updated_at": "..."},
    {"adapter_id": "minwon24_submit", "ministry": "민원24", "purpose_category": "tax_filing", "decision": "ask", "source": "user", ...}
  ]
}
```

**Alternatives considered**:
- **Reuse Continue.dev YAML shape verbatim** — rejected: PyYAML dep.
- **Full JSON-LD with Continue.dev `@context`** — rejected: overkill, adds parsing complexity.
- **TOML** — rejected: less obvious write-atomicity story than JSON, more stdlib-touchy.

### 3.3 Hash-chain canonical JSON encoding

**Question**: Which canonical JSON encoding to use for hash-chain input?

**Decision**: **RFC 8785 JCS (JSON Canonicalization Scheme).**

**Rationale**:
- RFC 8785 is the only IETF-standardized canonical JSON encoding (2020).
- Reference Python implementation (`jcs` PyPI package) is MIT-licensed and **stdlib-only** internally — however, adding it as a dep violates AGENTS.md hard rule.
- **Our approach**: implement a ~50-line `kosmos.permissions.canonical_json` module that realizes RFC 8785 on top of stdlib `json` (sort keys + ASCII-escape-preservation + number canonicalization per IEEE 754). This is well within AGENTS.md's "stdlib-first" ethos. WS3 owns this module. Test coverage: RFC 8785 Appendix A test vectors (23 cases) via `test_canonical_json_jcs.py`.

**Alternatives considered**:
- **OLPC canonical JSON** — rejected: no IETF status, deprecated.
- **JSON-LD canonicalization (URDNA2015)** — rejected: heavyweight RDF-based, overkill.
- **Just `json.dumps(sort_keys=True)`** — rejected: doesn't normalize numbers (1.0 ≠ 1), doesn't preserve UTF-8 escapes deterministically across implementations; would not survive a hash-chain round-trip with different Python versions.
- **CBOR deterministic encoding (RFC 8949 § 4.2)** — rejected: non-JSON, breaks human-readability of ledger file which is an FR for manual audit.

**Test vectors**: WS3 tasks include porting RFC 8785 Appendix A into `tests/permissions/data/jcs_vectors.json` + running round-trip property tests.

### 3.4 HMAC key rotation policy

**Question**: Single-user MVP — what's the key rotation policy?

**Decision**: **Single active key + yearly manual rotation via ADR-gated CLI command.**

**Rationale**:
- Single-user MVP (per MEMORY `user_profile`) + local-filesystem ledger = no distributed key management.
- NIST SP 800-57 recommends cryptoperiod ≤ 1 year for HMAC keys used for log integrity — we match.
- **Automatic rotation** would introduce re-keying complexity (need to re-HMAC every record or maintain key-ID tagging) inappropriate for MVP.
- **Manual rotation** via `kosmos permissions rotate-key` CLI: generates a new key at `~/.kosmos/keys/ledger.key.NNN`, writes a `action=hmac_key_rotation, new_key_id=NNN` ledger record sealed with the **new** key (breaking chain deliberately at the rotation boundary), archives old key read-only at `~/.kosmos/keys/archive/ledger.key.N-1`. ADR-gated: rotation happens only with explicit operator intent.
- Verifier CLI is key-ID aware — reads `key_id` from each record and loads the matching archived key for verification of records before the rotation boundary.

**Alternatives considered**:
- **No rotation** — rejected: violates NIST SP 800-57 guidance and ISMS-P § 9.1.1.
- **Automatic quarterly rotation** — rejected: MVP complexity budget.
- **External KMS (AWS KMS / Vault)** — rejected: single-user local; crosses AGENTS.md "no cloud dep" boundary for core permission logic.

### 3.5 Deferred-item placeholder issues

**Question**: List all 7 items to be converted into placeholder GitHub issues at `/speckit-taskstoissues`.

**Decision**: Seven placeholders, each with the following stub body (to be created by `/speckit-taskstoissues` after `/speckit-tasks`):

```
Title: [Deferred from Spec 033] <item name>
Labels: deferred, permission-pipeline, needs-roadmap
Body: Deferred from Spec 033 (Permission v2) per Constitution §VI. Target Epic: <name from spec.md>. Placeholder for future scoping. See specs/033-permission-v2-spectrum/spec.md § Scope Boundaries.
```

Seven items (full list in § 2.2). **Rationale**: Constitution §VI mandates a tracking issue for every deferred item. Placeholders prevent ghost-work without forcing premature epic scoping.

---

## 4. Risk Matrix

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | RFC 8785 JCS implementation bug → silent chain-break on ledger verification | Low | High (silent integrity failure) | WS3 includes porting RFC 8785 Appendix A test vectors + Hypothesis property test (round-trip × 1000 random JSON values) | Backend Architect (WS3) |
| R2 | HMAC key file mode drift (user `chmod`s to 0644) → tampering exposure | Medium | High (ledger forgeable) | Boot-time mode check in `hmac_key.py` — refuses load if mode ≠ 0400 and reports as fail-closed; covered by `test_ledger_hmac_seal.py` key-missing & wrong-mode cases | Security Engineer (WS3 spot-check) |
| R3 | Rule store written by external editor with invalid schema between our read and next read | Medium | Medium (fallback to `default`, user sees warning but no data loss) | FR-C02 fail-closed fallback + mtime-based detection at every boot + schema regeneration via `/permissions edit` TUI | Backend Architect (WS2) |
| R4 | Shift+Tab in TUI dropping through to OS-level focus cycling on some terminals | Low | Low (ergonomic degradation) | Spec 287 already handles keychord capture; `test_mode_cycle.ts` covers the captured keychord path | Frontend Developer (WS1) |
| R5 | `consent_receipt_id` join drift against Spec 024 schema over time | Medium | High (audit query correctness) | `test_audit_coupling_consent_receipt_id.py` runs on every PR that touches either spec via a cross-test CI matrix; SC-009 is the gate | Backend Architect (WS5) |
| R6 | PIPA §22(1) individual-consent interpretation: users want single-click multi-purpose consent | High (UX pressure) | Medium (compliance regression if relaxed) | Spec-level block: FR-D07 is a hard requirement; no prompt-merging allowed. UX counterweight: `/permissions edit` lets power users batch-enable post-hoc, but each enable emits its own ledger record | Lead (policy decision) |
| R7 | Canonical JSON test-vector regressions after Pydantic v2 minor upgrade (floating-point repr changes) | Low | Medium (CI flakes) | Lock `pydantic >= 2.13` in pyproject.toml (already done); cross-version CI runs canonical JSON vectors against Pydantic v2.13, 2.14, 2.15 matrix | API Tester (final gate) |
| R8 | `kosmos permissions rotate-key` lost-key scenario (user deletes archive, old records unverifiable) | Low | High (irrecoverable audit gap) | CLI refuses rotation unless archive directory is writable; doc warning + ADR-gated; recovery procedure documented in quickstart.md § Troubleshooting | Backend Architect (WS3) |

---

## 5. Existing-Code Extension Analysis

Permission v2 lands in a **new** package (`src/kosmos/permissions/`) — no existing code is modified except via imports. Integration points:

| Touchpoint | Spec of origin | Change type | Risk |
|---|---|---|---|
| `src/kosmos/tools/base.py` (GovAPITool metadata) | Spec 024 v1 | **Read-only** — Permission v2 consumes `is_personal_data`, `is_irreversible`, `auth_level`, `pipa_class` fields; does not modify. | None |
| `src/kosmos/tools/registry.py` (`ToolRegistry.register`) | Specs 024 + 025 V6 | **Read-only** — Permission v2 adds a second call-time backstop; `register()`-time backstop unchanged. | None |
| `src/kosmos/audit/tool_call_record.py` (ToolCallAuditRecord) | Spec 024 v1 | **Read-only** — Permission v2 populates the existing `consent_receipt_id` optional field. | Depends on Spec 024 field stability (R5). |
| `src/kosmos/telemetry/otel.py` (span emission) | Spec 021 | **Read-only** — Permission v2 adds attributes via the existing `emit_span` helper. | None |
| `src/kosmos/mailbox/` (mailbox IPC) | Spec 027 | **Read-only** — `RequireHumanOversight` errors flow through existing mailbox; no protocol change. | None |
| `tui/src/ipc/frame_schema.ts` (frame union) | Spec 032 | **Read-only** — Permission v2 prompts piggyback on existing `payload_delta` frame with a new `payload_kind="permission_prompt"` discriminator. No new frame arm required. | None |
| `tui/src/app/command-registry.ts` (slash command routing) | Spec 287 | **Extend** — register 5 new slash commands (`/permissions` sub-tree). Existing commands unaffected. | None |

**Summary**: all integration points are **read-only or additive-only**. Permission v2 does not modify any existing Spec 024/025/021/027/287/032 surface — it layers on top. This keeps the blast radius of this Epic contained to its own package.

---

## 6. Phase 0 Exit Checklist

- [x] All 5 open questions resolved with decisions + rationale + alternatives considered
- [x] Every FR group (A..F) mapped to primary + secondary reference
- [x] Constitution §I Permission Pipeline mapping (OpenAI Agents SDK primary + CC reconstructed secondary) honored
- [x] 7 deferred items enumerated with target Epic + NEEDS TRACKING marker
- [x] 4 permanent-out-of-scope items validated with no spec-prose orphans
- [x] 8 risks identified with mitigations + owners
- [x] Existing-code extension analysis — all touchpoints are read-only or additive-only
- [x] Zero new runtime dependencies confirmed (SC-008 hard gate)

**Ready for Phase 1 Design & Contracts.**
