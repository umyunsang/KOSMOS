# Feature Specification: P4 · UI L2 Citizen Port

**Feature Branch**: `feat/1635-ui-l2-citizen-port`
**Created**: 2026-04-25
**Status**: Draft
**Input**: Epic #1635 — `docs/requirements/kosmos-migration-tree.md § UI L2 결정사항` 의 승인된 5개 surface(UI-A 온보딩 / UI-B REPL Main / UI-C Permission Gauntlet / UI-D Ministry Agent / UI-E 보조 surface)를 TUI 컴포넌트로 포팅. P3(#1634) 의 closed 13-tool surface · stdio-MCP 서버 · 4 primitive wrapper 위에 시민용 UI 를 와이어업.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Citizen runs a public-service query through the REPL (Priority: P1)

처음으로 KOSMOS 를 띄운 시민이 한국어로 행정 질의를 입력하면 응답이 약 20 토큰 단위로 끊김 없이 흘러 나오고, 답변이 길면 `Ctrl-O` 로 펼쳐서 PDF·표·인용 박스를 한 화면에서 확인하고, Slash 명령을 시작하면 자동완성 드롭다운이 떠서 다음 명령을 추천받는다. LLM·도구·네트워크 어디에서 문제가 나도 어느 계층에서 어떤 일이 일어났는지 시민이 즉시 식별할 수 있다.

**Why this priority**: REPL 메인 화면이 동작하지 않으면 KOSMOS 자체가 사용 불가. 시민이 가장 오래 보는 surface 이고, 다른 모든 UI L2 surface(권한 모달, 부처 에이전트 패널, 보조 surface)는 REPL 위에 떠야 한다.

**Independent Test**: `bun run tui` 로 KOSMOS 를 띄워 한국어로 임의 행정 질의를 입력 → 스트리밍 chunk 가 한 호흡으로 끊김 없이 들어오는지, `Ctrl-O` 로 긴 응답이 expand 되는지, PDF 가 첨부된 응답에서 인라인 미리보기 또는 외부 fallback 이 작동하는지, `/` 입력 시 드롭다운이 뜨는지, 일부러 LLM·Tool·Network 오류를 발생시켜 3종 envelope 가 시각적으로 구별되는지를 시민(비개발자) 관찰자가 확인.

**Acceptance Scenarios**:

1. **Given** 시민이 KOSMOS 를 처음 띄우고 행정 질의를 입력했을 때, **When** LLM 이 응답 스트리밍을 시작, **Then** 약 20 토큰 묶음 단위로 화면이 갱신되며 마지막 chunk 가 도착할 때까지 입력창은 비활성 표시 + 하단 진행 표시가 유지된다.
2. **Given** 응답이 화면 높이를 넘는 분량으로 도착했을 때, **When** 시민이 `Ctrl-O` 를 누름, **Then** 해당 응답 블록이 풀 사이즈로 펼쳐지고 다시 누르면 collapsed 상태로 돌아간다.
3. **Given** 응답에 PDF 링크가 포함되어 있고 터미널이 Kitty 또는 iTerm2 graphics protocol 을 지원할 때, **When** 응답이 렌더, **Then** PDF 의 첫 페이지가 인라인 PNG 로 표시된다. 미지원 터미널에서는 OS `open` 으로 외부 뷰어가 열린다.
4. **Given** 응답이 표를 포함할 때, **When** 렌더링, **Then** Claude Code `MarkdownTable` 와 동일한 시각 양식으로 렌더된다.
5. **Given** 시민이 입력창에서 `/` 를 입력, **When** 첫 글자가 들어옴, **Then** 슬래시 명령 자동완성 드롭다운이 강조 매칭 + 인라인 미리보기와 함께 표시된다.
6. **Given** 도구 호출 도중 LLM 4xx, 도구 본문 에러, 또는 네트워크 단절 중 하나가 발생, **When** 응답 envelope 가 도착, **Then** 세 가지 에러 타입이 구별 가능한 색상·아이콘·헤더로 별도 envelope 컴포넌트에 표시된다.
7. **Given** 멀티턴 대화가 진행 중, **When** 시민이 직전 turn 을 인용, **Then** `⎿` 접두 + single-border 박스로 인용 블록이 렌더된다.

---

### User Story 2 — Citizen sees a clear permission gate before any sensitive action (Priority: P1)

시민이 의료기관 이력 조회 같은 Layer 2 도구나 정부24 제출 같은 Layer 3 도구 호출을 트리거하면, 색상·기호로 위험도가 표시된 모달이 떠서 `[Y 한 번만 / A 세션 자동 / N 거부]` 중 선택을 강제받는다. 결정 직후 receipt ID 가 화면과 audit ledger 에 기록되며, 시민은 `/consent list` 로 과거 동의를 확인하고 `/consent revoke rcpt-<id>` 로 철회할 수 있다. 시민이 모드 전환 단축키(Shift+Tab)를 눌러도 더 위험한 모드(`bypassPermissions`)로 들어갈 때는 추가 확인 단계가 한 번 더 강제된다.

**Why this priority**: PIPA 수탁자 책임의 시각적 표면. 권한 게이트가 없으면 KOSMOS 가 시민 이름으로 외부 시스템을 건드릴 수 없다. Layer 1/2/3 spec 033 백엔드는 이미 동작하므로 본 epic 은 그 위의 시각·키바인딩 전면을 채운다.

**Independent Test**: 임의로 Layer 1/Layer 2/Layer 3 도구 호출을 트리거 → 각 Layer 색상(green ⓵ / orange ⓶ / red ⓷)이 모달에 정확히 적용되는지, `[Y/A/N]` 키로 결정 후 receipt ID 가 화면+`/consent list` 에 노출되는지, `/consent revoke` 에 확인 모달이 따라 붙는지, Shift+Tab 으로 `bypassPermissions` 진입 시 추가 확인이 뜨는지를 검증.

**Acceptance Scenarios**:

1. **Given** Layer 1 도구 호출이 큐에 오름, **When** 모달이 뜸, **Then** 헤더에 green 색의 ⓵ 기호와 도구 메타가 표시되며 `[Y / A / N]` 3-choice 가 활성된다.
2. **Given** Layer 2 도구 호출이 큐에 오름, **When** 모달이 뜸, **Then** 헤더가 orange ⓶ 로 바뀐다.
3. **Given** Layer 3 도구 호출이 큐에 오름, **When** 모달이 뜸, **Then** 헤더가 red ⓷ 로 바뀌고 시민에게 한 번 더 확인을 요청하는 보조 라인이 추가된다.
4. **Given** 시민이 모달에서 `Y` 또는 `A` 를 선택, **When** 결정이 적용, **Then** 화면 하단에 `rcpt-<id>` 가 토스트로 표시되고 동시에 audit ledger 에 같은 ID 로 append-only 기록된다.
5. **Given** 시민이 `/consent list` 입력, **When** 명령 실행, **Then** 본 세션의 모든 receipt 가 시간 역순으로 ID·Layer·도구명·결정·타임스탬프 칼럼과 함께 출력된다.
6. **Given** 시민이 `/consent revoke rcpt-<id>` 입력, **When** 명령 실행, **Then** 확인 모달이 한 번 더 뜨고 `Y` 시 해당 receipt 의 `revoked_at` 이 ledger 에 추가된다.
7. **Given** 현재 모드가 `default`, **When** 시민이 Shift+Tab 을 눌러 `bypassPermissions` 로 전환, **Then** "이 모드는 모든 권한 모달을 우회합니다" 강화 확인 모달이 한 번 더 표시되고 `Y` 를 눌러야 모드가 적용된다.

---

### User Story 3 — Citizen completes onboarding in five well-paced steps with accessibility toggles (Priority: P2)

KOSMOS 첫 실행 시(또는 `/onboarding` 재실행 시) 다섯 단계가 순차로 진행된다: ① preflight(환경 점검) → ② theme(보라 팔레트 + UFO 마스코트 미리보기) → ③ pipa-consent(개인정보 수탁자 책임 동의) → ④ ministry-scope(부처 옵트인 범위 선택) → ⑤ terminal-setup(접근성 4종 토글 + Shift+Tab 키바인딩 안내). 각 단계는 한국어가 기본이고 영어 fallback 이 가능하다. 동의 철회 시에도 audit ledger 와 OTEL span 은 그대로 보존된다.

**Why this priority**: 시민이 처음 진입할 때 무슨 일이 벌어지는지를 분명히 알게 하고, 부처 옵트인 범위 + PIPA 동의 receipt 가 명시적으로 캡처되는 surface. Spec 035 의 일부 인프라(memdir 동의 기록)와 결합되며, 본 epic 은 5-step 시퀀스 자체를 완성한다.

**Independent Test**: `~/.kosmos` 디렉토리를 비운 상태에서 `bun run tui` 실행 → 5 step 이 순차로 진행되는지, `/onboarding terminal-setup` 형태로 특정 step 만 재실행 가능한지, 한·영 전환이 작동하는지, 4종 접근성 토글(스크린리더 / 큰글씨 / 고대비 / reduced motion)이 즉시 반영되는지를 비개발자 관찰자가 확인.

**Acceptance Scenarios**:

1. **Given** `~/.kosmos/memdir/user/onboarding/state.json` 이 존재하지 않음, **When** 시민이 `bun run tui` 실행, **Then** 5 step 이 1→5 순서로 자동 재생되며 마지막 step 완료 후에만 REPL 로 진입한다.
2. **Given** 온보딩이 이미 완료된 상태, **When** 시민이 REPL 에서 `/onboarding` 입력, **Then** 첫 step 부터 다시 시작한다.
3. **Given** 온보딩이 이미 완료된 상태, **When** 시민이 `/onboarding ministry-scope` 입력, **Then** 4번째 step 만 단독 재실행되고 종료 시 REPL 로 복귀한다.
4. **Given** preflight step, **When** 환경 점검(Bun 버전·터미널 그래픽 프로토콜·KOSMOS_* 환경변수)이 실행, **Then** 항목별 ✓/✗ 결과와 다음 단계로 진행 가능 여부가 표시된다.
5. **Given** terminal-setup step, **When** 시민이 4종 접근성 토글 중 하나를 선택, **Then** 해당 옵션이 즉시 화면에 반영되고 `~/.kosmos/memdir/user/preferences/a11y.json` 에 영구 저장된다.
6. **Given** 한국어가 기본 언어, **When** 시민이 `/lang en` 또는 환경변수로 영어를 선택, **Then** 모든 step 의 텍스트·aria 레이블이 영어로 전환된다.
7. **Given** 시민이 pipa-consent step 에서 동의 후, 나중에 `/consent revoke` 로 철회, **When** 철회가 적용, **Then** 새 receipt 가 ledger 에 추가될 뿐 기존 동의 receipt 와 OTEL span 은 삭제되지 않는다.

---

### User Story 4 — Citizen sees which ministry agent is doing what at any moment (Priority: P2)

복잡한 다부처 질의(예: "차상위 가구 의료급여 + 운전면허 갱신 + 주민센터 발급" 같은 3+ 부처 작업)에서 시민이 `/agents` 를 입력하면 활성 부처 에이전트 목록이 5-state proposal-iv 도식(idle / dispatched / running / waiting-permission / done) 으로 표시된다. `/agents --detail` 을 추가하면 각 에이전트의 SLA 잔여, 건강 상태, 평균 응답 시간이 함께 노출된다. Swarm 모드는 시민이 명시적으로 3개 이상의 부처를 언급한 경우 또는 LLM 이 "복잡 질의" 라벨을 부여한 경우에만 자동 활성된다.

**Why this priority**: 시민이 백엔드에서 무슨 일이 벌어지는지 못 보면 KOSMOS 가 블랙박스로 보임. Spec 027 swarm + Spec 031 4-primitive wrapper 가 백엔드에 이미 있으므로, 본 epic 은 그것을 시각화하고 임계치 결정만 와이어업한다.

**Independent Test**: 3개 부처를 명시한 질의(예: "복지부 + 행안부 + 교육부 동시 안내")를 입력 → swarm 모드 자동 활성 → `/agents` 로 5-state 가 시간상 변하는지 → `/agents --detail` 에서 SLA·건강·평균응답이 채워지는지 검증. 단일 부처 질의에서는 swarm 이 활성되지 않아야 한다.

**Acceptance Scenarios**:

1. **Given** 시민이 단일 부처 질의를 입력, **When** LLM 이 plan 을 생성, **Then** swarm 은 활성되지 않고 단일 에이전트만 작업한다.
2. **Given** 시민이 3개 이상 부처를 명시, **When** plan 이 생성, **Then** swarm 모드가 자동 활성되고 `/agents` 가 다중 에이전트를 보여준다.
3. **Given** LLM 이 plan 에 "복잡" 태그를 부여, **When** swarm 후보 임계치를 평가, **Then** 명시 부처 수가 3 미만이라도 swarm 이 활성된다.
4. **Given** swarm 활성 상태, **When** 시민이 `/agents` 를 입력, **Then** proposal-iv 5-state 의 현재 상태가 에이전트별로 표시된다.
5. **Given** swarm 활성 상태, **When** 시민이 `/agents --detail` 을 입력, **Then** 에이전트별 SLA 잔여 시간·헬스(녹/황/적)·최근 N회 평균 응답 시간이 함께 표시된다.

---

### User Story 5 — Citizen can find help, edit config, browse plugins, export, and search history (Priority: P3)

시민이 `/help` 를 입력하면 명령이 4개 그룹(세션 / 권한 / 도구 / 저장)으로 묶여 노출되고, `/config` 는 overlay 로 떠서 일반 설정은 즉시 반영하되 `.env` 의 비밀값 편집은 격리 모드로만 진입한다. `/plugins` 는 ⏺/○ 토글, Space 활성, `i` 상세, `r` 제거, `a` 스토어 진입의 키바인딩으로 동작한다. `/export` 는 현재 대화 + 도구 결과 + 동의 receipt 를 포함한 PDF 를 만들지만 OTEL span 과 플러그인 내부 상태는 제외한다. `/history` 는 날짜 / 세션 / Layer 3종 필터로 과거 대화를 검색한다.

**Why this priority**: 시민이 KOSMOS 를 며칠 이상 사용할 때 필요한 surface. 핵심 REPL·권한·온보딩 surface 가 동작한 후에 가치를 더하므로 P3.

**Independent Test**: `/help` → 그룹 4개 확인. `/config` → overlay 진입 + `.env` 편집 격리 진입 시도. `/plugins` → 기본 화면 + 키바인딩 5종 작동. `/export` → PDF 가 대화+도구+receipt 만 포함하는지 grep. `/history` → 3종 필터 각각 적용 결과 비교.

**Acceptance Scenarios**:

1. **Given** 시민이 `/help` 입력, **When** 화면이 렌더, **Then** 명령 목록이 세션 / 권한 / 도구 / 저장 4개 그룹으로 묶여 표시된다.
2. **Given** 시민이 `/config` 입력, **When** overlay 가 열림, **Then** 일반 설정은 inline 편집되고 `.env` 비밀값 항목은 별도의 격리 편집기로만 진입할 수 있다.
3. **Given** 시민이 `/plugins` 입력, **When** 플러그인 브라우저가 열림, **Then** 활성 플러그인은 ⏺ 비활성은 ○ 로 표시되며 Space(활성 토글)·`i`(상세)·`r`(제거)·`a`(스토어) 키바인딩이 작동한다.
4. **Given** 시민이 `/export` 입력, **When** PDF 가 생성, **Then** 출력 PDF 의 텍스트에 대화 + 도구 호출/결과 + receipt ID 가 포함되고 OTEL span ID 와 플러그인 내부 상태는 포함되지 않는다.
5. **Given** 시민이 `/history --date 2026-04-01..2026-04-25` 입력, **When** 검색 실행, **Then** 해당 기간 세션만 결과로 출력된다. `--session <id>` 와 `--layer 2` 필터도 같은 방식으로 단독·복합 적용된다.

---

### Edge Cases

- 터미널이 graphics protocol 을 지원하지도 않고 OS `open` 도 사용 불가능한 환경(예: 헤드리스 SSH 세션)에서 PDF 첨부가 도착하면 어떻게 되는가 — 텍스트 fallback 으로 PDF 경로 + 사이즈 + 바이트 해시만 표시하고 사용자에게 다운로드 링크를 알린다.
- 스트리밍 도중 네트워크가 끊어졌을 때 chunk 가 중간에 멈추면 — 마지막 chunk 이후 5 초 무응답 시 Network 에러 envelope 로 전환하고 시민에게 retry 옵션을 제시한다.
- 권한 모달이 떠 있는 상태에서 시민이 Ctrl-C 를 누르면 — 모달은 자동 거부(`N`)로 닫히고 receipt 에 `auto_denied_at_cancel` 플래그가 기록된다.
- 5-step 온보딩 도중 강제 종료(SIGINT)가 발생하면 — 다음 실행 시 마지막으로 완료된 step 다음부터 재개한다.
- swarm 활성 임계치가 모호한 경계 케이스(2개 부처 명시 + LLM "복잡" 태그) — 두 신호 중 하나라도 충족 시 활성으로 처리한다.
- Layer 3 모달에서 시민이 5 분 이상 응답하지 않으면 — 자동 거부로 처리되고 receipt 에 `timeout_denied` 가 기록된다.
- `/consent revoke` 가 이미 revoked 된 receipt 를 대상으로 다시 호출되면 — 멱등 처리하며 추가 ledger 항목 없이 토스트로 "이미 철회됨" 만 안내한다.
- 한국어가 기본인 환경에서 영어 사용자가 들어오면 — 환경변수 `KOSMOS_LANG=en` 또는 `/lang en` 으로 즉시 전환되고 모든 모달·토스트·aria 레이블이 영어로 출력된다.

## Requirements *(mandatory)*

### Functional Requirements

#### UI-A · Onboarding 5-step

- **FR-001**: System MUST run a fixed five-step onboarding sequence in this order on first launch: `preflight → theme → pipa-consent → ministry-scope → terminal-setup`.
- **FR-002**: System MUST persist completion state per step in the user-tier memdir so partially completed onboardings can resume from the last completed step after a restart.
- **FR-003**: System MUST expose a `/onboarding` command that re-runs the entire sequence and a `/onboarding <step-name>` form that re-runs a single step in isolation.
- **FR-004**: System MUST default to Korean text and provide an English fallback selectable via `/lang <code>` or environment configuration.
- **FR-005**: System MUST provide four independent accessibility toggles in the terminal-setup step: screen-reader-friendly mode, large-font mode, high-contrast mode, and reduced-motion mode. Each toggle MUST persist to the user-tier memdir and apply immediately without restart.
- **FR-006**: System MUST surface a clear visual + textual notice in the pipa-consent step explaining the trustee responsibility under PIPA §26 before accepting consent.
- **FR-007**: When a citizen revokes a previously granted consent, System MUST append a new revoke record to the audit ledger and MUST NOT delete the prior consent record or OTEL span.

#### UI-B · REPL Main

- **FR-008**: System MUST stream LLM responses to the REPL in chunks of approximately 20 tokens per render frame.
- **FR-009**: System MUST bind `Ctrl-O` to expand/collapse any rendered response block that exceeds the visible viewport, with the keystroke toggling between collapsed and expanded states.
- **FR-010**: System MUST detect Kitty and iTerm2 graphics protocol support at runtime and, when supported, render the first page of any PDF attachment inline as a PNG. When unsupported, System MUST fall back to invoking the operating system's default file opener.
- **FR-011**: System MUST render markdown tables with the same visual layout as the Claude Code reference `MarkdownTable` component.
- **FR-012**: System MUST render three distinct error envelope styles — LLM-error, Tool-error, and Network-error — each with a unique color, icon, and header label. The envelope type MUST be clearly identifiable to a non-technical citizen.
- **FR-013**: System MUST render multi-turn quote blocks with a `⎿` prefix and a single-border surrounding box.
- **FR-014**: System MUST display a slash-command autocomplete dropdown the moment the citizen types `/` in the input, showing highlighted matches with inline previews.

#### UI-C · Permission Gauntlet

- **FR-015**: System MUST display a permission modal before invoking any tool whose Layer is 1, 2, or 3.
- **FR-016**: System MUST color-code the modal header by Layer: green with the ⓵ glyph for Layer 1, orange with ⓶ for Layer 2, red with ⓷ for Layer 3.
- **FR-017**: System MUST present three choices in every permission modal — `[Y]` allow once, `[A]` allow for the rest of the session, `[N]` deny — and MUST require an explicit choice before continuing.
- **FR-018**: After every permission decision, System MUST display the resulting `rcpt-<id>` to the citizen and MUST persist the same ID to the append-only audit ledger.
- **FR-019**: System MUST provide a `/consent list` command that prints all consent receipts from the current session in reverse chronological order including ID, Layer, tool name, decision, and timestamp.
- **FR-020**: System MUST provide a `/consent revoke rcpt-<id>` command that prompts a confirmation modal and, on confirmation, appends a revocation record to the ledger.
- **FR-021**: System MUST treat repeated `/consent revoke` calls on an already-revoked receipt as idempotent — no new ledger entry is created and a "already revoked" toast is shown.
- **FR-022**: System MUST switch permission modes via `Shift+Tab` keybinding and MUST display an additional reinforcement-confirmation modal when the citizen attempts to enter `bypassPermissions` mode.
- **FR-023**: System MUST treat `Ctrl-C` while a permission modal is open as an automatic denial and record `auto_denied_at_cancel` on the receipt.
- **FR-024**: System MUST treat 5 minutes of citizen inactivity on a Layer 3 modal as an automatic denial and record `timeout_denied` on the receipt.

#### UI-D · Ministry Agent Visibility

- **FR-025**: System MUST render an agent visibility surface that maps each active ministry agent to one of five states: `idle`, `dispatched`, `running`, `waiting-permission`, `done`.
- **FR-026**: System MUST provide a `/agents` command that displays the current state per active agent and a `/agents --detail` form that adds SLA-remaining, health (green / amber / red), and rolling-average response time per agent.
- **FR-027**: System MUST automatically activate swarm mode when EITHER the citizen explicitly mentions three or more distinct ministries in a single turn OR the LLM tags the plan as "complex". When neither signal is present, swarm mode MUST remain off.
- **FR-028**: System MUST keep the agent visibility surface live-updated as agent state transitions arrive from the backend, without requiring the citizen to re-invoke `/agents`.

#### UI-E · Auxiliary Surfaces

- **FR-029**: System MUST group the `/help` output into exactly four sections: Session, Permission, Tool, Storage. Every slash command MUST belong to exactly one group.
- **FR-030**: System MUST open `/config` as an overlay that allows inline editing of non-secret settings and isolates `.env` secret editing into a separate confined editor view.
- **FR-031**: System MUST render the `/plugins` browser using `⏺` for active plugins and `○` for inactive plugins, with keybindings `Space` (toggle activation), `i` (detail view), `r` (remove), `a` (open marketplace).
- **FR-032**: System MUST produce a PDF export via `/export` that contains the conversation transcript, tool invocations and results, and consent receipts, and MUST exclude OTEL span identifiers and plugin-internal state.
- **FR-033**: System MUST provide a `/history` search with three independent filters that can be combined: date range (`--date FROM..TO`), session ID (`--session <id>`), and Layer (`--layer <n>`).

#### Cross-cutting (Brand · Accessibility · Citizen visibility)

- **FR-034**: System MUST preserve the Claude Code 2.1.88 visual and structural layout to a fidelity of at least 90% across all UI L2 surfaces, replacing only the functional wiring with KOSMOS-specific behavior.
- **FR-035**: System MUST render the UFO mascot in four poses (idle / thinking / success / error) using the approved purple palette: body `#a78bfa`, background `#4c1d95`.
- **FR-036**: System MUST keep the Claude Code brand glyph `✻` and thread glyphs `⏺` / `⎿` unchanged.
- **FR-037**: System MUST emit an OTEL span attribute `kosmos.ui.surface` with value drawn from `{onboarding, repl, permission_gauntlet, agents, help, config, plugins, export, history}` for every user-visible surface activation, allowing the existing observability stack (Spec 021 + Spec 028) to count surface usage.
- **FR-038**: System MUST not introduce any new external network dependency; all UI L2 surfaces MUST function with the existing FriendliAI + local Langfuse stack and MUST NOT contact additional third-party hosts.

### Key Entities

- **Onboarding step** — One of five named stages with persisted completion state. Attributes: name (`preflight | theme | pipa-consent | ministry-scope | terminal-setup`), completed_at, citizen-selected values (theme, ministry scope set, accessibility toggles).
- **Permission receipt** — Append-only record produced by every modal decision. Attributes: `rcpt-<id>`, layer (1 / 2 / 3), tool name, decision (`allow_once | allow_session | deny | auto_denied_at_cancel | timeout_denied`), timestamp, optional `revoked_at`.
- **Agent visibility entry** — Live-updating row per active ministry agent. Attributes: agent ID, ministry name, state (5 enum), SLA remaining, health, rolling-average response time.
- **Slash command catalog entry** — Static metadata for autocomplete dropdown and `/help` grouping. Attributes: name, group (`session | permission | tool | storage`), one-line description, optional argument signature.
- **Accessibility preference** — Persisted per-citizen toggle set. Attributes: screen_reader, large_font, high_contrast, reduced_motion (each boolean).
- **Error envelope** — Wrapper around any failed operation result. Attributes: type (`llm | tool | network`), title, detail, retry-suggested flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A citizen who has never used KOSMOS before completes the entire 5-step onboarding within 3 minutes on a first try, with at least 95% of test participants finishing without external help.
- **SC-002**: Streaming response perceived smoothness is at least 4 of 5 (Likert) in citizen testing — no perceivable stutter at the 20-token chunk boundary.
- **SC-003**: 100% of Layer 2 and Layer 3 tool invocations display a permission modal before execution (zero bypasses in CI test runs).
- **SC-004**: Citizens correctly identify the layer (1 / 2 / 3) of a tool from the modal alone in at least 90% of usability test trials within 2 seconds of seeing the modal.
- **SC-005**: Slash-command autocomplete dropdown appears within 100 ms of the `/` keystroke in 99% of measured render frames.
- **SC-006**: PDF inline rendering activates on Kitty and iTerm2 in 100% of supported-terminal test runs and falls back to OS opener on 100% of unsupported-terminal test runs (no crash, no missing-attachment surface).
- **SC-007**: Agent visibility surface state lag (backend transition → screen update) is under 500 ms in the 95th percentile.
- **SC-008**: All UI L2 surfaces operate with zero new external network egress (verified by Spec 028 collector traffic logs); existing FriendliAI + local Langfuse footprint is unchanged.
- **SC-009**: Visual diff against Claude Code 2.1.88 reference screens shows ≥ 90% structural and visual fidelity per surface (manual scoring across 9 surfaces).
- **SC-010**: Citizen-reported confidence that "KOSMOS will not act without my permission" is at least 4 of 5 (Likert) after a usability session that includes at least one Layer 2 or Layer 3 invocation.
- **SC-011**: Accessibility toggles change rendered output within 500 ms of activation and persist across restarts in 100% of test runs.
- **SC-012**: `/export` PDF contains zero OTEL span identifiers and zero plugin-internal state markers in automated content scans across 20 sample sessions.

## Assumptions

- The Claude Code 2.1.88 reference src under `.references/claude-code-sourcemap/restored-src/src/{components,screens,keybindings,context}` is the canonical visual + structural source for this port; no new visual language is invented in this epic.
- P3 (#1634) deliverables — closed 13-tool surface, stdio-MCP server, four primitive wrappers — are merged and operational; this epic wires UI on top, not into them.
- Spec 033 permission v2 spectrum, Spec 027 swarm core, Spec 035 onboarding-brand-port memdir infrastructure, Spec 021 OTEL emission, and Spec 028 OTLP collector are all in production; no backend changes are required for UI L2 to function.
- Citizens run KOSMOS in a modern terminal that either supports Kitty/iTerm2 graphics protocol OR has a working OS file opener.
- A citizen is identified per OS user; multi-citizen accounts on the same OS user are out of scope.
- "Three or more ministries" for swarm activation is detected by the LLM's structured plan output, not by static keyword matching.
- The UFO mascot assets and purple palette referenced in `docs/wireframes/ufo-mascot-proposal.mjs` are already approved and present in the repository.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Native mobile UI** — KOSMOS is a terminal-based platform; iOS / Android clients are excluded by architecture.
- **Multi-tenant single-host deployment** — KOSMOS runs as a per-OS-user CLI; multi-tenant gateways are not part of this product.
- **Voice interface** — Voice input/output to drive the REPL is not part of UI L2; the spec deliberately stays text-based with accessibility toggles for screen readers instead.
- **Re-implementation of Claude Code's developer-facing surfaces** — Surfaces unique to developer workflows (e.g., diff review, slash commands not in the four `/help` groups) stay disabled in citizen UI.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Plugin DX (5-tier template / guide / examples / submission / registry) | Citizen UI must stabilize before exposing third-party plugin authoring | Phase P5 — Plugin DX | #1810 |
| `docs/api` and `docs/plugins` reference docs | Documentation site rebuild belongs to the docs phase | Phase P6 — Docs + Smoke | #1812 |
| Phase 2 auxiliary tools (TextToSpeech / SpeechToText / LargeFontRender / OCR / Reminder) | Required only after MVP citizen surface ships and is observed in production | Phase P6 follow-up | #1814 |
| Japanese (日本語) localization | Korean primary + English fallback covers MVP audience; Japanese is in the migration tree as "예정" | Post-P6 localization epic | #1816 |
| `/agents` advanced views beyond `--detail` (e.g., per-ministry SLA history graphs) | Outside the proposal-iv 5-state scope; needs more usage data first | Phase P6 follow-up | #1818 |
| Plugin marketplace store UI itself (the `a` keybinding's destination) | Marketplace is a separate epic; this epic only wires the entry-point keystroke | Phase P5 — Plugin DX | #1820 |
| Re-styling of Spec 035 brand-port memdir layouts | Memdir storage paths are owned by Spec 035 and should not change here | Spec 035 follow-up | #1822 |
| Composite tools (verb chains beyond the 4 primitives) | Decision in migration tree § L1-B6 to remove composites; primitive chains via LLM are the path | Out of scope by canonical decision | #1824 |
