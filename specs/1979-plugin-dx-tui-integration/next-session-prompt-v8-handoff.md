# 다음 세션 시작 프롬프트 — Initiative #2290 핸드오프 v8 (vhs Layer 4 mandatory 룰 추가)

**작성일**: 2026-04-29 (Epic γ 머지 + AGENTS.md vhs rule 정착 직후)
**상태**: Epic α + β + γ + δ 머지 완료. Epic ε / ζ / η 모두 OPEN.

---

## 머지 결과 + 룰 변경

| 항목 | commit |
|---|---|
| Epic γ #2294 5-primitive align | `b47db4c` (PR #2394) |
| handoff v7 + Epic ε/ζ/η OPEN 안내 | `7258526` |
| Epic γ vhs companion gif | `ce4dbc8` |
| **AGENTS.md vhs Layer 4 mandatory + LLM PNG keyframes** | **`dbf066a`** |

### 새 mandatory rule (다음 Epic 부터 즉시 적용)

`tui/src/**` 변경 PR 은 머지 전에 **두 종류 모두** 박제 필수:

1. **Layer 2 expect 텍스트 로그** — `specs/<feature>/smoke-<scenario>-pty.txt` (기존 룰)
2. **Layer 4 vhs `.tape` + 3+ Screenshot PNG 키프레임** — `specs/<feature>/scripts/smoke-<scenario>.tape` 가 다음을 모두 emit:
   - `Output specs/<feature>/smoke-<scenario>.gif` (사람 시각 + 애니메이션)
   - `Screenshot specs/<feature>/smoke-keyframe-1-boot.png`
   - `Screenshot specs/<feature>/smoke-keyframe-2-input.png`
   - `Screenshot specs/<feature>/smoke-keyframe-3-action.png`
   - Lead Opus 가 각 PNG 에 Read tool 호출해 시각 검증 후 push.

`Output ...gif` 만 emit 하면 룰 위반 — agent Read 가 첫 frame (보통 빈 prompt) 만 봄. ffmpeg 후처리 금지 (vhs `Screenshot` 가 native).

**Reference impl**: `specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.tape` + 3 keyframe PNG.
**Canonical docs**: `AGENTS.md § TUI verification` + `docs/testing.md § Layer 4 — vhs visual + PNG keyframes` + memory `feedback_vhs_tui_smoke`.

---

## 다음 세션 진입 (1 Lead Opus = 1 Epic)

### Epic ε #2296 — AX-mock-adapters (Codex P1 #2395 piggyback 권장)

```bash
cd /Users/um-yunsang/KOSMOS && git pull --ff-only
git worktree add ../KOSMOS-w-2296 -b 2296-ax-mock-adapters
cd ../KOSMOS-w-2296
# /speckit-specify Epic ε — 9 mock adapter (5 verify + 3 submit + 1 subscribe)
# + DelegationToken/Context 스키마 + Codex P1 #2395 (adapter manifest IPC sync)
```

**spec scope 권장**: 9 mock adapter 신설 + #2395 (TS-side adapter manifest IPC sync) 같이. 새 adapter 등록 흐름이 manifest sync 흐름과 같은 IPC frame 가족 → cohesive.

### Epic ζ #2297 — E2E smoke + 정책 매핑 doc

```bash
cd /Users/um-yunsang/KOSMOS && git pull --ff-only
git worktree add ../KOSMOS-w-2297 -b 2297-e2e-smoke
cd ../KOSMOS-w-2297
# /speckit-specify Epic ζ — End-to-end 시나리오 + docs/scenarios OPAQUE + KOSMOS v0.1-beta tag
```

### Epic η #2298 — 본문 미정

이슈 본문 채우기 + speckit cycle.

---

## 불변 규칙 (이번 세션 박제 + 강화)

1. **1 Lead Opus = 1 Epic** (Layer 1 parallelism). 의존성 없는 Epic 들은 별도 session/worktree 동시 진행.
2. **Sonnet teammate 단위 = task/task-group** (≤ 5 task / ≤ 10 file).
3. **push/PR/CI/Codex = Lead** (sequential).
4. **Codex P1/P2 처리**: P2 = 즉시 fix + reply. P1 (architecture mismatch) = deferred sub-issue + spec.md 백필 + reply.
5. **PR title subject 첫 글자 lowercase** (Conventional Commits action).
6. **`gh issue close --quiet` 금지** — silent fail. flag 빼고 close.
7. **🆕 vhs Layer 4 mandatory** — `.tape` + 3+ Screenshot PNG + Lead 시각 Read 검증.
8. **이슈 추적 = GraphQL Sub-Issues API only** (closure verify 는 REST per-issue — eventual consistency 우회).
9. **신규 dep 0** (AGENTS.md hard rule).

---

## 다음 세션 첫 명령

```
/clear → 새 conversation
이 파일 (specs/1979-plugin-dx-tui-integration/next-session-prompt-v8-handoff.md) 읽고 Epic <ε/ζ/η> #<번호> resume.
```
