# Feature Specification: Backend Permissions Cleanup + AdapterRealDomainPolicy (Epic δ)

**Feature Branch**: `2295-backend-permissions-cleanup`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "Epic δ — `src/kosmos/permissions/` 에서 ~20 KOSMOS-invented Spec 033 파일 삭제 + Spec 035 영수증 ledger 7 파일 보존 + `AdapterRealDomainPolicy` Pydantic v2 모델 신설 + 18 어댑터 metadata 마이그레이션."
**Authority** (cite in every downstream artefact):
- `AGENTS.md § CORE THESIS` — KOSMOS = AX-infrastructure callable-channel client (3rd thesis canonical); KOSMOS does NOT invent permission policy
- `AGENTS.md § Hard rules` — Pydantic v2 strict typing for tool I/O; no `Any`; English source text; `KOSMOS_` env vars; never add deps outside spec
- `.specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)` — KOSMOS-invented 권한 분류 (5-mode spectrum / pipa_class / auth_level / permission_tier / is_personal_data / is_irreversible / requires_auth / dpa_reference) MUST NOT be reintroduced
- `.specify/memory/constitution.md § III Pydantic v2 Strict Typing (NON-NEGOTIABLE)` — 모든 도구 I/O 는 Pydantic v2 모델, `Any` 금지
- `specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 2.3.1, § 2.3.2`
- `specs/1979-plugin-dx-tui-integration/domain-harness-design.md § 3.2` — adapter real-domain policy citation pattern
- `specs/1979-plugin-dx-tui-integration/delegation-flow-design.md § 12` — final canonical architecture
- Memory feedback `feedback_tool_wrapping_is_the_work` — adapter metadata migration 이 작업 단위
- Memory feedback `feedback_no_stubs_remove_or_migrate` — 제거 또는 마이그레이션, 스텁 X

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Spec 033 KOSMOS-invented permission residue 제거 (Priority: P1) 🎯 MVP

KOSMOS Lead 가 `src/kosmos/permissions/` 의 KOSMOS-invented Spec 033 잔재 파일을 모두 제거한다. Constitution II 가 NON-NEGOTIABLE 하게 금지한 5-mode spectrum / pipa_class / auth_level / permission_tier / is_personal_data / is_irreversible / requires_auth / dpa_reference 같은 분류가 코드 레벨에서 0 회 잔존해야 한다. 단 Spec 035 영수증 ledger 관련 파일 (ledger.py / action_digest.py / hmac_key.py / canonical_json.py / audit_coupling.py / ledger_verify.py / otel_emit.py / otel_integration.py) 은 보존해 receipt 발행 시스템이 계속 작동.

**Why this priority**: KOSMOS thesis (CC + 2 swaps) 의 boundary 가 코드에서 enforce 되려면 KOSMOS-invented 권한 정책이 0 이어야 한다. 백엔드 잔재가 남아 있으면 어댑터 metadata 마이그레이션 (US3) 이 "정리 안 된 위에 새 모델 얹기" 가 되어 의미가 흐려진다.

**Independent Test**: cleanup 후 (a) `src/kosmos/permissions/` 디렉토리에 14 잔재 source file + `steps/` 0 회 잔존 + Spec 035 receipt 8 파일 + `models.py` (SessionContext-only) + `credentials.py` + `__init__.py` 만 보존, (b) FR-006 narrowed grep gate 출력 0 행 (어댑터 metadata + `src/kosmos/permissions/` 영역만), (c) `uv run pytest` baseline 대비 NEW failure 0.

**Acceptance Scenarios**:

1. **Given** `src/kosmos/permissions/` 의 14 Spec 033 잔재 source file + `steps/` list, **When** Lead 가 각 파일의 importer 를 `grep -r` 로 추적해 importer 도 함께 cleanup 후 잔재 파일 삭제, **Then** `git ls-files src/kosmos/permissions/` 가 11 entry (Spec 035 receipt 8 + `models.py` SessionContext-only + `credentials.py` + `__init__.py`) 만 출력.
2. **Given** Constitution II 금지 토큰 list, **When** FR-006 narrowed grep gate 실행 (어댑터 metadata + `src/kosmos/permissions/` 영역), **Then** 0 행.
3. **Given** cleanup 완료, **When** `uv run pytest` 실행 + baseline 비교, **Then** NEW failure 0.

---

### User Story 2 — `AdapterRealDomainPolicy` Pydantic v2 모델 신설 (Priority: P2)

KOSMOS-invented 권한 분류를 대체할 단일 표준 모델 `AdapterRealDomainPolicy` 를 Pydantic v2 strict 로 신설한다. 본 모델은 어댑터가 (a) 한국 정부 기관의 published 정책 URL 을 인용하고, (b) 시민에게 노출할 gate 카테고리 (`read-only` / `login` / `action` / `sign` / `submit`) 를 선언하며, (c) 정책 인용의 마지막 검증 시점을 박제하는 단일 진실원으로 작동한다.

**Why this priority**: KOSMOS = AX-infrastructure callable-channel client thesis 의 핵심 — KOSMOS 는 권한 정책을 발명하지 않고 기관의 정책을 cite 한다. `AdapterRealDomainPolicy` 가 그 cite 의 codified 형태. US1 (잔재 제거) 후 US3 (어댑터 마이그레이션) 진입 전 본 모델이 박제되어 있어야 함.

**Independent Test**: 모델이 `src/kosmos/tools/models.py` 에 추가되고, frozen=True + `extra="forbid"` 로 strict 강제, 모든 필드 type-annotated, `uv run pytest` 가 모델의 schema 검증 케이스 통과.

**Acceptance Scenarios**:

1. **Given** 신설 요구 — 4 필드 (`real_classification_url: str`, `real_classification_text: str`, `citizen_facing_gate: Literal["read-only","login","action","sign","submit"]`, `last_verified: datetime`), **When** Pydantic v2 모델 정의 + `model_config = ConfigDict(frozen=True, extra="forbid")` 적용, **Then** 다른 모듈에서 import 가능 + frozen 위반 시 ValidationError 발생.
2. **Given** 모델 정의 완료, **When** 빈 url 또는 빈 text 로 인스턴스 시도, **Then** Pydantic v2 가 ValidationError 로 거절 (str 필드는 non-empty validator 적용).
3. **Given** `citizen_facing_gate` 가 5 enum 외 값 시도, **When** 인스턴스화 시도, **Then** ValidationError.

---

### User Story 3 — 18 어댑터 metadata 마이그레이션 (Priority: P3)

기존 18 어댑터 (KOROAD ×2 + KMA ×6 + HIRA ×1 + NMC ×1 + NFA119 ×1 + MOHW ×1 + 6 mocks) 의 metadata 를 Constitution II 금지 필드에서 `AdapterRealDomainPolicy` 인스턴스로 옮긴다. 각 어댑터는 기관의 published 정책 URL 을 cite 하며, KOSMOS 가 권한을 invent 하지 않음을 코드로 증명한다.

**Why this priority**: 본 마이그레이션이 "Tool wrapping is the work" 의 1:1 적용. 한 어댑터당 한 metadata block 마이그레이션이 단위 작업. US1+US2 완료 후 진입.

**Independent Test**: 18 어댑터 모두가 (a) 금지 필드 0 회 잔존, (b) `policy: AdapterRealDomainPolicy` 인스턴스 보유, (c) 모든 인스턴스의 `real_classification_url` 이 non-empty + 기관 published 정책 URL 형식. `uv run python -c "from kosmos.tools.registry import ToolRegistry; r = ToolRegistry(); ..."` 로 18 어댑터 모두 import 통과.

**Acceptance Scenarios**:

1. **Given** 18 어댑터 metadata, **When** 각 metadata 에서 `auth_level / pipa_class / is_personal_data / dpa_reference / is_irreversible / requires_auth` 제거 + `AdapterRealDomainPolicy` 추가, **Then** 모든 어댑터가 새 모델로 import 통과.
2. **Given** 마이그레이션 완료 어댑터, **When** registry 가 그 어댑터의 metadata 를 노출, **Then** `policy.real_classification_url` 이 https://... 형식 + non-empty.
3. **Given** schema validation, **When** `uv run pytest` 의 어댑터 metadata 검증 케이스 실행, **Then** 18 어댑터 모두 pass.

---

### Edge Cases

- **잔재 파일이 Spec 035 receipt 파일을 import 하는 경우**: 잔재 파일 삭제 시 Spec 035 receipt import 도 dead 가 되지 않는지 확인. 일반적으로 receipt 는 standalone, 잔재 → receipt 의 단방향 import 가 dead 화는 없음.
- **`AdapterRealDomainPolicy` 의 `last_verified` 필드 정의 시점**: 마이그레이션 시점의 timestamp 를 사용하면 거짓말 (기관 정책 URL 의 실제 검증을 안 했으니) — 본 spec 은 `last_verified=datetime.fromisoformat("2026-04-29")` 형태로 마이그레이션 시점을 명시하고, 실 정책 검증은 후속 spec 에서 진행 (Deferred Items 에 추적).
- **18 어댑터 중 일부의 정책 URL 이 불확실한 경우**: 개별 spec dir Decision Log 에 `placeholder + TODO 마커` 박제 + Deferred Items 에 후속 검증 작업으로 추적.
- **`uv run pytest` 의 pre-existing failure**: baseline 측정 후 동일 failure 만 유지되어야 함. 잔재 파일 삭제로 인한 import 누락 등 NEW failure 는 0 이어야.
- **금지 토큰 grep 이 docstring 또는 docs/ 의 historical reference 에서 매치**: 본 Epic 의 grep 검사는 `src/kosmos/` 하위 source code 만 대상. docs/ 의 historical reference (예: `cc-source-scope-audit.md` 자체) 는 대상 외.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `src/kosmos/permissions/` 의 KOSMOS-invented Spec 033 잔재 source file 14개 + `steps/` 디렉토리가 100% 삭제되어야 한다 (deletion 대상: `aal_backstop.py`, `adapter_metadata.py`, `bypass.py`, `cli.py`, `killswitch.py`, `mode_bypass.py`, `mode_default.py`, `modes.py`, `pipeline.py`, `pipeline_v2.py`, `prompt.py`, `rules.py`, `session_boot.py`, `synthesis_guard.py`, `steps/`). `__init__.py` 는 Spec 035 receipt 모듈 + `SessionContext` (`models.py` 잔존) + credentials helpers (`credentials.py` 잔존) 만 export 하도록 재작성.
- **FR-002**: Spec 035 영수증 ledger 8 파일이 보존되어야 한다: `ledger.py`, `action_digest.py`, `hmac_key.py`, `canonical_json.py`, `audit_coupling.py`, `ledger_verify.py`, `otel_emit.py`, `otel_integration.py`. 각 파일은 receipt 발행 use case 를 cite 하는 docstring 보유.
- **FR-002a** (NEW): KOSMOS-needed 보조 파일 2개도 보존:
  - **(a) `credentials.py`** — `src/kosmos/recovery/auth_refresh.py` 가 `candidate_env_vars` / `resolve_credential` 을 import 해 credential resolution 에 사용.
  - **(b) `models.py`** — Spec 035 receipt schema 가 의존하는 클래스들 + harness session schema 만 잔존:
    - `SessionContext` — `src/kosmos/cli/{app,repl}.py` + `src/kosmos/engine/models.py` + observability tests 가 import (harness session state, KOSMOS-invented permission policy 가 아님 — 단순 session bookkeeping).
    - `ConsentDecision`, `ConsentLedgerRecord`, `LedgerVerifyReport`, `ToolPermissionContext`, `AdapterPermissionMetadata` — Spec 035 ledger / ledger_verify / audit_coupling / otel_integration 의 schema dependency. **historical-record schema** (영수증은 결정 시점의 사실 박제, 권한 정책 invention 아님). FR-006 명시 제외 영역 적용.
    - 삭제 대상 (KOSMOS-invented orchestration): `AccessTier`, `PermissionDecision`, `PermissionCheckRequest`, `PermissionStepResult`, `AuditLogEntry`, `PermissionRule`.
    - `PermissionMode` Literal — `modes.py` 가 삭제되므로 **inline 으로 `models.py` 에 통합** (Spec 035 receipt schema 가 `mode` 필드로 참조).
- **FR-003**: `AdapterRealDomainPolicy` Pydantic v2 모델이 `src/kosmos/tools/models.py` 에 추가되어야 한다. 필드: `real_classification_url: str`, `real_classification_text: str`, `citizen_facing_gate: Literal["read-only","login","action","sign","submit"]`, `last_verified: datetime`. `model_config = ConfigDict(frozen=True, extra="forbid")`. 모든 str 필드는 non-empty 검증.
- **FR-004**: 18 어댑터 (KOROAD ×2 + KMA ×6 + HIRA ×1 + NMC ×1 + NFA119 ×1 + MOHW ×1 + 6 mocks: barocert / cbs / data_go_kr / mydata / npki_crypto / omnione) 의 metadata 가 모두 `policy: AdapterRealDomainPolicy` 필드를 가져야 한다.
- **FR-005**: 모든 18 어댑터의 `policy.real_classification_url` 이 non-empty + URL 형식 (https:// 시작) 이어야 한다. 불확실 URL 은 `# TODO: verify URL` 마커 + Deferred Items 추적.
- **FR-006** (NARROWED 2026-04-29): KOSMOS 가 발명한 권한 분류 토큰이 **어댑터 metadata 영역**에서 0 회 잔존해야 한다. Grep gate 명시:
  - **검사 대상 (must be 0 lines)**: `grep -rE 'pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference' src/kosmos/tools/koroad/ src/kosmos/tools/kma/ src/kosmos/tools/hira/ src/kosmos/tools/nmc/ src/kosmos/tools/nfa119/ src/kosmos/tools/ssis/ src/kosmos/tools/mock/`
  - **명시 제외 (KOSMOS-needed legitimate uses, NOT permission policy invention)**:
    - `src/kosmos/permissions/` — Spec 035 receipt schema (`ConsentLedgerRecord` / `ConsentDecision` / `ToolPermissionContext` / `AdapterPermissionMetadata` 등) 가 **historical-record Optional 필드**로 이 토큰들을 담는다. 영수증은 결정 시점의 사실을 박제하는 schema 이지, KOSMOS 가 새 권한 정책을 invent 하는 곳이 아니다. (Spec 035 ledger v1.0.0 schema invariant 보존 — 변경 시 hash chain 검증 깨짐.)
    - `src/kosmos/security/audit.py` — Spec 024 `ToolCallAuditRecord` invariant (TOOL_MIN_AAL 매트릭스 enforce, 어댑터가 declare 한 field 의 consistency 만 강제 — 권한 정책 발명 X)
    - `src/kosmos/tools/permissions.py` — Spec 025 v6 `compute_permission_tier(auth_level, is_irreversible)` (UI-C layer derivation; 같은 invariant)
    - `src/kosmos/tools/register_all.py` — single comment referencing `compute_permission_tier`
    - `src/kosmos/plugins/checks/q3_security.py` — Spec 1636 plugin Q3-V2/V3/V4/V6 invariant gates
    - `src/kosmos/plugins/checks/q2_failclosed.py` — Spec 1636 plugin Q2 fail-closed gate
    - `src/kosmos/plugins/cli_init.py` — Spec 1636 plugin template (`auth_level="AAL1"` default)
    - `src/kosmos/plugins/tests/*` — plugin test fixtures
    - `src/kosmos/ipc/tx_cache.py` — Spec 032 T041 idempotency pin enforcement (`is_irreversible=True` ⇒ pinned cache)
    - `src/kosmos/ipc/demo/register_irreversible_fixture.py` — Spec 032 demo fixture
    - `src/kosmos/recovery/auth_refresh.py` — credential resolution (uses `kosmos.permissions.credentials`)
  - **Rationale**: KOSMOS thesis (CC + 2 swaps) 는 KOSMOS 가 어댑터 metadata 단계에서 새 권한 정책을 *발명*하지 않음을 의미한다. 위 제외 항목들은 (a) 어댑터가 **이미 declare 한** field 들의 *consistency invariant* 만 강제하거나 (Spec 024/025/1636 Q3), (b) infrastructure-level state (Spec 032 idempotency cache, Spec 035 receipt ledger schema) 를 다룬다 — 권한 정책 발명이 아니다. 어댑터 metadata 자체에서 KOSMOS-invented field 가 0 이면 thesis enforce 됨.
- **FR-007**: `uv run pytest` 의 NEW failure 가 0 이어야 한다 (baseline 비교 기준).
- **FR-008**: 신규 runtime dependency 0 — `pyproject.toml` 의 `[project.dependencies]` 에 추가 0 (AGENTS.md hard rule).
- **FR-009**: 본 Epic 의 모든 commit message 와 spec 산출물이 Authority 5+ reference (AGENTS.md / Constitution II + III / cc-source-scope-audit / domain-harness-design / delegation-flow-design) 를 인용해야 한다.
- **FR-010**: `__init__.py` 가 다음만 export — KOSMOS-invented 잔재 모듈 (bypass / killswitch / modes / pipeline / pipeline_v2 / rules / session_boot / synthesis_guard / mode_bypass / mode_default / aal_backstop / adapter_metadata / cli / prompt) export 0:
  - Spec 035 receipt 8 모듈 (ledger / action_digest / hmac_key / canonical_json / audit_coupling / ledger_verify / otel_emit / otel_integration)
  - `SessionContext` (from `models.py`)
  - Receipt schema classes (`ConsentDecision`, `ConsentLedgerRecord`, `LedgerVerifyReport`, `ToolPermissionContext`, `AdapterPermissionMetadata`)
  - credentials helpers (`candidate_env_vars`, `resolve_credential`, `has_credential`)

### Key Entities

- **AdapterRealDomainPolicy**: 4 필드 Pydantic v2 frozen 모델. KOSMOS 의 단일 권한 표현 — 기관 published 정책 URL 인용 + 시민-facing gate 카테고리 + 검증 시점.
- **ResidueFile**: 삭제 대상 파일 — `path`, `importers` (이 파일이 import 되는 곳), `disposition` (`delete` / `keep_with_rationale`), `migration_target` (delete 시 caller 를 어디로 옮기는지 또는 caller 도 함께 삭제하는지).
- **AdapterMigration**: 18 어댑터 each 의 마이그레이션 기록 — `adapter_id`, `agency`, `removed_fields` (auth_level 등), `added_policy` (`AdapterRealDomainPolicy` 인스턴스), `policy_url_verified` (boolean — placeholder 면 false), `last_verified_timestamp`.
- **TestBaseline**: pytest 결과 spreadsheet — `total`, `pass`, `fail`, `failure_test_ids`. NEW failure 검출 input.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 14 Spec 033 잔재 source file + `steps/` 디렉토리 100% 삭제 (`git ls-files src/kosmos/permissions/` 의 11 row 만 잔존 — Spec 035 receipt 8 + `models.py` (trimmed to SessionContext + receipt-schema dependencies) + `credentials.py` + `__init__.py`).
- **SC-002**: `AdapterRealDomainPolicy` 모델 추가 + frozen=True + extra="forbid" + 4 필드 모두 type-annotated.
- **SC-003**: 18 어댑터 metadata 100% 마이그레이션 — 모든 어댑터에 `policy: AdapterRealDomainPolicy` 인스턴스 보유.
- **SC-004**: 18 어댑터 모두 `policy.real_classification_url` non-empty + https:// 형식.
- **SC-005**: `uv run pytest` NEW failure 0 (baseline 대비).
- **SC-006**: Constitution II 금지 토큰 grep 결과 0 행 매치 (FR-006 narrowed scope: 어댑터 metadata 영역 + `src/kosmos/permissions/` 만).
- **SC-007**: 신규 runtime dependency 0 (`pyproject.toml` 의 `[project.dependencies]` 변경 0).
- **SC-008**: PR `Closes #2295` 단독 / Conventional Commits PR title 통과 / 14 required CI checks 모두 PASS / Codex P1 0건 또는 모두 resolved.

---

## Assumptions

- `pytest` baseline 측정은 cleanup 시작 직전에 수행 — 결과를 `/tmp/baseline-2295.txt` 에 박제.
- Spec 035 receipt ledger 7 파일은 KOSMOS 가 발행하는 영수증 (consent / action 기록) 의 정형화된 인프라이며, 본 Epic 의 cleanup 로 인해 receipt 발행 use case 가 깨지지 않아야 한다 — receipt 단위 테스트가 baseline 에서 통과 중이면 그대로 통과해야 한다.
- 18 어댑터 마이그레이션의 `real_classification_url` 은 가능한 한 기관의 실제 published 정책 URL 사용 (예: KOROAD `https://www.koroad.or.kr/...`, KMA `https://www.kma.go.kr/...`); 검증 불가능한 경우 placeholder + TODO 마커 + Deferred Items 추적.
- `last_verified` 는 본 마이그레이션 시점의 ISO 8601 timestamp (`2026-04-29` 또는 그 이후) 사용. 실 정책 URL 검증은 별도 spec 으로 후속.
- 본 Epic 작업은 `/Users/um-yunsang/KOSMOS-w-2295/` worktree 에서 진행되며 Epic β / main worktree 와 file conflict 없음.
- `__init__.py` 변경은 단순 export list 정정 — 잔재 모듈 export 줄을 제거하고 Spec 035 receipt 모듈만 남김.

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **TUI 잔재 cleanup (`tui/src/services/api/` 등)**: Epic β #2293 territory.
- **5-primitive 를 CC `Tool.ts` 인터페이스에 align**: Epic γ #2294 territory.
- **AX-infrastructure mock 어댑터 신설** (Singapore APEX 식 통로 mirror): Epic ε #2296.
- **End-to-end smoke + 정책 매핑 문서**: Epic ζ #2297.
- **System prompt rewrite**: Epic η #2298 (선택).
- **Spec 287 TUI 인프라 변경**: 본 Epic 은 백엔드 Python 만 다룸.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| 18 어댑터의 `real_classification_url` 실 정책 URL 검증 (placeholder TODO 항목) | 본 Epic 은 model + 마이그레이션 골격; 실 정책 URL 의 정확성 검증은 사람의 외부 cite 검토가 필요 | Epic ζ (#2297) E2E smoke 의 일부 또는 별도 documentation Epic | #2362 (조건부 — placeholder 0 이면 자연 close) |
| `AdapterRealDomainPolicy` 의 `citizen_facing_gate` 5 카테고리 부족 시 확장 | 본 Epic 의 5 카테고리 (read-only/login/action/sign/submit) 가 18 어댑터 커버 추정; 부족 발견 시 후속 spec 에서 확장 | Epic ε (#2296) AX-infrastructure mock 신설 작업 중 발견되면 그 spec 에 흡수 | #2296 |
| Spec 035 receipt ledger 의 KOSMOS 통합 시점 (현재는 backend-only, TUI 노출 미연결) | 본 Epic 은 receipt ledger 보존만 다룸; receipt 발행 → TUI 노출 (사용자에게 영수증 보여주기) 은 별도 작업 | Epic ζ (#2297) E2E smoke + 정책 매핑 doc | #2297 |
