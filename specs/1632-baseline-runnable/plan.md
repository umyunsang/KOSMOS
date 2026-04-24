# Implementation Plan: P0 · Baseline Runnable (CC src 컴파일·런타임 복구)

**Branch**: `1632-baseline-runnable` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/1632-baseline-runnable/spec.md`
**Epic**: [#1632](https://github.com/umyunsang/KOSMOS/issues/1632)

## Summary

KOSMOS 마이그레이션 DAG 의 최하단(P0) — 포팅된 CC 2.1.88 소스 (`tui/src/`)
가 `bun install` · `bun run src/main.tsx` · `bun test` 세 커맨드에서 compile/
runtime 오류 없이 동작하도록 복구한다. 실제 기능(Anthropic API, OAuth, MCP,
analytics, KAIROS/COORDINATOR 등)은 전부 stub/no-op 으로 고정해 후속 P1 dead
code elimination 이 안전하게 "도달 불가" 증명에 기대 정리할 수 있게 한다.

**기술적 접근**: (1) 누락 5 개 npm 패키지 추가 → `bun install` 해결. (2)
`bun:bundle` 가상 모듈을 `tsconfig.json paths` 로 stub 파일에 매핑해 960 개
`feature()` 호출을 전부 `() => false` 로 수렴. (3) `src/main.tsx` 의 부트스트랩
사이드이펙트(MDM raw read, keychain prefetch, OAuth config, GrowthBook,
telemetry, analytics) 를 in-place no-op 으로 neutralize. (4) `cp` 로 생긴
이중 중첩 디렉터리(`src/constants/constants/`, `src/services/services/`) 를
canonical 단일 경로로 flatten. (5) `tsconfig.json paths` 에 `src/*` bare-root
import 매핑 추가 (CC 원본이 사용하는 `from 'src/services/...'` 해결).

## Technical Context

**Language/Version**: TypeScript 5.6+ · React 19.2 (TUI layer only — 본 Epic 은
Python 레이어를 건드리지 않음)
**Primary Dependencies**:
- Existing (baseline 유지): `ink (npm:@jrichman/ink@6.6.9)` · `react@19.2` ·
  `@inkjs/ui@2.0.0` · `zod@3.23`
- **Adding in P0** (FR-001): `@commander-js/extra-typings` · `chalk` ·
  `lodash-es` · `chokidar` · `@anthropic-ai/sdk`
**Storage**: N/A — P0 에는 사용자 데이터/세션 저장이 없음 (스플래시까지만 목표)
**Testing**: `bun test` (`bun-types` + `ink-testing-library@4.0.0`)
**Target Platform**: macOS ARM64 · Bun v1.2.x · 터미널(Kitty/iTerm2/Terminal.app)
**Project Type**: Terminal UI application (Ink + React, CC 2.1.88 포팅)
**Performance Goals**: 스플래시 3 초 이상 stable 유지 (spec SC-001). 첫 프레임
지연은 P0 에서 측정만 하고 threshold 를 강제하지 않음 — 최적화는 후속 Epic 범주.
**Constraints**:
- 부트스트랩 외부 egress = 0 (FR-008 · 헌법 I/II 정렬 · PIPA §17)
- `bun test` 통과 수 ≥ 540 / upstream 549 (SC-003)
- CC 시각 ≥ 90% fidelity 유지 (메모리 `CC TUI 90% fidelity`)
**Scale/Scope**: `tui/src/` 하위 1,884 .ts/.tsx 파일 · 960 `feature()` call-sites ·
200 `bun:bundle` import · 10 file 레벨 변경 (plan 에 따라)

## Constitution Check

*GATE: Phase 0 전 통과 필수. Phase 1 설계 후 재평가.*

### I. Reference-Driven Development → **PASS**
- 본 Epic 의 primary source 는 `.references/claude-code-sourcemap/restored-src/src/`
  (CC 2.1.88). 포팅은 Epic #287 에서 완료됐고, 본 Epic 은 그 포팅의 compile/runtime
  경로 복구만 담당.
- `bun:bundle` 의 `feature(flag)` 패턴 자체가 CC 원본 관용이므로(`grep -l bun:bundle`
  결과에서 restored-src 에도 동일 존재 확인), stub 구현은 CC 의 dead-code-elimination
  관용(항상 false 반환 시 bundler 가 경로 제거)을 따른다.
- docs/vision.md § Reference materials 매핑: TUI 레이어 → Ink + Gemini CLI (기반),
  Claude Code sourcemap (세부 구조). 본 Epic 은 기반만 복구하고 레이어별 확장은
  후속 Epic 에서.

### II. Fail-Closed Security → **PASS (by default)**
- P0 는 tool adapter 를 추가하지 않음. 헌법 §II 의 fail-closed 기본값 (`requires_auth
  = True`, `is_personal_data = True`, `cache_ttl_seconds = 0`) 적용 대상 0 건.
- **fail-closed 정신의 일반화**: 본 Epic 에서 도입하는 `feature()` stub 은 "모르면
  false" 로 수렴 — 이는 fail-closed 의 TS 세계 유사체. 활성화된 코드 경로가 실수로
  연결되는 것을 방지 (Anthropic-only 코드가 런타임에 깨어나지 않음).

### III. Pydantic v2 Strict Typing → **N/A**
- P0 는 Python 백엔드 또는 tool I/O 를 건드리지 않음. TypeScript side 만 변경.

### IV. Government API Compliance → **PASS**
- P0 부트스트랩 경로에서 `data.go.kr` · 외부 API 호출 0 건 (FR-008). CI 에서
  live-API 호출 금지 규칙 위반 없음.

### V. Policy Alignment → **N/A**
- P0 는 인프라 복구로, 한국 AI Action Plan 원칙 8/9 · PIPA 정렬은 후속 Epic
  (#1633 Anthropic→FriendliAI, #1634 Tool system) 에서 실제로 구현됨.

### VI. Deferred Work Accountability → **PASS**
- spec.md "Scope Boundaries & Deferred Items" 섹션 존재 · 9 개 deferred 항목 전부
  tracking issue (#1633–#1637) 매핑 완료 · `/speckit-analyze` ghost-work gate
  통과 설계.

**Gate 종합**: 모든 항목 PASS 또는 N/A. 위반 없음 → Phase 0 진입 허용.

## Project Structure

### Documentation (this feature)

```text
specs/1632-baseline-runnable/
├── plan.md                   # This file
├── research.md               # Phase 0 output (이 문서와 함께 생성)
├── quickstart.md             # Phase 1 output (이 문서와 함께 생성)
├── checklists/
│   └── requirements.md       # spec quality checklist (완료)
└── tasks.md                  # Phase 2 output (/speckit-tasks — 다음 단계)
```

data-model.md 는 생성하지 않음 — spec.md "Key Entities" 절에서 이미 "본 Epic
은 데이터 엔티티를 새로 정의하지 않는다" 라고 명시.

contracts/ 디렉터리는 생성하지 않음 — 외부 사용자 대상 인터페이스는 세 개의 CLI
커맨드(`bun install`, `bun run src/main.tsx`, `bun test`) 이고 모두 표준 출력/
exit status 로 검증 가능하며, `bun:bundle.feature` 의 함수 시그니처는 quickstart.md
에 단일 블록으로 문서화.

### Source Code (repository root)

본 Epic 의 모든 변경은 `tui/` 서브트리 안에서 이뤄지며 다른 경로(`backend/`,
`docs/`, `.specify/` 등)는 수정하지 않는다.

```text
tui/
├── package.json              # MODIFY · +5 deps (FR-001)
├── tsconfig.json             # MODIFY · +paths (FR-003, FR-004)
├── src/
│   ├── main.tsx              # MODIFY · bootstrap neutralize (FR-005)
│   ├── stubs/
│   │   ├── any-stub.ts       # (기존 · 유지)
│   │   ├── react-compiler-runtime.ts  # (기존 · 유지)
│   │   └── bun-bundle.ts     # CREATE · `feature` stub (FR-003)
│   ├── constants/
│   │   ├── constants/        # DELETE (이중 중첩) — 내부 파일 20+ 개 상위로 이동
│   │   ├── apiLimits.ts      # MOVED from constants/constants/apiLimits.ts
│   │   ├── oauth.ts          # MOVED …
│   │   └── …                 # (총 20 개 파일 flatten)
│   └── services/
│       ├── services/         # DELETE (이중 중첩) — 내부 하위 전부 상위로 이동
│       ├── api/              # MOVED / merged
│       ├── analytics/        # MOVED / merged
│       └── …                 # 기타 기존 하위들
└── tests/
    └── unit/
        └── stubs/
            └── bun-bundle.test.ts   # CREATE · US3 단위 테스트 (FR-003)
```

**Structure Decision**: 단일 TypeScript 프로젝트 (`tui/`). 본 Epic 은 신규
디렉터리 도입 없이 기존 구조 내에서 수정/삭제/1 개 신설 파일로 제한. FR-007 의
flatten 은 디렉터리 수준 이동으로 수행 (import 수정 불필요 — 소비자는 이미
`src/constants/X` · `src/services/Y` 단일 중첩 경로로 참조 중).

## Phase Summary

### Phase 0 · Research (이 PR 에서 산출)

아래 5 개 design decision 을 `research.md` 에 기록. 각 decision 은 (1) 무엇을
선택, (2) 왜, (3) 대안, (4) `docs/vision.md § Reference materials` 또는
constitution 매핑을 포함.

1. `bun:bundle` 해소 전략 → tsconfig `paths` 매핑 채택.
2. `@anthropic-ai/sdk` 런타임 해소 → 실 패키지 설치 채택.
3. `main.tsx` 부트스트랩 neutralize 방식 → in-place edit + 로컬 stub 채택.
4. 이중 중첩 디렉터리 해소 → filesystem move (flatten) 채택.
5. 테스트 회귀 floor 설정 근거 → 540 (upstream 549 대비 98%) 설정.

**Deferred Items 검증**: spec.md 의 9 개 deferred 항목을 Phase 0 에서 재확인 —
7 개가 `#1633`, 1 개가 `#1634`, 1 개가 `#1635`/`#1636`/`#1637` 에 연결됨. 모든
이슈가 현재 OPEN 상태임을 `gh issue view` 로 확인. 헌법 §VI 통과.

### Phase 1 · Design & Contracts (이 PR 에서 산출)

- **data-model.md**: 생략 — 엔티티 0.
- **contracts/**: 생략 — P0 의 외부 인터페이스는 `bun run src/main.tsx` stdout/
  tty 렌더 결과 (시각 검증) + `bun test` exit status (수치 검증). 신규 API 계약
  없음.
- **quickstart.md**: 기여자가 P0 변경을 로컬에서 검증하는 3 단계 절차
  (`bun install → bun run src/main.tsx → bun test`) + 예상 출력/실패 시 triage
  가이드. (신규 기여자 5 분 onboarding 검증에 사용 — SC-005 지원.)
- **Agent context update**: `.specify/scripts/bash/update-agent-context.sh
  claude` 실행 → `CLAUDE.md` 에 P0 변경사항(신규 deps, stub 경로 규칙)을
  반영.

### Phase 2 · Tasks (다음 명령 `/speckit-tasks` 에서 생성)

본 plan 은 tasks.md 를 직접 생성하지 않음. 예상 task 수: **9–12 건**
(FR-001 ~ FR-010 을 TDD 순서로 분할 · 이중 중첩 flatten 은 독립 commit · stub
단위 테스트 + 통합 smoke 테스트 각각 1 건).

## Complexity Tracking

본 Epic 은 헌법 위반 없음. 복잡도 justification 필요 항목 0 개.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(없음)*  | —          | —                                   |
