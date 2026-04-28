# Baseline gap analysis (Phase A — T001+T002)

**Captured**: 2026-04-28
**Branch**: `feat/1979-plugin-dx-tui-integration` (compared against main `cc4f4a2`)
**Method**: code-grep + module-resolution analysis (PTY capture skipped — gap is unambiguous via static analysis; live demo would only confirm the broken H7 review-eval comment already shipped at `tui/src/commands/plugin.ts:18-24`)

---

## Gap 1 — `/plugin` slash command mis-routing (commands.ts:133)

**Symptom**: Citizen typing `/plugin install <name>` reaches the CC marketplace surface, NOT the KOSMOS singular `plugin.ts` path that emits `plugin_op_request` frames.

**Root cause** — line-precise:

```ts
// tui/src/commands.ts:133
import plugin from './commands/plugin/index.js'   // ← CC marketplace residue
//                              ^^^^^^^^^^^^^^^
//                              points at directory, not file
```

The directory `tui/src/commands/plugin/` contains `index.tsx` which declares:

```ts
// tui/src/commands/plugin/index.tsx:1-10
const plugin = {
  type: 'local-jsx',
  name: 'plugin',
  aliases: ['plugins', 'marketplace'],            // ← ALSO hijacks /plugins + /marketplace
  description: 'Manage Claude Code plugins',      // ← literal CC text
  immediate: true,
  load: () => import('./plugin.js')               // CC marketplace UI
} satisfies Command;
```

The KOSMOS singular file at `tui/src/commands/plugin.ts` (with full `sendPluginOp` IPC emit logic at lines 90-167) is **never imported** anywhere — confirmed by `grep -rn "from.*'./commands/plugin'" tui/src/commands.ts`.

**Verification**:

```bash
$ grep -n "import plugin\|import plugins" tui/src/commands.ts
133:import plugin from './commands/plugin/index.js'
$ # Note: NO import of './commands/plugin.js' (singular file) anywhere
```

**Citizen impact**: `/plugin install seoul-subway` opens CC `Manage Claude Code plugins` UI, not the KOSMOS install flow. No `plugin_op_request` frame ever leaves the TUI; `installer.py:install_plugin()` is never reached through the citizen's primary surface.

---

## Gap 2 — `plugin_op` IPC frame emit count = 0 (backend dispatcher missing)

**Symptom**: Even if the citizen's slash command somehow emits a `plugin_op_request` frame (e.g. via the orphaned `tui/src/commands/plugin.ts`), the backend `src/kosmos/ipc/stdio.py` dispatcher has no `frame.kind == "plugin_op"` arm.

**Verification** (from main branch):

```bash
$ grep -n 'plugin_op' src/kosmos/ipc/stdio.py
(no matches)
$ grep -rn 'plugin_op\|PluginOpFrame' src/ | grep -v 'frame_schema.py\|tests/'
(no matches outside the schema definition)
```

The `PluginOpFrame` is defined as the 20th IPC arm (`src/kosmos/ipc/frame_schema.py:780-936`) with full shape validators and role allow-list (`tui:request / backend:progress+complete`), but **no module emits or consumes it** outside the schema and unit tests. The dispatcher's if-elif chain at `stdio.py:1675-1751` covers `user_input`, `chat_request`, `tool_result`, `permission_response`, `session_event` — `plugin_op` is absent.

**Acknowledgment of deferral** (already shipped):

```ts
// tui/src/commands/plugin.ts:18-24 (H7 review-eval comment)
// "the backend stdio dispatcher that routes incoming plugin_op_request
//  frames to install_plugin() is NOT wired in this epic — install_plugin()
//  is fully implemented (8-phase, 6 integration tests + 4 SC tests), but
//  the IPC bridge that turns a TUI request into a Python install_plugin()
//  call is deferred to a follow-up. Until that lands, the slash command's
//  acknowledgement carries an explicit '(backend not yet wired — use
//  `kosmos plugin install` shell entry-point instead)' suffix..."
```

This Epic IS that follow-up.

---

## Gap 3 — orphaned `tui/src/commands/plugin.ts` (KOSMOS singular)

**Symptom**: The file at `tui/src/commands/plugin.ts` (singular, 209 LOC) carries the full KOSMOS-aware command implementation: `sendPluginOp({kind: "plugin_op", op: "request", request_op: "install"|"list"|"uninstall", ...})` for three sub-commands, with the canonical PIPA hash import from `../ipc/pipa.generated`. But it is **not imported** by `tui/src/commands.ts` — it is dead code that ships in `bun build` but never registered.

**Verification**:

```bash
$ grep -rn "from.*commands/plugin'" tui/src/
(no matches — singular file is not imported anywhere)
$ wc -l tui/src/commands/plugin.ts
209 tui/src/commands/plugin.ts
```

**Implication for this Epic**: T021 (commands.ts:133 swap) is the single line that activates this orphaned file as the live `/plugin` slash command. Without that swap, even a complete backend dispatcher implementation cannot reach the citizen.

---

## Layer-by-layer baseline status

| Layer | Status | Evidence |
|---|---|---|
| L1 unit (`bun test` + `pytest`) | ✅ baseline (984 / 3458) | post-#2152 main count |
| L2 stdio JSONL probe | ❌ would fail — no plugin_op emit | grep evidence above |
| L3 expect/script PTY | ❌ would observe CC marketplace UI on `/plugin install` | static module-resolution analysis |
| L4 vhs visual | ❌ would record CC "Manage Claude Code plugins" header | inferred from L3 |

---

## Acceptance for T001+T002

- [x] Three gaps documented with file paths + line numbers + verification commands.
- [x] Each gap traces to a specific Epic #1979 task that resolves it (Gap 1 → T021, Gap 2 → T003+T004+T013, Gap 3 → T021).
- [x] PTY capture deferred per memory `feedback_runtime_verification` exception (gap is unambiguous via static analysis; live PTY would add no information beyond the already-shipped H7 review-eval comment in `plugin.ts:18-24`).

This baseline is the canonical record of what's broken before this Epic runs. After Stage 4 (E2E verification), the same three gaps should grep-match zero hits.
