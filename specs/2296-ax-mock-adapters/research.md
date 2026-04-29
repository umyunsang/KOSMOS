# Phase 0 Research — Epic ε #2296

**Date**: 2026-04-29
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Branch**: `2296-ax-mock-adapters`

This document records the architectural unknowns discovered while reading the existing codebase against the spec, and the design decisions taken to resolve them. Every decision cites the file or spec it was derived from.

---

## Decision 1 — Mock catalog lives in per-primitive sub-registries, not the main `ToolRegistry`

**Context**: Spec SC-003 says the registry will contain "exactly 28 entries (12 Live + 15 Mock + 1 meta = `resolve_location`)". Phase 0 reading of `src/kosmos/tools/register_all.py` and `src/kosmos/tools/mock/__init__.py` reveals that:

1. The main `ToolRegistry` boot path (`register_all_tools()` at `src/kosmos/tools/register_all.py:48`) registers exactly **14 entries**: 12 Live agency tools + 2 MVP-surface entries (`resolve_location` + `lookup`).
2. The 6 existing verify mocks register to a separate per-primitive sub-registry at `kosmos.primitives.verify._ADAPTER_REGISTRY` via `register_verify_adapter("family", invoke)` (see `verify_mobile_id.py:61`).
3. The 2 existing submit mocks register to `kosmos.primitives.submit._ADAPTER_REGISTRY`. The 3 existing subscribe mocks register to `kosmos.primitives.subscribe._ADAPTER_REGISTRY`.
4. The mocks register only when `kosmos.tools.mock` is **explicitly imported**. The production paths (`src/kosmos/cli/app.py:230` and `src/kosmos/ipc/mcp_server.py:246`) do **not** import the mock package; only test fixtures do. Production registries today contain **zero mocks**.

**Decision**: Treat the `15 Mock` count in the spec as referring to the **union of all sub-registry entries** (not "in main `ToolRegistry`"). The actual after-Epic-ε counts will be:

| Surface | After Epic ε | Composition |
|---|---|---|
| Main `ToolRegistry` | 16 | 12 Live + 2 MVP-surface (`resolve_location` + `lookup`) + 2 new lookup mock GovAPITools |
| `verify._ADAPTER_REGISTRY` | 10 families | 5 existing (after `digital_onepass` deletion) + 5 new `mock_verify_module_*` |
| `submit._ADAPTER_REGISTRY` | 5 families | 2 existing + 3 new `mock_submit_module_*` |
| `subscribe._ADAPTER_REGISTRY` | 3 families | unchanged |
| **Total mock surfaces** | **20** | 10 verify + 5 submit + 3 subscribe + 2 lookup |

The lookup mocks (`mock_lookup_module_hometax_simplified`, `mock_lookup_module_gov24_certificate`) are GovAPITools because the lookup primitive resolves IDs against the main `ToolRegistry` BM25 index — there is no per-primitive sub-registry for lookup.

**Spec amendment required**: The plan triggers a minor edit to `spec.md` SC-003 before `/speckit-analyze`, replacing the single "exactly 28" claim with the four-surface breakdown above. SC-008 (zero new runtime deps) and other criteria are unaffected.

**Alternatives considered**:
- **A. Move all 10 new mocks into the main `ToolRegistry`**: Rejected — would mean the new mocks bypass the per-primitive sub-registry contract and would not match how existing mocks are invoked (verify/submit by family parameter, not by tool_id). Inconsistent.
- **B. Move all existing per-primitive mocks into main `ToolRegistry`**: Rejected — large refactor outside this Epic's scope and would break Spec 031 interface that downstream specs depend on.

**Rationale**: Per-primitive sub-registries are the canonical pattern (Spec 031 prior art). The new mocks must follow it. The only correction needed is to the spec's count math, not to the architecture.

**Reference files**: `src/kosmos/tools/register_all.py:48-180` · `src/kosmos/tools/mock/__init__.py` · `src/kosmos/tools/mock/verify_mobile_id.py:61` · Spec 031 `cc-source-scope-audit.md § 2.3.3`

---

## Decision 2 — Existing 5 verify mocks gain transparency fields, do NOT get renamed

**Context**: FR-005 mandates the six transparency fields on every Mock adapter response. Existing verify mocks (`mock_verify_mobile_id`, etc.) return `MobileIdContext` (`src/kosmos/tools/mock/verify_mobile_id.py:43`) with no transparency fields. The new mocks ship with the `mock_verify_module_*` prefix — apparently a different naming family.

**Question**: Are the new mocks **replacements** for the existing ones (rename + delete), or **additions** (existing kept, new added)?

**Decision**: **Additions, not replacements**. The existing 5 verify mocks keep their tool IDs (`mock_verify_mobile_id`, `mock_verify_geumyung_injeungseo`, `mock_verify_gongdong_injeungseo`, `mock_verify_ganpyeon_injeung`, `mock_verify_mydata`) and gain the six transparency fields via a retrofit. The new 5 mocks ship under the `mock_verify_module_*` prefix to make the AX-channel-reference framing visible in the tool ID. Total verify mock families after Epic ε: **10**.

The new naming makes sense semantically:
- Existing `mock_verify_mobile_id` mirrors the **citizen-facing** ceremony (push notification, biometric) — the surface a citizen interacts with today
- New `mock_verify_module_modid` mirrors the **LLM-callable secure-wrapping** module the AX gateway is expected to expose to KOSMOS — a different shape (OAuth2.1 + scope-bound DelegationToken)

Both can co-exist; they answer different "what does this look like as a Mock?" questions.

**Alternatives considered**:
- **A. Rename + delete**: Rejected — breaks any test fixtures or downstream tooling that imports the existing mock symbols. Higher blast radius.
- **B. Skip transparency retrofit on existing 5**: Rejected — FR-005 says "every Mock adapter", and the regression test FR-006 would fail. Scope-creep is acceptable here because the retrofit is small (6 fields per response, one place each).

**Reference files**: `src/kosmos/tools/mock/__init__.py:42-51` · spec FR-001/FR-005/FR-006 · `delegation-flow-design.md § 12.7` (mock catalog re-design)

---

## Decision 3 — IPC frame: NEW arm, joins union as 21st discriminator value

**Context**: Spec FR-015 requires the backend to emit an `adapter_manifest_sync` frame at boot. Spec Assumptions section says "NEW arm" preferred. Phase 0 confirmed the existing `IPCFrame` discriminated union has 20 arms (`src/kosmos/ipc/frame_schema.py:943-965`).

**Decision**: Add `AdapterManifestSyncFrame` as the **21st arm** of the union, inserted between `PluginOpFrame` (the 20th, added by Spec 1636) and the closing bracket. The frame:

- Inherits from `_BaseFrame` (envelope version 1.0, role/correlation_id/timestamp)
- Discriminator: `kind: Literal["adapter_manifest_sync"]`
- Payload: `entries: list[AdapterManifestEntry]` + `manifest_hash: str` (SHA-256 of the canonical-JSON-serialised entries, for cheap change-detection)
- Role: `"backend"` (always emitted by Python backend)
- Emitted exactly once at successful boot, then again on hot-reload (deferred to a later epic per spec § Deferred Items)

**Why not extend `SessionEventFrame` or `PluginOpFrame`**: Both have a clear single-purpose discriminator and reuse would require an inner sub-discriminator on `kind="session_event"` or `kind="plugin_op"` — that breaks the Spec 032 ring-buffer replay invariant which assumes each `kind` value identifies one schema shape. Spec 032 verbatim: "20 arms with single-purpose discriminators". Adding a 21st keeps the invariant.

**Reference files**: `src/kosmos/ipc/frame_schema.py:943-965` · Spec 032 `frame_schema.py` · spec FR-015 + Assumptions

---

## Decision 4 — `mock_verify_module_any_id_sso` returns identity assertion only, NOT a `DelegationToken`

**Context**: Per `delegation-flow-design.md § 2.2`, Any-ID (the digital-onepass successor that launched 2026-01) is **identity-SSO only** — it does not issue OAuth bearer tokens or any delegation grant. Including it as a `mock_verify_module_*` adapter that returns a `DelegationToken` would misrepresent the real channel.

**Decision**: `mock_verify_module_any_id_sso` is the canonical Mock for "the citizen authenticated via Any-ID SSO, but no delegation channel exists for this ID family yet". Return shape: an `IdentityAssertion` Pydantic model containing `citizen_did: str | None`, `assertion_jwt: str`, `expires_at: datetime`, plus the six transparency fields. **Crucially, no `delegation_token` field, no `scope` field**. Downstream submit adapters that receive only an `IdentityAssertion` (not a `DelegationContext`) MUST reject the call with `DelegationGrantMissing` — preserving fail-closed semantics (Constitution § II).

This adapter exists to demonstrate the AX-gateway-spec gap: identity exists, delegation does not. It is the most policy-relevant Mock in the catalog for Public AI Impact Assessment 과제 54 readers.

**Reference files**: `delegation-flow-design.md § 2.2` · spec FR-001 + Assumptions

---

## Decision 5 — Mock-fixture backend for PTY smoke is a real Python process

**Context**: Spec FR-021 requires the PTY smoke harness to spawn a Mock-fixture backend (NOT `KOSMOS_BACKEND_CMD=sleep 60`). Codex P1 #2395 specifically called out the `sleep 60` placeholder as the reason the PTY smoke could not catch the dispatch path.

**Decision**: Add a new module `src/kosmos/ipc/demo/mock_backend.py` that:

1. Boots the full `ToolRegistry` + per-primitive sub-registries with all mocks registered (i.e., explicitly imports `kosmos.tools.mock`)
2. Emits the `adapter_manifest_sync` frame at startup (just like production)
3. Speaks the same JSONL frame protocol the production backend speaks (Spec 032)
4. Uses deterministic recorded fixtures so the US1 chain (verify → lookup → submit) returns the same 접수번호 every run
5. Logs to stderr only (no stdout pollution that would interfere with JSONL frames over stdout)

The PTY smoke launches the TUI with `KOSMOS_BACKEND_CMD="python -m kosmos.ipc.demo.mock_backend"`. End-to-end: real TUI ↔ real Python process speaking real frames ↔ real registry with real mock adapters. The only "mock" element is the recorded fixture data.

**Reference files**: spec FR-021 · auto-memory `feedback_runtime_verification` · auto-memory `feedback_pr_pre_merge_interactive_test` · Codex P1 #2395 body

---

## Decision 6 — Production registry boots with mocks registered

**Context**: Today, `src/kosmos/cli/app.py:230` and `src/kosmos/ipc/mcp_server.py:246` call `register_all_tools(registry, executor)` but do not import `kosmos.tools.mock`. Production therefore has zero mocks visible to the LLM. The US1 chain (citizen → 종합소득세 신고) cannot work in production unless the mocks are registered.

**Decision**: `register_all_tools()` gains a single line:

```python
import kosmos.tools.mock  # noqa: F401 — side-effect: registers all 20 mock surfaces
```

This is the same idiom used in the test fixtures. With this single change, production boots register all 20 mock surfaces (10 verify + 5 submit + 3 subscribe + 2 lookup-as-GovAPITool).

**Why this is safe**:
- All Mock adapter responses carry `_mode: "mock"` (FR-005) — the LLM and audit ledger always know.
- `_actual_endpoint_when_live` documents the hypothetical real URL — the citizen-facing surface can render this transparently.
- BM25 surfaces mocks with bilingual `search_hint`; the LLM sees them as discoverable but explicitly tagged.

**Why it's not premature**:
- The whole point of Epic ε is to demonstrate the AX-callable-channel reference shape end-to-end (US1).
- KOSMOS at student-tier has no Live agency channels for these domains, so Mock is the only available reference.
- The transparency fields make the Mock status loudly visible to operators, auditors, and the LLM itself.

**Reference files**: `src/kosmos/tools/register_all.py:107` (single insertion point) · spec § Assumptions ("the Mock backend used by the PTY smoke is a pure-Python process that imports `kosmos.tools.registry`")

---

## Decision 7 — Six transparency fields use a shared stamping helper

**Context**: FR-005 + FR-006 require every Mock adapter response to carry the six transparency fields. Hand-stamping each field on every response in 20 different adapter modules invites drift; the regression test (FR-006) catches drift but lets it merge before catching it.

**Decision**: Add `src/kosmos/tools/transparency.py` with a single function:

```python
def stamp_mock_response(
    payload: dict,
    *,
    reference_implementation: str,
    actual_endpoint_when_live: str,
    security_wrapping_pattern: str,
    policy_authority: str,
    international_reference: str,
) -> dict:
    """Add the six transparency fields to a Mock adapter response payload.
    Always stamps `_mode='mock'`. Caller-supplied values for the other five.
    Pure function — caller passes the dict, gets a new dict back."""
```

Every Mock adapter wraps its response builder with `stamp_mock_response(payload, reference_implementation=..., ...)`. The five caller-supplied values become per-adapter constants (typically declared at module top-level). This makes the contract impossible to drift accidentally and makes adding new fields a single-file change.

**Alternatives considered**:
- **A. Per-adapter inline literals**: Rejected — drift risk, regression test catches drift after merge.
- **B. Pydantic mixin model**: Rejected — most adapter responses are heterogeneous Pydantic types (`MobileIdContext`, `SimpleAuthContext`, etc.) and forcing them to inherit from a common mixin would couple unrelated schemas.

**Reference files**: spec FR-005/006 · `delegation-flow-design.md § 12.7` (6-field contract origin)

---

## Decision 8 — Audit ledger event kinds extend the existing Spec 035 union

**Context**: Spec 035 defined the consent-receipt JSONL ledger format at `~/.kosmos/memdir/user/consent/`. FR-012/013/014 add three new event kinds (`delegation_issued`, `delegation_used`, `delegation_revoked`) to the same ledger.

**Decision**: Extend the existing `LedgerEvent` discriminated union (in `src/kosmos/memdir/consent_ledger.py`, currently containing consent-receipt event kinds) with three new Pydantic models. Each carries a `kind: Literal["delegation_issued" | "delegation_used" | "delegation_revoked"]` discriminator, a `ts: datetime` field, and event-specific payload fields. The append path is unchanged: open file in append mode, `json.dumps()` one line, fsync. No new file, no new directory.

The TS-side `/consent` UI surface (Spec 035 component) will need a follow-up to render the new event kinds — that follow-up is captured in spec § Deferred Items as a Spec 035 follow-up.

**Reference files**: spec FR-012/013/014 · Spec 035 (`onboarding-brand-port`) consent-ledger schema

---

## Deferred Items Validation

Per Constitution § VI, every deferred item in the spec MUST have a tracking issue or be flagged `NEEDS TRACKING`.

Validation result for `spec.md § Scope Boundaries & Deferred Items § Deferred to Future Work` table:

| Item | Tracking Status | Validation |
|---|---|---|
| End-to-end smoke + policy-mapping doc | #2297 (Epic ζ, OPEN) | ✅ Verified open |
| System-prompt rewrite | #2298 (Epic η, OPEN) | ✅ Verified open |
| Manifest-frame chunking at scale | NEEDS TRACKING | ✅ Will be resolved by `/speckit-taskstoissues` |
| Hot-reload of adapter manifest mid-session | NEEDS TRACKING | ✅ Will be resolved by `/speckit-taskstoissues` |
| Live-mode promotion (Mock → Live) | NEEDS TRACKING | ✅ Will be resolved by `/speckit-taskstoissues` |
| Spec 035 ledger UI surface for `delegation_*` events | NEEDS TRACKING | ✅ Will be resolved by `/speckit-taskstoissues` |

Spec prose was scanned for unregistered deferral patterns (`"separate epic"`, `"future epic"`, `"Phase [2+]"`, `"v2"`, `"deferred to"`, `"later release"`, `"out of scope for v1"`). No matches without a corresponding table entry. Constitution § VI gate: **PASS**.

---

## Open Questions Resolved

| Question (raised at spec time) | Resolution |
|---|---|
| 9 vs 10 new mock count? | **10** — only this count balances the spec's mock-count assertion (resolved at spec authoring, captured in spec Assumptions) |
| Any-ID SSO returns delegation token? | **No** — identity-only per `delegation-flow-design.md § 2.2`. `IdentityAssertion` Pydantic model, distinct from `DelegationContext` (Decision 4) |
| IPC frame: new arm vs extend existing? | **New arm** — preserves Spec 032 invariant (Decision 3) |
| Where do existing/new mocks live in the registry? | **Per-primitive sub-registries** for verify/submit/subscribe; **main ToolRegistry** for lookup (Decision 1) |
| Should production register mocks at boot? | **Yes** — single import line in `register_all_tools()`; transparency fields make Mock status visible (Decision 6) |
| Retrofit transparency fields onto existing 5 verify mocks? | **Yes** — small change per file; shared stamping helper prevents drift (Decisions 2 + 7) |
| PTY smoke backend implementation? | **Real Python process** at `kosmos.ipc.demo.mock_backend` speaking JSONL frames, NOT `sleep 60` (Decision 5) |
| Audit ledger event kinds: new file or extend existing? | **Extend existing** Spec 035 union (Decision 8) |

No open questions remain for `/speckit-tasks`.

---

## Reference Mapping (per Constitution § I)

Every design decision in this Epic traces to a concrete reference. Cross-reference table:

| Decision | Primary reference | Secondary reference |
|---|---|---|
| 5-primitive harness preserved | Spec 031 (Five-Primitive Harness) | Spec 022 (MVP Main-Tool) |
| Per-primitive sub-registry for new mocks | Spec 031 prior art (`kosmos.tools.mock.__init__.py`) | Pydantic AI schema-driven registry pattern |
| `DelegationToken` envelope shape | OID4VP draft 21 (`delegation-flow-design.md § 5.6`) | Singapore Myinfo + APEX (`delegation-flow-design.md § 3.1`) |
| Six transparency fields contract | `delegation-flow-design.md § 12.7` (3rd correction final) | Estonia X-Road audit-by-design pattern |
| New `IPCFrame` arm | Spec 032 (envelope hardening) | restored-src CC tool registry sync pattern |
| TS `validateInput` two-tier resolution | Spec 2294 (5-primitive align with CC Tool.ts) | restored-src `getAllBaseTools()` |
| Audit ledger `delegation_*` events | Spec 035 (consent JSONL append-only) | Constitution § II fail-closed |
| Mock-fixture backend for smoke | auto-memory `feedback_runtime_verification` + `feedback_pr_pre_merge_interactive_test` | AGENTS.md § TUI verification (Layer 4 mandate) |
| `IdentityAssertion` vs `DelegationContext` distinction | `delegation-flow-design.md § 2.2` (Any-ID is SSO-only) | OAuth 2.0 RFC 6749 (token vs assertion) |
| Per-adapter transparency stamping helper | spec FR-005/006 + DRY principle | restored-src CC tool response stamping |

Constitution § I gate: **PASS**.
