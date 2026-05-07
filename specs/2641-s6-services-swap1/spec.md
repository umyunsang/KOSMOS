# Spec 2641 · S6 Services swap-1 마무리

> Feature for Epic #2641 under Initiative #2636 (CC Migration Audit-Driven Realignment).
> Source-of-truth: `specs/cc-migration-audit/scope-S6-services.md` § 사용자 결정 + `specs/cc-migration-audit/decisions.md § S6 Services`.

## Why

S6 services 감사 (`scope-S6-services.md`) 가 swap-1 (Anthropic SDK → UMMAYA IPC)
마이그레이션 상태를 "양호" 로 판정했지만 **3 개의 잔존 risk** 가 남았다:

1. `tui/src/services/api/client.ts` 에 `getAnthropicClient` 함수가 **두 번 정의됨**
   (line 22 async/throw + line 47 sync/null). TS 는 컴파일은 하지만 동일-symbol
   중복 선언으로 linter / IDE / 향후 typescript@5.7 strict 빌드에서 경고 → 회귀
   잠재 위험. CC 원본은 단일 정의 (`getAnthropicClient(opts): Anthropic`).
2. `tui/src/services/teamMemorySync/index.ts` 가 CC 원본 axios live-call 코드를
   거의 그대로 보존하면서 헤더에 "zero callers" 단언이 없다. 실제 callgraph 는
   `feature('TEAMMEM')=false` (`tui/src/stubs/bun-bundle.ts`) 로 dead 이지만
   **누가 미래에 feature flag 를 켜면 axios 가 claude.ai 로 발신**한다.
   `claude.ts` 처럼 박제 헤더 + dead-call gate 가 없어 callgraph 안전성이 코드
   에 명시되지 않는다.
3. `tui/src/services/settingsSync/index.ts` 는 `feature('DOWNLOAD/UPLOAD_USER_SETTINGS')`
   가 false 라서 runtime-dead 지만, `cli/print.ts` + `commands/reload-plugins/`
   에서 `downloadUserSettings` / `redownloadUserSettings` 를 **여전히 호출**한다.
   동일 박제-gate 부재.

## What

박제 패턴은 `tui/src/services/api/claude.ts` 가 Spec 2521 으로 확립한 4-항 헤더:

```
// SPDX-License-Identifier: Apache-2.0
// Spec <N> — byte-copy(<N>) baseline restored from <CC SHA-256 path>.
// • swap/llm-provider(<N>)         — <SDK rebind>
// • swap/anti-anthropic-1p(<N>)    — <1P deactivation strategy>
// • swap/identifier-rename(<N>)    — <brand token rename>
// This file has zero (live) callers in tui/src after Spec <M>; …
```

이 패턴을 두 sync 모듈에 적용 + dead-call gate (런타임 entry point 에서 throw
또는 명시적 short-circuit log) 를 추가. `api/client.ts` 는 중복 정의 제거
(line 47 의 Spec 2521 stub 만 남기고 line 22 의 Spec 2077 stub 삭제). 그 이유는
호출 site 가 `claude.ts` (그 자체가 zero-callers) 의 type-erased 위치이기
때문에 sync `null` 반환이 더 단순하고 충분.

## Scope

### In scope
- `tui/src/services/api/client.ts` — duplicate `getAnthropicClient` fix
- `tui/src/services/teamMemorySync/index.ts` — 박제 header + dead-call gate
- `tui/src/services/settingsSync/index.ts` — 박제 header + dead-call gate
- 회귀 검증:
  - `bun typecheck` — duplicate-symbol warning 0
  - `bun test` — services 회귀 0 (특히 teamMemSecretGuard / secretScanner /
    settingsSync schema 사용 site)
  - Layer 5 tmux capture-pane boot smoke — services 초기화 boot path 무손상
  - dead-call gate 단위 테스트 — gate 가 무인-callable 인지 + active call site
    가 silent-skip 인지 명시

### Out of scope
- `tui/src/services/api/claude.ts` 추가 변경 (이미 Spec 2521 박제 완료)
- `services/oauth/*` (이미 Spec #1633 P2 stub 완료)
- `services/teamMemorySync/secretScanner.ts` / `teamMemSecretGuard.ts` /
  `types.ts` / `watcher.ts` (전부 PRESERVE-IDENTICAL — `scope-S6-services.md` § 64)
- `services/settingsSync/types.ts` (PRESERVE-IDENTICAL)
- 기타 64 PRESERVE-IDENTICAL 파일 (변경 금지)
- swap-2 (도구 시스템) 종속 (Epic ε #2296 / γ #2294 영역)

## Functional Requirements

### FR-001 (api/client.ts duplicate fix)
`tui/src/services/api/client.ts` 에 `getAnthropicClient` 함수 정의는 **정확히
하나만** 존재해야 한다. 남은 단일 정의는 Spec 2521 의 sync/null stub
(`function getAnthropicClient(..._args: unknown[]): null { return null }`)
이며, 그 위 swap label 코멘트와 SPDX 헤더는 보존한다.

### FR-002 (teamMemorySync 박제 header)
`tui/src/services/teamMemorySync/index.ts` 파일 최상단에 `claude.ts` 패턴의
4-항 박제 헤더를 추가한다:
- SPDX 라인
- "Spec 2641 — byte-copy(2641) baseline … `services/teamMemorySync/index.ts`"
- swap/llm-provider(2641): constants/oauth → UMMAYA-1633 inline stub (이미 적용
  된 상태를 헤더로 명시)
- swap/anti-anthropic-1p(2641): `feature('TEAMMEM')=false` (`tui/src/stubs/bun-bundle.ts`)
  + `setup.ts:358` 게이트로 watcher 시작 자체가 dead → 모든 export 의 axios
  call site 가 unreachable
- "This file has zero live callers in tui/src after Spec 2641 (verified by
  callgraph audit)" 단언

### FR-003 (teamMemorySync dead-call gate)
`tui/src/services/teamMemorySync/index.ts` 의 4 개 public entry-point —
`pullTeamMemory`, `pushTeamMemory`, `syncTeamMemory`, `isTeamMemorySyncAvailable`
— 의 함수 본문 첫 줄에 dead-call gate 를 삽입한다:

```ts
if (!process.env.UMMAYA_ENABLE_DEAD_TEAM_MEM_SYNC) {
  throw new Error(
    '[UMMAYA] services/teamMemorySync: dead in UMMAYA — claude.ai team memory ' +
    'is not part of L1-A K-EXAONE harness. Set UMMAYA_ENABLE_DEAD_TEAM_MEM_SYNC=1 ' +
    'only when intentionally exercising the byte-copy reference (Spec 2641).',
  )
}
```

이로써 `feature('TEAMMEM')` 이 미래에 (실수로 또는 다른 구현 변경으로) 켜진
경우라도 axios 호출이 발생하기 전에 실패하여 callgraph 안전이 코드로 enforce
된다. `createSyncState` / `hashContent` / `batchDeltaByBytes` 는 순수 함수
이므로 gate 미적용 (외부 다른 UMMAYA 코드가 import 가능하므로 — 단, 현재 그런
caller 는 0).

### FR-004 (settingsSync 박제 header)
`tui/src/services/settingsSync/index.ts` 파일 최상단에 동일 패턴의 박제 헤더를
추가한다:
- SPDX
- "Spec 2641 — byte-copy(2641) baseline …"
- swap/llm-provider(2641): constants/oauth → inline stub (기존 상태 명시)
- swap/anti-anthropic-1p(2641): `feature('DOWNLOAD_USER_SETTINGS')` /
  `feature('UPLOAD_USER_SETTINGS')` 가 `tui/src/stubs/bun-bundle.ts` 에서 모두
  `false` → 모든 axios call site 가 unreachable
- "Two callers (`cli/print.ts` + `commands/reload-plugins/`) survive but receive
  early-`false` from the feature gate; this file's surface is preserved for CC
  parity (Spec 2641)."

### FR-005 (settingsSync dead-call gate)
`uploadUserSettingsInBackground`, `doDownloadUserSettings` (private helper —
gate at `feature('DOWNLOAD_USER_SETTINGS')` 분기 직후), `downloadUserSettings`,
`redownloadUserSettings` 의 axios-호출 ENTRY 직전에 명시적 dead-call gate
assert 를 삽입한다. 단, **에러 throw 가 아닌 explicit early-return + debug log**
로 처리해야 한다 (caller 가 print.ts 의 critical path 라 throw 시 실제 보트
실패 위험). 형태:

```ts
if (!process.env.UMMAYA_ENABLE_DEAD_SETTINGS_SYNC) {
  // Dead-call gate (Spec 2641): claude.ai settings sync is not part of L1-A
  // K-EXAONE harness. Surface preserved for CC parity; runtime is no-op.
  return /* false | void as appropriate */
}
```

`feature(...)` early-return 보다 더 안쪽 — 즉 만약 누가 `tui/src/stubs/bun-bundle.ts`
의 `feature()` 를 변경해도 UMMAYA_ENABLE_DEAD_SETTINGS_SYNC 가 명시 set 되지
않으면 axios 가 발신되지 않는다. 다층 방어.

### FR-006 (test coverage)
- `tui/src/services/teamMemorySync/__tests__/dead-call-gate.test.ts` 신설:
  4 개 entry-point 가 gate 없이 throw 함을 assert.
- `tui/src/services/settingsSync/__tests__/dead-call-gate.test.ts` 신설:
  4 개 entry-point 가 gate 없이 silent-return / false 임을 assert.
- 기존 `bun test` 회귀 0 (services 영역 + cli/print + reload-plugins 단위
  테스트 모두 green).

## Success Criteria

| ID | 측정 |
|---|---|
| SC-001 | `bun typecheck` exit 0, `getAnthropicClient` 중복 선언 경고 0 |
| SC-002 | `grep -c "function getAnthropicClient" tui/src/services/api/client.ts` == 1 |
| SC-003 | `bun test` services 영역 회귀 0 (변경 전후 pass count 동일 또는 ≥) |
| SC-004 | 신규 dead-call-gate 테스트 2 개 모두 PASS |
| SC-005 | `tui/src/services/teamMemorySync/index.ts` head 30 lines 에 SPDX + Spec 2641 + 3 swap labels + "zero live callers" 단언 모두 포함 |
| SC-006 | `tui/src/services/settingsSync/index.ts` head 30 lines 에 SPDX + Spec 2641 + 3 swap labels + 2-callers 명시 + early-skip 단언 포함 |
| SC-007 | Layer 5 tmux capture-pane boot smoke (`scripts/tui-tmux-capture.sh`) 가 boot 완료 후 services 초기화 path 무손상 캡처 + UMMAYA branding 출력 + tool_registry 메시지 출력 |
| SC-008 | 0 new runtime dependencies (AGENTS.md hard rule). |
| SC-009 | 변경 파일 3 개 + test 파일 2 개 + spec dir = 총 6 paths 이내 (≤ 10 file changes / 1 teammate dispatch budget) |

## Constraints / Hard Rules

- AGENTS.md byte-identical CC default: 박제 헤더 추가 외에 CC 원본 텍스트 보존
  (axios import / SyncState / batchDeltaByBytes / 모든 함수 시그니처 동일).
- AGENTS.md hard rule: zero new runtime deps.
- AGENTS.md spec-driven: PR body `Closes #2641` only; Task sub-issues 는 merge
  후 close.
- AGENTS.md TUI verification: services 변경이라 Layer 5 boot smoke 만으로 충분
  (interactive scenario 변경 0). PR description 에 boot smoke txt + screenshot
  3+ keyframe 첨부.
- Spec 2521 박제 패턴 일관성: 헤더 형식 동일, swap label 형식 동일.

## Non-Goals (이번 사이클 외)

- `services/teamMemorySync/watcher.ts` 박제 (PRESERVE-IDENTICAL — 변경 금지).
- `services/settingsSync/types.ts` 변경 (PRESERVE-IDENTICAL).
- `setup.ts:358` `feature('TEAMMEM')` 분기 자체 제거 (Initiative #1633 영역).
- 다른 6 Epic 의 작업 (Epic A/B/C/D/F/G).

## Open Questions (이미 결정됨)

`decisions.md § S6 Services` 에 명시:
1. api/client.ts 중복 → 즉시 fix (Epic E P1) ✓
2. teamMemorySync + settingsSync → 방안 B (claude.ts-style 박제 헤더 + dead-call gate) ✓

추가 결정 필요 사항 0.

## References

- `specs/cc-migration-audit/scope-S6-services.md` (특히 § swap-1 종속 표면 매핑 표 row 11-12)
- `specs/cc-migration-audit/decisions.md § S6 Services`
- `tui/src/services/api/claude.ts` 헤더 (line 1-23) — 박제 패턴 reference
- `.references/claude-code-sourcemap/restored-src/services/teamMemorySync/index.ts` — byte-copy 비교 baseline
- `.references/claude-code-sourcemap/restored-src/services/settingsSync/index.ts` — byte-copy 비교 baseline
- `tui/src/stubs/bun-bundle.ts` — `feature() === false` 의 단일 source-of-truth
- `tui/src/setup.ts:358` — `feature('TEAMMEM')` 게이트 site
- `tui/src/cli/print.ts:516,1715,3073` + `tui/src/commands/reload-plugins/reload-plugins.ts:25` — settingsSync 외부 caller
- AGENTS.md § CORE THESIS · § Hard rules · § TUI verification (Layer 5)
- `docs/vision.md § Reference materials`
- `docs/requirements/ummaya-migration-tree.md` § L1-A LLM Harness (services 가 swap-1 의 일부)
