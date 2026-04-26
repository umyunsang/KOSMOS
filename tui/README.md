# KOSMOS TUI (Ink + Bun)

The terminal user interface for KOSMOS — a Korean public-service multi-agent harness ported from Claude Code 2.1.88 onto the FriendliAI/EXAONE backend.

## Stack

- **Runtime**: Bun v1.2.x (`bun.lock` pinned)
- **Language**: TypeScript 5.6+
- **UI**: [Ink](https://github.com/vadimdemedes/ink) (React for CLIs) + `@inkjs/ui`
- **Schemas**: Zod v3 for runtime validation
- **PDF rendering**: `pdf-to-img` (Apache-2.0, WASM) + `pdf-lib` (MIT) — citizen-facing PDF inline preview and `/export` assembly

## Running

```bash
bun install
bun run tui
```

## Slash commands (UI L2)

Citizen-facing surfaces from Spec 1635 P4 UI L2:

### Session
- `/onboarding` — restart 5-step onboarding from step 1
- `/onboarding <step>` — re-run a single step (`preflight | theme | pipa-consent | ministry-scope | terminal-setup`)
- `/lang ko|en` — switch language (Korean primary + English fallback)
- `/help` — show all commands grouped into Session / Permission / Tool / Storage

### Permission
- `/consent list` — list permission receipts in reverse-chronological order
- `/consent revoke rcpt-<id>` — revoke a previously granted receipt (idempotent)

### Tool
- `/agents` — show active ministry agent state (proposal-iv 5-state)
- `/agents --detail` — add SLA-remaining + health + rolling-avg response columns
- `/plugins` — open the plugin browser (Space toggle / `i` detail / `r` remove / `a` marketplace)

### Storage
- `/config` — open configuration overlay (`.env` secret editor isolated)
- `/export` — write PDF (transcript + tool invocations + consent receipts; OTEL + plugin-internal state excluded)
- `/history` — search past sessions with `--date FROM..TO`, `--session <id>`, `--layer <n>` filters (AND composition)

## Keybindings

UI L2 additions on top of the Spec 287/288 keybinding registry:

| Combo | Context | Action | FR |
|---|---|---|---|
| `Ctrl-O` | REPL | Toggle expand/collapse on long messages | FR-009 |
| `Shift+Tab` | REPL | Cycle permission mode (with `bypassPermissions` reinforcement) | FR-022 |
| `/` | REPL input | Open slash-command autocomplete dropdown | FR-014 |
| `Y` / `A` / `N` | Permission modal | Allow once / Allow session / Deny | FR-017 |
| `Space` / `i` / `r` / `a` | Plugin browser | Toggle / detail / remove / marketplace | FR-031 |

IME-safety: every input-mutating binding checks `!useKoreanIME().isComposing` before firing (`vision.md § Keyboard-shortcut migration`).

## Memdir paths

UI L2 owns two new USER-tier paths under `~/.kosmos/memdir/user/`:

- `onboarding/state.json` — resumable 5-step onboarding state (atomic-rename writes)
- `preferences/a11y.json` — four accessibility toggles (screen reader / large font / high contrast / reduced motion)

Other user-tier directories (`consent/`, `sessions/`, `ministry-scope/`) belong to Specs 027 / 033 / 035 and are accessed read-through.

## Testing

```bash
bun test                                     # full suite
bun test tests/components tests/commands     # UI L2 scoped
bunx tsc --noEmit -p tsconfig.typecheck.json # typecheck
```

## Reference porting source

`.references/claude-code-sourcemap/restored-src/src/` (Claude Code 2.1.88, research-use reconstruction). The migration target is ≥ 90% visual + structural fidelity per surface — see `docs/visual-fidelity/1635-scoring.md` for per-surface scoring.
