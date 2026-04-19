# TUI Documentation

This directory contains supplementary documentation for the KOSMOS TUI (Ink + React + Bun).

| File | Content |
|------|---------|
| `accessibility-checklist.md` | FR-055 keyboard-only navigation audit table + FR-056 screen-reader smoke plan |
| `cjk-width-known-issues.md` | ink#688 / ink#759 CJK width edge cases |
| `korean-ime.md` | Korean IME strategy, fallback instructions, known terminal incompatibilities |

---

## Quickstart Delta Log (T127)

Executed on: macOS Darwin 25.2.0, bun 1.3.12, Python 3.12+

Each step below corresponds to a numbered step in `specs/287-tui-ink-react-bun/quickstart.md`.

---

### Step 1 — Bootstrap the workspace

**Command run**: `uv sync` from repo root

**Result**: PASS. `uv sync` resolves all 142 packages with no changes (already locked).

**Command run**: `~/.bun/bin/bun install` from `tui/`

**Result**: PASS. `bun install v1.3.12` — "Checked 90 installs across 85 packages (no changes)".

**Command run**: `~/.bun/bin/bun scripts/gen-ipc-types.ts` from `tui/` (direct invocation — see delta below)

**Result**: PASS. Extracted 10 discriminator arms, compiled schema to TypeScript, written `tui/src/ipc/frames.generated.ts`.

**Deltas for Step 1**:

- **PATH delta**: The quickstart writes `bun install` and `bun run gen:ipc`. On this machine, `bun` is installed at `~/.bun/bin/bun` but is NOT on the `$PATH` available to `/bin/bash` (the shell used by `bun run` scripts). Any `bun run <script>` invocation that internally calls another `bun` command fails with `bun: command not found` (exit 127). Workaround: either add `~/.bun/bin` to `$PATH` in your shell profile (e.g., `export PATH="$HOME/.bun/bin:$PATH"` in `~/.zshrc`), or invoke `~/.bun/bin/bun` with the full path.

- **`bun run gen:ipc` vs direct invocation**: The `package.json` `gen:ipc` script is `bun run scripts/gen-ipc-types.ts`, which under `/bin/bash` fails as above. The script itself works correctly when called as `~/.bun/bin/bun scripts/gen-ipc-types.ts`.

- **IME fork gate**: The quickstart notes that if the IME ADR selected option (a), `bun install` will verify the ADR. The installed `package.json` pins `"ink": "npm:@jrichman/ink@6.6.9"`, confirming option (a) was chosen. The ADR gate ran without error.

---

### Step 2 — Run the TUI against a fixture backend (no live APIs)

**Command attempted**: `bun run tui:fixture specs/287-tui-ink-react-bun/../tests/fixtures/smoke/route-safety.jsonl` (per quickstart) / `~/.bun/bin/bun scripts/fixture-runner.ts tests/fixtures/smoke/route-safety.jsonl` (direct equivalent)

**Result**: FAIL — `scripts/fixture-runner.ts` does not exist.

```
error: Module not found "scripts/fixture-runner.ts"
```

The `tui/scripts/` directory contains only `diff-upstream.sh`, `gen-ipc-types.ts`, and `soak.ts`. The `fixture-runner.ts` script referenced by the `tui:fixture` npm script and by quickstart Step 2 has not been implemented.

The fixture file itself (`tui/tests/fixtures/smoke/route-safety.jsonl`) exists and is non-empty.

**Quickstart execution stopped here per T127 instructions** ("Stop after the first failing step and document it").

**Steps 3 through 10 were not executed.**

---

### Summary of deltas

| Step | Status | Delta |
|------|--------|-------|
| 1a — `uv sync` | PASS | None |
| 1b — `bun install` | PASS (with workaround) | `bun` must be invoked as `~/.bun/bin/bun`; not on `$PATH` in `/bin/bash` |
| 1c — `bun run gen:ipc` | PASS (with workaround) | Same PATH issue; use `~/.bun/bin/bun scripts/gen-ipc-types.ts` directly |
| 2 — `bun run tui:fixture` | FAIL | `scripts/fixture-runner.ts` does not exist; task T038 (create fixture-runner) appears incomplete |
| 3–10 | NOT EXECUTED | Blocked by Step 2 failure |

**Recommendations** (do not fix in this doc — these are findings for the implementation team):

- Add `~/.bun/bin` to the required PATH in the quickstart prerequisites section.
- Implement `tui/scripts/fixture-runner.ts` (referenced by T038 in tasks.md Phase 3) before the quickstart can be executed past Step 2.
- The `bun run` script wrapper in `package.json` inherits the shell's `$PATH`. If running in a CI environment or a non-interactive shell, ensure `bun` is on `$PATH` before invoking any `bun run *` scripts.
