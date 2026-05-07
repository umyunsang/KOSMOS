# CC → UMMAYA Migration Audit (2026-05-03)

## 목적

CC 원본 (`.references/claude-code-sourcemap/restored-src/src/`) 을 UMMAYA 의 source of truth 로 삼아, 현재 UMMAYA 코드(tui/src/, src/ummaya/) 와 CC 사이의 모든 발산을 4-bucket 으로 분류하여 마이그레이션 누락 및 정당성 없는 발산을 식별한다.

## CORE THESIS

**UMMAYA = CC-original harness + 2 swaps만**
- swap 1: LLM = K-EXAONE on FriendliAI
- swap 2: Tool 시스템 = 한국 부처 GovAPITool / ToolRegistry / 4 primitive (lookup·submit·verify·subscribe)
- 그 외 모든 것은 CC 와 byte-identical 유지. 발산은 회귀 대상.

**swap 종속 표면** (제거 정당) — Anthropic OAuth · claude.ai 결제/sync/1P 텔레메트리 · Anthropic 모델 ID · 개발자 전용 도구(Bash/FileEdit/FileWrite/Glob/Grep/NotebookEdit) 등.

## 4-bucket 분류

| 분류 | CC | UMMAYA | 액션 |
|---|---|---|---|
| **PORT** | ✓ | ✗ | 카피 + 마이그레이션해서 UMMAYA 에 추가 [최우선] |
| **PRESERVE-IDENTICAL** | ✓ | ✓ (동등) | byte-identical 유지 |
| **MIGRATE-FOR-SWAP** | ✓ | ✓ (다름) | 2-swap 종속 입증, 못 하면 CC 로 회귀 |
| **DROP-CANDIDATE** | ✗ | ✓ | swap 종속 입증, 못 하면 제거 |

## 9 스트림 분할

| 스트림 | 영역 | 산출물 |
|---|---|---|
| S1 | Engine Core (query, QueryEngine, Task, tasks, assistant, coordinator, cost) | `scope-S1-engine-core.md` |
| S2 | Tool System (Tool.ts, tools.ts, tools/, services/tools/) | `scope-S2-tool-system.md` |
| S3 | Components + Screens + UI Helpers | `scope-S3-components-screens.md` |
| S4 | Ink (ink/, ink.ts) | `scope-S4-ink.md` |
| S5 | Commands + Hooks + Keybindings + Skills + Vim | `scope-S5-commands-input.md` |
| S6 | Services (services/ minus tools) | `scope-S6-services.md` |
| S7 | IPC + Bridge + Server + Remote + Native | `scope-S7-ipc-bridge.md` |
| S8 | State + Boot + Misc (bootstrap, cli, entrypoints, main, memdir, state, context, history, migrations, voice, buddy, plugins, observability, constants, schemas, types) | `scope-S8-state-boot-misc.md` |
| S9 | Utils (utils/) | `scope-S9-utils.md` |
