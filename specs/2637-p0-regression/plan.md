# Implementation Plan: Epic A — P0 회귀 즉시 복구

**Branch**: `feat/2637-p0-regression` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2637-p0-regression/spec.md`

## Summary

audit Initiative #2636 의 9-stream 결과에서 발견된 9건 회귀 (6 P0 + 3 부수) 를 byte-copy 복원 + Spec 021 OTEL telemetry wire 로 해결한다. CORE THESIS ("KOSMOS = CC + 2 swap만, byte-identical default") 의 직접 위반 영역을 복구하는 P0 작업.

**기술적 접근**: CC source-of-truth (`.references/claude-code-sourcemap/restored-src/src/`) 에서 7개 파일 byte-copy + 1개 wire (toolExecution.ts) + 3개 stub 헤더 박제 + 1개 누락 cascade module 신설. swap-1 종속 식별자 화이트리스트 외 diff 라인 0 보장.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x runtime (TUI 측, 본 Epic 의 100% 변경 범위) · Python 3.12+ (백엔드, 본 Epic 변경 없음).
**Primary Dependencies**:
- 기존: `@opentelemetry/api ^1.9.1`, `@opentelemetry/api-logs ^0.215.0`, `@opentelemetry/core ^2.7.0`, `@opentelemetry/resources ^2.7.0`, `@opentelemetry/sdk-logs ^0.215.0`, `@opentelemetry/sdk-metrics ^2.7.0`, `@opentelemetry/sdk-trace-base ^2.7.0`, `https-proxy-agent ^9.0.0`
- **신규** (본 spec-driven PR 에서 추가, AGENTS.md 하드 룰 준수): `@opentelemetry/semantic-conventions`, `@opentelemetry/exporter-trace-otlp-http`, `@opentelemetry/exporter-trace-otlp-grpc`, `@opentelemetry/exporter-logs-otlp-http`, `@opentelemetry/exporter-logs-otlp-grpc`, `@opentelemetry/exporter-metrics-otlp-http`, `@opentelemetry/exporter-metrics-otlp-grpc`, `@grpc/grpc-js` (총 8개) — `instrumentation.ts` PORT 가 dynamic import 하는 OTLP/gRPC exporter 패키지들. 모두 Apache-2.0.
**Storage**: N/A — 본 Epic 은 in-memory + filesystem-only. `~/.kosmos/memdir/user/sessions/` JSONL (Spec 027) 와 OTLP collector → Langfuse (Spec 028) 기존 경로 변경 없음.
**Testing**: `bun test` (Ink snapshot + ts-bun unit) · `uv run pytest` (백엔드 parity 유지) · `bun typecheck` · TUI 5-layer smoke (Layer 1a/1b/2/3/4/5).
**Target Platform**: macOS / Linux 터미널 (Bun runtime + ink).
**Project Type**: TypeScript TUI client (Ink + React) over IPC stdio bridge to Python backend. 본 Epic 은 TUI 측만 건드림.
**Performance Goals**: instrumentation.ts dynamic import latency ≤ 500ms (현재 lazy load `~400KB`). toolExecution.ts wire 후 tool span emission overhead ≤ 5ms p99. headless `--print` mode 응답 시간 동등성 (interactive REPL 과 비교 deviation ≤ 100ms).
**Constraints**:
- AGENTS.md 하드 룰 "Never add a dependency outside a spec-driven PR" — 본 PR 이 spec-driven 이므로 OTel 8개 추가 정당, 단 plan 단계 명시 필수 (✅ 위 Primary Dependencies).
- AGENTS.md 하드 룰 "TypeScript is allowed only for the TUI layer (Ink + Bun)" — 본 Epic TS 측만 변경, 준수.
- AGENTS.md 하드 룰 "All source text in English" — PORTed 파일은 CC byte-identical, KOSMOS 헤더 주석은 영어, ko 도메인 데이터 변경 없음.
- byte-identical 검증: PORTed 파일 7개 모두 swap-1 식별자 화이트리스트 외 diff 라인 0.
**Scale/Scope**: 7 PORT (총 ~7900 LOC, byte-copy) + 1 wire (~50 LOC) + 3 박제 (~30 LOC 주석) + 1 신설 stub (`remoteManagedSettings/index.ts` ~30 LOC) + 8 dependency 추가. 단일 PR. ~7 task.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Reference-Driven Development ✅ PASS

본 Epic 은 100% reference-driven. 모든 PORT 가 `.references/claude-code-sourcemap/restored-src/src/` (Claude Code 2.1.88) 에서 byte-copy.

**docs/vision.md § Reference materials 매핑**:

| 변경 영역 | Primary Reference | Secondary Reference |
|---|---|---|
| `instrumentation.ts` PORT | Claude Code reconstructed (TUI components — `restored-src/src/utils/telemetry/instrumentation.ts` 825 LOC) | Spec 021 OTEL GenAI v1.40 + Spec 028 OTLP collector |
| `toolExecution.ts` wire | Claude Code reconstructed (Tool System — `restored-src/src/services/tools/toolExecution.ts` 1745 LOC byte-identical 본체) | Spec 021 4-tier OTEL Tool layer (KOSMOS-side helper, swap-5 spillover) |
| `events_mono/*.ts` PORT | Claude Code reconstructed (`restored-src/src/types/generated/events_mono/`) | type-only, dependency 없음 |
| `constants/{messages,xml,figures,oauth}.ts` PORT | Claude Code reconstructed (`restored-src/src/constants/`) | swap-1 종속 식별자 (Anthropic OAuth) 만 KOSMOS-side null |
| `types/logs.ts` PORT | Claude Code reconstructed (`restored-src/src/types/logs.ts`) | type-only |
| `cli/print.ts` PORT | Claude Code reconstructed (`restored-src/src/cli/print.ts` 5594 LOC) | swap-1 종속 cascade (`remoteManagedSettings/`) KOSMOS-side stub 신설 |
| Stage-1 NO-OP 3 박제 | KOSMOS-original (CC source 부재 — find 결과 0) | decisions.md S9 § Stage-1 cite |
| 누락 cascade `remoteManagedSettings/index.ts` 신설 | KOSMOS-original stub (Spec 1633 P1 dead-surface) | KOSMOS analytics/index.ts 패턴 (Spec 1633 stub-noop replacement) |

### Principle II — Fail-Closed Security ✅ PASS

본 Epic 은 권한 정책 변경 없음. KOSMOS-invented permission classifications 도입 0. byte-copy 한 `oauth.ts` 의 `USER_TYPE === 'ant'` 가드는 CC 그대로 — KOSMOS 환경에서는 자동 prod fallback. OAuth flow 자체는 swap-1 종속이라 영구 비활성 (out of scope).

### Principle III — Pydantic v2 Strict Typing ✅ N/A

본 Epic 은 TS 측만 변경. Python Pydantic 모델 변경 0.

### Principle IV — Government API Compliance ✅ N/A

본 Epic 은 어댑터 변경 0. data.go.kr API 호출 없음.

### Principle V — Policy Alignment ✅ N/A

본 Epic 은 정책 표면 변경 0.

### Principle VI — Deferred Work Accountability ⚠ PASS WITH FOLLOW-UP

spec.md § Scope Boundaries 의 6개 deferred 항목 모두 NEEDS TRACKING (`/speckit-taskstoissues` 가 Task issue 발행 시 GitHub issue 번호로 back-fill 예정). 본 Epic 외부 deferral 검증:

- "TUI Fidelity Meta-Epic" — `protectedNamespace.ts` 정식 구현 (NEEDS TRACKING)
- "UI L2 Theme Polish Epic" — `systemThemeWatcher.ts` 정식 구현 (NEEDS TRACKING)
- "Epic D (Commands/Skills 정리)" — `ultraplan/prompt.txt` 결정 + main.tsx PROACTIVE/BRIEF 검증 (NEEDS TRACKING)
- "Epic E (Services swap-1 마무리)" — entrypoints/sdk/ 6 파일 audit (NEEDS TRACKING)
- 별도 future Epic — migration version 12 시작 (NEEDS TRACKING)

추가 발견 (research.md 에서 detail): cli/print.ts cascade 의 일환으로 발견된 누락 `remoteManagedSettings/` 디렉토리는 본 Epic A scope 내 stub 신설로 처리 (FR-016 추가 — spec 업데이트 필요).

**Constitution Check verdict**: PASS. 위반 0. 모든 deferred 항목 표 entry 존재.

## Project Structure

### Documentation (this feature)

```text
specs/2637-p0-regression/
├── spec.md              # 9건 회귀 + acceptance scenarios + FR + SC + scope
├── plan.md              # This file
├── research.md          # Phase 0 — 4개 핵심 결정
├── data-model.md        # Phase 1 — 9 entity + swap-1 식별자 화이트리스트
├── quickstart.md        # Phase 1 — Sonnet teammate PORT 명령 시퀀스
├── contracts/
│   ├── dispatch-tree.md  # 단일 Sonnet sequential dispatch tree
│   └── byte-identical-verification.md  # diff -q 검증 + swap-1 식별자 화이트리스트
├── checklists/
│   └── requirements.md  # spec quality checklist (PASS)
└── tasks.md             # Phase 2 — /speckit-tasks 산출
```

### Source Code (worktree root: `/Users/um-yunsang/KOSMOS-w-2637/`)

```text
tui/src/
├── types/generated/events_mono/       # FR-001 PORT
│   ├── claude_code/v1/
│   │   └── claude_code_internal_event.ts  # 21 → 865 LOC
│   ├── growthbook/v1/
│   │   └── growthbook_experiment_event.ts # 15 → 223 LOC
│   └── common/v1/                      # 디렉토리 신설
│       └── auth.ts                     # CC 에서 byte-copy
├── constants/
│   ├── messages.ts                     # FR-002a 32 → 1 LOC byte-copy
│   ├── xml.ts                          # FR-002b 37 → 86 LOC byte-copy
│   ├── figures.ts                      # FR-002c 검증 (이미 plain string 일치)
│   └── oauth.ts                        # FR-004 신설 234 LOC, swap-1 식별자만 교체
├── types/
│   └── logs.ts                         # FR-002d 55 → 330 LOC byte-copy
├── cli/
│   └── print.ts                        # FR-003 신설 5594 LOC byte-copy
├── utils/
│   ├── telemetry/
│   │   └── instrumentation.ts          # FR-005 신설 825 LOC, swap-1 import 만 KOSMOS-side
│   ├── protectedNamespace.ts           # FR-007a 헤더 박제 only
│   ├── systemThemeWatcher.ts           # FR-007b 헤더 박제 only
│   └── ultraplan/prompt.txt            # FR-007c 헤더 박제 only
├── services/
│   ├── tools/
│   │   └── toolExecution.ts            # FR-006 9 stub wire (line 91-100)
│   └── remoteManagedSettings/
│       └── index.ts                    # FR-016 신설 KOSMOS stub (cascade)
└── main.tsx                            # FR-003 L1960 차단 메시지 제거 (PORT 후)

tui/package.json                        # 8개 OTel 의존성 추가 (FR-005 prerequisite)
specs/cc-migration-audit/decisions.md   # FR-015 Stage-1 row 업데이트
```

**Structure Decision**: 본 Epic 은 단일 spec, 단일 PR, 단일 Sonnet teammate sequential. TUI side 만 건드리며 Python 백엔드 + spec docs + 기타 영역 변경 0. 디렉토리 신설 2건 (`tui/src/types/generated/events_mono/common/v1/`, `tui/src/services/remoteManagedSettings/`), 파일 신설 5건 (`oauth.ts`, `print.ts`, `instrumentation.ts`, `auth.ts`, cascade `remoteManagedSettings/index.ts`), 파일 PORT/대체 4건 (events_mono 2 + constants 2 + types/logs 1, 단 figures.ts 는 이미 plain string 이라 검증만), 헤더 박제 3건, wire 1건 (toolExecution.ts).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 8개 OTel dependency 신규 추가 | `instrumentation.ts` byte-copy PORT 의 dynamic import targets (semantic-conventions 1 + OTLP exporters 6 + grpc-js 1). audit S9 § P0-1 + spec FR-005 직접 종속. AGENTS.md 하드 룰 "spec-driven PR" 조건 충족. | "instrumentation.ts 본체 stub 유지" 거부 이유: Spec 021 4-tier OTEL TS-측 telemetry surface 가 silent. Spec 028 OTLP collector 가 Python-측 spans 만 받아 GenAI/Tool layer 의 client-side trace 누락. CC byte-identical 원칙 위반. |
| `toolExecution.ts` 9 stub wire 가 KOSMOS-side OTEL helper 직접 사용 (CC `events.ts` + `sessionTracing.ts` cascade PORT 회피) | CC `sessionTracing.ts` 927 LOC + `betaSessionTracing.ts` 491 LOC + `events.ts` 75 LOC + `perfettoTracing.ts` + `bigqueryExporter.ts` + `logger.ts` 모두 swap-1 (Anthropic 1P GrowthBook + BigQuery + Perfetto) 종속. Cascade PORT 폭발 (~2000+ LOC). swap-5 (Observability) 정당성으로 KOSMOS Spec 021 helper 직접 wire 가 정답. | "CC 7-file telemetry cascade PORT" 거부 이유: swap-1 종속 dependency 7 file PORT 후 다시 stubbing 필요 → 의미 0 + Spec 021 attribute 정합 깨짐. |
| `cli/print.ts` PORT 시 누락 cascade `remoteManagedSettings/index.ts` KOSMOS-side stub 신설 (CC source 의 swap-1 종속 surface) | CC `print.ts:9` 가 `services/remoteManagedSettings/index.js` import. KOSMOS 누락 → import 실패. Spec 1633 P1 dead-surface 패턴 (analytics/index.ts 와 동일 stub-noop replacement). | "CC remoteManagedSettings/ 본체 PORT" 거부 이유: Anthropic enterprise managed settings (claude.ai 1P 종속) → swap-1 종속이라 본체 무의미. KOSMOS analytics/index.ts 패턴으로 stub 정당. |
| Stage-1 NO-OP 3건 박제 (byte-copy 불가, CC source 부재) | `find .references/.../src -name "protectedNamespace*" -o -name "systemThemeWatcher*" -o -name "prompt.txt"` 결과 0건. audit 권고 "byte-copy" 가 CC source 가 정의되지 않은 영역에서는 사실상 KOSMOS-only stub 정당화 + decisions.md cite 박제로만 처리 가능. | "CC source-of-truth 에 정식 구현 추가" 거부 이유: research-only mirror (`restored-src/`) 는 modify 금지 (AGENTS.md hard rule). KOSMOS 정식 구현은 spec 외부 (Out of Scope). |
