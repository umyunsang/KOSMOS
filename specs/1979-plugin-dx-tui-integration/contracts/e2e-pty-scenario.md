# Contract — 4-layer PTY E2E scenario artifacts

**Surface**: `specs/1979-plugin-dx-tui-integration/` (artifacts) + scripts under `specs/1979-plugin-dx-tui-integration/scripts/` (NEW).
**Trigger**: Manual (`bash specs/1979-plugin-dx-tui-integration/scripts/run-e2e.sh`) or CI (matrix entry `e2e-plugin-1979`).
**Purpose**: Produce grep-friendly proof that Story 1 + Story 2 work end-to-end. Per `docs/testing.md § TUI verification methodology` — the 4-layer ladder.

---

## Layer-by-layer artifacts

| Layer | Path | Format | Producer | Consumer |
|---|---|---|---|---|
| L1 | (existing) `tests/` directories | `.py` / `.test.ts` | `pytest` + `bun test` | CI runners |
| L2 | `specs/1979-plugin-dx-tui-integration/smoke-stdio.jsonl` | JSONL | `scripts/smoke-stdio.sh` | grep / jq |
| L3 | `specs/1979-plugin-dx-tui-integration/smoke-1979.txt` | text log (script(1) output) | `scripts/smoke-1979.expect` | grep / Codex review |
| L4 | `specs/1979-plugin-dx-tui-integration/smoke-1979.gif` | gif (vhs output) | `scripts/smoke-1979.tape` | human visual review |

L4 is gitignored (binary, > 1 MB risk per AGENTS.md). L2 + L3 are committed.

---

## L1 — Unit + integration tests

`tests/ipc/test_plugin_op_dispatch.py`:
- `test_install_request_dispatches_to_installer`
- `test_uninstall_request_dispatches_to_uninstaller`
- `test_list_request_emits_payload_only`
- `test_unknown_request_op_returns_error_frame`
- `test_consent_timeout_emits_complete_exit5`

`tests/ipc/test_consent_bridge.py`: 6 unit tests per data-model.md E2.

`tests/plugins/test_uninstall.py`:
- `test_uninstall_removes_install_dir`
- `test_uninstall_deregisters_tool`
- `test_uninstall_writes_consent_receipt`
- `test_uninstall_idempotent`

`tests/plugins/test_registry_inactive_set.py`:
- `test_set_active_filters_bm25`
- `test_set_active_filters_export_core_tools_openai`
- `test_register_starts_active`
- `test_set_active_unknown_tool_raises`

`tests/e2e/test_plugin_install_e2e.py`:
- `test_install_and_invoke_fixture_plugin`: installs a fixture plugin via dispatcher, sends a chat_request matching its search_hint, asserts `tool_use` for `plugin.<id>.<verb>` is emitted.

**SC-005 baseline parity**: existing 3458 + ~12 new tests = ~3470. `bun test` adds ~6 new tests under `tui/src/commands/plugins.test.ts` and `tui/src/components/plugins/PluginBrowser.test.tsx`.

---

## L2 — stdio JSONL probe (`scripts/smoke-stdio.sh`)

```bash
#!/usr/bin/env bash
# Sends raw plugin_op_request frames to the backend over stdio,
# captures the response stream as JSONL.

set -euo pipefail

OUTPUT="$(dirname "$0")/../smoke-stdio.jsonl"
FIXTURE_CATALOG="$(dirname "$0")/fixtures/catalog.json"

# Build a temp file:// catalog URL pointing at the fixture
export KOSMOS_PLUGIN_CATALOG_URL="file://$FIXTURE_CATALOG"
export KOSMOS_PLUGIN_SLSA_SKIP=true
export KOSMOS_ENV=development

# Start backend in stdio mode, pipe input, capture output
{
  # Frame 1: list before install (expect empty)
  echo '{"kind":"plugin_op","version":"1.0","session_id":"s1","correlation_id":"c1","ts":"2026-04-28T00:00:00Z","role":"tui","op":"request","request_op":"list"}'

  # Frame 2: install seoul-subway fixture
  echo '{"kind":"plugin_op","version":"1.0","session_id":"s1","correlation_id":"c2","ts":"2026-04-28T00:00:01Z","role":"tui","op":"request","request_op":"install","name":"seoul-subway","dry_run":false}'

  # Wait for permission_request, send response
  # (Simulated — production probe uses a small Python harness here)
  sleep 1
  echo '{"kind":"permission_response","version":"1.0","session_id":"s1","correlation_id":"c2-p1","ts":"2026-04-28T00:00:02Z","role":"tui","request_id":"<P>","decision":"allow_once"}'

  # Frame 3: list after install (expect 1 entry)
  echo '{"kind":"plugin_op","version":"1.0","session_id":"s1","correlation_id":"c3","ts":"2026-04-28T00:00:30Z","role":"tui","op":"request","request_op":"list"}'

  # Frame 4: chat_request with empty tools[] (let backend export new registry)
  echo '{"kind":"chat_request","version":"1.0","session_id":"s1","correlation_id":"c4","ts":"2026-04-28T00:00:35Z","role":"tui","tools":[],"messages":[{"role":"user","content":"강남역 다음 열차 언제?"}]}'

} | uv run python -m kosmos.cli --ipc stdio > "$OUTPUT"

# Validate
jq -c 'select(.kind == "plugin_op" and .op == "complete")' "$OUTPUT"
```

**Expected JSONL frames** (filtered by kind):

```
plugin_op:complete   # list-before, exit_code=0, empty body
plugin_op:progress   # phase 1 (📡)
plugin_op:progress   # phase 2 (📦)
plugin_op:progress   # phase 3 (🔐)
plugin_op:progress   # phase 4 (🧪)
permission_request   # consent prompt
plugin_op:progress   # phase 5 (📝)
plugin_op:progress   # phase 6 (🔄)
plugin_op:progress   # phase 7 (📜)
plugin_op:complete   # install success, exit_code=0, receipt_id=rcpt-...
plugin_op:complete   # list-after, exit_code=0, body has 1 entry (seoul-subway)
chat_request         # echo
assistant_chunk      # streamed model reply
tool_use             # plugin.seoul_subway.lookup invoked
permission_request   # gauntlet consent for the tool call
permission_response  # auto-allow in test rig
tool_result          # subway-arrival mock response
assistant_chunk      # final model reply citing the tool result
```

L2 grep markers (per FR-021):
- `plugin_op_progress.*phase=1` through `phase=7`
- `plugin_op_complete.*result="success"`
- `tool_use.*tool_id="plugin\.seoul_subway`
- `permission_response.*decision`

---

## L3 — expect/script text-log smoke

`scripts/smoke-1979.expect`:

```expect
#!/usr/bin/env expect -f
# Drives the TUI under PTY; captures full session as text log.

set timeout 60

# Use script(1) to capture the full PTY session
spawn script -q smoke-1979.txt bun run --cwd tui dev

# Wait for REPL prompt
expect "✻"

# Type the install command
send "/plugin install seoul-subway\r"

# Wait for consent prompt
expect "📝 동의 확인"
expect "⓵"  ;# Layer 1 green glyph

# Approve once
send "Y"

# Wait for install completion
expect "✓ 설치 완료"

# Ask the citizen question
send "강남역 다음 열차 언제?\r"

# Wait for tool use
expect "plugin.seoul_subway"

# Wait for response
expect "다음 열차"

# Test list browser
send "/plugins\r"
expect "KOSMOS 플러그인"
expect "seoul-subway"

# Test remove
send "r"
expect "제거하시겠습니까"
send "Y"
expect "(제거 중…)"
expect_eof
```

**L3 grep markers** (Codex/automated review verifiable):

```
$ grep -E '(📡|📦|🔐|🧪|📝|🔄|📜|✓ 설치 완료|plugin\.seoul_subway|⓵|⓶|⓷)' smoke-1979.txt
📡 카탈로그 조회 중…
📦 번들 다운로드 중…
🔐 SLSA 서명 검증 중…
🧪 매니페스트 검증 중…
📝 동의 확인…
⓵
🔄 등록 + BM25 색인 중…
📜 동의 영수증 기록 중…
✓ 설치 완료
plugin.seoul_subway.lookup
```

---

## L4 — vhs `.tape` visual demonstration

`scripts/smoke-1979.tape`:

```tape
Output specs/1979-plugin-dx-tui-integration/smoke-1979.gif
Set Width 1200
Set Height 600
Set FontFamily "JetBrains Mono"
Set Theme "Tokyo Night"

Type "bun run --cwd tui dev"
Enter
Sleep 2s

Type "/plugin install seoul-subway"
Enter
Sleep 8s

Type "Y"
Sleep 5s

Type "강남역 다음 열차 언제?"
Enter
Sleep 6s

Type "/plugins"
Enter
Sleep 2s

Escape
```

L4 produces `.gif` for human review only. Per memory `feedback_vhs_tui_smoke`, this is supplemental — never the primary verification source.

---

## Failure mode coverage

The E2E scenario MUST also cover negative paths. Add three additional expect scripts:

1. `smoke-1979-deny.expect` — citizen presses `N` → assert exit_code=5 in L2 + Korean error in L3.
2. `smoke-1979-bad-name.expect` — install non-existent plugin → exit_code=1 + catalog miss message.
3. `smoke-1979-revoke.expect` — install + ask question + revoke consent + ask same question → second invocation fail-closed.

These use the same fixture catalog with name variations.

---

## Run conditions

Local dev: `bash specs/1979-plugin-dx-tui-integration/scripts/run-e2e.sh` runs all 4 layers in sequence.

CI: matrix entry runs L1 + L2 + L3 only (L4 vhs requires display + recording infrastructure not present in headless CI). Local re-run produces L4 for human review on demand.

---

## Acceptance evidence

Each SC produces a specific artifact path:

| SC | Layer | Artifact | Verification |
|---|---|---|---|
| SC-001 (≤30s install) | L2 + L3 | timestamps in JSONL | jq parsing of phase 1 → phase 7 elapsed |
| SC-002 (≤3s tool inventory) | L2 | next chat_request after complete | jq filter |
| SC-003 (gauntlet routing) | L2 + L3 | permission_request + response frames | grep `permission_response.decision` |
| SC-004 (4-layer artifacts) | L1 + L2 + L3 + L4 | all 4 file paths exist | path existence check |
| SC-005 (baseline parity) | L1 | bun test + pytest output | exit code + count |
| SC-006 (zero deps) | (CI) | git diff `pyproject.toml` + `tui/package.json` | empty diff in dependency declarations |
| SC-007 (≤90 sub-issues) | (GraphQL) | post `/speckit-taskstoissues` | gh api graphql query |
| SC-008 (revocation 100%) | L1 + L3 | smoke-1979-revoke.expect | grep |
| SC-009 (concurrent ledger) | L1 | unit test with 5 concurrent installs | pytest |
| SC-010 (consent N → no state) | L1 + L3 | smoke-1979-deny.expect | filesystem absence check |

---

## Citations

- `docs/testing.md § TUI verification methodology` (4-layer ladder definition)
- memory `feedback_runtime_verification` + `feedback_vhs_tui_smoke`
- `specs/2152-system-prompt-redesign/` smoke artifacts pattern (precedent established post-#2152 merge)
- `specs/2112-dead-anthropic-models/smoke-scenario-*.png` (precedent for layered artifacts)
