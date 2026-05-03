# Analyze 2641 · Constitution Compliance

## Constitution check (.specify/memory/constitution.md + AGENTS.md hard rules)

| Constitution principle | Spec 2641 status | 증거 |
|---|---|---|
| **CORE THESIS — CC + 2 swaps** | PASS | 본 작업은 swap-1 (LLM provider) 의 마무리 정리. CC byte-identical default 보존 (axios import, SyncState 구조, 함수 시그니처 모두 동일). 박제 헤더 + dead-call gate 만 layer. |
| **AGENTS.md hard rule: zero new runtime deps** | PASS | spec.md SC-008 + plan.md Phase 4. tui/package.json + pyproject.toml diff = empty. |
| **AGENTS.md hard rule: byte-identical CC default** | PASS | 헤더 + gate insertion 외에 CC 원본 텍스트 0 변경. axios import, getOauthConfig stub, classifyAxiosError 등 그대로. |
| **AGENTS.md hard rule: never `--force`, `--no-verify`** | PASS | 본 spec 은 destructive op 0. |
| **AGENTS.md hard rule: 영문 source** | PASS | 헤더 + gate 메시지 모두 영문. (한국어 spec 본문은 spec/plan/tasks.md 만 — source 코드는 영문.) |
| **AGENTS.md spec-driven workflow** | PASS | spec → plan → tasks → analyze → taskstoissues → implement → PR `Closes #2641` only. |
| **AGENTS.md TUI verification (services 변경)** | PASS | Layer 5 tmux boot smoke 단계 (T009) 명시. interactive scenario 변경 0 이라 Layer 1-4 는 services 단위 테스트로 충족. |
| **AGENTS.md issue hierarchy: GraphQL only** | PASS | speckit-taskstoissues 가 GraphQL Sub-Issues API v2 사용. |
| **AGENTS.md PR closing rule: Closes #EPIC only** | PASS | tasks.md T012 명시. |
| **AGENTS.md L1-A canonical: A1 single provider, A7 zero egress** | PASS | dead-call gate 가 axios → claude.ai 발신을 코드 enforcement. plan.md Phase 0 § kosmos-migration-tree 인용. |
| **CC sourcemap byte-copy default** | PASS | restored-src 비교 baseline 명시. 박제 헤더가 SHA-256 path 인용. |
| **Spec 2521 박제 패턴 일관성** | PASS | claude.ts:1-23 4-항 헤더 구조 그대로 답습. |
| **Initiative #1633 P2 stub 전례 vs 박제** | RESOLVED | decisions.md § S6 Services 가 "claude.ts 패턴 일관성" 으로 박제 (방안 B) 명시. |
| **Constitution §VI deferred sub-issue tracking** | N/A | 본 spec 은 deferred 항목 0. |

## Risk audit
- **Risk #1: claude.ts 가 line 22 (async) 시그니처 expect** — spec.md FR-001
  + plan.md Phase 4 에서 검증: zero-callers 박제이므로 sync vs async 무의미
  + typecheck 가 1차 gate. 위험 등급 LOW.
- **Risk #2: settingsSync silent-skip 이 boot 회귀** — settingsSync 가 이미
  `feature() === false` 로 silent-skip 중. dead-call gate 는 동일 행동 유지
  → 회귀 0 보장. 위험 등급 ZERO.
- **Risk #3: teamMemorySync throw 가 production 에 도달** — `setup.ts:358`
  의 `feature('TEAMMEM') === false` 1차 gate 가 startTeamMemoryWatcher
  자체를 skip → 4 entry-point 도달 불가. 위험 등급 ZERO.
- **Risk #4: bun:test fixtures 가 다른 KOSMOS env 변수 의존** — 신규 테스트
  는 `process.env.KOSMOS_ENABLE_DEAD_*` 만 명시 unset → 격리. 위험 등급
  LOW.

## Cross-artifact 일관성 check
- spec.md FR-001..006 ↔ tasks.md T002..T006 1:1 매핑 ✓
- spec.md SC-001..009 ↔ tasks.md T007..T011 1:1 매핑 ✓
- plan.md Phase 1 task group T1/T2/T3 ↔ tasks.md Phase 3/4/5 매핑 ✓
- plan.md Phase 2 통합 검증 ↔ tasks.md Phase 6 매핑 ✓
- 박제 헤더 형식 (4-항) — spec FR-002/004 + plan Phase 0 + tasks T003/T005
  모두 동일 명시 ✓

## 결론
모든 constitution check PASS. spec-driven 사이클 다음 단계 (taskstoissues +
implement) 진행 가능.
