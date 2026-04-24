# Phase 0 Research: P0 · Baseline Runnable

**Epic**: #1632 · Baseline Runnable
**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Date**: 2026-04-24

## Deferred Items Validation (Constitution §VI gate)

`spec.md § Scope Boundaries & Deferred Items` 의 9 개 deferred 항목을 GitHub 상태로 재확인.

| # | Item (요약) | Tracking Issue | State (2026-04-24) |
|---|---|---|---|
| 1 | Anthropic-only dead code 제거 | [#1633](https://github.com/umyunsang/KOSMOS/issues/1633) | OPEN |
| 2 | FriendliAI 엔드포인트 연결 · 세션 JSONL 저장 | [#1633](https://github.com/umyunsang/KOSMOS/issues/1633) | OPEN |
| 3 | Tool system wiring · 4 primitive · Python stdio MCP | [#1634](https://github.com/umyunsang/KOSMOS/issues/1634) | OPEN |
| 4 | UI L2 컴포넌트 구현 | [#1635](https://github.com/umyunsang/KOSMOS/issues/1635) | OPEN |
| 5 | Plugin DX Full 5-tier | [#1636](https://github.com/umyunsang/KOSMOS/issues/1636) | OPEN |
| 6 | Docs/API specs + 종단간 smoke | [#1637](https://github.com/umyunsang/KOSMOS/issues/1637) | OPEN |
| 7 | Coordinator · KAIROS · SSH · BG sessions · bridge mode | [#1633](https://github.com/umyunsang/KOSMOS/issues/1633) | OPEN |
| 8 | Telemetry sinks 재연결 | [#1633](https://github.com/umyunsang/KOSMOS/issues/1633) | OPEN |
| 9 | GrowthBook analytics · refresh·growthbook·* · services/analytics/* | [#1633](https://github.com/umyunsang/KOSMOS/issues/1633) | OPEN |

**Unregistered-deferral scan**: spec.md 전문에서 정규식 `(separate epic|future
epic|Phase [2-9]|v2|deferred to|later release|out of scope for v1)` 매치를 수행.
매치된 모든 표현은 Deferred Items 테이블 또는 Out of Scope 섹션에 대응 엔트리
존재 — 위반 없음.

**Gate 판정**: PASS. 9/9 tracking issue 가 OPEN, 모든 자유문 deferral 이 구조화
테이블에 기록됨.

---

## Design Decisions

### Decision 1 — `bun:bundle` 해소 전략

**Chosen**: `tsconfig.json` `paths` 매핑으로 `bun:bundle` → `./src/stubs/bun-bundle.ts`
에 매핑한다. stub 는 `export function feature(_flag: string): boolean { return
false; }` 한 줄로 구성.

**Rationale**:
- `bun:bundle` 은 Bun bundler 가 번들 시점에만 제공하는 가상 모듈이다. 개발 모드
  `bun run src/main.tsx` 나 `bun test` 는 bundler 를 타지 않아 resolve 실패.
- 기존 `tsconfig.json` 에 이미 동일 패턴 6 건 등록 (`react/compiler-runtime`,
  `lodash-es/*`, `@alcalzone/ansi-tokenize`, `semver`, `usehooks-ts`,
  `@anthropic-ai/sdk/*` → any-stub). 새 매핑은 그 관용을 그대로 확장.
- `feature()` 가 항상 `false` 반환하면 CC 의 dead-code-elimination 관용(upstream
  도 `feature('X') ? require('…') : null` 패턴)과 정합. P1 에서 이 경로들을 잘라
  낼 근거가 그대로 확보됨.

**Alternatives considered**:
- **Bun plugin (`Bun.plugin({ setup(build) { build.onResolve({filter:/bun:bundle/},…) }})`)**:
  런타임 resolver 가 필요하고 `bun test`/`bun run` 양쪽 모두에 plugin 주입이 필요.
  tsconfig paths 보다 복잡하고, 기존 stub 인프라와 이질적.
- **Global shim module (e.g. `@types/bun-bundle`)**: 타입만 해결되고 런타임
  resolve 실패. 불충분.
- **Sed 일괄 치환 (`feature('X')` → `false`)**: 960 call-site 전부 수정, CC
  원본과의 diff 팽창으로 Spec 031/Epic #287 의 fidelity 원칙 위반 (메모리
  `CC TUI 90% fidelity`).

**Reference mapping**: `docs/vision.md § Reference materials` → Claude Code
sourcemap (upstream 동일 관용). 헌법 §I.

### Decision 2 — `@anthropic-ai/sdk` 런타임 해소

**Chosen**: 실제 npm 패키지 `@anthropic-ai/sdk` 를 `tui/package.json`
`dependencies` 에 추가해 런타임 import 가 정상 resolve 되게 한다. tsconfig 의
`@anthropic-ai/sdk/*` → `./src/stubs/any-stub` 매핑은 **유지** — 타입 해결은
any-stub 경로로 stub, 런타임만 실제 패키지로 작동.

**Rationale**:
- `src/utils/errors.ts` · `src/hooks/useCanUseTool.tsx` 가 런타임에 심볼을
  실제로 요구. 타입 stub 만으로는 `Cannot find module` 에러.
- 실제 패키지 설치는 npm 디스크 비용만 추가 (대략 8MB) — 빌드/시각 영향 없음.
- 타입 stub 유지 이유: CC 의 타입 복잡도를 그대로 가져오면 `noUncheckedIndexedAccess`
  등 엄격 옵션과 충돌할 수 있음. any-stub 로 점진 완화해 빌드 성공을 우선.
- FR-008 (부트스트랩 egress 0) 은 "SDK 가 설치돼 있음" 과 독립. 호출을 안 하면
  네트워크 egress 0. SDK 의 생성자(`new Anthropic({...})`) 가 실제로 실행되는
  경로는 `feature()` 로 gate 돼 stub 이 false 를 반환하면 도달 불가.

**Alternatives considered**:
- **런타임 stub 모듈(`src/stubs/anthropic-sdk-runtime.ts`)**: CC 가 사용하는 모든
  export(수십 개 class/type) 를 손으로 stub 해야 함. 유지보수 비용 큼.
- **의존성 제거하고 호출부 삭제**: P1 스코프. P0 에서 대규모 삭제는 Epic 목적
  이탈.

**Reference mapping**: AGENTS.md § 'Never add a dependency outside a spec-driven
PR' — 본 Epic 이 그 spec. PR 본문에서 명시.

### Decision 3 — `src/main.tsx` 부트스트랩 neutralize 방식

**Chosen**: `src/main.tsx` 상단(1–86 라인) 의 Anthropic-only 사이드이펙트 6 곳을
**in-place edit** 으로 no-op 한다. import 자체는 유지 (모듈 최상위 사이드이펙트
제거만), 함수 호출만 주석 처리 또는 빈 async 함수로 교체.

대상:
1. `profileCheckpoint('main_tsx_entry')` → comment out
2. `startMdmRawRead()` → comment out
3. `startKeychainPrefetch()` → comment out
4. `initializeTelemetryAfterTrust` · `initializeGrowthBook` ·
   `refreshGrowthBookAfterAuthChange` → 호출 주석, import 은 유지
5. `getOauthConfig` · `fetchBootstrapData` · `prefetchPassesEligibility` ·
   `prefetchOfficialMcpUrls` 계열 prefetch → `feature()` 가드 뒤로 이동 or
   주석
6. `src/services/analytics/*` 관련 4 개 import → 사용처가 호출 안 하도록
   주석 (import 자체는 any-stub 타입으로 resolve)

**Rationale**:
- "시각 ≥ 90% fidelity" 원칙(메모리 `CC TUI 90% fidelity`) 은 UI 트리와 이름
  보존을 요구. main.tsx 를 통째로 재작성/대체하면 그 원칙 위반.
- P1 dead code elimination 이 최종 삭제 주체 — P0 는 "호출만 끊어 스플래시
  렌더를 막지 않는" 최소 변경에 집중.
- 주석 블록에 `// [P0 neutralized] see Epic #1633` 표식을 남겨 P1 에서 grep 으로
  일괄 추적 가능.

**Alternatives considered**:
- **`src/entrypoints/kosmos-main.tsx` 신설**: CC `src/entrypoints/cli.tsx`, `init.ts`
  등과 공존 → 엔트리 포인트 혼란, `bun run` target 변경 필요.
- **`feature()` 가드로 전부 감싸기**: 이미 일부 호출은 그 패턴. 일관성은 있으나
  diff 가 이 Epic 에서 커짐 — P1 에서 해당 가드 + call-site 통째로 제거하는
  게 더 깔끔.

**Reference mapping**: CC 원본 구조 보존 → 헌법 §I primary source. 변경 최소화
→ 메모리 `Minimal Change Engineer` 정신.

### Decision 4 — 이중 중첩 디렉터리(`constants/constants/`, `services/services/`) 해소

**Chosen**: 파일시스템 수준에서 `git mv` 로 내부 파일을 상위로 올리고 빈 디렉터리
제거 (**flatten**).

예:
```
tui/src/constants/constants/oauth.ts  →  tui/src/constants/oauth.ts
tui/src/constants/constants/*          →  tui/src/constants/*
tui/src/services/services/*            →  tui/src/services/*  (기존 services 와 merge)
```

소비자 import 는 이미 `from './constants/oauth.js'`, `from './services/api/...'`
등 canonical 단일 중첩 경로를 참조 — 이동 후 import 수정 없음.

**Rationale**:
- 이중 중첩은 "`cp -r src-a/src src-b/src`" 실수로 생긴 artefact (메모리 `TUI
  migration source` · Epic #287 컨텍스트). 포팅 원본 CC 의 `src/constants/`,
  `src/services/` 구조와 일치시키는 게 정답.
- tsconfig path remap 대안(`constants/*` → `src/constants/constants/*`) 은
  검색/편집/IDE 에서 혼란. 실제 파일 위치를 원본과 맞춤이 훨씬 간단.
- Merge 시 파일명 충돌 가능성 확인: `ls tui/src/services/` 결과에 이미 `api`,
  `analytics` 등 디렉터리가 존재하고, `tui/src/services/services/` 의 하위도
  `api`, `analytics` 포함 가능 — 실제 flatten 시 각 파일 단위 비교 필수
  (tasks.md 에서 task 별로 세분).

**Alternatives considered**:
- **tsconfig `paths` remap**: 위 "혼란" 이유로 기각.
- **심볼릭 링크**: 크로스 플랫폼 이슈, git 처리 복잡.

**Reference mapping**: CC 2.1.88 원본 `src/constants/*`, `src/services/*` 구조
와 동일. 헌법 §I (primary source fidelity).

### Decision 5 — 테스트 회귀 floor 540 설정 근거

**Chosen**: `bun test` 통과 수 ≥ **540** 을 P0 의 CI gate 로 고정. 상류 CC
2.1.88 baseline 이 **549** 이므로 약 **98.4%** 커버리지.

**Rationale**:
- 현재 통과 수 **449** (Epic #1632 본문). P0 변경으로 기대 회복: (a) missing
  dep 5 종 해소 → 관련 테스트 ~40 개 복구, (b) `bun:bundle` 해소 → 관련 테스트
  ~20 개 복구, (c) 이중 중첩 경로 수정 → 관련 테스트 ~40 개 복구. 낙관 합계
  ~100 개, 목표 91 개 확보.
- 9 개 (549 − 540) gap 은 P1 에서 Anthropic-only 테스트 제거와 함께 처리하거나,
  P0 단계에서 skip 마킹하는 옵션을 Phase 2 task 에서 결정.
- 98% 는 "upstream 기준 신뢰 가능한 플로어" 의 관례적 허용치. 더 낮추면 P1
  에서의 회귀 감지력 저하.

**Alternatives considered**:
- **≥ 549 (upstream 완전 패리티)**: 현실성 낮음 — Anthropic-only 테스트
  (OAuth, analytics, MDM 등) 는 stub 만으로 통과시키기 어려움. 이들은 P1 삭제 대상.
- **≥ 449 (현재 유지만)**: 실질적 개선 없음 — "baseline runnable" 의 이름값
  미달.

**Reference mapping**: 없음 (프로젝트 정책적 판단). spec.md SC-003 에 수치
고정.

---

## Open items forwarded to Phase 2 (`/speckit-tasks`)

- **Test triage**: 540 → 549 의 9 개 gap 을 어떤 테스트로 메꿀지 / 어떤 테스트를
  skip 처리할지 결정. (FR-006 / SC-003 지원)
- **`services/services/` flatten 충돌 해소 순서**: 파일명 충돌이 실제로 있는지
  `diff` 로 확인 후 task 를 파일 단위로 분할.
- **신규 패키지 lockfile 반영**: `bun.lockb` 가 커밋되는지 확인 (프로젝트 정책)
  + `bun install` 재현성 검증 step.

## Reference materials consulted

- `AGENTS.md § Stack` — Bun v1.2.x · Ink · TS 5.6+ 확정
- `CLAUDE.md § Active Technologies` — 의존성 추가 규칙 ("no new runtime
  dependencies outside a spec-driven PR")
- `docs/vision.md § Reference materials` — Claude Code sourcemap primary
- `.specify/memory/constitution.md § I–VI` — 헌법 gate 평가
- 메모리: `TUI migration source` · `CC TUI 90% fidelity` · `Minimal Change Engineer`
- Epic 본문 #1632 — file-level scope · package list · feature flag list
