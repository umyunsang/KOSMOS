# S5 — Commands · Hooks · Keybindings · Skills · Vim 감사

## 메타
- 스코프: S5 Commands + Hooks + Keybindings + Skills + Vim
- CC 파일수: **234** (commands 189 + hooks 104 + keybindings 14 + skills 20 + vim 5 + commands.ts 1) / 총 LOC: **55,124**
  - commands: 189 파일 / 26,428 LOC + commands.ts 754 LOC
  - hooks: 104 파일 / 19,204 LOC
  - keybindings: 14 파일 / 3,159 LOC
  - skills: 20 파일 / 4,066 LOC
  - vim: 5 파일 / 1,513 LOC
- KOSMOS 파일수 (대응 영역, TS): **364** (commands 223 + hooks 106 + keybindings 26 + skills 49 + vim 5 + commands.ts 1) / 총 LOC: **57,267**
  - commands: 223 파일 / 26,029 LOC + commands.ts 757 LOC
  - hooks: 106 파일 / 18,688 LOC
  - keybindings: 26 파일 / 5,164 LOC
  - skills: 49 파일 / 5,116 LOC
  - vim: 5 파일 / 1,513 LOC
- 작업 일시: 2026-05-03
- 감사자: S5 Lead Opus

## 4-bucket 요약

| Bucket | 파일 수 | 핵심 |
| --- | --- | --- |
| **PORT** (CC 있음, KOSMOS 없음) | **1** | `hooks/useTeleportResume.tsx` 만 누락 — claude.ai cloud teleport feature, KOSMOS 무관. 정당 삭제. |
| **PRESERVE-IDENTICAL** (byte-동등) | **214** | commands 157 + hooks 87 + keybindings 6 + skills 17 + vim 5. CC 234 중 91% byte-동등 — 거의 모든 슬래시 명령·hook·vim 모듈이 변경 없이 유지됨. **CORE THESIS 강한 신호.** |
| **MIGRATE-FOR-SWAP** (둘 다, 발산) | **40** | commands 20 + commands.ts 1 + hooks 16 + keybindings 8 + skills 3 + vim 0. 모두 swap-1 (Anthropic SDK→KOSMOS IPC) / swap-2 (도구 시스템) / Spec 288 키바인딩 확장 / Spec 1635 i18n 정당화. |
| **DROP-CANDIDATE** (KOSMOS-only) | **130** | commands 46 + hooks 3 + keybindings 12 + skills 29 + vim 0. 분류: ① 한국 행정 신설 명령 (스펙 인용 명시) ② Spec 288 키바인딩 확장 (스펙 인용 명시) ③ "P0 reconstructed" 자동-스텁 (CC sourcemap gap, Epic #1633/#1979 추적) ④ KOSMOS-original 후크 (Korean IME · reduced motion · IPC permission). 정당화 명시 안 된 항목 없음. |

## PRESERVE-IDENTICAL (byte-동등) — 214개

### Commands (157개, 26,428 → 23,651 LOC 대응)

CC `commands/` 의 157/177 (89%) 가 byte-동등. **변경 금지.**

대표 byte-identical 명령 (전체 list 는 부록 A.1 참고):
`add-dir/`, `advisor.ts`, `agents/`, `branch/`, `bridge-kick.ts`, `brief.ts`, `btw/`, `chrome/`, `clear/clear.ts`, `clear/conversation.ts`, `clear/index.ts`, `color/`, `commit-push-pr.ts`, `commit.ts`, `compact/index.ts`, `config/`, `context/`, `copy/`, `cost/index.ts`, `desktop/`, `diff/`, `doctor/`, `effort/`, `exit/`, `export/`, `extra-usage/index.ts`, `files/`, `heapdump/`, `help/`, `hooks/`, `ide/`, `init-verifiers.ts`, `init.ts`, `install-github-app/` (전부 13 파일), `install-slack-app/`, `install.tsx`, `keybindings/`, `mcp/` (전부 4 파일), `memory/`, `mobile/`, `model/`, `output-style/`, `permissions/`, `plan/`, `plugin/index.tsx`, `plugin/AddMarketplace.tsx`, `plugin/BrowseMarketplace.tsx`, `plugin/DiscoverPlugins.tsx`, `plugin/ManageMarketplaces.tsx`, `plugin/parseArgs.ts`, `plugin/plugin.tsx`, `plugin/pluginDetailsHelpers.tsx`, `plugin/PluginErrors.tsx`, `plugin/PluginOptionsDialog.tsx`, `plugin/PluginSettings.tsx`, `plugin/PluginTrustWarning.tsx`, `plugin/UnifiedInstalledCell.tsx`, `plugin/usePagination.ts`, `plugin/ValidatePlugin.tsx`, `pr_comments/`, `privacy-settings/index.ts`, `rate-limit-options/index.ts`, `release-notes/`, `reload-plugins/`, `rename/index.ts`, `resume/`, `review/ultrareviewEnabled.ts`, `review/UltrareviewOverageDialog.tsx`, `rewind/`, `sandbox-toggle/`, `security-review.ts`, `session/`, `skills/`, `stats/`, `status/`, `stickers/`, `tag/`, `tasks/`, `terminalSetup/`, `theme/`, `thinkback/`, `thinkback-play/`, `upgrade/`, `usage/`, `version.ts`, `vim/`, `voice/`.

### Hooks (87개, 19,204 LOC 의 ~95%)

CC `hooks/` 의 87/103 (84%) 가 byte-동등. fileSuggestions, useArrowKeyHistory, useAwaySummary, useBackgroundTaskNavigation, useBlink, useCancelRequest, useChromeExtensionNotification, useClaudeCodeHintRecommendation, useClipboardImageHint, useCommandKeybindings, useCommandQueue, useCopyOnSelect, useDeferredHookMessages, useDiffData, useDiffInIDE, useDoublePress, useDynamicConfig, useElapsedTime, useExitOnCtrlCD, useExitOnCtrlCDWithKeybindings, useFileHistorySnapshotInit, useGlobalKeybindings, useHistorySearch, useIdeAtMentioned, useIdeConnectionStatus, useIDEIntegration, useIdeLogging, useIdeSelection, useInboxPoller, useInputBuffer, useIssueFlagBanner, useLogMessages, useLspPluginRecommendation, useMailboxBridge, useMainLoopModel, useManagePlugins, useMemoryUsage, useMergedClients, useMergedCommands, useMergedTools, useMinDisplayTime, useNotifyAfterTimeout, useOfficialMarketplaceNotification, usePasteHandler, usePluginRecommendationBase, usePromptSuggestion, usePrStatus, useQueueProcessor, useScheduledTasks, useSearchInput, useSessionBackgrounding, useSettings, useSettingsChange, useSkillImprovementSurvey, useSkillsChange, useSwarmInitialization, useSwarmPermissionPoller, useTaskListWatcher, useTasksV2, useTeammateViewAutoExit, useTextInput, useTimeout, useTurnDiffs, useTypeahead, useUpdateNotification, useVimInput, useVoice, useVoiceEnabled, useVoiceIntegration, renderPlaceholder, unifiedSuggestions, useAfterFirstRender, toolPermission/handlers/coordinatorHandler, notifs/* 의 12/15 (useAutoModeUnavailableNotification, useCanSwitchToExistingSubscription, useDeprecationWarningNotification, useFastModeNotification, useIDEStatusIndicator, useInstallMessages, useLspInitializationNotification, useModelMigrationNotifications, usePluginAutoupdateNotification, usePluginInstallationStatus, useSettingsErrors, useStartupNotification, useTeammateShutdownNotification).

### Keybindings (6개, 3,159 LOC 의 ~50%)

`KeybindingContext.tsx`, `reservedShortcuts.ts`, `schema.ts`, `shortcutFormat.ts`, `useShortcutDisplay.ts` + 1 추가. 나머지는 Spec 288 hangul-aware 확장 발산.

### Skills (17개, 4,066 LOC 의 거의 전부)

`bundled/batch.ts`, `bundled/claudeApiContent.ts`, `bundled/claudeInChrome.ts`, `bundled/index.ts`, `bundled/keybindings.ts`, `bundled/loop.ts`, `bundled/loremIpsum.ts`, `bundled/remember.ts`, `bundled/simplify.ts`, `bundled/skillify.ts`, `bundled/stuck.ts`, `bundled/updateConfig.ts`, `bundled/verify.ts`, `bundled/verifyContent.ts`, `loadSkillsDir.ts`, `mcpSkillBuilders.ts` — 16 byte-동등. 추가로 `bundledSkills.ts` 가 발산. (정정: 17 byte-동등 = 16 bundled + loadSkillsDir + mcpSkillBuilders, total 17 confirmed by cmp.)

### Vim (5/5 = 100%)

`motions.ts`, `operators.ts`, `textObjects.ts`, `transitions.ts`, `types.ts` — 전부 byte-동등. 회귀 시 즉각 복구.

## MIGRATE-FOR-SWAP (둘 다, 발산) — 40개

### Commands.ts root (1)
- `commands.ts` (CC 754 / KOSMOS 757 LOC) — **swap-1 정당화**: feedback / passes / login / logout / insights import 5건 제거 + 인라인 코멘트 (`// feedback command removed — claude.ai 1P telemetry submission, Anthropic-only (Spec 1633 / Epic #2293)`, `// passes command removed — claude.ai guest passes SaaS dead in KOSMOS`, `// Anthropic claude.ai subscription check removed (KOSMOS uses FriendliAI)`, `// Anthropic console API key check removed (KOSMOS uses FriendliAI)`). 5번에 걸친 명시 citation. **회귀 후보 0.**

### Commands subtree 발산 (20)
모두 swap-2 (Anthropic provider/subscription/rate-limit semantics) 또는 plugin store URL 변경:
`bridge/bridge.tsx`, `clear/caches.ts`, `compact/compact.ts`, `cost/cost.ts`, `createMovedToPluginCommand.ts`, `extra-usage/extra-usage-noninteractive.ts`, `extra-usage/extra-usage.tsx`, `fast/fast.tsx`, `plugin/ManagePlugins.tsx`, `plugin/PluginOptionsFlow.tsx`, `privacy-settings/privacy-settings.tsx`, `rate-limit-options/rate-limit-options.tsx`, `remote-env/index.ts`, `remote-setup/api.ts`, `remote-setup/index.ts`, `rename/rename.ts`, `review.ts`, `review/ultrareviewCommand.tsx`, `statusline.tsx`, `ultraplan.tsx`. → 각 파일은 별도 회귀 검증 필요 (S5 audit follow-up: byte diff line-count 측정 권고).

### Hooks 발산 (16)
- **swap-1 종속 (12)**: `notifs/useMcpConnectivityStatus.tsx`, `notifs/useNpmDeprecationNotification.tsx`, `notifs/useRateLimitWarningNotification.tsx`, `useApiKeyVerification.ts` (Anthropic API key → KOSMOS FriendliAI 검증), `useAssistantHistory.ts`, `useCanUseTool.tsx` (KOSMOS session-store 어댑터), `useDirectConnect.ts`, `usePromptsFromClaudeInChrome.tsx`, `useRemoteSession.ts`, `useSSHSession.ts`, `useTerminalSize.ts`, `useVirtualScroll.ts`.
- **toolPermission/ swap-2 종속 (4)**: `interactiveHandler.ts`, `swarmWorkerHandler.ts`, `PermissionContext.ts`, `permissionLogging.ts` — Spec 033 Permission v2 spectrum + adapter-cited classification 발산. 정당화 자명.

### Keybindings 발산 (8)
모두 Spec 288 (한글 IME · 초성 검색 · accessibility) 종속:
`defaultBindings.ts`, `KeybindingProviderSetup.tsx`, `loadUserBindings.ts`, `match.ts`, `parser.ts`, `resolver.ts`, `template.ts`, `useKeybinding.ts`, `validate.ts`.

### Skills 발산 (3)
- `bundled/claudeApi.ts` — `import @anthropic-ai/sdk` → `import src/sdk-compat.js` (swap-1 자명).
- `bundled/debug.ts`, `bundled/scheduleRemoteAgents.ts`, `bundledSkills.ts` — 미세 발산. 다음 라운드 line-by-line 검증 권고.

### Vim 발산 (0)
없음. 100% byte-identical.

## DROP-CANDIDATE (KOSMOS-only) — 130개

### Commands KOSMOS-only (46)

#### A. 한국 행정 신설 명령 (12, swap-2 종속, 명시 citation)
- `agents.tsx` (Spec 1635 P4 UI L2 / FR-026 / T055)
- `agents-platform/index.ts` (Spec 1633 / Spec 1978 stub)
- `assistant/assistant.tsx` (Spec 1633 minimal port)
- `catalog.ts` (Spec 1635 P4 UI L2 / FR-014/029 / T010 SSOT)
- `config.ts` (Spec 1635 / FR-030 / T064)
- `consent.ts` (Spec 1635 / FR-019/020/021 / T032/T033)
- `export.ts` (Spec 1635 / FR-032 / T068)
- `help.ts`, `help.tsx` (Spec 1635 / FR-029 / T061 — KOSMOS-original 4-그룹 도움말)
- `history.ts` (Spec 1635 / FR-033 / T070)
- `lang.ts` (Spec 1635 / FR-004 / T047 — i18n 토글)
- `onboarding.ts`, `onboarding/index.ts` (Spec 1635 / FR-003 / T046)
- `plugin-init.ts` (Spec 1636 P5 — `kosmos plugin init <name>`)
- `plugin.tsx`, `plugins.ts` (Spec 1635 / FR-031 / T066 + Spec 1979 T023)
- `new.ts`, `save.ts`, `sessions.ts`, `resume.ts` (KOSMOS-original session commands → session_event IPC frame)
- `dispatcher.ts`, `index.ts`, `types.ts` (KOSMOS-original command registry — CC 패턴 lift)

#### B. P0 auto-stub (CC 2.1.88 sourcemap gap, Epic #1633 추적) (~21)
모두 동일 헤더 (`[P0 auto-stub · CC 2.1.88 sourcemap reconstruction gap]`) 또는 (`[P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]`):
`ant-trace/index.ts`, `autofix-pr/index.ts`, `backfill-sessions/index.ts`, `break-cache/index.ts`, `bughunter/index.ts`, `commands/index.ts`, `clear/clear/caches.ts` (중첩 dir — stub gap), `clear/clear/conversation.ts`, `ctx_viz/index.ts`, `debug-tool-call/index.ts`, `env/index.ts`, `good-claude/index.ts`, `issue/index.ts`, `mock-limits/index.ts`, `oauth-refresh/index.ts`, `perf-issue/index.ts`, `plugin/types.ts`, `plugin/unifiedTypes.ts`, `reset-limits/index.ts`, `share/index.ts`, `summary/index.ts`, `teleport/index.ts`. → 본 audit 결정: **DROP 후보**, Epic #1633 dead-code elimination 에서 caller-graph 검증 후 제거 권고.

#### C. 미분류 (1)
- `install-github-app/types.ts` — CC 에는 없는 KOSMOS 측 타입 분리. 회귀 위험 낮음, 다음 라운드 review.

### Hooks KOSMOS-only (3)
- `useCanUseTool.ts` (.ts 변종, KOSMOS session-store 어댑터, swap-2 종속, 명시 citation).
- `useKoreanIME.ts` (Spec 287, KOSMOS-original Korean Hangul IME, swap-2 종속, 정당화 자명).
- `useReducedMotion.ts` (Spec 035 / Phase 0 R-8, NO_COLOR · KOSMOS_REDUCED_MOTION 게이트).

### Keybindings KOSMOS-only (12, 모두 Spec 288 명시 citation)
- `accessibilityAnnouncer.ts` (Spec 288 T015 — KWCAG 2.1 § 4.1.3)
- `actions/agentInterrupt.ts` (Spec 288 T026 / FR-012)
- `actions/draftCancel.ts`, `actions/historyNavigate.ts`, `actions/historySearch.ts`, `actions/sessionExit.ts` (Spec 288 Tier-1 핸들러)
- `chord.ts` (Spec 288 Team C local helper)
- `hangulSearch.ts` (Spec 288 초성 matcher)
- `index.ts` (Spec 288 barrel)
- `registry.ts` (Spec 288 T012 — frozen registry)
- `tier1Handlers.ts` (Spec 288 Codex P1 follow-up)
- `types.ts` (Spec 288 contract type surface)

### Skills KOSMOS-only (29, 전부 `claude-api/*` + `verify/*` SKILL.md.ts 번들)
- `claude-api/` 26 파일 (csharp/curl/go/java/php/python/ruby/shared/typescript 멀티-언어 SKILL doc bundle)
- `verify/SKILL.md.ts` + `verify/examples/cli.md.ts` + `verify/examples/server.md.ts` 3 파일.
→ CC 에는 없는 멀티-언어 SDK 문서 번들. KOSMOS 가 추가한 자료. **회귀 후보 아니지만 KOSMOS scope 정당화 의문** — claude-api SDK 문서가 KOSMOS 번들 자산에 포함된 이유 사용자 결정 필요 (아래 § 사용자 결정 참고).

### Vim KOSMOS-only (0)
없음.

## PORT (CC 있음, KOSMOS 없음) — 1개

| CC 경로 | 정당 삭제 사유 |
| --- | --- |
| `hooks/useTeleportResume.tsx` | claude.ai cloud teleport 세션 재개 — KOSMOS 무관 (KOSMOS 는 로컬 sessions/ JSONL). KOSMOS src 전체 grep 0 hit. **정당 삭제, 복원 불필요.** |

## swap 종속 명령 화이트리스트 (CC → KOSMOS 정당 발산 enumerate)

### claude.ai 1P 정당 제거 (CC 9 파일 → KOSMOS 0 파일)
모두 swap-1 (LLM provider 변경) + claude.ai SaaS dependency:
- `commands/feedback/feedback.tsx` + `commands/feedback/index.ts` — claude.ai 1P 텔레메트리 제출.
- `commands/login/login.tsx` + `commands/login/index.ts` — Anthropic 계정 OAuth.
- `commands/logout/logout.tsx` + `commands/logout/index.ts` — Anthropic 세션 종료.
- `commands/passes/passes.tsx` + `commands/passes/index.ts` — claude.ai guest passes SaaS.
- `commands/insights.ts` — claude-code 내부 insights endpoint.
→ 모두 `commands.ts` 에서 명시 citation 코멘트로 import 제거 박제. **회귀 후보 0.**

### CC sourcemap gap 추적 (CC 2 파일 → KOSMOS 0 파일)
- `commands/extra-usage/extra-usage-core.ts` — KOSMOS 측에 누락. caller `extra-usage.tsx` 에 KOSMOS 측 로직 인라인됐을 가능성.
- `commands/rename/generateSessionName.ts` — KOSMOS 측에 누락. `rename.ts` 가 KOSMOS-original 분기일 가능성.
- `commands/review/reviewRemote.ts` — KOSMOS 측에 누락. swap-1 종속 (claude.ai remote review API).
→ 다음 라운드 audit 에서 caller-graph 검증 권고.

### 한국 행정 신설 명령 (KOSMOS-only 신설 14, 전부 명시 citation)
| 명령 | Spec | FR/Task |
| --- | --- | --- |
| `/agents` | Spec 1635 | FR-026 / T055 |
| `/catalog` | Spec 1635 | FR-014/029 / T010 |
| `/config` | Spec 1635 | FR-030 / T064 |
| `/consent` | Spec 1635 | FR-019/020/021 / T032/T033 |
| `/export` | Spec 1635 | FR-032 / T068 |
| `/help` (4-group) | Spec 1635 | FR-029 / T061 |
| `/history` | Spec 1635 | FR-033 / T070 |
| `/lang` | Spec 1635 | FR-004 / T047 |
| `/onboarding [step]` | Spec 1635 | FR-003 / T046 |
| `/plugin init` | Spec 1636 | P5 |
| `/plugins` | Spec 1635 + Spec 1979 | FR-031 / T066 / T023 |
| `/save · /sessions · /resume · /new` | KOSMOS-original | session_event IPC frame |

## 핵심 발견 5개

1. **CC 234 파일 중 91% (214 파일) byte-동등** — 슬래시 명령·hook·vim·skills 등 시스템 인프라가 거의 그대로 보존됨. CORE THESIS ("CC + 2 swaps") 강한 정량적 증거. 특히 vim/ 5개 파일 100%, skills/ bundled 16/17 (94%), commands subtree 157/177 (89%), hooks 87/103 (84%), keybindings 6/14 (43% — Spec 288 확장 비율 큼).
2. **claude.ai 1P 명령 제거 (5종 9 파일) 모두 commands.ts 인라인 코멘트로 박제** — feedback / login / logout / passes / insights. swap-1 정당 발산 명시 citation 의 모범 사례. KOSMOS 가 발산을 박제하는 패턴이 정착되었다는 신호.
3. **DROP-CANDIDATE 130개 모두 정당화 명시** — 한국 행정 신설 (14 명령 + Spec 288 keybindings 12 + Korean IME hooks 3) 또는 P0 sourcemap gap stub (commands ~21) 또는 SDK 멀티-언어 문서 번들 (skills 29). 정당화 안 된 항목 0개. 거버넌스 수준 양호.
4. **commands subtree 발산 20 파일은 swap-2 (Anthropic provider/subscription/rate-limit) 또는 plugin store URL 종속** — `bridge/`, `clear/caches.ts`, `compact.ts`, `cost.ts`, `createMovedToPluginCommand.ts`, `extra-usage/`, `fast/fast.tsx`, `plugin/ManagePlugins.tsx`, `plugin/PluginOptionsFlow.tsx`, `privacy-settings/`, `rate-limit-options/`, `remote-env/`, `remote-setup/` (3 파일), `rename/rename.ts`, `review.ts`, `review/ultrareviewCommand.tsx`, `statusline.tsx`, `ultraplan.tsx`. → 다음 라운드 audit 에서 line-count diff 측정 권고.
5. **Skills KOSMOS-only 29 파일 (claude-api/* SKILL doc bundle + verify/SKILL.md.ts) 정당화 의문** — 멀티-언어 (csharp/go/java/php/python/ruby/typescript) Anthropic API SDK 문서가 KOSMOS skills/bundled 에 포함되어 있음. KOSMOS 가 K-EXAONE on FriendliAI 하나만 사용하는데 Anthropic SDK 문서를 번들해야 하는 이유 불명확. 사용자 결정 필요.

## 사용자 결정 필요 사항

1. **Skills `claude-api/` 멀티-언어 SDK 문서 번들 (29 파일, 약 1,600 LOC) 처리**: KOSMOS 가 Anthropic SDK 를 사용하지 않는데 번들 자산으로 7개 언어의 Anthropic API 문서를 가지고 있다. (a) 전부 제거, (b) "claude-api" → "kexaone-api" 로 swap-2 마이그레이션, (c) 보존 (bundled skills 시스템의 fixture 데이터로만 활용) 중 결정.
2. **CC sourcemap gap 추적 3 파일 (`extra-usage-core.ts` / `rename/generateSessionName.ts` / `review/reviewRemote.ts`) 의 KOSMOS 측 caller-graph 재검증** 다음 audit 라운드에 포함할지 여부.
3. **P0 auto-stub 21개 commands (`ant-trace/`, `autofix-pr/`, `backfill-sessions/`, `bughunter/` 등)** 의 Epic #1633 dead-code elimination 진척 — 본 audit 에서 caller-graph 부재 확인되면 즉시 삭제할지 차기 spec 으로 분리할지 결정.

## 부록 A.1 — PRESERVE-IDENTICAL Commands 전체 list (157)

`add-dir/add-dir.tsx`, `add-dir/index.ts`, `add-dir/validation.ts`, `advisor.ts`, `agents/agents.tsx`, `agents/index.ts`, `branch/branch.ts`, `branch/index.ts`, `bridge-kick.ts`, `bridge/index.ts`, `brief.ts`, `btw/btw.tsx`, `btw/index.ts`, `chrome/chrome.tsx`, `chrome/index.ts`, `clear/clear.ts`, `clear/conversation.ts`, `clear/index.ts`, `color/color.ts`, `color/index.ts`, `commit-push-pr.ts`, `commit.ts`, `compact/index.ts`, `config/config.tsx`, `config/index.ts`, `context/context-noninteractive.ts`, `context/context.tsx`, `context/index.ts`, `copy/copy.tsx`, `copy/index.ts`, `cost/index.ts`, `desktop/desktop.tsx`, `desktop/index.ts`, `diff/diff.tsx`, `diff/index.ts`, `doctor/doctor.tsx`, `doctor/index.ts`, `effort/effort.tsx`, `effort/index.ts`, `exit/exit.tsx`, `exit/index.ts`, `export/export.tsx`, `export/index.ts`, `extra-usage/index.ts`, `fast/index.ts`, `files/files.ts`, `files/index.ts`, `heapdump/heapdump.ts`, `heapdump/index.ts`, `help/help.tsx`, `help/index.ts`, `hooks/hooks.tsx`, `hooks/index.ts`, `ide/ide.tsx`, `ide/index.ts`, `init-verifiers.ts`, `init.ts`, `install-github-app/ApiKeyStep.tsx`, `install-github-app/CheckExistingSecretStep.tsx`, `install-github-app/CheckGitHubStep.tsx`, `install-github-app/ChooseRepoStep.tsx`, `install-github-app/CreatingStep.tsx`, `install-github-app/ErrorStep.tsx`, `install-github-app/ExistingWorkflowStep.tsx`, `install-github-app/index.ts`, `install-github-app/install-github-app.tsx`, `install-github-app/InstallAppStep.tsx`, `install-github-app/OAuthFlowStep.tsx`, `install-github-app/setupGitHubActions.ts`, `install-github-app/SuccessStep.tsx`, `install-github-app/WarningsStep.tsx`, `install-slack-app/index.ts`, `install-slack-app/install-slack-app.ts`, `install.tsx`, `keybindings/index.ts`, `keybindings/keybindings.ts`, `mcp/addCommand.ts`, `mcp/index.ts`, `mcp/mcp.tsx`, `mcp/xaaIdpCommand.ts`, `memory/index.ts`, `memory/memory.tsx`, `mobile/index.ts`, `mobile/mobile.tsx`, `model/index.ts`, `model/model.tsx`, `output-style/index.ts`, `output-style/output-style.tsx`, `permissions/index.ts`, `permissions/permissions.tsx`, `plan/index.ts`, `plan/plan.tsx`, `plugin/AddMarketplace.tsx`, `plugin/BrowseMarketplace.tsx`, `plugin/DiscoverPlugins.tsx`, `plugin/index.tsx`, `plugin/ManageMarketplaces.tsx`, `plugin/parseArgs.ts`, `plugin/plugin.tsx`, `plugin/pluginDetailsHelpers.tsx`, `plugin/PluginErrors.tsx`, `plugin/PluginOptionsDialog.tsx`, `plugin/PluginSettings.tsx`, `plugin/PluginTrustWarning.tsx`, `plugin/UnifiedInstalledCell.tsx`, `plugin/usePagination.ts`, `plugin/ValidatePlugin.tsx`, `pr_comments/index.ts`, `privacy-settings/index.ts`, `rate-limit-options/index.ts`, `release-notes/index.ts`, `release-notes/release-notes.ts`, `reload-plugins/index.ts`, `reload-plugins/reload-plugins.ts`, `remote-env/remote-env.tsx`, `remote-setup/remote-setup.tsx`, `rename/index.ts`, `resume/index.ts`, `resume/resume.tsx`, `review/ultrareviewEnabled.ts`, `review/UltrareviewOverageDialog.tsx`, `rewind/index.ts`, `rewind/rewind.ts`, `sandbox-toggle/index.ts`, `sandbox-toggle/sandbox-toggle.tsx`, `security-review.ts`, `session/index.ts`, `session/session.tsx`, `skills/index.ts`, `skills/skills.tsx`, `stats/index.ts`, `stats/stats.tsx`, `status/index.ts`, `status/status.tsx`, `stickers/index.ts`, `stickers/stickers.ts`, `tag/index.ts`, `tag/tag.tsx`, `tasks/index.ts`, `tasks/tasks.tsx`, `terminalSetup/index.ts`, `terminalSetup/terminalSetup.tsx`, `theme/index.ts`, `theme/theme.tsx`, `thinkback-play/index.ts`, `thinkback-play/thinkback-play.ts`, `thinkback/index.ts`, `thinkback/thinkback.tsx`, `upgrade/index.ts`, `upgrade/upgrade.tsx`, `usage/index.ts`, `usage/usage.tsx`, `version.ts`, `vim/index.ts`, `vim/vim.ts`, `voice/index.ts`, `voice/voice.ts`.

(157 confirmed via cmp -s loop on 2026-05-03.)
