# Feature Specification: TUI ↔ K-EXAONE wiring closure (5-primitive demo surface)

**Feature Branch**: `feat/1978-tui-kexaone-wiring`
**Created**: 2026-04-27
**Last revised**: 2026-04-27 (user-directed scope expansion — 5-primitive coverage + Mock adapter activation)
**Status**: Draft
**Input**: User description: Epic #1978 — close the wiring gaps left by Spec 1633 (dead-code Friendli migration) and Spec 1634 (P3 tool system wiring) so the citizen-facing TUI can complete an end-to-end conversational turn against K-EXAONE that exercises **all five main-surface primitives** (`lookup`, `resolve_location`, `submit`, `verify`, `subscribe`) — using Live adapters where available and registered Mock adapters where the underlying API/SDK is unauthorised or OPAQUE — without further code-grep claims of closure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen finds public information through `lookup` (Priority: P1) 🎯 MVP step 1

A citizen launches KOSMOS, asks a natural-language question that needs public-data retrieval (e.g., "응급실 알려줘" or "강남구 응급실"), and the model uses the `lookup` primitive — internally chaining `resolve_location` for any place-name normalisation — to find and call the right ministry adapter. The streaming reply names the source ministry / API for transparency, and the entire round-trip completes within demo-grade latency.

**Why this priority**: This is the foundational "agentic harness reads public data" demonstration. It exercises two of the five primitives (`lookup` and `resolve_location`), uses the Live adapters that already exist (NMC, KMA, KOROAD, HIRA, NFA119, MOHW — 14 total registered), and is the highest-volume citizen interaction in the KOSMOS thesis. If this fails, every other primitive demo is irrelevant.

**Independent Test**: From a fresh TUI session, type "응급실 알려줘" and press Enter. Within 2 seconds the first response chunk streams; within 25 seconds the response completes with at least one source attribution naming the ministry / adapter that ran. Then type "강남구 응급실" — the response must demonstrate that `resolve_location` was invoked first (visible as a tool-execution event) before the lookup `fetch`.

**Acceptance Scenarios**:

1. **Given** a fresh TUI session with no prior conversation, **When** the citizen types "응급실 알려줘", **Then** the screen shows (a) the model's reasoning text, (b) a visible tool-invocation naming `lookup` with mode `search` then `fetch`, (c) a synthesised answer with attribution to the source ministry (e.g., "(국립중앙의료원 NMC)").
2. **Given** the citizen has just received an emergency-room reply, **When** they ask a follow-up that adds a place name ("강남구 응급실"), **Then** the model first invokes `resolve_location` to normalise the region, then `lookup` `fetch` with the normalised arguments — both tool events visible to the citizen.
3. **Given** the citizen's machine has no Anthropic credentials configured, **When** the TUI starts and they begin the lookup conversation, **Then** no warning about Anthropic, no outbound HTTPS request to `*.anthropic.com`, and no degradation in the response stream.

---

### User Story 2 — Citizen completes a write action through `submit` (Mock), with consent gauntlet visible (Priority: P1) 🎯 MVP step 2

A citizen asks for a public-sector write action — e.g., "교통 범칙금 납부 시뮬레이션해줘" (simulate paying my traffic fine). The model invokes the `submit` primitive with a registered Mock adapter (`mock_traffic_fine_pay_v1`), the permission gauntlet auto-classifies this as a write/irreversible-class call and pauses the conversation with a consent modal. The citizen sees what tool will run, what data class is affected, who the data goes to, and chooses one of three options. After consent, the Mock returns a structured `(transaction_id, status, adapter_receipt)` envelope — exactly what a real write action would — and the model summarises the result for the citizen.

**Why this priority**: `submit` is the largest surface-area primitive (absorbs 5 prior verbs: pay / issue_certificate / submit_application / reserve_slot / check_eligibility) and its activation is what proves "KOSMOS handles citizen *transactions*, not just queries". Bundling the permission gauntlet inside `submit`'s natural flow (rather than as a synthetic standalone story) is more honest — write transactions naturally trigger Layer 2/3 gauntlet evaluations, so the consent modal demo arrives organically.

**Independent Test**: From a clean session, type a sentence that should map to `submit(tool_id="mock_traffic_fine_pay_v1", params=...)`. The TUI must (a) show a tool-call event for `submit` with the resolved arguments, (b) render a consent modal with three buttons within 1 second of the gauntlet trigger, (c) on "allow once" produce a Mock receipt visible in the stream and a consent-receipt file on disk, (d) on "deny" suppress the call and let the model respond gracefully without the data.

**Acceptance Scenarios**:

1. **Given** a citizen in a fresh session, **When** they ask to simulate a traffic-fine payment, **Then** the model invokes `submit` and the TUI surfaces a consent modal naming the Mock adapter, the data class (sensitive — payment-class), the destination ("국민안전처 / 행안부 — 모의" because Mock), and the three citizen choices.
2. **Given** the citizen taps "allow once", **When** the Mock adapter executes, **Then** the screen renders the resulting `(transaction_id, status, adapter_receipt)` triple with field labels, and a consent receipt file appears at `~/.kosmos/memdir/user/consent/<receipt_id>.json` with `decision: "allow_once"`.
3. **Given** the citizen taps "deny", **When** the call would have run, **Then** the Mock adapter is NOT executed, the model receives a structured permission-denial as the tool result, and the model's follow-up reply explains the situation politely without inventing fake transaction data.
4. **Given** the citizen taps "allow for this session" once for `mock_traffic_fine_pay_v1`, **When** the same `submit(tool_id=...)` is invoked again later in the same session, **Then** the modal does NOT re-appear and the Mock executes silently.

---

### User Story 3 — Citizen authenticates through `verify` (Mock 6-family) (Priority: P2)

A citizen asks for identity verification — e.g., "공동인증서로 인증해줘" or "디지털원패스로 인증". The model invokes the `verify` primitive with `family_hint` set to one of the six Korean published tiers (`gongdong_injeungseo` / `geumyung_injeungseo` / `ganpyeon_injeung` / `digital_onepass` / `mobile_id` / `mydata`). The corresponding Mock adapter returns a structured `AuthContext` carrying both the published tier label (primary) and a NIST `AAL` hint (advisory). The citizen sees the resulting context summarised — "인증 완료 — 공동인증서 (AAL3 advisory)".

**Why this priority**: `verify` is what makes downstream privileged actions possible. It is P2 (not P1) because the MVP demo can stage `submit` against tools whose permission gauntlet does not require AAL2/3, but to demonstrate the *full* KOSMOS thesis — including AAL-gated write actions — `verify` must be visible and produce real-shape output. The 6-family discriminated union is also a key fidelity claim against the rejected single-AAL-dimension design (Spec 031 § US2).

**Independent Test**: Starting from a clean session, ask the model to authenticate using one named family. The TUI must (a) show a `verify` tool-call event with the family hint, (b) the Mock adapter returns within 2 seconds, (c) the model surfaces the resulting `AuthContext.published_tier` and `nist_aal_hint` fields in its reply, (d) repeat with a different family and observe the discriminated-union shape switch (different fields shaped per family).

**Acceptance Scenarios**:

1. **Given** a citizen in a fresh session, **When** they ask "공동인증서로 인증해줘", **Then** the model invokes `verify` with `family_hint="gongdong_injeungseo"`, the Mock returns an `AuthContext` carrying `published_tier="gongdong_injeungseo_aal3"` (or the exact ratified label) and `nist_aal_hint="AAL3"`, and the model's reply explicitly mentions both the Korean tier name and the AAL hint.
2. **Given** the citizen has authenticated as one family, **When** they ask in the same session "이번엔 디지털원패스로 인증해봐", **Then** a new `verify` call produces a different `AuthContext` with `family="digital_onepass"` and the model recognises the distinction in its reply.
3. **Given** any `verify` Mock adapter, **When** the citizen later inspects the transcript, **Then** the `family_hint` argument and the resulting `AuthContext` discriminator are visible alongside the call — full provenance of the authentication claim.

---

### User Story 4 — Citizen subscribes to disaster alerts through `subscribe` (Mock CBS) (Priority: P3 — demo-time gated)

A citizen asks "재난문자 구독해줘" and the model invokes `subscribe` with the Mock CBS broadcast adapter. The TUI shows the subscription handle and renders one or two simulated incoming alerts before the citizen ends the demo. This proves the streaming-frame path beyond a single round-trip and exercises the third under-utilised primitive.

**Why this priority**: `subscribe` is the only primitive whose value is most visible *over time*, not in a single turn. KSC 2026 has limited stage time, so this story is graceful to drop if the rehearsal runs long. It is captured here (rather than purely as a Deferred Item) because the Mock CBS adapter already exists — so the cost to wire it is small and the demo gain is real if time permits.

**Independent Test**: Starting from a clean session, type "재난문자 구독해줘". The TUI must (a) show a `subscribe` tool-call event, (b) render at least one simulated CBS alert delivered through the streaming frame within 30 seconds of subscription start, (c) close the subscription cleanly when the citizen ends the session.

**Acceptance Scenarios**:

1. **Given** a fresh session, **When** the citizen requests disaster-alert subscription, **Then** the model invokes `subscribe` with the Mock CBS adapter and the TUI surfaces a subscription handle (UUIDv7) the citizen can later reference.
2. **Given** an active CBS subscription, **When** the Mock simulates an incoming alert, **Then** the TUI renders the alert as a streamed event in the conversation flow without disrupting the prompt — proving the long-running stream coexists with normal turns.
3. **Given** the citizen ends the session (`/quit`), **When** the subscription closes, **Then** no orphaned process or socket remains — verified by post-quit inspection.

---

### Edge Cases

- **Backend process fails to start**: If the Python harness cannot launch (missing `KOSMOS_FRIENDLI_TOKEN`, file system corruption, etc.), the TUI must show a single human-readable diagnostic and not silently hang the citizen at a frozen prompt.
- **K-EXAONE stream interruption mid-reply**: If the upstream model connection drops while a reply is streaming, the TUI must mark the partial reply as incomplete, surface a "connection interrupted — retry?" affordance, and keep the conversation history coherent.
- **Tool returns a payload that violates the declared schema**: The harness must reject the result with a structured error frame; the TUI must show "the tool returned data we couldn't validate" rather than crash or render raw payload garbage.
- **Citizen presses Enter while a previous turn is still streaming**: The new input must be queued (not dropped, not interleaved) and processed after the current turn closes, preserving order.
- **Empty input**: Pressing Enter on an empty prompt must not start a turn or send an IPC frame.
- **Anthropic SDK code path is reached**: Defence-in-depth — even if some legacy module accidentally tries to call the deprecated SDK, the call must fail fast with a structured error rather than reach `anthropic.com`. This regression-prevention guard follows from FR-004.
- **`submit` Mock receipt ID collision**: Submit primitive derives `transaction_id` deterministically per Spec 031 T023 (URN over `{tool_id, params, adapter_nonce}`). The Mock adapter must declare a stable nonce so two identical-input submits produce the same receipt — this is observable to the citizen as "이 신청은 이미 기록되어 있습니다".
- **`verify` family_hint mismatch with session evidence**: Per Spec 031 FR-010, a mismatched hint must produce a structured `VerifyMismatchError`; the harness must NOT silently coerce one family to another.
- **Citizen revokes a session-scoped consent mid-session**: A subsequent `submit` for that tool must re-trigger the modal as if the original "allow_session" had never happened.
- **`subscribe` source closes upstream**: If the Mock CBS broadcast loop ends, the TUI must surface a "subscription ended" event and the model must be informed it cannot stream further from that handle.

## Requirements *(mandatory)*

### Functional Requirements

**Conversational core**
- **FR-001**: A citizen MUST be able to type any UTF-8 message into the TUI prompt and have it delivered to the model on Enter, with a visible end-to-end latency from keystroke-to-first-response-chunk under 2 seconds under nominal network conditions.
- **FR-002**: The assistant's reply MUST stream into the TUI incrementally as the model produces it, not appear all-at-once at the end of the turn.
- **FR-003**: The session MUST preserve conversation history across turns within one session, so multi-turn references work.
- **FR-004**: The system MUST NOT, under any normal operational path, make outbound network calls to `anthropic.com`. Operating with no Anthropic credentials available must be the supported default.

**Five-primitive main surface**
- **FR-005**: The model MUST be able to invoke each of the five main-surface primitives — `lookup`, `resolve_location`, `submit`, `verify`, `subscribe` — through the same conversational interface, without the citizen specifying tool IDs manually.
- **FR-006**: The TUI MUST render every primitive invocation as a visible tool-call event before the call runs, including the primitive name and resolved arguments.
- **FR-007**: After a primitive call returns, the result MUST flow back into the model's context so multi-step ReAct loops complete naturally; the TUI MUST render the resulting follow-up assistant message as a streamed event.
- **FR-008**: The system MUST forward the model's available primitive surface and the registered adapter set on each turn so the model can choose primitive + adapter combinations dynamically.

**Adapter coverage**
- **FR-009**: The `lookup` primitive MUST be wired to the existing 14 Live adapters (KMA × 6, KOROAD × 2, HIRA, NMC, NFA119, MOHW) so a citizen's information-seeking question can land on real public-data responses.
- **FR-010**: The `submit` primitive MUST have at least one registered Mock adapter (`mock_traffic_fine_pay_v1` from `src/kosmos/tools/mock/data_go_kr/fines_pay.py`) so the write-transaction demo runs without depending on OPAQUE government endpoints.
- **FR-011**: The `verify` primitive MUST have at least two registered Mock adapters spanning at least two families (e.g., `gongdong_injeungseo` and `digital_onepass`) so the discriminated-union design is visible in the demo.
- **FR-012**: The `subscribe` primitive MUST have at least one registered Mock adapter (CBS broadcast) for the streaming-frame demo path. (Demo-time gated — may be deferred per priority.)

**Permission gauntlet**
- **FR-013**: When a `submit` call's classification triggers consent (Layer 2/3 per Spec 033), the TUI MUST display a modal pausing the conversation, naming the tool, the data class, the destination ministry / API, and offering exactly three citizen choices: "allow once", "allow for this session", "deny".
- **FR-014**: The citizen's consent decision MUST be recorded as a structured receipt with a tracking ID; the citizen MUST be able to list and revoke prior receipts via a TUI command.
- **FR-015**: A "deny" decision MUST be communicated back to the model as a tool-result-denial; the conversation must continue with the model aware the call did not happen.
- **FR-016**: A "allow for this session" decision MUST suppress the modal for that exact tool for the rest of the session, but MUST NOT persist past session end.

**Boundary contracts**
- **FR-017**: All progress events that cross the TUI ↔ harness boundary MUST conform to the project's published frame schema; events that cannot be validated MUST be dropped with a logged structured error and MUST NOT crash the session.
- **FR-018**: For every conversational turn, the system MUST emit telemetry spans tagged with a session correlation ID such that an operator can later reconstruct the turn end-to-end (input → primitive calls → response) from telemetry alone.

**Failure surfaces**
- **FR-019**: When the harness process is unreachable or exits, the TUI MUST surface a single, human-readable diagnostic and offer a retry; it must not display a frozen empty prompt with no feedback.
- **FR-020**: When the model stream is interrupted mid-turn, the partial reply MUST be marked incomplete and the citizen MUST be offered a retry; the conversation history MUST remain consistent.

### Key Entities *(include if feature involves data)*

- **Citizen Session**: One contiguous use of the TUI by one person, identified by an opaque session ID. Owns the conversation history, consent receipts active for this session, AuthContext snapshots from `verify` calls, and a token-budget meter.
- **Conversation Turn**: One round-trip beginning at a citizen's Enter and ending when the model produces a final non-tool message. May include zero-to-many internal primitive calls.
- **Primitive Invocation Event**: A record that a specific primitive (`lookup` / `resolve_location` / `submit` / `verify` / `subscribe`) was called with a specific adapter, with arguments and a unique ID; pairs 1:1 with a Primitive Result event.
- **Primitive Result Event**: The output (or error) from a primitive invocation, addressed to its originating Invocation by ID. For `submit`, includes the deterministic `transaction_id`. For `verify`, carries the `AuthContext` discriminated union. For `subscribe`, carries the subscription handle.
- **Consent Decision**: A citizen's response to a permission gauntlet prompt — what tool, what scope (one-time / session), what timestamp, what receipt ID.
- **Consent Receipt**: A durable record of a Consent Decision the citizen can list, audit, or revoke.
- **AuthContext**: A typed binding between a citizen's session and an external authentication evidence — the output of `verify`. Carries `published_tier` (primary, Korean) and `nist_aal_hint` (advisory).
- **Subscription Handle**: A long-lived reference returned by `subscribe`, allowing the model to associate streamed events with a citizen-initiated subscription.
- **Frame**: The structured single-line message format used to carry every event across the TUI ↔ harness boundary; arms are pre-defined and validated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of fresh-launch greeting-or-lookup turns ("응급실 알려줘") complete within 25 seconds end-to-end across a sample of 20 trials, with the first response chunk visible in under 2 seconds.
- **SC-002**: 100% of `submit` Mock turns ("교통 범칙금 납부 시뮬") trigger a consent modal within 1 second of gauntlet evaluation; "allow once" path produces a Mock receipt and a memdir consent file; "deny" path correctly suppresses adapter execution. Across a sample of 5 trials.
- **SC-003**: Across at least two `verify` family invocations, the citizen-visible reply mentions both the Korean published tier label AND the AAL advisory hint, demonstrating the discriminated-union surface. Across a sample of 5 trials covering ≥ 2 families.
- **SC-004**: No fresh launch of the TUI produces any visible diagnostic mentioning Anthropic, API key, or `anthropic.com`. Verified by manual trial and by an outbound-network log filter showing zero hits to that domain during a 20-minute mixed-conversation session.
- **SC-005**: Across a 30-minute mixed citizen scenario session covering all primitives in scope, zero unhandled exceptions appear in the TUI; all error paths render a citizen-readable diagnostic.
- **SC-006**: The conversational frame types in scope (`assistant_chunk`, `tool_call`, `tool_result`, `permission_request`, `permission_response`) all show up live in observability traces during a single demo session — not as schema-only definitions.
- **SC-007**: The KSC 2026 demo script ("응급실 알려줘 → 교통 범칙금 납부 시뮬 → 공동인증서 인증") runs end-to-end on stage without manual intervention, exercising at least three of the five primitives consecutively. Verified by a rehearsal screen recording.
- **SC-008**: Every primitive in scope (`lookup`, `resolve_location`, `submit`, `verify` — with `subscribe` demo-time gated) has at least one registered adapter visible to the model on a fresh boot, verified by inspecting the model's tool inventory at session start.

## Assumptions

- The citizen has a working `KOSMOS_FRIENDLI_TOKEN` available in their environment, supplied during onboarding. KOSMOS does not handle FriendliAI key procurement.
- The citizen has Bun ≥ 1.2 and `uv` ≥ 0.5 installed. The TUI installer / quickstart handles preflight.
- The citizen has completed first-run onboarding (PIPA introduction, ministry-scope opt-in). Onboarding-flow changes are out of scope — owned by epic `1635-ui-l2-citizen-port`.
- Network reachability to FriendliAI's serverless endpoint is available. KOSMOS does not bring an offline LLM.
- The citizen is on macOS or Linux. Windows TTY behaviour is not part of this acceptance.
- All Live adapters used in US1 demos are already registered and validated under spec `1637-p6-docs-smoke`. This epic does not register new Live adapters.
- All Mock adapters used in US2/US3/US4 demos already exist as code under `src/kosmos/tools/mock/...` (validated 2026-04-27). This epic adds the *registration* sites (so the dispatcher discovers them) but does not author new Mock logic.
- The five primitives' Pydantic envelopes (`src/kosmos/primitives/{submit, verify, subscribe}.py` plus the existing `lookup` / `resolve_location` modules) are shape-stable from Spec 031 ship; this epic does not modify them.
- The CC 2.1.88 source map under `.references/claude-code-sourcemap/restored-src/` is the authoritative reference for any TUI behaviour parity question. The project memory and `AGENTS.md` are the authoritative reference for KOSMOS-specific deviation. `docs/vision.md` is a derivative description and is permitted to be corrected when it conflicts with the source map or memory.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **TUI visual layout changes** — KOSMOS preserves CC 2.1.88 visual fidelity at ≥90% per memory `feedback_cc_tui_90_fidelity`. Cosmetic re-skins are explicitly outside this epic.
- **Onboarding flow changes** — owned by epic `1635-ui-l2-citizen-port`.
- **New Live adapter authoring** — adapter coverage is owned by P3 follow-ups and the plugin DX surface (epic `1636-plugin-dx-5tier`); this epic only wires what exists.
- **New Mock logic authoring** — every Mock adapter referenced in this epic already exists under `src/kosmos/tools/mock/...`; this epic only adds registration sites.
- **Anthropic SDK bring-back** — the project has committed to a single fixed provider (FriendliAI K-EXAONE per `kosmos-migration-tree.md § L1-A`).
- **OPAQUE flows by Mock** — `gov24_submission`, `kec_xml_signature`, and `npki_portal_session` remain `docs/scenarios/`-only per memory `feedback_mock_vs_scenario`.
- **Mobile / web TUI** — KOSMOS is a terminal-native experience.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Multi-ministry agent swarm — coordinator phases, worker status visibility, multi-worker permission delegation, L4 demo scenario | Not part of this Epic's single-citizen demo arc; the four bridge frames (`coordinator_phase` / `worker_status` / their TUI consumers) need a real multi-worker scenario first. Wiring them here without that scenario would be schema-only theatre — exactly the failure mode this Epic is correcting. Materialised as a sibling successor Epic under Initiative #1631. | Successor Epic — "Agent Swarm TUI integration (027 closure + L4 frames)" | [#1980](https://github.com/umyunsang/KOSMOS/issues/1980) |
| Plugin DX TUI integration — `plugin_op` frame backend emit, plugin browser UI activation, citizen-installed plugin tool surfacing | Spec 1636 plugin DX infrastructure ships but TUI activation is unverified — install / list / remove commands exist as TS code but their wiring through `mcp.ts` ↔ `mcp_server.py` for plugin tool dispatch is not end-to-end demoed. Materialised as a sibling successor Epic under Initiative #1631. | Successor Epic — "Plugin DX TUI integration (1636 closure)" | [#1979](https://github.com/umyunsang/KOSMOS/issues/1979) |
| `subscribe` primitive demo (US4) — long-running CBS / RSS / REST-pull stream surfacing inside the conversation flow | If KSC 2026 stage time runs short during rehearsal, US4 is the most graceful drop because it uniquely depends on time-elapsed events. The Mock and primitive code stay registered (FR-012 still holds) but the user-facing demo step may be skipped. | This Epic, demo-time gated | [#2067](https://github.com/umyunsang/KOSMOS/issues/2067) |
| Streaming large attachment payload events (chunked binary / large JSON) | The demo surface uses only text + small structured tool/primitive results; large-payload streaming (PDF inline render of a large lookup result) is a separate UX problem. | Successor Epic — "Large payload streaming" | [#2068](https://github.com/umyunsang/KOSMOS/issues/2068) |
| Session resume across backend restart with replay-of-pending-turn | The current scope guarantees graceful diagnostic on backend death (FR-019). Replay-on-resume is a stronger property requiring durable per-turn checkpointing. | Successor Epic — "Session durability" | [#2069](https://github.com/umyunsang/KOSMOS/issues/2069) |
| Heartbeat / backpressure / push-notification frame surfaces | These are stability-signalling concerns. Wiring them without an active flow-control consumer would be schema-only — better to scope them with the operator-facing reliability epic. | Successor Epic — "Operator reliability surfaces" | [#2070](https://github.com/umyunsang/KOSMOS/issues/2070) |
| `verify` 6-family completeness — registering all 6 families' Mock adapters | The MVP demo surfaces 2 families (FR-011) to prove the discriminated-union shape. Registering the remaining 4 families (`geumyung_injeungseo`, `ganpyeon_injeung`, `mobile_id`, `mydata`) is mechanical follow-up work that does not affect the demo's correctness signal. | Successor Epic — "verify 6-family full coverage" | [#2071](https://github.com/umyunsang/KOSMOS/issues/2071) |
