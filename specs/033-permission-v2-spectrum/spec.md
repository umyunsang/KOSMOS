# Feature Specification: Permission v2 — Mode Spectrum, Persistent Rule Store, PIPA Consent Ledger

**Feature Branch**: `033-permission-v2-spectrum`
**Created**: 2026-04-20
**Status**: Draft
**Epic**: #1297 (Permission v2 — Claude Code 5-mode + PIPA 동의 원장)
**Input**: Epic B scope — migrate Claude Code 2.1.88 PermissionMode spectrum (`default` / `plan` / `acceptEdits` / `bypassPermissions` / `dontAsk`) into KOSMOS's citizen-API harness, layer a persistent per-adapter rule store on top (tri-state `allow | ask | deny`), and attach a PIPA-compliant consent decision ledger so every data-access session carries a verifiable legal basis. Preserves Spec 024/025 fail-closed AAL invariants and Constitution §II bypass-immune checks.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 한 번의 명시적 동의로 민감 조회를 안전하게 반복 실행 (Priority: P1)

시민 사용자가 "지난 3개월 건강보험 진료 내역을 보여줘"라고 요청한다. 하네스는 해당 요청이 민감 개인정보(의료 기록)에 해당하므로 현재 PermissionMode가 `default`일 때 동의 프롬프트를 띄운다. 프롬프트에는 (a) 처리 목적, (b) 수집 항목, (c) 보유 기간, (d) 동의 거부 시 결과가 PIPA §15(2) 형식으로 표시된다. 사용자가 "이 세션 동안 허용"을 선택하면 결정이 consent ledger에 append-only로 기록되고, 같은 세션의 후속 동종 호출은 추가 프롬프트 없이 실행된다. 사용자가 "영구 허용"을 선택하면 persistent rule store에 `allow`로 저장되어 향후 세션에서도 적용된다.

**Why this priority**: Constitution §II(fail-closed) + §V(PIPA)의 핵심이자 Epic #1297이 존재하는 근본 이유. 이 스토리가 없으면 시민용 하네스는 합법적으로 배포될 수 없다.

**Independent Test**: mock HIRA 진료내역 어댑터(`is_personal_data=True`, `auth_level=AAL2`)에 대해 `default` 모드에서 호출 → 프롬프트 표시 확인 → 세션 동의 수락 → 동일 호출 2회 무프롬프트 통과 → ledger에 단일 레코드 존재 확인만으로 완전 검증 가능.

**Acceptance Scenarios**:

1. **Given** 모드 `default` + 해당 어댑터에 저장된 규칙 없음, **When** 사용자가 민감 조회 요청 → 하네스가 동의 프롬프트 제시 → 사용자가 "이 세션 허용" 선택, **Then** 첫 호출은 승인 후 실행되고 consent ledger에 `scope=session` 레코드 1건이 append되며 같은 어댑터·같은 목적의 후속 호출은 프롬프트 없이 즉시 실행된다.
2. **Given** 모드 `default` + 동일 조건, **When** 사용자가 "영구 허용" 선택, **Then** persistent rule store에 `{adapter_id, scope, decision=allow}` 레코드가 저장되고, 새 세션에서도 프롬프트 없이 실행되며, 같은 어댑터에 대한 `consent_receipt_id`가 세션 간에 유지·링크된다.
3. **Given** 모드 `default` + 동일 조건, **When** 사용자가 "거부" 선택, **Then** 호출은 차단되고 ledger에 `scope=denied` 레코드가 기록되며, 즉시 재시도 시 재프롬프트 없이 차단이 유지된다(세션 내 부정 결과 기억).

---

### User Story 2 — 동의·철회 이력을 언제든 검증 가능 (Priority: P1)

감사자·사용자·법무 대응자가 "2026-04-01~2026-04-20 구간 내 X 어댑터 호출의 동의 근거와 무결성"을 요구한다. 하네스는 ledger 파일을 SHA-256 hash chain + HMAC-SHA-256으로 봉인해 저장하며, CLI 질의 시 해당 구간 레코드와 체인 무결성 검증 결과를 출력한다. 사용자가 특정 어댑터 동의를 철회하면 철회 레코드가 ledger에 append되고, 향후 호출은 차단되며, 과거 수집된 데이터에 대한 처리 중단이 기록으로 남는다.

**Why this priority**: AI 기본법 §27(고영향 AI — 문서화 + 사람 감독) + PIPA §36(정정·삭제권) + ISMS-P 2.9.4(로그 보관·위변조 방지) 동시 충족에 필수. 감사 증적이 없는 시스템은 공공배포 불가.

**Independent Test**: 연속된 5개 동의 결정을 기록 → ledger 파일을 외부에서 1바이트 변조 → 검증 CLI 실행 시 "체인 무결성 파손: 레코드 N부터 불일치" 출력 확인만으로 검증 가능.

**Acceptance Scenarios**:

1. **Given** 5건의 동의 결정이 ledger에 기록된 상태, **When** 외부 프로세스가 3번째 레코드의 `consentTimestamp` 필드 1바이트 변조, **Then** 검증 CLI가 "chain broken at record index 3" 에러를 반환하고 종료 코드 ≠ 0이다.
2. **Given** 어댑터 X에 `allow` 규칙이 persistent rule store에 저장된 상태, **When** 사용자가 "X 어댑터 동의 철회" 명령 실행, **Then** rule store의 `allow` 규칙이 즉시 `deny`로 치환되고 ledger에 `action=withdraw, scope=previous_receipt_id` 레코드가 append되며, 다음 호출 시 프롬프트 없이 차단되고 오류 메시지에 "2026-04-20 사용자 철회" 사유가 포함된다.
3. **Given** ledger 디렉터리가 존재하지만 HMAC 키 파일(`~/.kosmos/keys/ledger.key`)이 부재, **When** 새 동의 결정 기록 시도, **Then** 하네스는 **결정 실행을 거부**하고 사용자에게 키 초기화를 요구하며, 어떤 도구 호출도 실행하지 않는다 (fail-closed).

---

### User Story 3 — 돌이킬 수 없는 제출은 어떤 모드에서도 묵음 통과 금지 (Priority: P1)

민원24·국세청 제출 어댑터처럼 `is_irreversible=True`인 도구는 `bypassPermissions`·`dontAsk` 모드로 세션이 설정돼 있더라도 단일 호출마다 명시적 확인 프롬프트를 제시한다. 프롬프트에는 어댑터가 수행할 구체적 행위(제출 대상, 파일명, 대상 기관), 철회 가능 여부, 동의 거부 결과가 표시된다. 확인을 누른 결정은 consent ledger에 `scope=single_irreversible_action` + `action_digest` 포함으로 기록되고, 같은 파라미터 재호출도 다시 프롬프트된다.

**Why this priority**: Constitution §II "bypass-immune checks" 절대 규칙 + AI 기본법 §27(고영향 AI — 사람 감독 의무화) 교차점. 이 스토리 실패 시 시민이 `bypassPermissions` 편의를 위해 전환한 순간 되돌릴 수 없는 제출이 묵음으로 발생할 수 있다.

**Independent Test**: mock 민원24 제출 어댑터(`is_irreversible=True`)를 `bypassPermissions` 모드에서 2회 연속 호출 → 매 호출마다 프롬프트 표시 확인 → ledger에 2건의 독립 `action_digest` 레코드 존재 확인만으로 검증 가능.

**Acceptance Scenarios**:

1. **Given** 세션 모드 `bypassPermissions` + 어댑터 `is_irreversible=True`, **When** 해당 어댑터 호출, **Then** 모드와 무관하게 확인 프롬프트가 표시되고, 확인 누락 시 호출 차단, 확인 시 실행 후 ledger에 `action=irreversible_submit, scope=single_action, action_digest=<파라미터의 SHA-256>` 레코드 append된다.
2. **Given** 세션 모드 `dontAsk` + persistent rule store에 해당 어댑터 `allow` 규칙, **When** 돌이킬 수 없는 제출 요청, **Then** **규칙이 무시되고** 확인 프롬프트가 강제 표시되며 사용자의 단일 액션 확인 전까지 호출이 차단된다.
3. **Given** 자동화된 에이전트(ant user)가 모드 `bypassPermissions`로 실행 중, **When** `is_irreversible=True` 도구 호출 시도, **Then** 호출은 즉시 차단되고 `RequireHumanOversight` 오류가 반환되며 ledger에 `action=blocked_no_human, reason=irreversible_requires_human` 레코드 append된다.

---

### User Story 4 — 부처별 tri-state 규칙을 영속화해 반복 호출을 단순화 (Priority: P2)

사용자가 평소 자주 쓰는 어댑터 5종(예: `kma_forecast_fetch`, `hira_hospital_search` 등)에 대해 개별로 `allow | ask | deny` 상태를 저장하고 세션을 재시작해도 유지되길 원한다. `~/.kosmos/permissions.json`에 JSON 스키마 형태로 저장되며, 파일은 사용자 편집 가능 + 하네스 부팅 시 무결성 검증 후 메모리 레지스트리에 로드된다. 어댑터 단위뿐 아니라 `{adapter_id, ministry, purpose_category}` 튜플 단위 규칙도 저장할 수 있다.

**Why this priority**: DX 개선. 없어도 P1 스토리로 시스템은 작동하지만 매 세션마다 재동의를 요구받아 UX가 무너짐. Continue.dev `~/.continue/permissions.yaml` tri-state 설계를 채용.

**Independent Test**: 3개 어댑터에 각각 `allow`, `ask`, `deny` 저장 → 세션 종료 후 재시작 → 각 어댑터 호출 시 대응하는 동작(무프롬프트 실행 / 프롬프트 / 즉시 차단) 발생 확인만으로 검증 가능.

**Acceptance Scenarios**:

1. **Given** `permissions.json`에 어댑터 X = `allow`, Y = `ask`, Z = `deny` 저장, **When** 세션 재시작 후 각각 호출, **Then** X는 무프롬프트 실행, Y는 프롬프트 후 결정, Z는 즉시 차단되며 어떤 경우에도 ledger에 누락 레코드가 없다.
2. **Given** 파일 변조 또는 스키마 위반(미지의 필드/잘못된 JSON), **When** 부팅 시 검증, **Then** 하네스는 rule store 로딩을 거부하고 전체 모드를 `default`로 폴백하며 경고 알림을 표시한다 (fail-closed).
3. **Given** 사용자가 TUI에서 `/permissions` 커맨드 실행, **When** 특정 어댑터의 상태를 `ask`에서 `allow`로 변경 후 저장, **Then** 파일이 원자적으로 교체되고(임시파일 + rename) 메모리 레지스트리가 재로드되며 ledger에 `action=rule_change, old=ask, new=allow` 레코드가 append된다.

---

### User Story 5 — 모드 전환 keychord + 고위험 모드 명시 명령 (Priority: P2)

사용자가 Shift+Tab 키체인으로 모드 스펙트럼을 순환(`default → acceptEdits → plan → [bypassPermissions | dontAsk] → default`)한다. `bypassPermissions`와 `dontAsk`는 로컬 발동이 아닌 **명시적 슬래시 명령**(`/permissions bypass`, `/permissions dontAsk`)으로만 진입 가능하며, 진입 시 사용자 확인 + ledger에 `action=enter_high_risk_mode` 레코드 기록, 종료 시 `action=exit_high_risk_mode`가 기록된다. TUI 상태바에 현재 모드가 상시 표시되고 고위험 모드는 별도 색상으로 강조된다.

**Why this priority**: Claude Code / Cursor / Continue.dev에 공통된 Shift+Tab 순환 idiom을 KOSMOS TUI에 이식하되, 고위험 모드 진입 의지를 명시화하여 감사성 확보. P1이 없어도 작동하지만 전환 UX가 무너지면 사용자가 모드를 이해 못함.

**Independent Test**: TUI에서 Shift+Tab 4회 → 표시 문자열이 `default → acceptEdits → plan → default`로 순환(고위험 모드 포함 안 됨) 확인 + `/permissions bypass` 명령 실행 시 확인 프롬프트 + 상태바 색상 변경 + ledger 기록 확인만으로 검증 가능.

**Acceptance Scenarios**:

1. **Given** 세션 시작 상태(모드 `default`), **When** Shift+Tab을 4회 눌러도 고위험 모드는 순환에서 제외, **Then** `default → acceptEdits → plan → default` 순환이 일어나고, `bypassPermissions`·`dontAsk`는 오직 슬래시 명령으로만 진입 가능하다.
2. **Given** 모드 `default`, **When** 사용자가 `/permissions bypass` 입력, **Then** 확인 프롬프트(위험 고지 + PIPA §15(2) 4-tuple + 자동 만료 시간) 표시 후 승인 시 모드가 `bypassPermissions`로 전환되고 상태바 색상이 빨강(warning)으로 변경되며 ledger에 `action=enter_high_risk_mode` 레코드 append된다.
3. **Given** 모드 `bypassPermissions`가 **N분**(정책으로 구성 가능) 이상 유지, **When** 하네스가 주기적 점검, **Then** 자동으로 `default`로 복귀하고 사용자에게 알림 + ledger에 `action=auto_exit_high_risk_mode, reason=timeout` 레코드 기록된다.

---

### Edge Cases

- **Ledger 디렉터리 부재 or 쓰기 실패** (`~/.kosmos/consent_ledger.jsonl`): 하네스는 일체의 민감 호출을 거부하고 부팅 단계에서 경고 후 동의 프롬프트 발동을 중단한다 (fail-closed; US1+US2 교차 요구).
- **HMAC 키(`~/.kosmos/keys/ledger.key`) 부재 or 권한 불일치(0400 아님)**: US2 시나리오 3에 따라 ledger append 거부, 도구 호출 차단.
- **Rule store 파일(`~/.kosmos/permissions.json`) JSON 파싱 실패**: US4 시나리오 2처럼 rule store 비활성화 + 모든 모드를 `default`로 폴백 + 경고.
- **사용자가 동의했지만 PIPA 4-tuple(목적·항목·보유기간·거부권) 중 하나라도 누락된 프롬프트에서 동의**: 프롬프트 빌더가 4-tuple 누락 시 즉시 UI 에러로 뜨고 호출 차단(PIPA §15(2) 위반 방지).
- **재동의 요구 조건 충족**: 어댑터의 목적·항목이 이전 동의 이후 변경되거나 동의 유효기간(기본 N개월, 어댑터별 override 가능) 초과 시 persistent rule store의 `allow`가 있어도 재프롬프트. ledger에 `action=reconsent_triggered, reason=<purpose_change|expiry>` 기록.
- **AAL 다운그레이드 시도**: 어댑터 `auth_level=AAL2`인데 세션이 AAL1 자격만 보유할 때, 모드·규칙과 무관하게 즉시 차단(Spec 025 V6 backstop).
- **Rule store와 ledger 불일치**(`allow`이나 과거 철회 레코드가 있음): 부팅 검증 단계에서 탐지 → ledger의 최신 레코드 우선 적용(덮어쓰지 않고 `action=reconciliation_applied` append), rule store 재생성.
- **돌이킬 수 없는 도구 + 에이전트 전용(human not present)**: US3 시나리오 3처럼 차단 + 사람 개입 요구.
- **동일 `consent_receipt_id`가 동시 세션에서 참조**: `consent_receipt_id`는 식별자일 뿐, 권한은 ledger 체인상 최신 레코드 기준으로 계산. 중복 참조 자체는 허용.

## Requirements *(mandatory)*

### Functional Requirements

#### Group A — Mode Spectrum (US1, US5)

- **FR-A01**: 하네스는 외부 공개 PermissionMode 5종(`default`, `plan`, `acceptEdits`, `bypassPermissions`, `dontAsk`)을 제공하며, 각 모드의 의미는 Claude Code 2.1.88 `PermissionMode.ts`의 외부 공개 모드 의미와 1:1 대응되어야 한다. 내부 모드(`auto`, `bubble`)는 이 Epic 범위에서 제외한다.
- **FR-A02**: TUI는 Shift+Tab keychord로 저위험 모드 순환(`default → acceptEdits → plan → default`)을 제공하고 고위험 모드(`bypassPermissions`, `dontAsk`)는 순환에서 **제외**한다.
- **FR-A03**: 고위험 모드 진입은 오직 명시적 슬래시 명령(`/permissions bypass`, `/permissions dontAsk`)으로만 허용되며, 진입 전 PIPA §15(2) 형식의 경고 프롬프트 + 타임아웃 정보를 표시해야 한다.
- **FR-A04**: 하네스는 모든 호출 지점에서 `ToolPermissionContext.mode`를 주입 가능한 값으로 노출하고, 현재 모드는 TUI 상태바·`/status` 커맨드·구조화 로그에서 관찰 가능해야 한다.
- **FR-A05**: 고위험 모드는 구성 가능한 자동 만료 시간(기본 30분, 어댑터·조직 정책으로 override 가능) 경과 시 `default`로 자동 폴백하고 ledger에 기록한다.

#### Group B — Killswitch (NON-NEGOTIABLE; US3)

- **FR-B01**: `is_irreversible=True`인 어댑터는 어떤 모드(`default`, `bypassPermissions`, `dontAsk` 포함) 또는 persistent rule store 규칙(`allow` 포함)에 의해서도 묵음으로 실행되어선 안 된다. 호출당 확인 프롬프트가 강제된다.
- **FR-B02**: `is_personal_data=True` + `auth_level ∈ {AAL2, AAL3}` 조합의 어댑터에 대한 호출은 유효한 consent ledger 레코드 없이 실행되어선 안 된다(Constitution §II "bypass-immune checks").
- **FR-B03**: 자동화된 에이전트(ant user, swarm worker)는 `is_irreversible=True` 도구 호출 시 자동 차단되어야 하며, 사람 개입 프롬프트를 `RequireHumanOversight` 오류로 변환해 반환해야 한다.
- **FR-B04**: Killswitch 검사는 permission mode 결정 전에 실행되며, 어떤 모드·규칙·자동화 설정으로도 override 불가능하다. 시도된 override는 ledger에 `action=killswitch_override_attempt` 레코드로 기록된다.

#### Group C — Persistent Rule Store (US4)

- **FR-C01**: 사용자 홈 디렉터리(`~/.kosmos/permissions.json`)에 tri-state(`allow | ask | deny`) 규칙을 JSON 스키마 형식으로 저장한다. 규칙 키는 최소 `{adapter_id}` 단위, 확장 키로 `{adapter_id, ministry, purpose_category}` 튜플을 지원한다.
- **FR-C02**: 규칙 파일은 부팅 시 스키마 검증을 거친 후 메모리 레지스트리에 로드되며, 검증 실패 시 전체 rule store를 비활성화하고 모든 모드를 `default`로 폴백한다.
- **FR-C03**: 규칙 변경은 원자적으로 수행되어야 한다(임시파일 쓰기 + rename). 부분 쓰기로 인한 깨진 상태가 발생해선 안 된다.
- **FR-C04**: 규칙 변경(create / update / delete)은 항상 consent ledger에 `action=rule_change` 레코드로 기록된다.
- **FR-C05**: TUI에서 `/permissions` 커맨드로 규칙 목록 조회·편집·삭제가 가능해야 하며, 외부 편집기로 직접 수정한 경우에도 부팅 시 감지해 반영된다.

#### Group D — PIPA Consent Ledger (US1, US2)

- **FR-D01**: 하네스는 `~/.kosmos/consent_ledger.jsonl`에 append-only JSONL 형식으로 모든 동의 결정 이벤트를 기록한다.
- **FR-D02**: 각 레코드는 Kantara Consent Receipt v1.1.0 필드(`consentReceiptID`, `piiControllers[]`, `services[]/purposes[]`, `consentTimestamp`, `jurisdiction`) + ISO/IEC 29184:2020 notice-binding 증거(`notice_hash`, `action_signifying_consent`) + KOSMOS 확장(`adapter_id`, `mode_at_decision`, `scope ∈ {session | persistent | single_irreversible_action | withdrawn}`)을 포함한다.
- **FR-D03**: 모든 프롬프트 UI는 PIPA §15(2)의 4-tuple(처리 목적·수집 항목·보유 기간·동의 거부 시 결과)을 표시해야 하며, 4-tuple 중 하나라도 누락된 프롬프트는 표시되지 않고 즉시 호출 차단된다.
- **FR-D04**: 각 레코드는 SHA-256 hash chain(`prev_hash || canonical_json(record)`) + HMAC-SHA-256(`~/.kosmos/keys/ledger.key`, 모드 0400)으로 봉인된다.
- **FR-D05**: 검증 CLI(`kosmos permissions verify`)는 체인 무결성을 검사하고, 체인 파손 시 종료 코드 ≠ 0과 파손 지점 index를 보고한다.
- **FR-D06**: 사용자는 언제든 특정 어댑터·어떤 목적의 동의를 철회할 수 있어야 하며, 철회는 `action=withdraw` 레코드로 append되고 rule store의 해당 규칙을 `deny`로 전환한다.
- **FR-D07**: PIPA §22(1)에 따라 개별 목적(`purpose_category`)마다 동의를 구분해 기록한다. 번들 동의는 허용하지 않는다.
- **FR-D08**: PIPA §18(2) 목적 외 이용 금지: ledger에서 동의된 목적과 다른 목적으로 같은 어댑터가 호출되면 재프롬프트가 발동되며, 기존 `allow` 규칙을 우회하지 않는다.
- **FR-D09**: 동의 유효기간(기본값은 정책으로 정의, 어댑터별 override 가능) 초과 또는 어댑터의 목적·항목·보유기간 중 하나라도 변경된 경우 재동의 요구가 발동된다.
- **FR-D10**: ledger 파일은 ISMS-P 2.9.4 + 개인정보 안전성 확보조치 §8에 따라 최소 2년 이상 보관되어야 하며, WORM(append-only) 의미론을 소프트웨어 수준에서 강제한다(수정·삭제 API 미제공).

#### Group E — LLM Synthesis Boundary (Constitution §V, MEMORY project_pipa_role)

- **FR-E01**: LLM에 전달되는 원시 개인정보는 컨텍스트 어셈블러 단계에서 가명화·요약되어야 하며, 가명화 실패 시 LLM 호출은 차단되고 ledger에 `action=synthesis_blocked_missing_pseudonym` 레코드 기록된다. KOSMOS는 PIPA §26 수탁자(기본값)로서 처리자 지침을 따르되, LLM 합성 단계만 controller-level 판단으로 carve-out된다.
- **FR-E02**: AI 기본법 §27 고영향 AI 요건에 따라 모든 세션은 (a) 사용자에게 고영향 AI 사용 사실을 알리는 세션 시작 배너 + (b) 사람 개입 요청 경로(`/escalate`) + (c) 결정 설명 가능성(최근 도구 호출 이력 + 동의 근거)을 제공해야 한다.

#### Group F — Integration & Audit (전체 스토리 공통)

- **FR-F01**: 모든 도구 호출의 `ToolCallAuditRecord`(Spec 024)는 `consent_receipt_id` 필드를 통해 consent ledger의 해당 결정 레코드와 링크되어야 한다.
- **FR-F02**: Permission v2 엔진은 Spec 025 V6 `auth_type` ↔ `auth_level` 불변식을 **우회하지 않으며**, 모드·규칙·동의 결정이 AAL backstop보다 먼저 평가되더라도 최종 결정은 AAL 불변식을 위반할 수 없다.
- **FR-F03**: OpenTelemetry span 속성으로 `kosmos.permission.mode`, `kosmos.permission.decision`, `kosmos.consent.receipt_id`를 모든 도구 호출 span에 첨부한다(Spec 021 호환).

### Key Entities

- **PermissionMode**: 5종 외부 모드 + 2종 내부 모드(제외). 각 모드는 title/shortTitle/symbol/color/external 필드를 갖는다.
- **PermissionRule**: `{adapter_id, ministry?, purpose_category?, decision: allow|ask|deny, created_at, updated_at, source: user|admin|system}` — rule store 엔트리.
- **ConsentDecision**: 단일 ledger 레코드. Kantara CR + ISO 29184 + KOSMOS 확장 필드 결합.
- **ConsentLedger**: 전체 hash-chain + HMAC 봉인된 append-only 파일. 무결성 검증 단위.
- **ToolPermissionContext**: `{mode, rule_hits, active_consent_receipts, is_bypass_available, is_dontask_available, high_risk_mode_expires_at}` — 도구 호출마다 주입.
- **AdapterPermissionMetadata**: 어댑터 선언 시 `{is_personal_data, is_irreversible, auth_level, pipa_class, purpose_categories, consent_validity_period}` 필드 제공(Spec 024 GovAPITool 확장).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 5가지 외부 PermissionMode가 모두 구현되고 각 모드에서 최소 1개의 자동화된 수용 테스트가 통과한다.
- **SC-002**: `is_irreversible=True` 어댑터에 대해 어떤 모드로도 묵음 통과가 발생하지 않음을 증명하는 회귀 테스트가 모든 5개 모드에 대해 각각 존재한다(총 ≥ 5개).
- **SC-003**: ledger 체인 검증 CLI가 단일 바이트 변조를 100% 탐지한다(20건 fuzz 테스트 기준).
- **SC-004**: 세션당 동의 프롬프트 중복 수가 스토리 US1 시나리오 1 기준 최대 1회로 제한된다.
- **SC-005**: 부팅 시 rule store·ledger·HMAC 키 파일 중 하나라도 검증 실패 시 하네스가 민감 호출 모드로 진입하지 않고 `default` + prompt-always 폴백 상태로 운영됨을 증명하는 테스트가 3개 이상 존재한다.
- **SC-006**: PIPA §15(2) 4-tuple 누락 프롬프트는 UI 단계에서 100% 차단된다(프로퍼티 기반 테스트 기준).
- **SC-007**: 고위험 모드 자동 만료(기본 30분)가 구성 가능하며, 설정값 대비 ±1초 이내 정밀도로 폴백이 발생함을 증명하는 통합 테스트가 존재한다.
- **SC-008**: Permission v2 도입으로 인한 도구 호출 경로 추가 지연이 p50 ≤ 5ms, p99 ≤ 20ms로 측정된다(rule store + ledger write 포함).
- **SC-009**: Spec 024 `ToolCallAuditRecord`와 consent ledger 간 `consent_receipt_id` join 누락률이 0%임을 증명하는 감사 테스트가 존재한다.

## Assumptions

- Epic 027(Agent Swarm)이 제공하는 mailbox 기반 IPC가 `RequireHumanOversight` 오류 전파 경로로 사용 가능하다(Spec 031 어댑터 메타데이터와 호환).
- Spec 024 `ToolCallAuditRecord` + Spec 025 V6 AAL backstop 이 이미 안정화되어 있으며, Permission v2 엔진은 두 spec의 불변식 위에 층(layer)으로 쌓인다.
- TUI(Spec 287)는 Shift+Tab 입력 캡처와 슬래시 명령 라우팅을 이미 제공한다(추가 입력 인프라 필요 없음).
- 사용자 홈 디렉터리(`~/.kosmos/`)에 대한 쓰기 권한은 하네스 프로세스가 보유한다(OS 수준 전제).
- `data.go.kr` API 포털은 공인인증(AAL2/AAL3) 레벨을 직접 검증해주지 않으므로, KOSMOS는 세션 수립 시 수집한 AAL 클레임을 신뢰한다(AAL claim provenance는 이 Epic 범위 밖).
- AI 기본법 §31 생성형 표시 요건은 Epic B 범위에서 세션 시작 배너 + 응답 말미 고지 수준까지만 다룬다(워터마킹은 별도 Epic).
- Kantara Consent Receipt v1.1.0 JSON 스키마는 KOSMOS ledger 레코드의 참조 스키마로 사용 가능하다(라이선스·사용권 검증 완료 전제, plan.md Phase 0에서 재확인).
- Claude Code 2.1.88 `PermissionMode.ts`의 `auto`/`bubble` 내부 모드는 본 Epic에서 구현하지 않으며 추후 별도 Epic으로 검토한다.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **모바일 네이티브 권한 UI**: KOSMOS는 터미널 기반 플랫폼으로, 모바일 OS 권한 모델 연동은 영구 범위 외.
- **Claude Code 내부 모드(`auto`, `bubble`)**: TRANSCRIPT_CLASSIFIER 피처 게이트 기반 내부 모드는 KOSMOS의 시민용 사용 사례와 무관. 영구 범위 외.
- **생체정보 기반 AAL3 획득 경로**: AAL 클레임 수집은 세션 수립 레이어 책임이며 본 Epic은 AAL을 "신뢰되는 입력"으로만 취급. 영구 범위 외.
- **AI 행동계획 §31 생성 콘텐츠 워터마킹**: 텍스트·이미지 워터마킹은 별도 연구 Epic에서 다룸. 영구 범위 외.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| 조직·멀티유저 정책 override (admin-level `permissions.json`) | 단일 사용자 하네스부터 안정화 후 확장 | Permission v3 (조직 배포) | #1434 |
| 동의 결정 원격 동기화(다중 디바이스) | 단말 1대 로컬 보관을 우선 | Sync Epic (세션 복원) | #1435 |
| Ledger 장기 보관 장소 분리(≥ 2년 요건 원격 저장) | 로컬 파일 기반이 먼저 | Audit Archive Epic | #1436 |
| 자동 재동의 만료 알림(배치 알림 서비스) | 대화형 세션 단위 재동의부터 | Notifications Epic | #1437 |
| GDPR/CCPA 매핑 확장(국외 거주자 지원) | PIPA 우선, 해외 규제는 전문가 감수 필요 | International Compliance Epic | #1438 |
| LLM 합성 단계 자동 가명화 엔진 | 가명화 실패 시 차단은 본 Epic, 자동 가명화 파이프라인은 별도 | Pseudonymization Engine Epic | #1439 |
| TUI `/permissions audit` 대화형 뷰어(ledger browsing UX) | CLI 검증 명령까지만 본 Epic | TUI Audit UX Epic | #1440 |
