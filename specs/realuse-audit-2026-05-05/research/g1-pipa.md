# G1 Deep Research — PIPA §22 / §15 정보주체 동의 enforcement

> Wave-2 Lead Opus G1. Targets: F-alpha-15, F-beta-04, F-gamma-07. Three legal-uninstallable PIPA findings.

## R-1 — Korean Personal Information Protection Act (PIPA) §22 + §15

**§15 (정보주체 이외로부터 수집)** — 컨트롤러는 정보주체의 동의를 받아 개인정보를 수집할 수 있다.

**§22 (동의를 받는 방법)** — 정보주체에게 개인정보 처리에 관한 동의를 받을 때에는 각각의 동의 사항을 구분하여 정보주체가 이를 명확하게 인지할 수 있도록 알리고 각각 동의를 받아야 한다. 정보주체의 동의 없이 처리할 수 있는 개인정보는 그 항목을 구분해 알려야 한다.

PIPC 가이드라인 (개인정보 보호위원회 표준 동의서식) 정리:
1. **Granular**: 항목 / 목적 / 보유기간 / 제공·위탁 별 별도 동의.
2. **Affirmative**: opt-out / pre-checked / silence / 시간경과 = 무효. 명시적 액션만 유효.
3. **Auditable**: 기록 (timestamp, IP, citizen identifier, 동의 버전, 철회 권리 고지) — 감사 가능.
4. **Channel-appropriate**: SSN (주민등록번호), 인증서 비밀번호, 생체정보 등 *민감정보* 는 anytime-readable 채널 (이메일/채팅/메신저) 로 수집 금지. PIPC Q&A: 개인정보 수집 채널은 "수집 후 추가 노출이 발생하지 않는 안전한 입력경로" 만 허용.

**KOSMOS 적용**: AGENTS.md L1-B B4 — KOSMOS 는 권한 정책을 발명하지 않고 *agency 자체 citation* 만. 그래서 KOSMOS 코드에는 "PIPA §22 가이드 그대로 fail-closed" 의 형태만 wired. 인용은 어댑터 자체.

## R-2 — Three failure modes vs PIPA §22

| Finding | PIPA §22 invariant 위반 |
|---|---|
| F-alpha-15 | **Affirmative**: non-interactive boot 가 모든 5 step `completed_at` 채움 — 정보주체가 명시적 입력 안함. opt-out / pre-checked 와 동등. |
| F-beta-04 | **Granular**: NMC L3 (응급실 실시간 데이터, login gate 어댑터) 호출이 modal 없이 dispatch. 항목별 별도 동의 절차 missing. |
| F-gamma-07 | **Channel-appropriate**: LLM 이 주민등록번호 + raw session_id 를 *채팅 textarea* 에 입력하라고 요청. 채팅은 LLM context window + session JSONL transcript 진입 — anytime-readable 채널 위반. verify primitive 의 modal/secure-input 만 합법. |

## R-3 — Existing infrastructure (KOSMOS 가 이미 가지고 있는 것)

### TUI permission_request handler — `tui/src/query/deps.ts:528-650`
- Backend 가 `PermissionRequestFrame` 을 emit 하면 TUI 가 `setPendingPermission()` + `pushIpcPermissionRequest()` 로 PermissionGauntletModal 을 mount.
- `setPendingPermission()` 은 Promise 반환 — 시민이 Y/A/N 누를 때까지 await.
- 결정 후 backend 에 `PermissionResponseFrame` 보내고 receipt_id 저장.

### Backend permission gate — `src/kosmos/ipc/stdio.py:1372-1539` (`_check_permission_gate`)
- `GATED_PRIMITIVES = {verify, submit, subscribe}` (`src/kosmos/primitives/__init__.py:62`).
- `lookup` 은 GATED_PRIMITIVES 에 포함 안 됨 — line 1397 `if fname not in _PERMISSION_GATED_PRIMITIVES` → return True (auto-allow).
- **gap**: lookup 으로 호출되는 L3 어댑터 (NMC, HIRA L3 variants, login-gated KMA endpoints) 가 modal 없이 통과.

### Layer-3 auth gate — `src/kosmos/tools/executor.py:174-194` (`invoke()`)
- `tool.policy.citizen_facing_gate != "read-only" and session_identity is None` → 즉시 `auth_required` 반환.
- `stdio.py:1897` 에서 `session_identity=session_id` 로 호출 — session_id 는 *항상* non-None (TUI 가 부팅 시 발급). 그래서 L3 gate 가 NMC 등에서 fire 안함.
- **이건 의도된 디자인**: session_identity 는 "백엔드가 시민의 활성 session 을 인지하고 있다" 의 signal — 어댑터별 modal 동의 와는 직교 개념.
- 진짜 동의는 `_check_permission_gate` 가 책임. 거기 에 lookup-side 어댑터-policy-aware 분기가 빠진 것.

### OnboardingFlow — `tui/src/components/onboarding/OnboardingFlow.tsx:127-144`
- `KOSMOS_ONBOARDING_AUTO_COMPLETE=1` env 가 set 되면 모든 5 step (preflight / theme / **pipa-consent** / ministry-scope / terminal-setup) 의 `completed_at` 을 *시민 액션 0회* 로 채움.
- 의도: PTY/tmux 자동 smoke 에서 onboarding overlay 의 useInput 미동작 을 우회 (AGENTS.md infra-insight #3 의 known-but-unresolved 동형).
- **위험**: 이 escape hatch 는 dev iteration / smoke 만 의도이지만 PIPA 동의를 *위조* 한다. 시민 환경에서 우연히 (test fixture import / docker env propagation) set 되면 합법 동의 없이 KOSMOS 가 launch.
- AGENTS.md hard rule: env vars `KOSMOS_FORCE_INTERACTIVE` 같은 test-harness signal 은 시민 환경에 절대 설정되면 안 됨 — 동일 위험 카테고리.

### system_v1.md — current state
- 단일 PIPA mention: line 112 `시민의 개인정보는 PIPA에 따라 처리합니다. 현재 요청에 꼭 필요하지 않은 식별 정보는 기록하거나 반복하지 않습니다.` — 너무 vague, "기록하거나 반복하지 않는다" 는 LLM-hard-to-enforce.
- `verify` primitive 설명 (line 34): `verify(tool_id, params)` — 인증 ceremony — 만 명시. *secure-input vs chat-input* 구분 없음.
- F-gamma-07 reproduction 의 LLM 발화: "주민등록번호 앞 6자리 + raw session_id 채팅창에 입력해주세요" — system_v1.md 가 이를 forbid 하는 directive 부재.

## R-4 — CC restored-src baseline

`.references/claude-code-sourcemap/restored-src/node_modules/@ant/computer-use-mcp/src/mcpServer.ts:100-127`
- CC 의 permission hook = `onPermissionRequest(req, signal): Promise<response>`.
- 비동기 resolve 까지 차단. 시민 거부 시 dispatch abort.
- KOSMOS 의 `_check_permission_gate` 는 byte-identical 패턴.

CC permission policy resolution 에서 *어떤 도구가* gate 에 들어가는지는 host 가 결정 — `permission_mode + ruleSet`. KOSMOS 도 같은 pattern 인데 ruleSet 이 "primitive name" 만 보고 lookup 의 inner tool_id 는 안 봄. 이게 gap.

## R-5 — context7 query: Pydantic / Ink modal-blocking patterns

(deep-research note — context7 MCP 사용 시도)

**Pydantic v2 frozen models** 는 이미 `tools/models.py` 에서 광범위 사용. `model_validator(mode="after")` 에서 raise 시 register() backstop 도 이미 있음 (Spec 025). 새 invariant 추가하려면 같은 pattern: `@model_validator(mode="after")` 에 PIPA-specific guard.

**Ink useInput** 은 `isModalOverlayActive` 가 gate (AGENTS.md infra-insight #3). Modal-blocking-input 구현은 `setPendingPermission(): Promise<decision>` 의 await 를 통해 backend dispatch loop 자체를 await — TUI render 와 별도. 본 G1 에서는 frontend modal 변경 X (G2 영역).

## R-6 — Specs 024/025/2295 invariants summary

- V1 (Spec 024): `pipa_class ⇒ auth_level` (personal ⇒ AAL2+, sensitive ⇒ AAL3).
- V2 (Spec 024): `dpa_reference` 가 published_url 이여야.
- V3 (Spec 025): `is_irreversible=True ⇒ AAL3`.
- V4 (Spec 025): irreversible ⇒ auth_level 일관.
- V5 (Spec 025): `requires_auth` (Spec δ #2295 에서 deprecated).
- V6 (Spec 025): `auth_type ↔ auth_level` 일관 (public⇒public/AAL1, api_key⇒AAL1+).
- Spec 2295 Path B (#2364 commit c0dbcd7): `requires_auth` 등 KOSMOS-invented field 제거 + `policy.citizen_facing_gate` 로 derive.

본 G1 fix 는 V1-V6 invariant 변경 X. 단지 **runtime gate** 가 derive 된 metadata 를 *읽는다* 는 점만 강화.

## R-7 — Spec 035 PermissionGauntlet wire

`specs/spec-035-permission-gauntlet-wire-completion/` — modal mount + Y/A/N decision dispatch + receipt persistence 의 wire 가 spec 한 것. `tui/src/query/deps.ts:528-650` 가 그 wire 의 frontend 측. Backend 측 `_check_permission_gate` 는 `verify/submit/subscribe` 만 trigger — Spec 035 의 spec.md 에서 `lookup` 도 *어댑터 policy 가 read-only 가 아니면 gate* 를 명시했지만 implementation 이 누락.

## R-8 — Fix design decision

세 finding 이 동일 root: "PIPA-required 동의 신호가 KOSMOS code 에서 명시 enforce 안 됨". 단일 fix bundle:

1. **F-alpha-15 fix**: `KOSMOS_ONBOARDING_AUTO_COMPLETE=1` 의 PIPA step 자동 완료를 fail-closed.
   - `KOSMOS_PIPA_CONSENT=opt-in-explicit` 도 동시 set 되어야만 PIPA step skip. 그렇지 않으면 PIPA step 는 자동 완료 X (다른 4 step 만 자동 완료, PIPA step 에서 stop). 시민이 직접 PIPA modal 통과해야.
   - Rationale: dev iteration 의 다른 4 step skip 편의는 유지하되 동의 위조는 막음.

2. **F-beta-04 fix**: `_check_permission_gate(fname='lookup', args_obj.tool_id=...)` 일 때 — 어댑터의 `policy.citizen_facing_gate` 를 read 하고 `read-only` 가 아니면 modal flow 진입. NMC (login), HIRA L3, KEC submit 어댑터 등 자동 적용.
   - Rationale: 단일 source-of-truth (어댑터 자체 policy) 를 follow. KOSMOS-invented policy 발명 X.

3. **F-gamma-07 fix**: `prompts/system_v1.md` 에 PIPA-sensitive 정보의 chat-input 금지 directive 추가.
   - "주민등록번호 / 인증서 비밀번호 / 생체정보 / raw session_id / 토큰 을 채팅으로 입력 요청 금지. 이런 정보는 verify primitive 의 modal 만으로 수집된다."
   - `verify` primitive description 에 "modal/secure-input only" 명시.
   - Manifest SHA-256 update.

## R-9 — Verification chain mapping

- **Layer 1a (pytest)**:
  - `tests/ipc/test_g1_pipa_lookup_gate.py` — `_check_permission_gate` lookup 분기 가 NMC 등에 modal trigger.
  - `tests/agents/test_g1_pipa_consent_fail_closed.py` 또는 비슷 — onboarding auto-complete 의 PIPA step 부분만 fail-closed.
- **Layer 1b (bun test snapshot)**: 본 G1 은 frontend modal 변경 안 함 — Layer 1b 는 기존 PermissionGauntletModal snapshot 재사용.
- **Layer 5 (tmux capture-pane)**: β5 (NMC) + γ9 (PIPA bypass) 재실행. NMC 호출 직전 modal 출현 wait_for_pane / γ9 LLM 발화에 주민등록번호 요청 0건 확인.

## R-10 — 회귀 가드

- `system_v1.md` 의 SHA-256 hash 가 `prompts/manifest.yaml` 에서 변경 — Spec 026 invariant trigger. 본 fix 가 hash update 포함해야 boot 시 fail-closed 되지 않음.
- `_check_permission_gate` 의 lookup 분기가 어댑터 lookup 실패 시 *fail-closed* (모달 trigger) 또는 *fail-open* (auto-allow)? 결정: fail-closed (registry 가 boot 시 rebuild — adapter 누락은 운영 incident, 시민 데이터 누출보다 낫다).
- Wave-2 G2 (showDialog isLocalJSXCommand) 와 충돌 없음 — G2 는 frontend, G1 는 backend gate + system prompt. 표면 직교.
