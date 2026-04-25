# Visual Evidence — KOSMOS Plugin Surfaces

> 측정일: 2026-04-26
> 측정자: Lead 자동화 (umyunsang)
>
> ink-testing-library 로 KOSMOS plugin 관련 인터랙티브 UI surface 의 lastFrame() 을 dump 한 시각 검증 산출물. PTY 인 실제 TUI 호스트 없이도 frame 의 정확성을 review 할 수 있도록 plain text + ANSI 양 형식으로 보존.

## 재현 절차

```sh
cd tui
bun scripts/dump-plugin-frames.tsx
# 결과: tui/test-output/plugin-frames/<surface>.{txt,ansi.txt}
```

`*.txt` 는 ANSI 제거된 plain text — diff / review 용.
`*.ansi.txt` 는 색상 / 굵기 등 이스케이프 코드 포함 — 터미널에서 `cat` 으로 색상 확인.

## 산출 surface 목록

### 1. 플러그인 브라우저 (PluginBrowser)

| 파일 | 상황 |
|---|---|
| `plugin-browser-4-entries.txt` | 4개 플러그인 등록 (3 active ⏺ + 1 inactive ○) |
| `plugin-browser-empty.txt` | 플러그인 0개 — empty state |

키바인드: `Space` 활성 토글 · `i` 상세 · `r` 제거 · `a` 스토어 · `Esc` 닫기.

### 2. PIPA Consent Step (Onboarding step 3)

| 파일 | 로케일 |
|---|---|
| `pipa-consent-step-ko.txt` | 한국어 (default) |
| `pipa-consent-step-en.txt` | English (KOSMOS_TUI_LOCALE=en) |

5-step onboarding 의 step 3 — 한국어가 primary, 동의 모달의 dot-progress + warning border + `[Y/Enter]` `[N/Esc]` 프롬프트.

### 3. /plugin slash command acknowledgements

7개 case (모두 `slash-*.txt`):

| 입력 | 결과 |
|---|---|
| `/plugin` | 사용법 텍스트 |
| `/plugin install seoul-subway` | 🔄 시작 acknowledgement + plugin_op_request 1건 emit |
| `/plugin install seoul-subway --version 1.2.0 --dry-run` | dry-run 표시 + frame 의 requested_version=1.2.0 / dry_run=true |
| `/plugin list` | 📋 조회 시작 + plugin_op_request{request_op="list"} |
| `/plugin uninstall seoul-subway` | 🗑️ 제거 시작 + plugin_op_request{request_op="uninstall"} |
| `/plugin pipa-text` | canonical SHA-256 + docs/plugins/security-review.md 안내 (IPC 미발산) |
| `/plugin reinstall foo` | 알 수 없는 subcommand + 사용법 |

전체 emit 된 plugin_op frame 의 JSON 페이로드는 [`00-slash-summary.md`](00-slash-summary.md) 참조.

## 시각 검증 포인트 (요약)

- ✅ 한국어 텍스트 (조사 / 종결어미 / 외래어) 모두 정상 렌더 — CJK width 처리.
- ✅ `⏺` (active) / `○` (inactive) glyph 분리 표시.
- ✅ 동의 dot-progress (●●◉○○) + 박스 border 정상.
- ✅ 슬래시 명령 acknowledgement 의 emoji (🔄 📋 🗑️) 인라인 표시.
- ✅ `--dry-run` 플래그가 acknowledgement 에 `(dry-run)` 으로 분기 표시.
- ✅ `/plugin pipa-text` 가 IPC 미발산 + canonical hash 평문 출력.
- ✅ unknown subcommand 가 명령 echo + 사용법 표시.

## 보완 검증

- backend 통합 테스트: `src/kosmos/plugins/tests/test_install_e2e.py` — SC-004 / SC-005 / SC-007 / SC-010 모두 PASS.
- TUI 단위 테스트: `tui/tests/commands/plugin.test.ts` — 13 tests (frame envelope shape + 7 contract negative cases + IPC 분리).
- 외부 repo pytest: SC-006 evidence (`sc006-evidence.md`) — 4 example repos × 4 tests = 16/16 pass.

## 한계

- 실제 TUI binary (`bun run tui`) 의 PTY 환경 boot 검증은 제외 — `tui/scripts/tui-smoke.ts` 가 cover 하지만 본 epic 시점에 pre-existing 문제로 별도 추적.
- `useInput` 키바인드 (Space / Esc / Y / N 등) 동작 검증은 ink-testing-library 의 stdin mock 으로 가능하나 본 dump 는 *initial frame* 만 캡처. 키 동작은 unit test (`PermissionGauntletModal.test.tsx` 등 기존 패턴) 가 cover.
