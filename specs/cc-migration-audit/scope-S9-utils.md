# S9 — Utils 감사

> CC = `.references/claude-code-sourcemap/restored-src/src/utils/`
> KOSMOS = `tui/src/utils/`
> 감사 일자: 2026-05-03

## 메타

| 항목 | CC | KOSMOS | Δ |
|---|---|---|---|
| 파일 수 | 564 | 551 | -13 |
| LOC (.ts/.tsx/.js) | 180,472 | 166,723 | -13,749 (-7.6%) |
| 서브디렉토리 | 31 | 29 (`secureStorage`, `teleport` 부재) | -2 |
| Top-level 파일 | 298 | 304 | +6 |

### 4-bucket 합계

| Bucket | 파일 수 | 비율 |
|---|---:|---:|
| **PRESERVE-IDENTICAL** (byte-identical) | **448** | 79.4% |
| **MIGRATE-FOR-SWAP** (sdk-compat / dead-import 정리만) | ~52 | 9.2% |
| **MIGRATE-FOR-SWAP** (substantive Spec 1633/2112/2293/2521 swap) | ~40 | 7.1% |
| **PORT** (CC 있음, KOSMOS 없음) | **24** | 4.3% |
| **DROP-CANDIDATE** (KOSMOS-only) | **11** | 2.0% |

448 byte-identical = **diff 결과의 모든 92개 발산 + 24개 only-CC 를 차감한 잔여**.
540개 공유 파일 중 92개가 발산 — 그 92개 중 ~52개는 4줄 이내 (전부 `@anthropic-ai/sdk` → `src/sdk-compat.js` import 교체).

## 카테고리별 4-bucket 표

| 카테고리 (서브디렉토리) | CC | KOSMOS | PORT | PRESERVE | MIGRATE | DROP |
|---|---:|---:|---:|---:|---:|---:|
| (top-level) | 298 | 304 | 1 (`sessionTitle.ts`) | ~256 | 42 | 6 (frameCommitOtel · messageReorder · messageText · multiToolLayout · proactiveModule · protectedNamespace · systemThemeWatcher · uiL2Memdir 중 일부) |
| `model/` (LLM swap zone) | 16 | 16 | 1 (`antModels.ts`?) | 2 | 14 | 1 (`constants.ts`) |
| `permissions/` | 24 | 23 | 1 (`yoloClassifier.ts` — 이미 stub) | 20 | 4 | 0 |
| `plugins/` | 44 | 43 | 1 (`mcpbHandler.ts`) | 39 | 4 | 0 |
| `telemetry/` | 9 | 1 | 8 ⚠️ | 0 | 1 (`sessionTracing.ts` MIGRATE 완료) | 0 |
| `secureStorage/` | 6 | 0 | 6 ⚠️ | 0 | 0 | 0 |
| `teleport/` + `teleport.tsx` | 5 | 0 | 0 | 0 | 0 | 5 (의도적 — claude.ai 1P) |
| `mcp/` | 2 | 1 | 1 (`dateTimeParser.ts`) | 1 | 0 | 0 |
| `swarm/` | 22 | 22 | 0 | 19 | 3 | 0 |
| `processUserInput/` | 4 | 4 | 0 | 0 | 4 | 0 |
| `hooks/` | 17 | 17 | 0 | 14 | 3 | 0 |
| `settings/` | 19 | 19 | 0 | 17 | 2 | 0 |
| `nativeInstaller/` | 5 | 5 | 0 | 3 | 2 | 0 |
| `shell/` | 10 | 10 | 0 | 8 | 2 | 0 |
| `background/`, `messages/`, `filePersistence/`, `dxt/`, `claudeInChrome/`, `computerUse/`, `sandbox/`, `ultraplan/` | 33 | 35 | 0 | 25 | 8 | 2 |
| `bash/`, `git/`, `github/`, `memory/`, `powershell/`, `skills/`, `suggestions/`, `task/`, `todo/`, `deepLink/` | 95 | 95 | 0 | 95 | 0 | 0 (모두 byte-identical) |

## P0 PORT — 즉시 마이그레이션 필요

### ⚠️ P0-1 — `utils/telemetry/instrumentation.ts` (825 LOC)

`tui/src/entrypoints/init.ts:285` 가 dynamic import 한다:
```ts
const { initializeOTel } = await import('../utils/telemetry/instrumentation.js')
```
KOSMOS에 파일이 없음 → 런타임 부팅에서 throw 가능. CC `instrumentation.ts` 는 OpenTelemetry SDK + OTLP 설정을 캡슐화하므로 Spec 021/028 (OTEL/Langfuse) 의 *전제*. **확인 필요**: KOSMOS 가 (a) 별도 모듈로 마이그레이션 했는지, (b) lazy-import 가 죽은 경로인지, (c) PORT 누락인지.

### P0-2~6 — `utils/secureStorage/*` (전체 6 파일, 629 LOC)

`index.ts` (17), `macOsKeychainStorage.ts` (231), `keychainPrefetch.ts` (116), `macOsKeychainHelpers.ts` (111), `fallbackStorage.ts` (70), `plainTextStorage.ts` (84). KOSMOS에 디렉토리 자체가 없음. KOSMOS는 `.env` API key 보관만 사용하지만 — 향후 user-tier credential storage (data.go.kr API 키 다중 보관) 가 필요하면 P3 요청. **현재 결정**: KOSMOS auth = `.env` only 라면 정당한 DROP. → resolved by [ADR-009](../../docs/adr/ADR-009-secureStorage-drop.md) (Epic G #2643)

### P0-7 — `utils/sessionTitle.ts` (129 LOC)

CC: Haiku로 6-word 세션 제목 자동 생성. KOSMOS에 없음. 만약 K-EXAONE으로 대체 마이그레이션 의도였다면 누락. PORT (FriendliAI/K-EXAONE swap 적용) 권장.

### P0-8 — `utils/mcp/dateTimeParser.ts` (121 LOC)

MCP 인자 자연어 시각 파싱(예: "tomorrow 9am" → ISO). KOSMOS의 MCP 클라이언트가 사용한다면 PORT 필요. 미사용이면 DROP.

## MIGRATE-FOR-SWAP — swap 정당화

### LLM swap zone (`utils/model/`, 14개 / 16)

`agent.ts · aliases.ts · bedrock.ts · check1mAccess.ts · configs.ts · deprecation.ts · model.ts · modelAllowlist.ts · modelCapabilities.ts · modelOptions.ts · modelStrings.ts · modelSupportOverrides.ts · providers.ts · validateModel.ts` — **Spec 2112 (dead Anthropic models) 정당 발산**. 예: `model.ts` 618→300 LOC, `modelOptions.ts` 540→124 LOC. K-EXAONE 단일 SoT로 축소. 정당.

### LLM auth swap (`utils/auth.ts`, `authPortable.ts`, `claudeAiSession*`)

`auth.ts` 2002→199 LOC. KOSMOS 헤더: `Epic #1633 stub restoration — All Anthropic OAuth / Claude.ai / ant-internal subscriber surfaces are inert in KOSMOS (FriendliAI API-key auth only)`. 정당.

### Anthropic SDK type bridge (~52 파일, 4줄 diff)

`log.ts · markdown.ts · notebook.ts · errors.ts · tokens.ts · queryHelpers.ts · attachments.ts · imageResizer.ts · cleanup.ts · doctorDiagnostic.ts · forkedAgent.ts · gracefulShutdown.ts · hooks.ts (5022 LOC, 16 diff lines!) · http.ts · context.ts · contextAnalysis.ts · env.ts · fastMode.ts · generators.ts · groupToolUses.ts · managedEnv.ts · mcpValidation.ts · messageQueueManager.ts · modifiers.ts · preflightChecks.tsx · sessionStorage.ts (5105 LOC, 9 diff lines) · sideQuestion.ts · toolResultStorage.ts · toolSchemaCache.ts · advisor.ts · analyzeContext.ts · ...` — 거의 전부 `@anthropic-ai/sdk/...` → `src/sdk-compat.js` 단일 import 교체 패턴. 정당. **PRESERVE-IDENTICAL 의 약한 변형**으로 분류 권장.

### Spec 1633/2293 dead-code purge (substantive ~10)

- `messages.ts` 5512→5327 LOC (-185, 268 diff lines): tool-use 헬퍼 일부 dead-code 절단.
- `permissions/permissions.ts` 1486→1526 LOC (+40): `yoloClassifier.ts` 삭제로 인한 inline stub 흡수 — 정당하지만 **CC ≥90% 시각·구조 동일 원칙 위반 신호**. 별도 모듈 PORT 후 stub 권장.
- `betas.ts` 434→42 LOC: KOSMOS 헤더 `Spec 2521 byte-copy bridge stub`.
- `modelCost.ts` 231→11 LOC: 같은 패턴.
- `systemPrompt.ts` 123→114 LOC, `sideQuery.ts` 222→217 LOC, `toolSearch.ts` 756→766 LOC.

## DROP-CANDIDATE — KOSMOS-only 11개 (모두 swap 종속 입증 ✅)

| 파일 | LOC | swap/spec 종속 | 평가 |
|---|---:|---|---|
| `frameCommitOtel.ts` | 130 | Spec debug-infra-rebuild R5 | ✅ 정당 |
| `messageReorder.ts` | 220 | sdk-compat type 사용 + KOSMOS message reorder | ⚠️ CC `messages.ts` 절단분의 분리 — PORT 역방향 검토 |
| `messageText.ts` | 30 | Spec debug-infra-rebuild — `stripPromptXMLTags` 분리 | ✅ 정당 |
| `model/constants.ts` | 15 | Spec 2112 K-EXAONE SoT | ✅ 정당 |
| `multiToolLayout.ts` | 90 | Spec 2521 multi-tool layout fix | ✅ 정당 |
| `proactiveModule.ts` | 62 | Epic #1633 + #2077 TDZ fix (lazy getter) | ✅ 정당 |
| `protectedNamespace.ts` | 7 | Stage-1 NO-OP stub | ⚠️ stub만 — 실제 마이그레이션 후속 필요 |
| `systemThemeWatcher.ts` | 7 | Stage-1 NO-OP stub | ⚠️ 같음 |
| `uiL2Memdir.ts` | 72 | Spec 1635 P4 UI L2 memdir | ✅ 정당 |
| `filePersistence/types.ts` | 44 | rebuild-stubs.ts (P0 reconstructed) | ✅ 정당 |
| `ultraplan/prompt.txt` | 1 | Epic #1633 placeholder | ⚠️ 1줄 placeholder |

## PRESERVE-IDENTICAL 카테고리 (간략)

전부 byte-identical 인 서브디렉토리: **`bash/` (23), `git/` (3), `github/` (1), `memory/` (2), `powershell/` (3), `skills/` (1), `suggestions/` (5), `task/` (5), `todo/` (1), `deepLink/` (6)** — 총 **50 파일**. 전부 순수 유틸 (string/path/parsing). KOSMOS 기준 정상.

서브디렉토리에서 byte-identical 비율 95%+: `claudeInChrome/` 6/7, `computerUse/` 14/15, `dxt/` 1/2, `hooks/` 14/17, `messages/` 1/2, `settings/` 17/19, `shell/` 8/10, `sandbox/` 1/2, `nativeInstaller/` 3/5, `swarm/` 19/22 (큰 디렉토리).

Top-level 298개 중 byte-identical 약 256개 (86%) — `abortController · activityManager · agentContext · agentId · ansiToPng · ansiToSvg · array · asciicast · ...` 거의 전부 순수 유틸로 정상 PRESERVE.

## 위험 신호

1. **🔴 `utils/telemetry/instrumentation.ts` 누락** — `init.ts:285` dynamic import target. 부팅 시 Spec 021/028 OTEL 초기화가 실제로 호출되는지 시점 확인 필요. PORT 또는 dead-import 정리.
2. **🟡 `utils/sessionTitle.ts` 누락** — Haiku 자동 제목 surface. K-EXAONE 마이그레이션 PORT 가 누락된 듯.
3. **🟡 `utils/mcp/dateTimeParser.ts` 누락** — MCP 시각 인자 파싱. KOSMOS의 stdio-MCP 스택이 한국어 시각 자연어 입력을 받는다면 즉시 PORT.
4. **🟡 `permissions/permissions.ts` +40 LOC inline stub** — `yoloClassifier.ts` DROP 후 inline 흡수. CC 구조 보존 원칙 위반. 별도 stub 모듈 분리 권장 (Path B 패턴, MEMORY `feedback_path_b_policy_derivation`).
5. **🟢 `secureStorage/` 6파일 누락** — `.env` 단일 의존이면 의도적 DROP 정당. 향후 다중 부처 credential 시 PORT.

## 사용자 결정 필요

- **D1**: `utils/telemetry/instrumentation.ts` PORT 여부 (Spec 021/028 OTEL 초기화 위치 vs `init.ts` 의 dynamic import 의도).
- **D2**: `utils/secureStorage/*` 6파일을 의도적 DROP 으로 확정 vs 향후 부처별 API key 다중 보관 PORT. → resolved by [ADR-009](../../docs/adr/ADR-009-secureStorage-drop.md) (Epic G #2643)
- **D3**: `utils/sessionTitle.ts` Haiku→K-EXAONE 마이그레이션 PORT 진행 여부.
- **D4**: `utils/mcp/dateTimeParser.ts` PORT (한국어 시각 파싱 보강) vs DROP.
- **D5**: `permissions.ts` inline-stub Path B 리팩터 (별도 stub 모듈 분리).
- **D6**: `protectedNamespace.ts` / `systemThemeWatcher.ts` 7-line NO-OP stub 의 실제 구현 채우기.
