# B1 root cause trace — Spec 1978 T003

**Status**: in-progress (Phase 2 mid-execution)
**Date**: 2026-04-27
**Author**: implementation track
**Memory**: `feedback_runtime_verification` requires PTY-driven evidence; this document captures what PTY actually showed.

## Original B1 hypothesis (per Epic #1978 issue body)

> "TUI 입력 미반응 (별개 버그): PTY 재현 결과 — TUI 부팅 OK + 텍스트 타이핑 OK, **Enter 후 25초 응답 0 byte**, IPC frame 송신 자체가 안 일어남. PromptInput.onSubmit 가드 swallow 위치 미확정 (KOSMOS_TUI_LOG_LEVEL=DEBUG stderr 분리 캡처 필요)."

## What was actually observed in the worktree (2026-04-27 ~03:50 KST)

When the new `scripts/pty-scenario.py` harness (T001) is run against the `feat/1978-tui-kexaone-wiring` worktree, the TUI **fails to boot at all** — exit code 1 within 600 ms — well before any Enter-keystroke scenario can be reproduced.

This is a **worktree environment regression**, not the original Enter-suppression bug. Two layers stacked:

### Layer 1 — `.gitignore` over-broad pattern hides P0 auto-stub files

`.gitignore:17` contains the bare pattern `env/`, intended for Python virtualenv directories. It also matches `tui/src/commands/env/`, which is the location of the Spec 1632 P0 auto-stub:

```
// [P0 auto-stub · CC 2.1.88 sourcemap reconstruction gap]
// The CC sourcemap reconstruction does not include the original implementation
// of this module; consumers are satisfied with a minimal symbol shape so
// `bun run src/main.tsx` can reach the splash render. Real implementation is
// tracked for recovery in Epic #1633 (dead code elimination may remove callers
// entirely).
```

These auto-stubs exist on disk in the main `KOSMOS/` checkout but are never committed because they are matched by `.gitignore`. A fresh worktree under `git worktree add` therefore lacks them, and `import env from './commands/env/index.js'` (`tui/src/commands.ts:169`) throws `Cannot find module`.

The same `.gitignore` rule hides **45 P0-stub files** total under `tui/src/`, `src/kosmos/`, and `scripts/`. Categories (sample):

- `tui/src/commands/{assistant,login,env}/*` (CC reconstruction gap fillers)
- `tui/src/services/api/{claude,client}.ts` (Anthropic SDK shells — to be collapsed in Epic #1978 Phase B)
- `tui/src/services/analytics/*` (datadog/firstParty stubs)
- `tui/src/remote/*` (CC remote-session shells)
- `tui/src/services/policyLimits/*`, `services/contextCollapse/index.ts`, etc.

These were copied from `KOSMOS/` into `KOSMOS-wiring/` mid-trace (411 files including Python `__pycache__` artefacts). The `Cannot find module` error went away.

**Recommendation (in scope of this Epic)**: tighten `.gitignore` line 17 to anchor `env/` so only top-level Python venvs match (e.g., `/env/` or `^env/$`). Commit P0 auto-stubs explicitly under their `// [P0 auto-stub ...]` header so `git worktree add` produces a runnable copy. Defer to a follow-up commit on this Epic's branch — pre-Phase 7 is the right time to land it (low risk, narrow surface).

### Layer 2 — `bun run tui` does not pass TTY-ness through to the child

After Layer 1 was patched, `python scripts/pty-scenario.py greeting` still fails:

- Exit 1 within 1015 ms
- stdout captures only ANSI escape sequences and `[31merror[0m[2m:[0m script "tui" exited with code 1`
- The actual TUI banner (`KOSMOS v…`) is never printed

Direct invocation outside the PTY harness shows the underlying error from `tui/src/cli/print.ts:783`:

```
Error: Input must be provided either through stdin or as a prompt argument when using --print
```

This points to `tui/src/main.tsx:396`:

```typescript
const isNonInteractive = hasPrintFlag || hasInitOnlyFlag || hasSdkUrl || !process.stdout.isTTY;
```

Inside `bun run tui`, the `bun run` wrapper invokes `bun run src/main.tsx` as a child process whose `process.stdout.isTTY` is **false** (run wrapper does not inherit the TTY). `isNonInteractive` therefore evaluates to `true`, the entrypoint takes the non-interactive `--print` branch, and the lack of a prompt argument trips the error at `print.ts:783`.

The PTY harness at T001 was patched to invoke `bun src/main.tsx` directly (skipping `bun run`). That **does** preserve TTY semantics on every fd, but the new run still terminates inside 600 ms with no banner. As of trace time, the second-layer cause is still under investigation — likely a different early-exit branch reached because some module-level condition (env var, file-system check, telemetry init) differs between the user's interactive shell and the PTY harness's environment.

## Why the original B1 ("Enter swallow") cannot be reproduced yet

Layer 1 + Layer 2 together prevent `bun run tui` from surviving long enough to render `PromptInput`. Until both layers are cleared, the original `PromptInput.onSubmit` guard hypothesis is unverifiable — a citizen who manages to launch the TUI on an interactive shell sees the banner, but a programmatic harness does not. This means the user's manual demo (`bun run tui` from a real terminal) and the harness rehearsal are **not currently equivalent**, contrary to memory `feedback_runtime_verification`'s premise.

## What this changes for Phase 2 / 7

T003 was scoped as "PromptInput guard identification". Reality is two prerequisite cleanup tasks plus the original guard work:

1. **Pre-Phase-2.5 cleanup** (NEW, in this Epic):
   - Patch `.gitignore:17` to narrow the `env/` rule.
   - Commit the 45 P0 auto-stubs under proper headers.
   - Verify `git worktree add` produces a runnable tree without manual file copying.
2. **Layer-2 PTY environment parity** (NEW, in this Epic):
   - Reach a clean banner render under `python scripts/pty-scenario.py greeting`.
   - Identify which `main.tsx` early-exit branch fires under the PTY (likely env-var or fs probe). Patch or feed the missing input.
3. **Original B1 guard identification** (T003 as originally scoped):
   - With banner rendering reliable, send an Enter keystroke after typing a UTF-8 message.
   - Capture which guard in `tui/src/components/PromptInput/PromptInput.tsx:984-1100` swallows the submit. Document file:line.
4. **T004 patch**: align that guard with CC original (`.references/claude-code-sourcemap/restored-src/src/components/PromptInput/PromptInput.tsx`); fidelity ≥ 99%.

## Phase 2 status checkpoint

| Task | Status | Notes |
|---|---|---|
| T001 — PTY harness skeleton | ✅ done | `scripts/pty-scenario.py` lands with 5 subcommand stubs |
| T002 — `_log` stderr-only guard | ✅ done | `tui/src/ipc/bridge.ts:199` annotation strengthened with Spec 1978 reference |
| T003 — B1 root cause trace | ⚠ partial — this document | Two new prerequisite layers identified; original guard still pending |
| T004 — guard patch | ⏸ blocked on T003 layer 1 + 2 | |

## Recommended path forward

Two equally-valid options:

- **Option Tight** — add 2 micro-tasks (`T003a .gitignore + P0 auto-stub commit` and `T003b PTY env parity`) to this Epic before resuming the original T003. Stays within sub-issue 100-cap (84 → 86 → 88, still ≤ 90).
- **Option Lift** — promote the worktree-environment regression to a sibling Epic (or attach to Initiative #1631 directly as a non-Epic standalone tracking issue). This Epic stays 86 tasks; the new work is tracked separately as a known prerequisite. Cleaner ownership boundary; slower wall-clock to demo readiness.

Option Tight is recommended because both layers are root-cause-adjacent to Epic #1978's stated mission ("TUI ↔ K-EXAONE wiring closure"). A worktree that cannot boot the TUI cannot prove any wiring claim. Sub-issue 100-cap can absorb the +2 micro-tasks.

Awaiting user direction before resuming Phase 2.
