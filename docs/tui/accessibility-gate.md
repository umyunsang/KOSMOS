# TUI Accessibility Gate

**Epic**: M #1310
**WCAG baseline**: 2.1 AA (subset — see §2)
**KWCAG baseline**: 한국 접근성 지침 2.2 (citizen-facing surfaces only)
**Palette-selection constraint for Epic H #1302**: body text ≥ 4.5:1 contrast, large text / non-text ≥ 3:1 (FR-022)
**IME composition rule**: every component that accepts text input MUST honor `useKoreanIME().isComposing`; see Epic E #1300 contract.

## §1 · Why this gate exists

FR-018 mandates that `docs/tui/accessibility-gate.md` exist and enumerate per-verdict accessibility requirements for every PORT and REWRITE row in the component catalog. FR-019 requires each row to be annotated with applicable WCAG 2.1 AA success criteria drawn from a closed set of five criteria. FR-020 extends the annotation requirement to Korean Accessibility Guidelines (한국 접근성 지침 2.2) for citizen-facing component families. FR-021 flags every text-input surface for IME composition-gate compliance under the Epic E #1300 contract. FR-022 documents color-contrast constraints (≥ 4.5:1 body text, ≥ 3:1 large text/non-text) as a palette-selection constraint passed to Epic H #1302. SC-009 (zero orphan verdicts) enforces that every PORT/REWRITE catalog row has exactly one matching gate row — no row may be omitted or duplicated. This gate document is the single source of truth for downstream Epics (B, C, D, E, H, I, J, K, L) to inherit WCAG/KWCAG constraints when authoring Task sub-issues.

### §1.1 · Terminal screen-reader pathway

KOSMOS TUI renders through Ink (React for CLIs) in a terminal emulator. Unlike the browser DOM, a terminal has **no native accessibility tree**: VoiceOver, NVDA, and JAWS cannot introspect Ink's virtual DOM directly. Per-row mentions of "스크린 리더 접근 가능" in §3 KWCAG notes therefore rely on the following concrete pathways, not on a DOM accessibility API:

1. **Text stream accessibility** — all visible content MUST render as plain UTF-8 text in the terminal output buffer. macOS VoiceOver in terminal mode (`Cmd+F5` in Terminal.app or iTerm2) reads the text stream line by line; refreshable braille displays attached via BRLTTY (Linux) or Duxbury (Windows) consume the same stream. Animated surfaces (Spinner, LogoV2 shimmer) MUST degrade gracefully when reading — no information may be conveyed by animation alone.
2. **Reduced-motion fallback** — components that animate (all `Spinner/*` rows, `LogoV2/AnimatedAsterisk.tsx`, `LogoV2/WelcomeV2.tsx`, `useShimmerAnimation.ts` consumers) MUST honor the `NO_COLOR` / `KOSMOS_REDUCED_MOTION=1` env flag and emit a static-text equivalent. Implementation Epic is H #1302 (palette + motion tokens); runtime check is the responsibility of the implementing Epic (typically H or B).
3. **Semantic ordering** — rendered output MUST follow top-to-bottom reading order matching visual precedence. Ink's `<Box>` flex layout with `flexDirection="column"` is the default compliant shape; `position="absolute"` or out-of-order rendering is a regression that breaks the text-stream pathway.
4. **Focus narration** — focus transitions (WCAG 2.4.7) MUST emit a human-readable cue in the text stream when focus lands. Inverse-video alone is insufficient for screen readers that cannot see color — every focused affordance MUST carry a visible label or announcement line.
5. **Keyboard-only operation** — per WCAG 2.1.1, no affordance may require a mouse or trackpad; no citizen workflow may depend on terminal mouse reporting (`xterm-mouse`). All `IME-safe = yes` rows (§5) additionally guard against composition-mid-submit — the composition keypress MUST NOT trigger an action.

Deep ARIA-style role/name/value conformance (WCAG 4.1.2) for an Ink virtual DOM is deferred to #25 (`4.1.2 Name Role Value — deep compliance`); this gate requires role annotations only as §3 table entries, not runtime exposure. Epic H #1302 (palette) and Epic I #1303 (shortcuts) are the primary downstream consumers of this pathway; their `/speckit-specify` inputs MUST cite this §1.1 when proposing any animation, color, or keybinding decision.

## §2 · WCAG 2.1 AA criteria (closed set)

| ID | Name | Typical TUI application |
|---|---|---|
| 1.4.3 | Contrast (Minimum) | Every foreground/background pair in the component's rendered output ≥ 4.5:1 (text) or 3:1 (non-text) |
| 2.1.1 | Keyboard | All interactive affordances reachable via keyboard |
| 2.4.7 | Focus Visible | Focus indicator must be visible on terminal (e.g., inverse video or explicit border) |
| 3.3.2 | Labels or Instructions | Input surfaces display a visible label or placeholder instruction |
| 4.1.2 | Name Role Value | Screen-reader-exposed semantic role; deferred to #25 for deep-compliance, but components MUST be annotated with intended role here |

## §3 · Per-verdict gate rows

<a id="ag-customselect"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 1 | CustomSelect/index.ts | PORT | 1.4.3 | — | n/a | n/a |
| 2 | CustomSelect/option-map.ts | PORT | 1.4.3 | — | n/a | n/a |
| 3 | CustomSelect/select-input-option.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 4 | CustomSelect/select-option.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 5 | CustomSelect/select.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | — | yes | 4.5:1 |
| 6 | CustomSelect/SelectMulti.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | — | yes | 4.5:1 |
| 7 | CustomSelect/use-multi-select-state.ts | PORT | 1.4.3 | — | n/a | n/a |
| 8 | CustomSelect/use-select-input.ts | PORT | 1.4.3, 2.1.1 | — | yes | n/a |
| 9 | CustomSelect/use-select-navigation.ts | PORT | 1.4.3, 2.1.1 | — | n/a | n/a |
| 10 | CustomSelect/use-select-state.ts | PORT | 1.4.3 | — | n/a | n/a |

<a id="ag-design-system"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 11 | design-system/Byline.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 12 | design-system/color.ts | PORT | 1.4.3 | — | n/a | n/a |
| 13 | design-system/Dialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 14 | design-system/Divider.tsx | PORT | 1.4.3 | — | n/a | 3:1 |
| 15 | design-system/FuzzyPicker.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | — | yes | 4.5:1 |
| 16 | design-system/KeyboardShortcutHint.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 17 | design-system/ListItem.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 18 | design-system/LoadingState.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 19 | design-system/Pane.tsx | PORT | 1.4.3 | — | n/a | 3:1 |
| 20 | design-system/ProgressBar.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 3:1 |
| 21 | design-system/Ratchet.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |
| 22 | design-system/StatusIcon.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 3:1 |
| 23 | design-system/Tabs.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 24 | design-system/ThemedBox.tsx | PORT | 1.4.3 | — | n/a | n/a |
| 25 | design-system/ThemedText.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |
| 26 | design-system/ThemeProvider.tsx | PORT | 1.4.3 | — | n/a | n/a |

<a id="ag-diff"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 27 | diff/DiffDetailView.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 28 | diff/DiffDialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 29 | diff/DiffFileList.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-highlightedcode"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 30 | HighlightedCode/Fallback.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |

<a id="ag-logov2"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 31 | LogoV2/AnimatedAsterisk.tsx | REWRITE | 1.4.3, 4.1.2 | 은하계 로고 애니메이션 대체 텍스트 제공; 고대비 모드 지원 | n/a | 3:1 |
| 32 | LogoV2/CondensedLogo.tsx | REWRITE | 1.4.3, 4.1.2 | 축약 헤더 KOSMOS 워드마크 대체 텍스트; 스크린 리더 세션 정보 안내 | n/a | 4.5:1 |
| 33 | LogoV2/Feed.tsx | REWRITE | 1.4.3, 4.1.2 | 피드 항목 스크린 리더 접근 가능; 사역부 상태 피드 대체 텍스트 | n/a | 4.5:1 |
| 34 | LogoV2/FeedColumn.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |
| 35 | LogoV2/feedConfigs.tsx | REWRITE | 1.4.3, 4.1.2 | 피드 팩토리 시민 온보딩 단계 스크린 리더 내레이션; 사역부 가용성 상태 안내 | n/a | 4.5:1 |
| 36 | LogoV2/LogoV2.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 은하계 스플래시 대체 텍스트; 키보드 포커스 순서 명확; 고대비 모드 지원 | n/a | 4.5:1 |
| 37 | LogoV2/WelcomeV2.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 은하계 웰컴 화면 대체 텍스트; 키보드 포커스 순서 명확; KOSMOS 핵(kosmosCore) 은유 설명 | n/a | 4.5:1 |

<a id="ag-spinner"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 38 | Spinner/FlashingChar.tsx | PORT | 1.4.3 | — | n/a | 3:1 |
| 39 | Spinner/GlimmerMessage.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 40 | Spinner/index.ts | PORT | 1.4.3 | — | n/a | n/a |
| 41 | Spinner/ShimmerChar.tsx | PORT | 1.4.3 | — | n/a | 3:1 |
| 42 | Spinner/SpinnerAnimationRow.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 3:1 |
| 43 | Spinner/SpinnerGlyph.tsx | PORT | 1.4.3 | — | n/a | 3:1 |
| 44 | Spinner/teammateSelectHint.ts | REWRITE | 1.4.3 | — | n/a | n/a |
| 45 | Spinner/TeammateSpinnerLine.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 46 | Spinner/TeammateSpinnerTree.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 47 | Spinner/useShimmerAnimation.ts | PORT | 1.4.3 | — | n/a | n/a |
| 48 | Spinner/useStalledAnimation.ts | PORT | 1.4.3 | — | n/a | n/a |
| 49 | Spinner/utils.ts | PORT | 1.4.3 | — | n/a | n/a |
| 50 | Spinner.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 3:1 |

<a id="ag-structureddiff"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 51 | StructuredDiff/colorDiff.ts | PORT | 1.4.3 | — | n/a | n/a |
| 52 | StructuredDiff/Fallback.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |

<a id="ag-ui"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 53 | ui/OrderedList.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 54 | ui/OrderedListItem.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 55 | ui/TreeSelect.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-messages"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 56 | messages/AssistantRedactedThinkingMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 57 | messages/AssistantTextMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 58 | messages/AssistantThinkingMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 59 | messages/AssistantToolUseMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 60 | messages/AttachmentMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 61 | messages/CollapsedReadSearchContent.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 62 | messages/CompactBoundaryMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 63 | messages/GroupedToolUseContent.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 64 | messages/HighlightedThinkingText.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 65 | messages/HookProgressMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 66 | messages/nullRenderingAttachments.ts | PORT | 1.4.3 | 유틸리티 모듈; 시민 가시 표면 없음 (null renderer) | n/a | n/a |
| 67 | messages/PlanApprovalMessage.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 68 | messages/RateLimitMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 69 | messages/ShutdownMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 70 | messages/SystemAPIErrorMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 71 | messages/SystemTextMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 72 | messages/TaskAssignmentMessage.tsx | REWRITE | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 73 | messages/teamMemCollapsed.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 74 | messages/teamMemSaved.ts | REWRITE | 1.4.3 | 유틸리티 모듈; 데이터 변환만 수행 (렌더링 없음) | n/a | n/a |
| 75 | messages/UserAgentNotificationMessage.tsx | REWRITE | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 76 | messages/UserCommandMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 77 | messages/UserImageMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 78 | messages/UserMemoryInputMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 79 | messages/UserPlanMessage.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 80 | messages/UserPromptMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 81 | messages/UserResourceUpdateMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 82 | messages/UserTeammateMessage.tsx | REWRITE | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 83 | messages/UserTextMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 84 | messages/UserToolResultMessage/RejectedPlanMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 85 | messages/UserToolResultMessage/RejectedToolUseMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 86 | messages/UserToolResultMessage/UserToolCanceledMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 87 | messages/UserToolResultMessage/UserToolErrorMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 88 | messages/UserToolResultMessage/UserToolRejectMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 89 | messages/UserToolResultMessage/UserToolResultMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 90 | messages/UserToolResultMessage/UserToolSuccessMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 91 | messages/UserToolResultMessage/utils.tsx | PORT | 1.4.3 | 유틸리티 헬퍼; 렌더링은 형제 메시지 컴포넌트가 담당 | n/a | n/a |
| 92 | CompactSummary.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 93 | ContextSuggestions.tsx | REWRITE | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 94 | ContextVisualization.tsx | REWRITE | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 95 | FallbackToolUseErrorMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 96 | FallbackToolUseRejectedMessage.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 97 | FileEditToolDiff.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 98 | FileEditToolUpdatedMessage.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 99 | FileEditToolUseRejectedMessage.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 100 | HighlightedCode.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |
| 101 | InterruptedByUser.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 102 | Markdown.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 103 | MarkdownTable.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 104 | Message.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 105 | messageActions.tsx | PORT | 1.4.3, 2.1.1 | — | n/a | n/a |
| 106 | MessageModel.tsx | PORT | 1.4.3 | — | n/a | n/a |
| 107 | MessageResponse.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 108 | MessageRow.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 109 | Messages.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |
| 110 | MessageTimestamp.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 111 | StructuredDiff.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |
| 112 | StructuredDiffList.tsx | PORT | 1.4.3 | — | n/a | 4.5:1 |
| 113 | VirtualMessageList.tsx | PORT | 1.4.3, 4.1.2 | 전체 대화 내역 스크린 리더 접근 가능; 개인정보(PIPA) 렌더링 시 processor 역할 유지 — controller 재고지 책임 없음 | n/a | 4.5:1 |

<a id="ag-promptinput"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 114 | PromptInput/* | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 한국어 IME 합성 보호; 키보드 접근성 유지; 입력 필드 레이블 및 플레이스홀더 한국어 제공 | yes | 4.5:1 |

<a id="ag-helpv2"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 115 | HelpV2/Commands.tsx | PORT | 1.4.3, 4.1.2 | 검색 가능한 단일 창 안내; 포커스 복귀 지원 | n/a | 4.5:1 |
| 116 | HelpV2/General.tsx | PORT | 1.4.3, 4.1.2 | 검색 가능한 단일 창 안내; 포커스 복귀 지원 | n/a | 4.5:1 |
| 117 | HelpV2/HelpV2.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 검색 가능한 단일 창 안내; 포커스 복귀 지원 | n/a | 4.5:1 |

<a id="ag-hooks"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 118 | hooks/HooksConfigMenu.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 119 | hooks/PromptDialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | — | n/a | 4.5:1 |
| 120 | hooks/SelectEventMode.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 121 | hooks/SelectHookMode.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 122 | hooks/SelectMatcherMode.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 123 | hooks/ViewHookMode.tsx | PORT | 1.4.3, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-memory"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 124 | memory/MemoryFileSelector.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 125 | memory/MemoryUpdateNotification.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-shell"></a>

_(No PORT or REWRITE rows in the shell family — all four shell/* rows are DISCARD.)_

<a id="ag-claudecodehint"></a>

_(No PORT or REWRITE rows in the ClaudeCodeHint family — PluginHintMenu.tsx is DISCARD.)_

<a id="ag-permissions"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 126 | permissions/PermissionDialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 권한 게이트 키보드 접근 + Shift+Tab 순환; 음성 안내 호환 | n/a | 4.5:1 |
| 127 | permissions/* | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 권한 게이트 키보드 접근 + Shift+Tab 순환; 음성 안내 호환; 권한 요청 레이블 한국어 제공 | n/a | 4.5:1 |
| 128 | BypassPermissionsModeDialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 권한 게이트 키보드 접근 + Shift+Tab 순환; 음성 안내 호환 | n/a | 4.5:1 |

<a id="ag-trustdialog"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 129 | TrustDialog/TrustDialog.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 권한 게이트 키보드 접근 + Shift+Tab 순환; 음성 안내 호환; 동의 절차 스크린 리더 안내 | n/a | 4.5:1 |
| 130 | TrustDialog/utils.ts | REWRITE | 1.4.3 | — | n/a | n/a |

<a id="ag-managedsettings"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 131 | ManagedSettingsSecurityDialog/ManagedSettingsSecurityDialog.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 언어/테마/권한모드 라벨; 오류 메시지 즉시 안내; 관리형 설정 경고 스크린 리더 접근 | n/a | 4.5:1 |
| 132 | ManagedSettingsSecurityDialog/utils.ts | REWRITE | 1.4.3 | — | n/a | n/a |

<a id="ag-agents"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 133 | agents/* | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-teams"></a>

_(No PORT or REWRITE rows in the teams family — TeamsDialog.tsx and TeamStatus.tsx are both DISCARD.)_

<a id="ag-grove"></a>

_(No PORT or REWRITE rows in the grove family — Grove.tsx is DISCARD.)_

<a id="ag-passes"></a>

_(No PORT or REWRITE rows in the Passes family — Passes.tsx is DISCARD.)_

<a id="ag-sandbox"></a>

_(No PORT or REWRITE rows in the sandbox family — all five sandbox/* rows are DISCARD.)_

<a id="ag-mcp"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 134 | mcp/CapabilitiesSection.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 135 | mcp/ElicitationDialog.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 한국어 IME 합성 보호; 키보드 접근성 유지; 입력 파라미터 레이블 한국어 검증 | yes | 4.5:1 |
| 136 | mcp/index.ts | REWRITE | 1.4.3 | — | n/a | n/a |
| 137 | mcp/MCPToolDetailView.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 138 | mcp/MCPToolListView.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-skills"></a>

_(No PORT or REWRITE rows in the skills family — SkillsMenu.tsx is DISCARD.)_

<a id="ag-tasks"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 139 | tasks/* | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-wizard"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 140 | wizard/index.ts | REWRITE | 1.4.3 | — | n/a | n/a |
| 141 | wizard/useWizard.ts | REWRITE | 1.4.3 | — | n/a | n/a |
| 142 | wizard/WizardDialogLayout.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 143 | wizard/WizardNavigationFooter.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 144 | wizard/WizardProvider.tsx | REWRITE | 1.4.3 | — | n/a | n/a |

<a id="ag-feedbacksurvey"></a>

_(No PORT or REWRITE rows in the FeedbackSurvey family — all nine rows are DISCARD.)_

<a id="ag-lsprecommendation"></a>

_(No PORT or REWRITE rows in the LspRecommendation family — LspRecommendationMenu.tsx is DISCARD.)_

<a id="ag-settings"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 145 | Settings/Config.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 언어/테마/권한모드 라벨; 오류 메시지 즉시 안내 | yes | 4.5:1 |
| 146 | Settings/Settings.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 언어/테마/권한모드 라벨; 오류 메시지 즉시 안내 | n/a | 4.5:1 |
| 147 | Settings/Status.tsx | REWRITE | 1.4.3, 4.1.2 | 언어/테마/권한모드 라벨; 오류 메시지 즉시 안내 | n/a | 4.5:1 |
| 148 | Settings/Usage.tsx | REWRITE | 1.4.3, 4.1.2 | 언어/테마/권한모드 라벨; 쿼터 상태 스크린 리더 내레이션 | n/a | 4.5:1 |
| 149 | InvalidConfigDialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 언어/테마/권한모드 라벨; 오류 메시지 즉시 안내 | n/a | 4.5:1 |
| 150 | InvalidSettingsDialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 언어/테마/권한모드 라벨; 오류 메시지 즉시 안내 | n/a | 4.5:1 |
| 151 | LanguagePicker.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 언어/테마/권한모드 라벨; 한국어/영어 토글 접근성; 오류 메시지 즉시 안내 | n/a | 4.5:1 |
| 152 | ThemePicker.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 언어/테마/권한모드 라벨; 고대비 테마 접근성 확인 | n/a | 4.5:1 |
| 153 | ValidationErrorsList.tsx | PORT | 1.4.3, 3.3.2, 4.1.2 | 언어/테마/권한모드 라벨; 오류 메시지 즉시 안내 | n/a | 4.5:1 |

<a id="ag-desktopupsell"></a>

_(No PORT or REWRITE rows in the DesktopUpsell family — DesktopUpsellStartup.tsx is DISCARD.)_

<a id="ag-logo-wordmark"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 154 | FastIcon.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 3:1 |
| 155 | TagTabs.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-onboarding"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 156 | Onboarding.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 은하계 스플래시 대체 텍스트; 키보드 포커스 순서 명확; 시민 온보딩 흐름 스크린 리더 안내 | n/a | 4.5:1 |

<a id="ag-shortcuts"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 157 | root.shortcuts/* | REWRITE | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | 단축키 충돌 사전 경고; 한영 입력 모드 전환 안내 | n/a | 4.5:1 |
| 158 | KeybindingWarnings.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 단축키 충돌 사전 경고; 한영 입력 모드 전환 안내; 경고 메시지 즉시 안내 | n/a | 4.5:1 |

<a id="ag-coordinator"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 159 | AgentProgressLine.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 160 | App.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 161 | CoordinatorAgentStatus.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 162 | EffortCallout.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 163 | EffortIndicator.ts | PORT | 1.4.3 | — | n/a | n/a |
| 164 | FullscreenLayout.tsx | PORT | 1.4.3 | — | n/a | n/a |
| 165 | OffscreenFreeze.tsx | PORT | 1.4.3 | — | n/a | n/a |
| 166 | SessionBackgroundHint.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 167 | StatusLine.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 168 | StatusNotices.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 169 | TaskListV2.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 170 | TeammateViewHeader.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 171 | ThinkingToggle.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 172 | ToolUseLoader.tsx | PORT | 1.4.3, 4.1.2 | — | n/a | 3:1 |

<a id="ag-dialogs"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 173 | CostThresholdDialog.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | — | n/a | 4.5:1 |
| 174 | ExitFlow.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 175 | IdleReturnDialog.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 176 | MessageSelector.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | yes | 4.5:1 |
| 177 | SearchBox.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | — | yes | 4.5:1 |
| 178 | SessionPreview.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 179 | Stats.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 180 | TokenWarning.tsx | REWRITE | 1.4.3, 4.1.2 | — | n/a | 4.5:1 |
| 181 | ResumeTask.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |
| 182 | ClickableImageRef.tsx | PORT | 1.4.3, 2.1.1, 2.4.7, 4.1.2 | — | n/a | 4.5:1 |

<a id="ag-input"></a>

| # | CC source path | Verdict | WCAG | KWCAG notes | IME-safe | Contrast constraint |
|---|---|---|---|---|---|---|
| 183 | BaseTextInput.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 한국어 IME 합성 보호; 키보드 접근성 유지 | yes | 4.5:1 |
| 184 | TextInput.tsx | REWRITE | 1.4.3, 2.1.1, 2.4.7, 3.3.2, 4.1.2 | 한국어 IME 합성 보호; 키보드 접근성 유지 | yes | 4.5:1 |

## §4 · Citizen-facing families (KWCAG REQUIRED)

The following families must include non-empty KWCAG notes in their gate rows (FR-020):

- `PromptInput` — all 21 files handle Korean text input; full IME + keyboard accessibility
- `messages` — full conversation history must be screen-reader accessible; PIPA re-disclosure on any PII display
- `Settings` — language/theme/permission-mode labels; immediate error message announcement
- `Onboarding` (root-level family bin `root.onboarding`, i.e., `Onboarding.tsx`) — galaxy splash alt text; keyboard focus order
- `HelpV2` — searchable single-pane help; focus return on close
- Any row whose KOSMOS target lives under `tui/src/components/conversation/` or `tui/src/components/input/`
- Any row from subdirectories `Passes`, `permissions`, `Spinner` when surfaced in citizen-visible flows
- `LogoV2` rows that are REWRITE — splash-screen brand metaphor surfaces require alt text for the kosmosCore glyph
- `TrustDialog` — consent flow must be keyboard-accessible and screen-reader narrated
- `ManagedSettingsSecurityDialog` — citizen-visible dangerous-settings warning
- Shortcut surfaces (`root.shortcuts/*`, `KeybindingWarnings.tsx`) — keyboard conflict warnings and IME-mode-switch guidance

## §5 · IME-safe composition-gate acceptance

Every `IME-safe = yes` gate row, when materialized as a Task sub-issue via `/speckit-taskstoissues`, MUST carry this line in its acceptance-checklist body:

```
- [ ] All keyboard handlers gated on `!useKoreanIME().isComposing` before mutating input buffer
```

IME-safe rows in this gate (11 total):

- `CustomSelect/select.tsx` (row 5) — search-filter keyboard handler
- `CustomSelect/SelectMulti.tsx` (row 6) — multi-select keyboard handler
- `CustomSelect/use-select-input.ts` (row 8) — keyboard input hook
- `design-system/FuzzyPicker.tsx` (row 15) — fuzzy-search text input
- `PromptInput/*` (row 114) — all 21 constituent files; primary citizen text-input surface
- `mcp/ElicitationDialog.tsx` (row 135) — parameter elicitation text input
- `Settings/Config.tsx` (row 145) — language/theme config pickers with typed search
- `MessageSelector.tsx` (row 176) — typed-string conversation jump filter
- `SearchBox.tsx` (row 177) — generic text search input
- `BaseTextInput.tsx` (row 183) — Ink text-input primitive
- `TextInput.tsx` (row 184) — Ink text-input primitive

## §6 · Enforcement

This gate is the single source of truth for six machine-checkable invariants. `/speckit-analyze` consumes `specs/034-tui-component-catalog/contracts/accessibility-gate-rows.md §6` as the rule set and applies the following consequences. Downstream Epics inherit this enforcement surface when materializing Task sub-issues.

| ID | Invariant | FR | Violation consequence |
|---|---|---|---|
| AG-01 | Every PORT/REWRITE `CatalogRow` has exactly one `AccessibilityGateRow` with matching `CC source path`. | FR-018, SC-009 | `/speckit-analyze` FAILS — reports the orphan verdict (catalog row without a gate row, or gate row without a catalog row) and blocks merge. Fix: add or remove the gate row to restore 1:1 pairing. |
| AG-02 | The `WCAG` column is non-empty for every row (at minimum `1.4.3` for any visible component). | FR-019 | `/speckit-analyze` FAILS — reports the offending row number. Fix: populate the `WCAG` column with ≥ 1 criterion from the §2 closed set. |
| AG-03 | Citizen-facing families (§4) have non-empty `KWCAG notes`. | FR-020 | `/speckit-analyze` FAILS — reports the family and row. Fix: author a KWCAG note specific to the citizen interaction (boilerplate strings without per-component detail do NOT satisfy this invariant and MUST be elaborated). |
| AG-04 | `IME-safe = yes` rows propagate the composition-gate acceptance line into the generated `TaskSubIssue.acceptance_checklist` body. | FR-021 | `/speckit-taskstoissues` REJECTS the Task creation — the sub-issue body template rendering fails with a missing-line error. Fix: ensure the §5 acceptance-checklist line is included verbatim in the Task template. Downstream Epic PR fails the AG-04 check if any IME-safe component ships without the gate. |
| AG-05 | `Contrast constraint` column values ⊆ `{4.5:1, 3:1, n/a}`. | FR-022 | `/speckit-analyze` FAILS — reports the out-of-set value. Fix: normalize to the three allowed values (not free-text). Epic H #1302 reviewer is copied on the failure. |
| AG-06 | Every row's `WCAG` values ⊆ the closed set defined in §2 (exactly five criteria: 1.4.3 / 2.1.1 / 2.4.7 / 3.3.2 / 4.1.2). | FR-019 | `/speckit-analyze` FAILS — reports the out-of-set criterion. Fix: either rewrite the row to use a criterion from the closed set, or open an ADR to extend §2 (requires Accessibility Auditor sign-off). |

**Enforcement runner**: `/speckit-analyze` scans this document by row and produces `specs/<epic>/artifacts/analyze-report.md`. The runner is authoritative — manual visual inspection does not substitute. A PR that modifies this gate document MUST also update `specs/034-tui-component-catalog/contracts/accessibility-gate-rows.md` to keep the contract in sync.

**Upstream rule for downstream Epics**: Epics B / C / D / E / H / I / J / K / L that author Task sub-issues from this gate MUST cite the row ID (`# N`) and the invariant ID in their Task acceptance checklist. A Task that violates AG-04 at merge time is a SEV-2 citizen-accessibility regression.

## §7 · Handoff to Epic H #1302

**Palette-selection constraint for Epic H #1302**: body text ≥ 4.5:1 contrast, large text / non-text ≥ 3:1 (FR-022).

Epic H's `/speckit-specify` input MUST acknowledge this line before proposing any concrete color value. The constraint applies to all foreground/background color pairs rendered by any PORT or REWRITE component in this gate. The 3:1 threshold applies to non-text UI chrome including spinner glyphs (`Spinner/FlashingChar.tsx`, `Spinner/ShimmerChar.tsx`, `Spinner/SpinnerGlyph.tsx`, `Spinner/SpinnerAnimationRow.tsx`), dividers (`design-system/Divider.tsx`), panes (`design-system/Pane.tsx`), progress indicators (`design-system/ProgressBar.tsx`, `design-system/StatusIcon.tsx`), and `ToolUseLoader.tsx`. All other visible text surfaces require the 4.5:1 minimum. This constraint is non-negotiable and supersedes any CC-inherited palette token values.
