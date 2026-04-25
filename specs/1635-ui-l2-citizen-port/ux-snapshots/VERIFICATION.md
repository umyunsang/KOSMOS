# UX Snapshot Verification — Epic #1635 P4 UI L2

**Generated**: 2026-04-25
**Tool**: `tui/scripts/dump-ui-l2-snapshots.tsx`
**Method**: Each UI L2 surface rendered through `ink-testing-library` and the last frame captured (ANSI-stripped) into a `.txt` file. Color tokens are not visible in plain-text capture, but glyph, layout, and text content are fully verifiable.

## Summary

**26 / 26 surfaces rendered successfully** — 0 fail. The Lead read every snapshot and confirms the items below.

## Per-surface verification

| # | Snapshot | FR | What the Lead verified |
|---|---|---|---|
| 01 | Permission modal Layer 1 | FR-015/016/017 | `⓵` glyph present, tool name + description rendered, `[Y/A/N]` 3-choice footer |
| 02 | Permission modal Layer 2 | FR-016 | `⓶` glyph differentiates from Layer 1; same modal frame |
| 03 | Permission modal Layer 3 | FR-016 | `⓷` glyph + extra `⚠️ 이 작업은 시민님 계정으로 외부 시스템에 영향을 줍니다` reinforcement line |
| 04 | Receipt toast — issued | FR-018 | `✻ 발급됨 rcpt-7d3a8f2e9c4b` surface format |
| 05 | Receipt toast — revoked | FR-020 | `✻ 철회 완료 rcpt-...` surface format |
| 06 | Receipt toast — already revoked | FR-021 | `✻ 이미 철회됨` (idempotent) — no new ledger entry |
| 07 | Bypass reinforcement modal | FR-022 | `⚠ bypassPermissions 전환 확인` + `이 모드는 모든 권한 모달을 우회합니다…` + `Y 확정 / N 취소` |
| 08-10 | Layer header standalone | FR-016 | `⓵/⓶/⓷ Layer N` glyphs differentiate per layer |
| 11 | Error envelope LLM | FR-012 | `🧠 LLM 응답 오류` + detail + retry hint + timestamp |
| 12 | Error envelope Tool | FR-012 | `🔧 도구 호출 오류` differentiated from LLM |
| 13 | Error envelope Network | FR-012 | `📡 네트워크 오류` + 5초 무응답 detail |
| 14 | Context quote block | FR-013 | `⎿` prefix glyph + label + single-border |
| 15 | Streaming chunk | FR-008 | Mid-stream Korean text rendered (chunk batching is logic, not visible at single frame) |
| 16 | Slash autocomplete | FR-014 | `/c` prefix → `/consent list`, `/consent revoke`, `/config` matched with descriptions |
| 17 | Agent panel (swarm) | FR-025 | `◆ 활성 부처 에이전트 · 3 agents` + 5-state per ministry (`실행 중`, `권한 대기`, `완료`) + primitive dot `⏺` per row + `/agents --detail` hint |
| 18 | Agent panel (--detail) | FR-026 | Columns `부처 / 상태 / SLA / 건강 / 평균응답` populated (`8s`, `12s`, `green`/`amber`, `320ms`/`580ms`) |
| 19 | HelpV2 4-group | FR-029 | Four sections rendered exactly: `─── 세션 ───`, `─── 권한 ───`, `─── 도구 ───`, `─── 저장 ───` with all 10 commands placed correctly |
| 20 | Plugin browser | FR-031 | `⏺/○` toggles + `Space 활성 토글 · i 상세 · r 제거 · a 스토어` keybinding hint |
| 21 | History search | FR-033 | `--date YYYY-MM-DD..YYYY-MM-DD  --session <id>  --layer <1|2|3>` 3-filter hint + session rows |
| 22 | Onboarding step 1 (preflight) | FR-001 step 1 | `◉ ○ ○ ○ ○  1/5` progress + 4 environment checks (Bun 1.3.12 ✓ / graphics protocol ✗ / FRIENDLI_API_KEY ✗ / KOSMOS_DATA_GO_KR_KEY ✓) |
| 23 | Onboarding step 2 (theme) | FR-001/035 | UFO mascot rendered with purple palette (note: hex `#a78bfa` / `#4c1d95` color cannot be confirmed in ANSI-strip capture; structural rendering OK) |
| 24 | Onboarding step 3 (PIPA) | FR-001/006 | `⚠ 수탁자 책임 안내 · 개인정보 보호법 §26` heading + 처리 정보 list + 수신 부처 list + audit-preservation notice (`동의 철회 후에도 audit ledger와 OTEL span은 삭제되지 않습니다 (FR-007)`) |
| 25 | Onboarding step 5 (terminal-setup) | FR-001/005 | 4 a11y toggles (스크린리더 / 큰 글씨 / 고대비 / 애니메이션 줄이기) + `Shift+Tab / Ctrl+C / Ctrl-O` keybinding hint |
| 26 | Agent detail row | FR-026 | Single ministry row matches the panel's column layout |

## What this verification does and does not cover

**Covered**:
- Component-level structural rendering (frame, borders, glyphs, layout)
- Text content (Korean primary copy + receipt-id format + state labels)
- Glyph differentiation (`⓵/⓶/⓷`, `🧠/🔧/📡`, `⏺/○`, `✓/✗`, `⎿`)
- Slash command catalog SSOT consumed correctly by `/help` and autocomplete

**Not covered (still requires operator verification with `bun run tui`)**:
- Color tokens (green/orange/red Layer headers, purple UFO palette) — ANSI strip removed
- Streaming animation cadence (~20-token batching, FR-008)
- Live agent state transitions (push from Spec 027 mailbox)
- Keystroke handling (`Y/A/N`, `Space/i/r/a`, `Ctrl-O`, `Shift+Tab`)
- 5-second no-chunk → network ErrorEnvelope transition
- `/export` writing actual PDF to `~/Downloads/`
- `/lang ko|en` hot-swap on next render
- PIPA consent record write-through + ministry-scope memdir write

The operator-driven `bun run tui` walk-through of `quickstart.md` 13 steps remains the final acceptance gate before declaring full surface parity.

## Bug found and fixed during this verification

The dump script initially passed `HistorySearchDialog` props in camelCase (`sessionId`, `startedAt`, …), which crashed because the component's `SessionHistoryEntry` type uses snake_case (`session_id`, `started_at`, `last_active_at`, `preview`, `layers_touched`). The script was corrected. **The component itself and `commands/history.ts` are consistent** — both use snake_case end-to-end, so the runtime path is correct. This was a verification-tooling bug, not a production bug.

## Reproduce

```bash
cd tui
bun run scripts/dump-ui-l2-snapshots.tsx
```

Outputs land in `specs/1635-ui-l2-citizen-port/ux-snapshots/*.txt` plus an `INDEX.txt` manifest.
