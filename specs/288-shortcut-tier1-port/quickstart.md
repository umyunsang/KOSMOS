# Quickstart — Shortcut Tier 1 Port

**Audience**: an implementing agent (Backend/Frontend Sonnet Teammate) or a human engineer verifying the port end-to-end.

## Preconditions

1. `bun` v1.2.23+ installed (`bun --version`).
2. On branch `288-shortcut-tier1-port`: `git status` clean.
3. TUI dev shell runs today: `cd tui && bun run dev` renders the existing 287/035 surfaces.

## 15-minute smoke path (after full implementation)

### 1. Install — nothing to install

Zero new dependencies (SC-008). Existing `tui/package.json` is sufficient.

### 2. Boot the TUI and press ctrl+c mid-query (User Story 1)

```bash
cd tui && bun run dev
# In the TUI, start a long-running query: "경부선 안전 경로 분석해줘"
# After the tool-loop log shows "LLM step 2 …", press Ctrl+C
```

**Expected**: the loop aborts within 500 ms; the status bar returns to "Ready"; the session indicator remains green; a new typed message is accepted without a consent re-prompt.

**Verify**: `tail -20 ~/.kosmos/logs/audit.jsonl` shows one `user-interrupted` record with the current session ID and the interrupted tool-call ID.

### 3. IME composition safety (User Story 3)

```bash
# With the TUI open, begin typing: "가나다" (press g-a-n-a-d-a in IME mode)
# Mid-composition (before the final jamo commits), press Escape
```

**Expected**: the draft preserves "가나", the IME continues composing the final syllable; escape does NOT clear the buffer.

### 4. Permission-mode cycle (User Story 4)

```bash
# In the TUI, observe the mode indicator (should say "plan")
# Press Shift+Tab
```

**Expected**: indicator advances to "default" within 200 ms; no buffer content changes; an OTel span `kosmos.permission.mode=default` is emitted (visible in Langfuse local, `docker-compose up -d` of Spec 028 collector).

### 5. Clean exit (User Story 2)

```bash
# With an empty input buffer, press Ctrl+D
```

**Expected**: a confirmation prompt appears only if an agent loop is still active; otherwise the TUI exits with status 0; every pending audit record is flushed.

**Verify** (after exit):
```bash
jq '.event_type' ~/.kosmos/logs/audit.jsonl | tail -5
# Should include "session-exited"
echo $?
# Should be 0
```

### 6. History navigation (User Story 5 / 6)

```bash
# Send two messages in the session: "날씨 알려줘" then "내일 비 와?"
# Clear the input buffer, press Up
# Expected: "내일 비 와?" loads into buffer
# Press Up again
# Expected: "날씨 알려줘" loads
# Press Ctrl+R, type "날씨"
# Expected: overlay opens, filters to entries containing "날씨"
```

### 7. User override — disable history search (User Story 7)

```bash
echo '{"ctrl+r": null}' > ~/.kosmos/keybindings.json
cd tui && bun run dev
# In the TUI, press Ctrl+R
```

**Expected**: nothing happens (no overlay); a log line confirms the override was loaded: `[keybindings] disabled: history-search (ctrl+r)`.

**Reset**:
```bash
rm ~/.kosmos/keybindings.json
```

### 8. User override — remap history search (User Story 7)

```bash
echo '{"ctrl+f": "history-search", "ctrl+r": null}' > ~/.kosmos/keybindings.json
cd tui && bun run dev
# In the TUI, press Ctrl+F
```

**Expected**: the overlay opens on ctrl+f; ctrl+r is a no-op.

### 9. User override — attempted remap of reserved action (fails safely)

```bash
echo '{"ctrl+c": "draft-cancel"}' > ~/.kosmos/keybindings.json
cd tui && bun run dev
# Look at stdout on launch
```

**Expected**: a warning `[keybindings] rejected remap of reserved action: agent-interrupt`; the default `ctrl+c` → `agent-interrupt` binding remains.

## Automated test paths

```bash
cd tui
bun test keybindings/parser.test.ts
bun test keybindings/resolver.test.ts
bun test keybindings/reservedShortcuts.test.ts
bun test keybindings/loadUserBindings.test.ts
bun test keybindings/ime-composition.integration.test.ts   # 200-sample IME suite
bun test keybindings/accessibility.test.ts                 # screen-reader channel
```

All six suites MUST pass. The IME-composition suite drops zero jamo (SC-002).

## Accessibility audit path

1. Launch TUI under NVDA (Windows) or VoiceOver (macOS) or 센스리더 (Korean desktop).
2. With only keyboard + screen reader, complete the Story 1–4 flows above.
3. Time the "Tier 1 catalogue discovery" from launch to the first spoken enumeration of ctrl+c/ctrl+d/escape/ctrl+r/shift+tab (SC-007 target ≤ 30 s).

## Failure triage

| Symptom | Likely cause | Fix |
|---|---|---|
| `ctrl+c` doesn't interrupt | Ink's `setRawMode` not enabled in your terminal | Check FR-016 implementation; ensure Bun ≥ 1.2.23 |
| `shift+tab` does nothing on Windows Terminal | VT mode off | Verify `defaultBindings.ts` platform check (D3); fallback to `meta+m` |
| `escape` clears buffer during 한글 입력 | IME gate not wired | Check resolver.ts `mutates_buffer` branch (FR-005) |
| History overlay shows cross-session entries without consent | memdir USER consent check missing | Verify FR-021 path in resolver |
| `ctrl+d` fires on non-empty buffer | FR-014 regression | Check `resolver.ts` buffer-non-empty guard |
| `ctrl+c` during a modal closes the whole TUI | Resolver precedence bug | Verify modal-first precedence (FR-003, D7) |
