# Code Review Evaluation — `feat/1636-plugin-dx-5tier`

> 평가일: 2026-04-26
> 평가자: 4-track Agent Teams (Lead 합의)
>   - Code Reviewer (Opus) — 정합성 + 유지보수
>   - Security Engineer (Sonnet) — PIPA + SLSA + 공급망 + 권한
>   - API Tester (Sonnet) — 테스트 커버리지 + 품질 + flake
>   - Technical Writer (Sonnet) — 한국어 문서 9종 + 영문 정합
>
> Branch: `feat/1636-plugin-dx-5tier` @ `17c32c7`
> Verdict: **HOLD merge — Critical 7건 fix 후 재평가**

## 평가 결과 (verdict)

PR을 **즉시 머지하지 않음**. 4-agent 합의로 7개 Critical 이슈가 식별되어 머지 차단. 그 중 2건은 사용자 작업 흐름을 즉시 깨는 empirical-verified 버그:

1. **PIPA canonical hash 가 prose 텍스트 5자를 hash** — 540자 의무 본문이 enforce 안 됨. 운영중인 plugin manifest 의 acknowledgment_sha256 검증이 fictional.
2. **Consent receipt 가 `~/.kosmos/consent/` 에 기록** — Spec 035 ledger (`~/.kosmos/memdir/user/consent/`) 와 분리되어 `/consent list` 에서 불가시.

나머지 5건도 사양 대비 보안 가정 위반 / cosmetic enforcement claim / 사용자 첫 단계 차단.

## Severity별 action items

### Critical (block merge — 7건)

| ID | 종류 | 위치 | 요지 | 검증 |
|---|---|---|---|---|
| C1 | 정합 | `installer.py:585` | Consent receipt 경로 `~/.kosmos/consent/` (data-model.md 명시는 `~/.kosmos/memdir/user/consent/`) → Spec 035 ledger 와 분리 | empirical: `print(consent_root)` 확인 |
| C2 | 정합 | `registry.py:208-212` | `model_construct` bypass — 5개 cross-field validator (PluginManifest._v_*) 무효화 가능. Spec 025 V6 패턴 (registry-level backstop) 미적용 | docstring honor-system; runtime 무방어 |
| C3 | 정합 | `tools/models.py:243` regex / `q8_namespace.py:18` | `plugin.<id>.resolve_location` 가 GovAPITool 등록 통과 (Q8-NO-ROOT-OVERRIDE 우회). 4-verb (manifest) vs 5-verb (registry) drift surface | dual source-of-truth |
| C4 | 보안 (TS↔Py drift) | `plugin.ts:27` `_PIPA_HASH = '434074581cab...'` | TS hardcoded; Python 은 docs 추출 hash. 실제 runtime hash 와 무관 (C5 참고). 시민이 보는 안내값과 manifest 가 서로 다른 hash | C5 와 결합 |
| C5 | 정합 (empirical) | `canonical_acknowledgment.py:60` `md.find()` | 첫 마커 occurrence 가 prose 설명문 안의 인용. `_extract_canonical_text()` 가 5자 (` ↔ `) 추출. Runtime 상수: `d159d8fd...`, docs 게시: `434074581cab...`. 실제 의무 텍스트 540자는 hash 영향권 밖 | empirical: 추출 텍스트 5자 + `d159d8fd02b2f4babb...` 검증 완료 |
| C6 | 보안 | `installer.py:402` + `settings.py:200` 주장 | `KOSMOS_PLUGIN_SLSA_SKIP=1` 의 production gate **존재하지 않음**. settings.py 주석 / security-review.md L3 약속 모두 vapor. 어떤 환경 변수 1개로 SLSA 건너뛰고 모든 layer 설치 가능. `slsa_state="skipped"` 는 consent receipt 에만 기록되고 OTEL span 에 미부착 | grep `.github/workflows/` → 0 matches |
| C7 | 보안 | `bootstrap_slsa_verifier.sh:101-120` | slsa-verifier 다운로드 TOFU. SHA-256 / cosign 검증 부재. MITM / 손상된 release asset → 임의 코드 실행 + 모든 후속 install gate 우회 | upstream `slsa-verifier-*.sha256` 미사용 |

### High (fix before public — 8건)

| ID | 종류 | 위치 | 요지 |
|---|---|---|---|
| H1 | 정합 | `installer.py:279-287` | `os.fsync(O_RDONLY fd)` no-op. Receipt 내구성 미보장. Parent dir fsync 누락 → 정전 시 rename 손실 가능 |
| H2 | 정합 | `registry.py:99-110` | `sys.modules` 누수 — 부분 실패 시 stale module 잔존 |
| H3 | 보안 | adapter top-level code 권한 | 어댑터 모듈 import 가 KOSMOS process 권한으로 실행 (HMAC key / sessions JSONL / canonical hash 변조 등). `block_network` fixture 는 contributor's tests/conftest.py 한정 — 운영 환경 무영향 |
| H4 | 보안 | `installer.py:264-267` | Consent ledger position race + `uuid4()[:16]` 64-bit collision 리스크 + dir fsync 누락 |
| H5 | 보안 | `manifest_schema.py:271-282` | Unicode confusable plugin_id (Cyrillic `о` 등) — `re.fullmatch(..., flags=re.ASCII)` 누락 |
| H6 | 보안 | `installer.py:247-261` | `_safe_extract` symlink TOCTOU — `member.linkname` resolution 미수행. PEP 706 `data` 필터 보완에 불완전 의존 |
| H7 | 정합 | TUI ↔ backend 미연결 | TUI 가 `plugin_op_request` 발산하나 Python 측 dispatcher 없음 — slash command 가 cosmetic |
| H8 | 정합 | `q1_schema.py:197` | `_has_model_config_kwarg` dead code. Q1-FROZEN 가 input/output 모델 중 하나만 있어도 통과 (xor 미강제) |

### Medium (follow-up PR — 12건)

테스트 품질:
- T1 Q9-OTEL-EMIT 검사가 production span 경로와 분리 (`q9_otel.py:54-84` local provider) — `registry.py:218` set_attribute 삭제해도 검사 통과
- T2 `q10_tests.py:121-142` Q10-NO-LIVE-IN-CI 가 tautology — promised httpx eager-import flagging 미구현
- T3 `test_validation_workflow.py` 11개 negative 중 8개가 disjunction-pass — Q1-MANIFEST-VALID 가 dominate, 명명 check 의 fail path 미검증
- T4 SC-005 30s budget meaningless (file:// 경로, `< 5.0` 검증으로 충분)
- T5 SC-010 N=1 측정 — 50 plugin scaling 미검증
- T6 Q2 family 0 negative tests
- T7 `test_cli_init.py:174` PIPA hash 가짜값 (`'a'*64`) → cli_init 성공해도 manifest 가 Q6-PIPA-HASH fail (cli_init success ≠ valid plugin)
- T8 `test_installer_slsa.py:149` timeout test (0.05s margin) flake risk

보안:
- M1 `q5_permission` "권장" language — `Spec 033` 자동 cross-check 미연결
- M2 OTEL emission 실패 silent (logging audit 누락)
- M3 drift-audit workflow `#1926` deferred — canonical hash 갱신 시 기존 plugin 이 stale hash 로 install 가능
- M4 `default_verifier_path` Windows 등 unsupported OS 시 silent fallback → 좌절한 사용자가 SLSA_SKIP 우회로 유도

코드 잡음:
- 5건 minor (q3 `model_fields`, frame_schema noqa, plugin.ts `as never` casts 등)

### 문서 결함 (Korean contributor 차단 — 5건)

| ID | 종류 | 위치 | 요지 |
|---|---|---|---|
| D1 | empirical 차단 | `security-review.md:12` | 게시 hash `434074581cab...` 와 runtime 상수 `d159d8fd...` 불일치 (C5 와 동일 root cause). 시민이 docs hash 를 manifest 에 복사하면 Q6-PIPA-HASH 즉시 fail |
| D2 | enum mismatch | `permission-tier.md:76,105,210-211` + `security-review.md:92-93,101,112,147` + `contracts/manifest.schema.json:152-154` | `pipa_class` 값을 `personal_standard` / `personal_sensitive` / `personal_unique_id` 로 게시. 실제 `models.py:22` 는 `Literal["non_personal", "personal", "sensitive", "identifier"]`. Layer 2/3 manifest 모두 pydantic 검증 fail |
| D3 | 부재 CLI | `quickstart.ko.md:248-250` + `quickstart.md:230-232` | `kosmos-plugin-validate` CLI 가 `pyproject.toml:38-41` 에 미등록 (등록된 entry: `kosmos`, `kosmos-permissions`, `kosmos-plugin-init`). step 8 의 50/50 green-light 도달 불가 |
| D4 | env var typo | `quickstart.md:168` | 영문 source: `KOSMOS_DATA_GO_KR_KEY` (오타). `settings.py:55` 와 한국어 가이드: `KOSMOS_DATA_GO_KR_API_KEY` (정답). 영문 source 만 typo |
| D5 | invalid pattern | `quickstart.md:147-184` Step 6 | 영문 가이드의 `class BusanBikeAdapter(GovAPITool):` declarative override 패턴이 `models.py:63-94` 의 frozen Pydantic BaseModel 과 충돌. `provider` 필드는 Spec 1634 FR-010 으로 `ministry` 로 대체됨. 영문 quickstart 전면 재작성 필요 |

### 문서 결함 (사용성 — 3건)

- DG1 anchor links 깨짐 — `review-checklist.md` 의 em-dash slug `q4--discovery--docs-8` 인데 가이드 5곳이 single-hyphen 사용
- DG2 `data-go-kr.md:209` 가 `kosmos plugin pipa-text` CLI 인용 — 존재하는 건 TUI slash command 만
- DG3 Step 7 `httpx.HTTPStatusError("404", request=None, response=None)` snippet 이 httpx 가 `request=None` 거부 → 그대로 실행 불가

### 문서 결함 (Korean register — 5건)

`testing.md:21` "scaffold 가 emit 하는", `security-review.md:82` "install 시점 + (이중공백) PR", `pydantic-schema.md:159-176` 명사형 마침표 등 — 모두 자연스러운 한국어로 보강 권장 (위 4-track Agent 보고서 참조).

## 합의된 fix 순서 (우선도)

### 1차 (이번 PR — Critical 7 + Doc Blocker 5)

1. **C5 + D1 fix**: `canonical_acknowledgment.py` 의 `_extract_canonical_text` 를 마지막 occurrence 또는 unique sentinel 로 변경. 추출된 540자 hash 가 docs 와 일치하는지 unit test 추가. TS hardcoded hash 도 build-time 생성으로 전환 (C4).
2. **C1 fix**: settings 에 `user_memdir_root` 추가, `consent_root = user_memdir_root / "consent"` 변경. test_install_e2e.py:179 fixture path 도 동기화.
3. **C2 fix**: `register_plugin_adapter` 에서 V1 패턴 backstop — `isinstance(manifest, PluginManifest)` 외에 5 validator 재실행 (Spec 025 V6 패턴 재현).
4. **C3 fix**: `_validate_id` regex 에서 `resolve_location` 제거 OR `ToolRegistry.register` 에 verb suffix backstop 추가.
5. **C6 fix**: `installer.py` 에 `if manifest.permission_layer == 3 and slsa_state == "skipped": return _EXIT_SLSA` + OTEL `kosmos.plugin.slsa_verification` attribute. `KOSMOS_ENV=production` 시 `plugin_slsa_skip=True` 거부.
6. **C7 fix**: `bootstrap_slsa_verifier.sh` 에 SHA-256 dictionary + `sha256sum -c` (upstream `slsa-verifier-*.sha256` 사용).
7. **D2 fix**: `pipa_class` enum 값 통일 — 실제 `models.py` 와 일치하도록 docs + manifest.schema.json 수정.
8. **D3 fix**: `pyproject.toml` 에 `kosmos-plugin-validate = "kosmos.plugins.checks.framework:_cli_main"` entry 추가 + framework.py 에 CLI main 함수 작성.
9. **D4 fix**: `quickstart.md:168` `KOSMOS_DATA_GO_KR_API_KEY` 로 정정.
10. **D5 fix**: 영문 quickstart Step 6 을 한국어 가이드의 `_build_tool()` factory 패턴으로 통일.

### 2차 (follow-up PR — High 8)

H1-H8 모두 follow-up 으로 분리 — 보안 hardening + sandbox + dir fsync + symlink TOCTOU + Q1-FROZEN xor + sys.modules 누수 등. Spec 1636 P5 의 즉시 차단 요건은 아니지만 첫 외부 contributor 도착 전 처리.

### 3차 (별도 epic — Medium 12)

테스트 quality + 보안 hardening + minor 정리. 본 PR scope 외.

## 평가 metric

| Track | Critical | High | Medium | Verdict |
|---|---|---|---|---|
| Code Reviewer | 4 | 5 | 5 | HOLD |
| Security Engineer | 2 | 5 | 5 | HOLD (C-1 alone blocks) |
| API Tester | 0 | 5 | 8 | OK with fixes |
| Technical Writer | 5 | 3 | 5 | HOLD (D1-D5 도달 차단) |

**합의: HOLD merge.** 1차 10개 fix 후 재평가. 4-track 모두 동일한 핵심 발견 (canonical hash + consent path + SLSA gate vapor) 을 독립적으로 식별 — high-confidence verdict.

## 다음 단계

1. **현 PR 머지 차단** 표시 + 이 평가서 첨부.
2. 1차 10개 fix 를 별도 commit 으로 분리해 본 branch 에 추가 (PR 자체는 유지).
3. 각 fix 별 단위 테스트 추가:
   - C5: extract → re-hash 후 docs hash 일치 (parity test).
   - C1: install_e2e 가 `~/.kosmos/memdir/user/consent/` 에 receipt 작성 검증.
   - C2: `model_construct` 우회 시도 → `register_plugin_adapter` 가 거부.
   - C3: `register(GovAPITool(id="plugin.foo.resolve_location"))` 거부.
   - C6: `KOSMOS_PLUGIN_SLSA_SKIP=1` + `permission_layer=3` → exit 3.
   - D2: 잘못된 enum 값으로 manifest 파싱 → 명확한 에러.
   - D3: `uvx kosmos-plugin-validate .` 통과.
4. 4-track agent 재평가 후 merge 가능 여부 확정.

## 첨부

- 4-track 원본 보고서: 본 PR 의 review thread (Code Reviewer / Security Engineer / API Tester / Technical Writer 각 보고서 본문 보존).
- Empirical verification logs: 본 평가서 작성 중 수행한 `_extract_canonical_text` 추출 결과 + `consent_root` Path 확인.

## 참고

- 본 평가서 자체가 검토 대상이 될 수 있음 — 4-track 합의는 "검토 평가 과정" 의 결과물이며 사용자가 fix 우선순위를 재조정할 수 있음.
- Critical 7건 모두 head-of-branch 가 만든 새 코드 — main branch 에서 가져온 기존 코드 결함이 아님.
