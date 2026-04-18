# ADR-003: Bun + Ink + React TUI Stack

**Status**: Accepted
**Date**: 2026-04-19
**Epic**: #287 (KOSMOS TUI — Ink + React + Bun)

---

## Context

Spec 287 ports Claude Code 2.1.88's Ink + React terminal UI to the KOSMOS Korean
public-service domain.  The TUI must spawn the Python backend as a child process,
stream JSONL IPC frames over stdio, and render the 5-primitive result variants
defined by Spec 031.  Before any TUI code lands, FR-057 mandates an ADR that
explicitly approves the runtime + package manager + test-runner stack (SC-1 gate).

Three constraints shape the decision space:

1. **Claude Code reference fidelity**: The primary migration source is
   `.references/claude-code-sourcemap/restored-src/src/ink/` (29 reconciler
   files, Claude Code 2.1.88).  Diverging from Ink's React model loses upstream
   diff traceability (SC-9) and forces a complete re-implementation of the
   reconciler, layout engine, and rendering spine.

2. **IPC mechanism (FR-001)**: The TUI spawns the Python backend via `Bun.spawn`.
   oven-sh/bun#4670 confirms that `Bun.spawn` does not pass extra file descriptors
   beyond stdin, stdout, and stderr.  Any IPC mechanism that depends on socket
   handle passing or extra fds fails silently.  The entire IPC protocol must fit
   on three fds.

3. **AGENTS.md hard rule**: TypeScript is allowed only for the TUI layer (Ink +
   Bun).  No Go, no Rust.  Python stays on `uv + pyproject.toml`; no new Python
   runtime dependencies may be added for the IPC bridge.

Additional context documented in `specs/287-tui-ink-react-bun/research.md` § 2.1
and § 2.2 and `specs/287-tui-ink-react-bun/plan.md` § Technical Context.

---

## Decision

**Adopt the following TUI stack**, pinned in `tui/package.json`:

| Component | Version | License | Role |
|-----------|---------|---------|------|
| Bun | v1.2.x | MIT | Runtime + package manager + test runner |
| TypeScript | 5.6+ | Apache-2.0 | Language |
| Ink | 7.0.0 | MIT | Terminal React reconciler |
| React + react-dom | 19.2 | MIT | UI runtime (Ink 7 peer) |
| @inkjs/ui | 2.x | MIT | TextInput / Spinner / Select components |
| zod | 3.23 | MIT | Runtime IPC frame validation (belt-and-braces) |
| ink-testing-library | 4.x | MIT | Component unit tests |

**IPC mechanism**: `Bun.spawn` with newline-delimited JSON (JSONL) over
stdin/stdout/stderr only.  No extra fds.  No TCP listener.

**Key rationale**:

1. **Ink is Claude Code's production TUI framework**.  The 29 reconciler files in
   `restored-src/src/ink/` can be lifted with attribution headers, preserving
   rendering behaviour and upstream diff traceability.  The Gemini CLI
   (`.references/gemini-cli/packages/cli/`, Apache-2.0) provides a second
   structural reference for the hooks layer, theme system, and
   `overflowToBackbuffer` scroll pattern.

2. **Bun collapses three tools into one binary**.  Bun serves as the runtime,
   package manager, and test runner simultaneously.  A Node + pnpm + vitest setup
   achieves the same functional result but adds two extra tools to the developer
   and CI surface for no architectural benefit.

3. **`Bun.spawn` is mandated by FR-001**.  Because Bun's `spawn` implementation
   does not support extra fds (oven-sh/bun#4670), the IPC protocol is constrained
   to stdin (requests in), stdout (events out), and stderr (log + crash trace)
   from day one.  JSONL framing matches Claude Code's SSE streaming-chunk format
   (`restored-src/src/services/api/client.ts`), keeping the TUI rendering pipeline
   structurally upstream-identical.

4. **Ink 7 + Node 22 compatibility**.  Ink 7.0.0 requires React 19.2 and Node 22
   compatibility per the Ink releases changelog
   (https://github.com/vadimdemedes/ink/releases).  Bun v1.2.x provides a
   Node-22-compatible runtime through its built-in Node.js compatibility layer,
   satisfying this requirement without installing Node separately.

5. **License compatibility**.  All selected packages are MIT or Apache-2.0,
   compatible with KOSMOS's Apache-2.0 project license.

---

## Consequences

**Positive**:

- One binary (`bun`) handles `install`, `run`, and `test` in CI and local dev.
  Reduces the Docker image layer count and eliminates Node version matrix
  management.
- Ink 7's React 19.2 runtime enables `useSyncExternalStore` for streaming-chunk
  rendering without full list re-renders — directly lifting the pattern from
  `restored-src/src/components/`.
- JSONL over stdio requires no TCP listener, no port management, and no OS-level
  socket permissions.  The IPC bridge is debuggable with plain `cat`.
- `@inkjs/ui` 2.x ships the TextInput / Spinner / Select components that Claude
  Code uses in permission prompts, reducing the volume of KOSMOS-original
  component code.
- `zod` 3.23's `z.discriminatedUnion` gives exhaustive compile-time coverage of
  all 5-primitive return variants, enforcing FR-008's ban on string sniffing.

**Negative / Trade-offs**:

- **`Bun.spawn` extra-fd limitation (oven-sh/bun#4670)**: The IPC protocol is
  permanently constrained to three fds.  Protocols that rely on socket handle
  passing (e.g., Unix domain sockets passed via `SCM_RIGHTS`) are not available
  without spawning a separate socket listener from the Python side.  Accepted
  cost: JSONL over three fds is sufficient for the 100 ev/s soak target (FR-007).
- **Ink 7 fork-or-upstream IME split**: Ink's `useInput` cannot buffer Hangul
  composition on macOS + Linux IMEs (R1; Claude Code issues #3045/#22732/#22853/
  #27857/#29745).  The choice between (a) the `@jrichman/ink@6.6.9` fork and
  (b) a Node `readline` hybrid is deferred to a separate ADR
  (`docs/adr/ADR-004-korean-ime-strategy.md`) per FR-014.  Adopting option (a)
  would pin the reconciler to Ink 6.6.9 rather than 7.0.0; if that path is
  chosen, the version column above changes accordingly and this ADR is updated.
- **Bun Node-compat layer maturity**: Bun's Node.js compatibility is not 100%
  complete at v1.2.x.  Any Ink internal that relies on an unimplemented Node API
  will surface as a runtime error.  Risk is mitigated by the `bun test` suite
  exercising the reconciler against representative fixtures before any lift file
  ships.
- **`tui/` is a separate workspace**: `bun install` runs from `tui/`; `uv sync`
  runs from the repo root.  There is no monorepo orchestrator (no Turborepo/Nx).
  CI must invoke both commands explicitly.  This is the simplest dual-language
  setup; a top-level orchestrator may be added by a future ADR if needed.

**Neutral**:

- The `tui/bun.lockb` binary lockfile is committed per Bun conventions, analogous
  to `uv.lock`.
- Devtool dependencies (`pydantic-to-typescript` or `datamodel-code-generator`)
  are Python CLI tools invoked by `tui/scripts/gen-ipc-types.ts`; their output
  (`tui/src/ipc/frames.generated.ts`) is committed.  Neither is a runtime
  dependency of the TUI binary.

---

## Alternatives Rejected

### Node 22 + pnpm + vitest

**Rejected**.  Functional, but adds two additional tools (pnpm, vitest) to the
runtime and CI surface.  Bun collapses runtime + package manager + test runner
into one binary, which is sufficient reason to prefer it given that FR-001 already
mandates `Bun.spawn`.  The only scenario where this alternative becomes relevant
is if Bun's Node-compat layer fails to run a critical Ink 7 internal; in that
case, the fallback is to switch to Node 22 + pnpm + vitest, with no IPC protocol
change (JSONL over stdio remains).

### Raw Blessed / neo-blessed

**Rejected**.  No React model; diverges from Claude Code's architecture entirely.
Upstream diff traceability (SC-9) is impossible: there is no structural analog
between a Blessed `widget` tree and Ink's React reconciler.  The entire lift plan
would need to be replaced by a clean-room re-implementation.

### Deno

**Rejected**.  Supports JSX but Ink 7 compatibility with Deno's standard library
is unverified.  `useSyncExternalStore` interaction with Deno's event loop has no
public production reference.  Node-compat surface is narrower than Bun at the
time of writing.

### HTTP localhost + SSE (instead of stdio IPC)

**Rejected** for the IPC transport layer.  Keeps Claude Code's wire format
identical but adds a TCP listener, port management, and a new security surface
(loopback-only binding, port collision).  `Bun.spawn` over stdio avoids all of
that at no protocol-expressiveness cost for the target event rate.

---

## References

- `specs/287-tui-ink-react-bun/plan.md` § Technical Context — full dependency
  list, platform targets, performance goals, and IPC constraints
- `specs/287-tui-ink-react-bun/research.md` § 2.1 (TUI stack) and § 2.2 (IPC
  mechanism) — detailed rationale and alternative analysis
- `.references/claude-code-sourcemap/restored-src/src/ink/` — 29 reconciler files
  (Claude Code 2.1.88); primary lift source
- `.references/gemini-cli/packages/cli/` — Apache-2.0 Ink TUI; second structural
  reference for hooks, theme, `overflowToBackbuffer`
- Ink releases changelog — https://github.com/vadimdemedes/ink/releases
  (Node 22 + React 19.2 requirement per v7.0.0 notes)
- Bun spawn docs — https://bun.sh/docs/api/spawn
- oven-sh/bun#4670 — extra-fd limitation (IPC protocol must use stdin/stdout/stderr
  only)
- `AGENTS.md` — hard rule: "TypeScript is allowed only for the TUI layer (Ink + Bun)"
- `specs/287-tui-ink-react-bun/spec.md` § FR-057 (ADR gate blocks Phase 2+) and
  § SC-1 (stack decision complete before first commit of lift work)
