# Feature Specification: P0 · Baseline Runnable (CC src 컴파일·런타임 복구)

**Feature Branch**: `1632-baseline-runnable`
**Created**: 2026-04-24
**Status**: Draft
**Input**: User description: "Epic #1632 (P0) 부터 /speckit-specify 착수해 spec.md 생성"
**Epic**: [#1632 · Baseline Runnable](https://github.com/umyunsang/KOSMOS/issues/1632)
**Canonical reference**: `docs/requirements/kosmos-migration-tree.md § 실행 Phase 순서 → P0`

## User Scenarios & Testing *(mandatory)*

<!--
  Audience: KOSMOS 기여자(내부 팀 + 외부 플러그인 기여자). 본 Epic은 하네스 인프라
  복구 단계이므로 "시민"이 아닌 "기여자"가 사용자이며, 모든 사용자 스토리는 포팅된
  CC 소스(`tui/src/`, CC 2.1.88)가 처음으로 정상 부팅·검증되는 흐름을 다룬다.

  Phase 관계:
    - 선행 완료: Epic #287 TUI 포팅(소스 cp) · Epic #288 shortcut Tier 1
    - 본 Epic (#1632 · P0): 컴파일·런타임 복구 (이 문서)
    - 후속: #1633 P1+P2 → #1634 P3 → #1635 P4 → #1636 P5 → #1637 P6
-->

### User Story 1 - 기여자가 기본 TUI 스플래시를 띄운다 (Priority: P1)

KOSMOS 기여자가 fresh clone 후 문서 지시(`bun install` → `bun run src/main.tsx`)만으로
CC 베이스라인 스플래시를 터미널에 띄운다. 스플래시는 최소 3초 동안 크래시 없이 유지되며,
이 시점에서 KOSMOS 하네스가 "실행 가능"한 상태임이 시각적으로 입증된다.

**Why this priority**: Epic #1632 의 문자 그대로의 목표. 이 한 가지가 달성되지 않으면
후속 Phase (P1 dead code elimination, P2 FriendliAI 연결, P3 tool system 등)는 전부
블로킹된다. 마이그레이션 DAG 의 최하단(bottom of the DAG).

**Independent Test**: 깨끗한 작업 디렉터리에서 `bun install && bun run src/main.tsx`
를 실행해 CC 스플래시가 3초 이상 렌더되고 그동안 uncaught exception/크래시가 발생하지
않음을 육안 + exit status + 로그로 확인할 수 있다.

**Acceptance Scenarios**:

1. **Given** `tui/` 가 fresh clone 상태이고 bun v1.2.x 가 설치돼 있을 때, **When**
   기여자가 `bun install` 을 실행하면, **Then** 설치가 0 missing-dep / 0 error 로
   완료된다.
2. **Given** 의존성 설치가 완료된 상태에서, **When** 기여자가 `bun run src/main.tsx`
   를 실행하면, **Then** CC 베이스라인 스플래시(`<App>` 루트)가 3초 이상 렌더되고
   그 시간 내에 프로세스가 비정상 종료되지 않는다.
3. **Given** 스플래시가 렌더된 상태에서, **When** 기여자가 프로세스를 `Ctrl+C` 로
   종료하면, **Then** exit status 0 또는 정상 SIGINT 종료 코드가 반환되고 stderr
   에 uncaught exception 스택트레이스가 남지 않는다.

---

### User Story 2 - 기여자가 회귀 테스트 플로어를 유지한다 (Priority: P2)

기여자가 `bun test` 를 실행하면 최소 540 개 테스트가 통과한다. 이는 현재 통과 수
449 에서 91 개 이상 회복되며, 상류 CC 2.1.88 baseline 549 대비 약 98.4% 수준을 유지
한다. 이 플로어는 이후 모든 PR 의 CI gate 기준이 된다.

**Why this priority**: 회귀 방지. P1+ 에서 대량 삭제가 발생할 때 회귀를 조기에
감지하려면 P0 시점에 "신뢰 가능한 최저 수"가 고정돼야 한다.

**Independent Test**: `bun test` 한 줄로 검증 가능 — 통과 테스트 수 ≥ 540 이면 통과,
미만이면 실패.

**Acceptance Scenarios**:

1. **Given** P0 변경이 적용된 브랜치에서, **When** 기여자가 `bun test` 를 실행하면,
   **Then** 통과 테스트 수가 540 이상이고 실패 테스트의 원인이 "모듈 해석 실패 / 누락
   의존성 / 이중 중첩 경로" 중 어느 것도 아님이 보장된다.
2. **Given** 동일 브랜치에서, **When** CI 에서 `bun test` 가 실행되면, **Then**
   로컬 실행과 동일한 통과 수가 재현된다 (flake 허용 ±0).

---

### User Story 3 - feature flag 호출이 안전하게 false 로 수렴한다 (Priority: P2)

기여자가 CC 포팅 코드 안에 산재한 `feature(<flag>)` 호출을 만났을 때, 모든 호출이
공통 stub 을 경유해 `false` 를 반환한다. 이로써 Anthropic-only 실험 플래그
(`COORDINATOR_MODE`, `KAIROS`, `DIRECT_CONNECT`, `WEB_BROWSER_TOOL` 등 17 종)
전부가 런타임에서 no-op 으로 비활성된다.

**Why this priority**: feature flag 누락은 `bun:bundle` 해석 실패 → 전체 빌드 실패로
이어진다. P1 에서 이 flag 와 관련된 코드 경로를 dead code 로 잘라낼 근거(= "false
일 때 도달 불가")를 본 Epic 이 공급한다.

**Independent Test**: `bun:bundle` 에서 import 된 `feature` 함수를 단위 테스트에서
임의의 flag name 으로 호출해 모두 `false` 를 반환하는지 검증.

**Acceptance Scenarios**:

1. **Given** stub 모듈 `tui/src/stubs/bun-bundle.ts` 가 존재할 때, **When**
   아무 코드에서 `feature("COORDINATOR_MODE")` 를 호출하면, **Then** `false` 를
   동기로 반환한다.
2. **Given** 알려지지 않은 flag name 이 전달돼도, **When** `feature("UNKNOWN")`
   를 호출하면, **Then** `false` 를 반환하고 예외를 던지지 않는다.
3. **Given** 960 call-site 가 포팅 코드에 존재할 때 (Epic #1632 본문 초기 추정
   61 → 실측 960), **When** 빌드(bun bundler) 가 실행되면, **Then** 모든
   call-site 가 단일 stub 구현으로 해석돼 "module not found: bun:bundle" 오류가
   0 건이다.

---

### Edge Cases

- **이중 중첩 경로 충돌**: `cp` 작업이 `src/constants/constants/oauth.ts`,
  `src/services/services/api/dumpPrompts.ts` 와 같은 이중 중첩을 남겼다. 다른 파일은
  `src/constants/oauth`, `src/services/api/dumpPrompts` 로 import 한다. P0 는
  canonical 경로(단일 중첩) 를 확정하고 소비자 import 와 일치시킨다.
- **타입 stub 은 있지만 런타임 패키지가 없는 경우**: `@anthropic-ai/sdk` 는 tsconfig
  가 타입 경로를 `any-stub` 으로 매핑하지만, 런타임에서 `src/utils/errors.ts`,
  `src/hooks/useCanUseTool.tsx` 가 실제 패키지를 resolve 한다. 이 Epic 은 "설치" 또는
  "런타임 stub" 둘 중 하나로 해소한다.
- **부트스트랩 사이드이펙트**: `src/main.tsx` 의 `profileCheckpoint`,
  `startMdmRawRead()`, `startKeychainPrefetch()`, `initializeTelemetryAfterTrust`,
  `initializeGrowthBook`, `getOauthConfig`, `src/services/analytics/*` 등은 P0 에서는
  no-op 처리 (본체 삭제 아님, 주석/stub) 해 스플래시 렌더까지의 경로를 확보한다.
- **bun bundler 가 bare-root `src/` import 를 해석하지 못함**: `tsconfig.json` `paths`
  에 `src/*` → `["./src/*"]` 매핑을 추가해 CC 원본의 bare import(`src/services/...`)
  를 해석 가능하게 한다.
- **스플래시 이후 입력 단계에서 크래시**: P0 는 "스플래시 3초 유지" 까지만 보장한다.
  그 이후 입력/세션/tool call 에서의 크래시는 P1+ 책임으로 남긴다.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `bun install` 은 `tui/` 디렉터리 내 어떤 `*.ts(x)` 파일의 직접 import
  도 "missing dependency" 경고 없이 해석해야 한다. 구체적으로 최소 다음 5 개 패키지가
  `tui/package.json` `dependencies` 에 추가돼 있어야 한다: `@commander-js/extra-typings`,
  `chalk`, `lodash-es`, `chokidar`, `@anthropic-ai/sdk`.
- **FR-002**: `bun run src/main.tsx` 는 CC 베이스라인 `<App>` 루트를 렌더해 스플래시
  화면을 최소 3 초간 표시해야 하며, 그 동안 프로세스에서 uncaught exception 이
  발생하지 않아야 한다.
- **FR-003**: `bun:bundle` 모듈의 `feature(flag: string): boolean` 심볼은 반드시
  단일 stub (`tui/src/stubs/bun-bundle.ts`) 으로 resolve 되어야 하며, 모든 알려진
  17 개 flag 및 미지의 flag 에 대해 동기 `false` 를 반환해야 한다.
- **FR-004**: `tsconfig.json` 의 `paths` 설정은 bare-root import `src/<rest>` 를
  `./src/<rest>` 로 매핑해야 한다. 현재는 `@/*` 만 존재하므로 CC 원본 import 스타일
  을 해석하지 못한다.
- **FR-005**: `src/main.tsx` 의 Anthropic-only 부트스트랩 사이드이펙트 (MDM raw read,
  keychain prefetch, OAuth config, analytics init, GrowthBook init, telemetry
  init) 는 P0 단계에서 호출되지 않거나 no-op 으로 대체돼야 한다. 단, CC 원본의 다른
  구조는 보존한다 (시각 ≥ 90% fidelity 원칙: 메모리 `CC TUI 90% fidelity`).
- **FR-006**: `bun test` 는 최소 540 개 테스트를 통과해야 하며, 실패 원인은
  "의존성 누락 / 모듈 해석 실패 / 이중 중첩 경로" 중 어느 것도 아니어야 한다.
- **FR-007**: 이중 중첩 디렉터리 (`src/constants/constants/`,
  `src/services/services/`) 는 canonical 단일 중첩 경로로 통합돼야 하며, 기존 소비자
  import 가 수정 없이 계속 해석되도록 해야 한다.
- **FR-008**: 본 Epic 의 변경으로 부트스트랩 경로에서 외부 네트워크 egress 가 발생
  하지 않아야 한다. 구체적으로 Anthropic API / OAuth 엔드포인트 / 외부 analytics
  sink / 외부 telemetry sink 호출이 0 건이어야 한다 (AGENTS.md "외부 egress 0"
  원칙, PIPA §17 준수).
- **FR-009**: `@anthropic-ai/sdk` 의 타입 import 는 컴파일 시점에 TypeScript 오류
  없이 해석돼야 한다. 해소 수단은 실제 패키지 설치 또는 런타임 stub 중 하나이며,
  그 선택은 plan 단계에서 결정한다.
- **FR-010**: P0 변경 범위 밖의 Anthropic 실제 호출, FriendliAI 실제 호출, OAuth
  실흐름, MCP connector, coordinator/KAIROS/SSH 기능 브랜치는 본 Epic 에서 활성화
  되지 않아야 한다 (feature flag `false` 고정 + 부트스트랩에서 차단).

### Key Entities

본 Epic 은 데이터 엔티티를 새로 정의하지 않는다. 파일·모듈 경로 컨벤션만 조정.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 최신 macOS (ARM64) + bun v1.2.x + fresh clone 환경에서 기여자가
  `bun install && bun run src/main.tsx` 를 순서대로 실행했을 때, 95% 이상의 시도
  에서 CC 스플래시가 3 초 이상 크래시 없이 렌더된다.
- **SC-002**: `bun install` 실행 결과에서 "missing dependency" / "cannot resolve"
  경고 및 에러가 0 건이다.
- **SC-003**: `bun test` 의 통과 테스트 수가 상류 CC 2.1.88 baseline 549 대비
  ≥ 98% (즉 ≥ 540 개) 에 도달한다.
- **SC-004**: 부트스트랩 (프로세스 시작부터 스플래시 렌더 완료까지) 중 외부 네트워크
  호출이 0 건으로 측정된다 (로컬 캡처 기준).
- **SC-005**: 신규 기여자 문서(`tui/README.md` 또는 `docs/` 해당 섹션)의 Quick
  start 절차대로 5 분 이내에 스플래시를 띄울 수 있다 (사용성 검증 · 1 명 이상 관찰
  기반).
- **SC-006**: P0 완료 후 P1 dead code elimination 을 시작할 때, feature flag 가
  활성화된 코드 경로가 "런타임 도달 불가" 로 증명 가능해야 한다 (stub 이 언제나
  `false` 반환).

## Assumptions

- CC 2.1.88 소스가 이미 `tui/src/` 아래 1:1 포팅돼 있다 (메모리 `TUI migration source`,
  Epic #287 완료 상태).
- 기본 개발 환경은 macOS (ARM64) + bun v1.2.x 이며 Node.js 는 요구하지 않는다
  (`docs/vision.md`, `AGENTS.md § Stack`).
- `tui/src/stubs/any-stub.ts` 와 유사한 타입 stub 인프라가 이미 존재해 재사용 가능
  (Epic #1632 본문 "existing any-stub.ts already covers lodash-es/*, @alcalzone/
  ansi-tokenize, semver, usehooks-ts, @anthropic-ai/sdk/* for type resolution").
- feature flag 17 종은 전부 `false` 고정으로 P0 단계의 사용자 가치 손실 없이 비활성
  가능하다. 각 flag 에 묶인 기능 (KAIROS, COORDINATOR, DIRECT_CONNECT 등) 은 P1+
  에서 삭제 또는 재도입 결정된다.
- 네트워크 연결이 제한된 환경에서도 스플래시 렌더까지는 성공해야 한다 (부트스트랩
  egress 0 원칙).

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Anthropic API 실제 호출 복구**: KOSMOS 미션상 Anthropic API 는 FriendliAI +
  K-EXAONE 으로 전면 교체됨 (`AGENTS.md § What KOSMOS is`). 이 Epic 은 Anthropic
  type import 만 해결하고, 실제 호출은 영구적으로 제거된다.
- **Developer-only Tools 복구**: `Read`, `Write`, `Edit`, `Bash`, `Glob`, `Grep`,
  `NotebookEdit` 는 KOSMOS 시민용 하네스 범위에서 영구 제외 (`CLAUDE.md §
  Architecture pillars` → C6).
- **Anthropic OAuth / MDM / keychain 실흐름**: KOSMOS 는 Anthropic 계정 시스템에
  의존하지 않음. Epic #287 문서에도 "services/api/만 stdio JSONL 로 교체" 라고
  명시되어 있고 OAuth 자체는 대체 대상.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Anthropic-only dead code 제거 (17 feature flag 경로, analytics, OAuth, GrowthBook, MCP claude.ai connector) | P0 는 "실행 가능"까지만, 정리는 stub 고정 이후 안전하게 P1 에서 수행 | Phase 1 · Dead code elimination | #1633 |
| FriendliAI 엔드포인트 연결 · K-EXAONE system prompt 적용 · 세션 JSONL 저장소 연결 | P0 에는 실제 LLM 호출 없이 스플래시만 목표 | Phase 2 · Anthropic → FriendliAI | #1633 |
| Tool system wiring · `Tool.ts` 인터페이스 재구현 · 4 primitive (`lookup`·`submit`·`verify`·`subscribe`) · Python stdio MCP | Tool 기반이 아직 없으므로 baseline 실행 보장 이후 진행 | Phase 3 · Tool system wiring | #1634 |
| UI L2 컴포넌트 구현 (B REPL · C Permission Gauntlet · D Ministry Agent · E 보조 surface · A Onboarding) | CC 베이스라인 렌더가 선행돼야 KOSMOS UI 변형을 얹을 수 있음 | Phase 4 · UI L2 Implementation | #1635 |
| Plugin DX Full 5-tier (Template · Guide · Examples · Submission · Registry) | 플러그인 ABI 는 tool system (P3) 이 선행 필요 | Phase 5 · Plugin DX | #1636 |
| Docs/API specs + `bun run tui` 종단간 스모크 | 기능 추가가 완료된 이후에만 문서·스모크가 의미 있음 | Phase 6 · Docs + Smoke | #1637 |
| Coordinator · KAIROS · SSH · BG sessions · bridge mode 기능 브랜치 | feature flag 모두 `false` 로 고정, 재도입·삭제 판정은 Epic #1633 에서 | Phase 1 dead code 결정 | #1633 |
| Telemetry sinks (Langfuse 외부 · Spec 028 컬렉터 재연결) | 부트스트랩 egress 0 원칙 준수 위해 P0 에서는 initialize 호출 자체를 제거 | Phase 2 재연결 / Spec 028 | #1633 |
| GrowthBook analytics · refreshGrowthBookAfterAuthChange · src/services/analytics/* | Anthropic-only 실험 플랫폼 · KOSMOS 에서 영구 삭제 또는 교체 결정은 P1 | Phase 1 · Dead code elimination | #1633 |
