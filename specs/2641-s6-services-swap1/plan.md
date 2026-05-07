# Plan 2641 · S6 Services swap-1 마무리

## Phase 0 — Reference grounding

### `docs/vision.md § Reference materials`
이 작업은 6-layer 설계의 Layer 1 (LLM Harness) 의 swap-1 (Anthropic SDK →
UMMAYA IPC) **마무리** 정리에 해당. Reference materials 표 중 직접 인용:

| Reference | 본 작업과의 매핑 |
|---|---|
| **Claude Code sourcemap** (ChinaSiro/claude-code-sourcemap) | `services/teamMemorySync/index.ts` + `services/settingsSync/index.ts` 의 byte-copy baseline. 박제 헤더가 인용해야 하는 SHA-256 source path. |
| **Claude Reviews Claude** (openedclaude/claude-reviews-claude) | claude.ai backend 의 team-memory + user-settings sync 가 claude.ai SaaS 종속이라는 architectural rationale 의 출처. 본 작업은 이를 UMMAYA 에서 반드시 deactivate 하는 정당화. |
| Anthropic 공식 docs | `/api/claude_code/team_memory` + `/api/claude_code/user_settings` endpoint 가 1P 서버에 존재한다는 확인 (참고용 — UMMAYA 는 도달하지 않음). |

### `docs/requirements/ummaya-migration-tree.md § L1-A LLM Harness`
- **A1 Provider** = "FriendliAI serverless + K-EXAONE 단일 고정". 그러므로
  claude.ai backend 호출은 UMMAYA 의 정의상 dead. teamMemorySync /
  settingsSync 가 axios 로 claude.ai 에 GET/PUT 하는 것은 A1 위반의 잠재 위험
  → dead-call gate 로 코드 enforcement.
- **A7 Observability** = "외부 egress 0". axios live-call 의 발신 자체가 외부
  egress → A7 위반의 잠재 위험. dead-call gate 가 enforce.

### `specs/cc-migration-audit/scope-S6-services.md`
- § swap-1 종속 표면 매핑 표 (row 11-12) 가 본 spec 의 직접 source.
- § 핵심 발견 #5 ("teamMemorySync + settingsSync 의 미해결 dead-call") 가 본
  작업의 정당화.
- § 사용자 결정 #1 가 방안 B (claude.ts-style 박제 헤더 + dead-call gate) 로
  resolved (`decisions.md`).

### `specs/cc-migration-audit/decisions.md § S6 Services`
- Row "api/client.ts 중복" → 즉시 fix (Epic E P1)
- Row "teamMemorySync + settingsSync" → 방안 B (claude.ts-style 박제 헤더 +
  dead-call gate). claude.ts 패턴 일관성.

### Spec 2521 박제 패턴 (`tui/src/services/api/claude.ts:1-23`)
직접 인용하는 4-항 헤더 구조:
1. SPDX-License-Identifier
2. "Spec <N> — byte-copy(<N>) baseline restored from <restored-src path>" +
   SHA-256
3. swap label 3 종 (`swap/llm-provider`, `swap/anti-anthropic-1p`,
   `swap/identifier-rename`)
4. "This file has zero (live) callers in tui/src after Spec <M>" 단언

### Initiative #1633 P2 stub 패턴 (`tui/src/services/oauth/client.ts`)
참고 — 박제 vs full no-op stub 선택 비교. `decisions.md` 가 "claude.ts 패턴
일관성" 명시이므로 **박제** 채택 (oauth stub 패턴 X).

---

## Phase 1 — 구현 전략 (3 작업 = 3 teammate dispatch unit)

### Task group T1 — `api/client.ts` duplicate fix (Sonnet teammate "client-fix")
- 책임: line 22-40 (Spec 2077 async/throw stub) 제거. line 47-49 (Spec 2521
  sync/null stub) + 그 위 swap label coment block 만 보존.
- 변경 라인 수 ≤ 25 (제거 위주). 1 file change.
- 위험: line 22 만 import 하는 caller 가 있는지 검증 필요. 위 grep 으로 확인:
  `claude.ts` 의 `getAnthropicClient` 호출은 line 47 sync 시그니처와 호환
  (호출 결과를 사용하는 코드 자체가 zero-callers 박제이므로 sync vs async 가
  의미 없음).
- 검증: `bun typecheck`, `bun test tui/src/services/api/`.

### Task group T2 — `teamMemorySync/index.ts` 박제 (Sonnet teammate "team-mem-deaden")
- 책임:
  - File top (line 1 직전) 에 4-항 박제 헤더 추가.
  - 4 public entry-point (`pullTeamMemory`, `pushTeamMemory`, `syncTeamMemory`,
    `isTeamMemorySyncAvailable`) 의 본문 첫 줄에 dead-call gate (throw) 삽입.
  - `createSyncState`, `hashContent`, `batchDeltaByBytes` 는 순수 — gate
    미적용.
  - 신규 테스트 파일 `services/teamMemorySync/__tests__/dead-call-gate.test.ts`
    추가 — 4 entry 가 throw 하는지 assert.
- 변경 라인 수 ≤ 80 (헤더 ~30 + gate × 4 ~20 + test file ~30). 2 file change.
- 위험: `teamMemSecretGuard.ts` 가 sibling 으로 `secretScanner.ts` 를 import
  하는데, 그 chain 은 전혀 건드리지 않음 → secrets guard 회귀 0 보장.
- 검증: `bun test tui/src/services/teamMemorySync/`, 신규 테스트 PASS.

### Task group T3 — `settingsSync/index.ts` 박제 (Sonnet teammate "settings-sync-deaden")
- 책임:
  - File top 에 4-항 박제 헤더 추가 (단, "two callers survive" 변형 명시).
  - 4 entry-point (`uploadUserSettingsInBackground`, `doDownloadUserSettings`
    [private], `downloadUserSettings`, `redownloadUserSettings`) 의 본문 첫
    줄 (또는 `feature(...)` 분기 직후) 에 dead-call gate (silent early-return,
    NOT throw — caller 가 critical path) 삽입.
  - `_resetDownloadPromiseForTesting` 는 test-only — gate 미적용.
  - 신규 테스트 파일 `services/settingsSync/__tests__/dead-call-gate.test.ts`
    추가 — 4 entry 가 silent-skip 인지 assert.
- 변경 라인 수 ≤ 100 (헤더 ~35 + gate × 4 ~25 + test file ~40). 2 file change.
- 위험: `cli/print.ts` 의 critical boot path 가 `downloadUserSettings()` 결과를
  사용 (line 519 `void downloadUserSettings()` + line 1718 `await
  downloadUserSettings()`). silent return false 가 기존 `feature() === false`
  와 동일한 행동이므로 회귀 0.
- 검증: `bun test tui/src/services/settingsSync/`, `bun test tui/src/cli/`,
  Layer 5 boot smoke 가 services 초기화 path 무손상 캡처.

### Phase 2 — 통합 검증 (Lead Opus 직접)
1. `bun typecheck` — duplicate `getAnthropicClient` 경고 0 확인.
2. `bun test` — 전체 회귀 0 확인 (services 변경 영역만 영향, 다른 파일
   touch 0).
3. Layer 5 tmux capture-pane boot smoke (`scripts/tui-tmux-capture.sh
   /tmp/2641-smoke specs/2641-s6-services-swap1/scripts/smoke-boot.sh`):
   - boot 완료 → tool_registry 메시지 → UMMAYA branding → snap-001-boot.txt
   - snap-002-final.txt
   - 3 + screenshot keyframe (PNG) — Read tool 로 시각 확인.
4. dead-call gate 단위 테스트 2 개 PASS 재확인.
5. PR 생성 → CI watch → Codex P1 처리 → Copilot Gate completion.

---

## Phase 3 — Reference materials cross-check

| 결정 | docs/vision.md 또는 docs/requirements 의 어떤 항목? |
|---|---|
| 박제 헤더 형식 = Spec 2521 패턴 일관 | `docs/vision.md § "Claude Code is the first reference"` (CC 박제 = first reference) |
| dead-call gate 가 axios call site 보다 훨씬 안쪽 (defense in depth) | `docs/vision.md § Layer 4 — Permission Pipeline` (defense-in-depth principle) + `ummaya-migration-tree.md § L1-A A7 Observability "외부 egress 0"` |
| `teamMemorySync` throw vs `settingsSync` silent-skip 차이 | `ummaya-migration-tree.md § L1-A A6 Error recovery "일반 네트워크 retry only"` (boot path 의 fail-open 원칙) |
| api/client.ts 중복 제거 = Spec 2521 stub 보존 | `decisions.md § S6 Services` 명시 결정 + `docs/vision.md § "byte-identical default"` |

---

## Phase 4 — Risks & mitigations

| 위험 | 완화 |
|---|---|
| `claude.ts` 가 line 22 (async) `getAnthropicClient` 시그니처를 expect | grep 으로 확인: `claude.ts` 의 호출은 결과를 즉시 dereference 하지 않고 객체 method 까지 다단계 — sync `null` 반환은 `null.beta...` 에서 throw 하지만 zero-callers 보장이므로 unreachable. typecheck 만 pass 하면 안전. |
| dead-call gate 가 production boot 를 깨뜨림 | settingsSync 는 silent early-return 으로 throw 회피. teamMemorySync 는 setup.ts:358 의 `feature('TEAMMEM')=false` 가 1차 gate 이므로 gate throw 도달 불가. |
| 신규 테스트가 다른 dead-call gate (process.env 변수) 에 영향 | 테스트 안에서 `process.env.UMMAYA_ENABLE_DEAD_TEAM_MEM_SYNC` / `UMMAYA_ENABLE_DEAD_SETTINGS_SYNC` 명시 unset → 테스트 격리. |
| Layer 5 boot smoke 가 reasoning latency 로 timeout | services 변경은 LLM 호출과 무관 — boot smoke 는 tool_registry 메시지 + branding 까지만 wait_for_pane (≤ 30s). K-EXAONE 30-90s 함정 회피. |
| Codex P1 review 가 dead-call gate 의 throw 메시지 형식에 이의 | UMMAYA_ENABLE_DEAD_* env override 옵션이 명시 되어있으므로 "절대 dead 가 아니라 escape hatch 가 있다" 로 응답 가능. |

---

## Phase 5 — Definition of Done (DoD)

- [ ] FR-001 ~ FR-006 모두 구현
- [ ] SC-001 ~ SC-009 모두 측정 PASS
- [ ] dispatch-tree.md 작성 (3 teammate)
- [ ] 박제 모듈 path 목록 PR description 에 명시
- [ ] `Closes #2641` only PR
- [ ] CI all green
- [ ] Codex P1 zero (or resolved)
- [ ] Copilot Gate completion 확인
