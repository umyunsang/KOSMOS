# Epic P4 · UI L2 Implementation

## Objective

`docs/requirements/kosmos-migration-tree.md § UI L2 결정사항` 의 승인된 UI
결정들을 실제 TUI 컴포넌트에 반영. 와이어프레임 mjs 파일들의 시각적 결정을
포팅된 CC 컴포넌트 + KOSMOS hook에 와이어링.

## Acceptance criteria

- [ ] `bun run src/main.tsx` 기동 시 onboarding 5-step 순차 진행 (A.1)
- [ ] `/onboarding` · `/onboarding <step>` 재실행 가능 (A.2)
- [ ] 응답 스트리밍이 chunk 단위 (≈20 token)로 업데이트 (B.1)
- [ ] 긴 응답에서 `Ctrl-O` 눌러 expand/collapse 작동 (B.2)
- [ ] PDF 링크 클릭시 Kitty/iTerm2 감지 → inline 렌더, 미지원 시 `open` fallback (B.3a)
- [ ] 표는 CC `MarkdownTable` 렌더 그대로 (B.3b)
- [ ] LLM · Tool · Network 3종 에러 envelope 별도 스타일 (B.4)
- [ ] Multi-turn 맥락 인용 박스 (`⎿` 접두 + single-border) 렌더 (B.5)
- [ ] Slash command 자동완성 드롭다운 (highlighted match + 인라인) (B.6)
- [ ] Permission modal `[Y/A/N]` + receipt ID 표시 (C.2)
- [ ] `/consent list`, `/consent revoke` 명령 작동 (C.3, C.4)
- [ ] Shift+Tab 모드 전환 + bypass 강화 확인 (C.5)
- [ ] `/agents` 기본 + `/agents --detail` (D.1)
- [ ] Help 그룹화 4개 섹션 (E.1) · Config overlay (E.2) · Plugin browser (E.3) · Export PDF (E.4) · History search (E.5)

## File-level scope

### `tui/src/screens/REPL.tsx`
- `<PromptInputFooter>` · `Ctrl-O` 핸들러 추가 (B.2)
- `<Messages>` streaming chunk size=20 config (B.1)
- `<ToolUseBlock>` · primitive 도트 색 규약 (UI-D proposal-iv)
- `<EmergencyTip>` · setEmergencyTip 호출 연결 (API 장애 surface)

### `tui/src/components/onboarding/`
- `Onboarding.tsx` · STEPS 배열을 5-step 재구성 (A.1)
- `PreflightStep.tsx` · 신설 (environment check)
- `ThemeStep.tsx` · CC `ThemePicker.tsx` 포트 활용
- `TerminalSetupStep.tsx` · 신설 (Shift+Tab 힌트 · a11y 토글)
- `OnboardingCommand.ts` · `/onboarding` `/onboarding <step>` 핸들러

### `tui/src/components/PromptInput/`
- `PromptInputFooterSuggestions.tsx` · B.6 autocomplete 드롭다운 확장
- `CtrlOToExpand.ts` · 기존 stub을 실구현으로 교체 (B.2)

### `tui/src/components/messages/`
- `MarkdownRenderer.tsx` 신설 (B.3a 인라인 preview)
- `PdfInlineViewer.tsx` 신설 (B.3a Kitty/iTerm2 감지 + pdf-to-img)
- `ErrorEnvelope.tsx` 신설 — LLM/Tool/Network 분기 (B.4)
- `ContextQuoteBlock.tsx` 신설 — `⎿` 접두 (B.5)

### `tui/src/components/permissions/`
- `PermissionGauntletModal.tsx` · `[Y/A/N]` 3-choice + receipt ID (C.2)
- `ConsentListCommand.tsx` 신설 (C.3)
- `ConsentRevokeCommand.tsx` 신설 (C.4)
- `PermissionModeSwitchHandler.tsx` · bypass 강화 확인 (C.5)

### `tui/src/commands/`
- `agents.ts` · `/agents` (기본) + `--detail` 플래그 (D.1)
- `plugins.ts` · `/plugins` 기본 + browser 진입 (E.3)
- `consent.ts` · list · revoke 서브커맨드 (C.3, C.4)
- `onboarding.ts` · 재실행 (A.2)
- `help.ts` · 그룹화 (E.1)
- `config.ts` · overlay 진입 (E.2)
- `export.ts` · PDF 저장 (E.4)
- `history.ts` · 세션 검색 (E.5)

### `tui/src/components/LogoV2/Clawd.tsx` + `AnimatedClawd.tsx`
- 이미 UFO 보라 버전으로 교체 완료 (이 Epic 착수 전 선행됨)

### `tui/src/i18n/`
- `ko.ts` / `en.ts` · 온보딩 · 에러 문구 추가 (A.3)
- 접근성 aria 힌트 키 추가 (A.4)

### 신규 의존성
- `pdf-to-img` (Apache-2.0, WASM) — PDF → PNG
- `pdf-lib` — Export PDF 생성
- (선택) `chafa` · `timg` 시스템 바이너리 — optional progressive enhancement

### Out of scope
Tool system 재배선 (P3) · 실 Plugin 어댑터 (P5) · docs/api 작성 (P6)

### Dependencies
Requires P0, P1+P2, P3 complete.

### Related decisions
`docs/requirements/kosmos-migration-tree.md § UI L2 결정사항`
`docs/wireframes/` (proposal-iv · ui-{a,b,c,d,e}.mjs)
