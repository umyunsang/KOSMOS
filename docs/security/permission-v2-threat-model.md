# Permission v2 Threat Model

> Spec 033 (Epic #1297) — 시민용 공공 API 하네스의 5-모드 허용 스펙트럼 + PIPA 동의 원장.
>
> 본 문서는 `specs/033-permission-v2-spectrum/research.md §4`의 R1–R8 위험 행렬을
> 코드 수준 증거(소스 파일 + 테스트 파일)와 함께 고정한다.  각 위험은 `Mitigation`
> 단계에서 하나 이상의 자동화된 회귀 게이트로 커버되어야 하며, CI 가 이 게이트를
> 통과하지 못하면 배포가 불가하다.

## Matrix

| ID | Risk | Likelihood | Impact | Mitigation | Test |
|----|------|------------|--------|------------|------|
| R1 | RFC 8785 JCS 인코더 버그로 해시 체인이 `record_hash` 차이를 감지하지 못함 — 원장 위조가 탐지되지 않을 수 있음 | Low | High | `kosmos.permissions.canonical_json.canonicalize` 는 RFC 8785 Appendix A 13 벡터를 바이트 일치로 통과해야 함. Hypothesis 라운드트립 (JSON → canonicalize → json.loads → canonicalize) 로 재인코딩 idempotence 확인 | `tests/permissions/test_canonical_json.py`; `tests/permissions/test_us2_tamper_detect.py`; `src/kosmos/permissions/canonical_json.py` |
| R2 | HMAC 키 파일 mode 가 외부 `chmod` 로 0o644 로 바뀌면 다른 OS 사용자가 키를 읽고 원장을 위조 가능 | Medium | High | `hmac_key.load_or_generate_key` 가 부팅 시 `os.stat()` 로 mode 를 확인하고 0o400 이 아니면 `HMACKeyFileModeError` 를 올려 ledger 쓰기를 fail-closed. 동일 검사가 `ledger.append` 의 첫 단계에서 재수행됨 | `src/kosmos/permissions/hmac_key.py`; `src/kosmos/permissions/ledger.py:LedgerFilePermissionsError`; `tests/permissions/test_us2_tamper_detect.py` |
| R3 | 외부 에디터가 `permissions.json` 을 깨뜨린 상태에서 부팅 → 악의적으로 모든 adapter 를 allow 로 바꾸면 silent grant 가능 | Medium | Medium | `rules.RuleStore.load()` 가 손으로 만든 Draft 2020-12 검증기로 schema 를 강제하고, 위반 시 `RuleStoreSchemaError` 를 올려 `session_boot.reset_session_state` 가 `rules_loaded=False` + 빈 스토어로 세션을 시작 (FR-C02). 파일 mode 0o600 이 아닐 때는 `RuleStorePermissionsError` 로 동일 처리 | `src/kosmos/permissions/rules.py`; `src/kosmos/permissions/session_boot.py`; `tests/permissions/test_us4_fail_closed_edit.py`; `tests/permissions/test_us4_tri_state_persistence.py` |
| R4 | Shift+Tab 이 TUI 가 아닌 터미널/OS 레벨에서 소비되어 시민이 플릿 모드를 바꿀 수 없음 (접근성 회귀) | Low | Low | Spec 287 Ink 키코드 캡처가 raw-mode 에서 Shift+Tab 을 가로챔. TUI 테스트가 캡처된 키체어 경로를 검증 | `tui/src/permissions/ModeCycle.tsx`; `tui/src/__tests__/ModeCycle.test.tsx` (Spec 287 리그레션 매트릭스) |
| R5 | `consent_receipt_id` 필드가 Spec 024 `ToolCallAuditRecord` 의 진화 과정에서 의미상 어긋나 감사 조인이 깨짐 | Medium | High | `audit_coupling.couple_audit_record` 가 `AuditCouplingResult` 프로즌 dataclass 로 포장하여 Spec 024 스키마를 수정하지 않고 coupling 을 표현. FR-F01 게이트는 `consent.action_digest` 를 receipt_id proxy 로 사용하되 비어 있으면 `MissingConsentReceiptError` 로 fail-closed | `src/kosmos/permissions/audit_coupling.py`; `tests/permissions/test_integration_spec_024_025_021.py` (FR-F01 섹션) |
| R6 | PIPA §22(1) 개별 동의 원칙을 UX 압력으로 완화 (batch-consent) 해서 컴플라이언스 회귀 | High (UX pressure) | Medium | `prompt.build_from_decisions` 가 pipa_class ∈ {민감, 고유식별, 특수} 를 묶은 입력을 거부(`IndividualConsentViolationError`). `/permissions edit` TUI 는 rule 별 개별 토글만 제공하여 프롬프트 병합 경로를 닫음 | `src/kosmos/permissions/prompt.py`; `tests/permissions/test_us2_tamper_detect.py`; `tests/permissions/test_us4_tri_state_persistence.py` |
| R7 | Pydantic v2 마이너 업그레이드로 부동소수점 repr 이 바뀌어 RFC 8785 벡터 테스트가 무너짐 (CI flake) | Low | Medium | `pyproject.toml` 이 `pydantic >= 2.13` 을 pin 하고, `canonical_json` 은 정수/실수 처리를 stdlib `json.dumps(sort_keys=True)` + 후처리 래퍼로 강제. SC-008 zero-deps lint 가 dependency 드리프트를 탐지 | `tests/permissions/test_canonical_json.py`; `tests/permissions/test_zero_new_dependencies.py`; `src/kosmos/permissions/canonical_json.py` |
| R8 | `kosmos permissions rotate-key` 가 archive 파일을 잃어버리면 과거 레코드의 HMAC 검증이 영구 불가 | Low | High | CLI 는 `keys/registry.json` 에 key_id 마다 entry 를 유지하고 archive 디렉터리가 쓰기 불가면 회전을 거부. `ledger_verify.py` 는 key_id 를 기준으로 registry 에서 과거 키를 찾고, `--acknowledge-key-loss` 플래그 없이는 키 소실을 묵과하지 않음 | `src/kosmos/permissions/cli.py:rotate_key`; `src/kosmos/permissions/ledger_verify.py`; `tests/permissions/test_ledger_verify_cli.py` (V-matrix `KEY_MISSING` 시나리오) |

## Cross-cutting controls

1. **Invariant K1 (killswitch-first)** — `killswitch.KILLSWITCH_ORDER == 1` 상수와
   `assert_killswitch_first()` 헬퍼가 pipeline step order 를 구조적으로 강제한다.
   `tests/permissions/test_killswitch_priority_order.py` 는 docstring + 상수 양쪽을
   변이 시 실패한다.
2. **Invariant K5 (no caching)** — `mode_bypass.resolve_bypass_mode` 는 캐시 파라미터
   가 없으며, `action_digest.compute_action_digest` 는 call-per-nonce 를 강제한다.
   동일한 `(tool_id, arguments)` 두 번 호출하면 서로 다른 digest 가 나오는지
   `tests/permissions/test_us3_bypass_killswitch.py` 에서 확인한다.
3. **FR-F02 AAL backstop** — `pipeline_v2.evaluate` 는 Step 0 에서
   `aal_backstop.check_aal_downgrade(ctx_at_prompt, ctx_at_exec)` 를 호출해 session
   다운그레이드/업그레이드 시도를 차단한다. 테스트는 `tests/permissions/test_pipeline_v2.py`
   (`test_aal_backstop_blocks_downgrade`) 및 `tests/permissions/test_integration_spec_024_025_021.py`
   (`test_aal_downgrade_blocks_execution`) 에 위치.
4. **Invariant C5 synthesis boundary** — `synthesis_guard.redact` 는 민감/고유식별
   pipa_class 필드를 LLM 프롬프트 조립 전에 제거한다. 하네스 계층에서
   `evaluate()` 이후 adapter output 을 통과시키며, 리그레션은
   `tests/permissions/test_integration_spec_024_025_021.py::TestSynthesisBoundaryC5`
   에서 확인한다.
5. **SC-008 zero-deps gate** — `tests/permissions/test_zero_new_dependencies.py` 가
   Spec 033 PR 에서 새 runtime dependency 가 추가되지 않았음을 자동 확인한다.

## Residual risk

- `permissions.json` / `consent_ledger.jsonl` 경로가 사용자 디렉터리에 저장되므로,
  시민이 사용하는 OS 계정 자체가 탈취되면 본 스펙의 통제로 막을 수 없다.
  Spec 033 scope 밖이며, OS 수준 FDE + 계정 잠금은 `docs/vision.md §Layer 0` 의
  deployment posture 에 위임된다.
- Kantara CR 표준 포맷의 full receipt 내보내기는 Epic `Consent Portability v1`
  으로 이연 (`specs/033-permission-v2-spectrum/tasks.md §Deferred Items`).
