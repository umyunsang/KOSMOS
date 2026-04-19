# ADR-004: Claude Code Sourcemap Port Policy — Research-Use Attribution and Diff Tracking

**Status**: Accepted
**Date**: 2026-04-19
**Epic**: #287 (KOSMOS TUI — Ink + React + Bun)

---

## Context

KOSMOS Spec 287 lifts approximately 120 TypeScript files from
`.references/claude-code-sourcemap/restored-src/` (a reconstructed approximation
of Claude Code 2.1.88 source) into `tui/src/`. The reconstructed source is
not an official release; it is a research artifact used under research-use
terms, with attribution to Anthropic.

Three questions require a recorded decision before any lift begins:

1. **Legal basis**: On what grounds are files from the reconstructed source
   incorporated into KOSMOS source?
2. **Scope**: Which directories are lifted verbatim, and which are
   KOSMOS-original?
3. **Compliance enforcement**: How does CI prevent unattributed lifts from
   landing on `main`?

Without a recorded policy, any future reviewer — or an automated gate — has no
basis for accepting or rejecting a lift PR. FR-057 in Spec 287 designates this
ADR as the single approval point for the port approach.

**Contrast case — Gemini CLI**: `.references/gemini-cli/` (Apache-2.0) is also
used as a reference. Gemini CLI carries an explicit Apache-2.0 NOTICE; its
components can be adapted directly under that license with standard attribution.
The Claude Code reconstructed source has a different posture: it is research-use
only. The two references require separate attribution treatment. This ADR covers
only the Claude Code reconstructed source; Gemini CLI attribution is handled
under its Apache-2.0 license in the standard `tui/NOTICE` section.

**References that motivated this decision**:

- `specs/287-tui-ink-react-bun/research.md § 2.10` — decision rationale
  for the header + NOTICE + diff script compliance surface
- `specs/287-tui-ink-react-bun/plan.md § Constitution Check I + II` —
  confirms reference-driven development and fail-closed security gates
- `AGENTS.md` hard rules: TypeScript is allowed only in the TUI layer;
  source text must be English; no file > 1 MB committed without approval
- Spec 287 FR-011 (attribution header on every lifted file), FR-012 (NOTICE
  file), FR-013 (diff-script tracking gate), SC-9 (100% header compliance
  in CI)

---

## Decision

### 1. Research-use legal basis

KOSMOS is a student portfolio project (not a commercial competing product)
and does not redistribute the reconstructed source as a standalone library.
The use is research and educational. All lifted files carry an explicit
attribution header that identifies the original source path and the
Claude Code version. Attribution goes to Anthropic.

This is not a grant of license. The lifted files remain subject to whatever
rights Anthropic holds in the original work. The research-use framing is an
interpretive position that the non-commercial, educational use of
reconstructed source for a student portfolio project falls within fair-use
research practice in the relevant jurisdictions. Any future commercialisation
of KOSMOS would require a separate legal review of the lifted files.

### 2. Attribution header (FR-011)

Every file lifted from `.references/claude-code-sourcemap/restored-src/` MUST
carry the following header as the first line of the file, before any imports:

```ts
// Source: .references/claude-code-sourcemap/restored-src/<original-path> (Claude Code 2.1.88, research-use)
```

`<original-path>` is the relative path within `restored-src/` that corresponds
to the file. Example:

```ts
// Source: .references/claude-code-sourcemap/restored-src/src/ink/reconciler.ts (Claude Code 2.1.88, research-use)
```

The header must be retained verbatim through all subsequent edits. If a lifted
file is substantially rewritten such that less than 20% of the original content
remains, the maintainer may convert it to a KOSMOS-original file by removing
the header and adding a code comment noting the original inspiration; this must
be recorded in the PR description.

### 3. Scope of the port

**Lifted directories** (carry FR-011 attribution header):

| Target path | Source in restored-src/ | Purpose |
|---|---|---|
| `tui/src/ink/` | `src/ink/` (~29 files) | Ink reconciler, layout engine, renderer |
| `tui/src/commands/` | `src/commands/` (subset: registry, dispatcher, /save, /sessions, /resume, /new) | Command dispatcher registry shape |
| `tui/src/theme/` | `src/theme.ts` and related | ThemeToken named set, three built-in themes |
| `tui/src/components/coordinator/` | `src/components/ToolPermission*.tsx`, coordinator components | Permission-gauntlet modal, coordinator status |
| `tui/src/components/conversation/VirtualizedList.tsx` | `src/components/VirtualizedList.tsx` | Virtualized message list |
| `tui/src/hooks/` (selected) | `src/hooks/` (useSyncExternalStore shim, useKeybindings) | Store + keybinding hooks |

**KOSMOS-original directories** (no attribution header; do not touch):

| Target path | Replaces upstream | Rationale |
|---|---|---|
| `tui/src/ipc/` | `src/services/api/` | JSONL-over-stdio bridge to `uv run kosmos-backend --ipc stdio`; upstream is Anthropic REST; incompatible surface |
| `tui/src/components/primitive/` | `src/tools/*` developer renderers | Spec 031 five-primitive return variants; Korean public API domain; not derived from upstream |
| `tui/src/i18n/` | N/A (upstream has none) | Bilingual command copy (Korean/English); fully original |

Files in KOSMOS-original directories MUST NOT carry the FR-011 header. If a
KOSMOS-original file happens to contain logic adapted from an upstream file,
the adaptation must be documented in a comment inside the file but the FR-011
header format is reserved exclusively for lifted files.

### 4. NOTICE file (FR-012)

`tui/NOTICE` MUST declare:

- That the `tui/src/ink/`, `tui/src/commands/`, `tui/src/theme/`,
  `tui/src/components/coordinator/`, and selected `tui/src/hooks/` files are
  derived from reconstructed Claude Code 2.1.88 source, used for research
  purposes.
- Attribution: "Claude Code is a product of Anthropic, PBC. Claude Code source
  is copyright Anthropic."
- That `.references/gemini-cli/` components are used under the Apache-2.0
  license; that license's NOTICE requirements are satisfied separately.
- That all remaining `tui/src/` code is original KOSMOS work under the
  project's Apache-2.0 license.

The NOTICE file must be updated whenever a new lifted directory is added.

### 5. Diff-tracking CI gate (FR-013, SC-9)

`tui/scripts/diff-upstream.sh` MUST be executed on every PR that touches any
file inside the lifted directories listed in Section 3. The script performs two
checks:

1. **Header presence check**: asserts that every `.ts` and `.tsx` file under
   `tui/src/ink/`, `tui/src/commands/`, `tui/src/theme/`,
   `tui/src/components/coordinator/`,
   `tui/src/components/conversation/VirtualizedList.tsx`, and
   `tui/src/hooks/useKeybindings.ts` + `tui/src/hooks/useIPC.ts` (the two
   lifted hooks) contains the string `(Claude Code 2.1.88, research-use)` in
   the first line. A file that fails this check causes a non-zero exit.

2. **Source path traceability check**: for each lifted file, asserts that the
   path embedded in the header (`restored-src/<original-path>`) exists under
   `.references/claude-code-sourcemap/`. If the restored-src file has been
   deleted or the path has changed, the script logs a `STALE-SOURCE` warning
   but does not fail the build (the restored-src may be updated separately).

The CI job name is `attribution-gate` and runs on `pull_request` events. A PR
that touches a lifted file and has any header-presence failure MUST NOT be
merged. Maintainers may not bypass this gate by adding the
`copilot-review-bypass` label; the gate is deterministic, not reviewer-driven.

A reviewer MAY reject a PR that lifts a new file from `restored-src/` if the
file is missing the attribution header, even if CI passes (i.e., even if the
file is outside the directories enumerated in the script's header-presence
check). Section 3 of this ADR is the authoritative list; the script must be
updated in the same PR whenever a new lifted directory is added.

---

## Consequences

**Positive:**

- Every lifted file is traceable to its source via the FR-011 header. A single
  `grep` locates all ported files: `grep -r "Claude Code 2.1.88, research-use"
  tui/src/`.
- The `tui/NOTICE` file satisfies the research-use attribution requirement
  without requiring maintainers to remember which files are lifted.
- The CI `attribution-gate` catches unattributed lifts at PR time, not at
  audit time — the cost of a missing header is a CI failure, not a legal
  discovery.
- KOSMOS-original directories (`tui/src/ipc/`, `tui/src/components/primitive/`,
  `tui/src/i18n/`) have a clear identity: no upstream entanglement, no
  attribution confusion.
- The boundary between "lifted" and "original" maps directly to KOSMOS's
  architectural boundary: the rendering spine is upstream-derived; the
  transport and domain-rendering layers are KOSMOS-original.

**Negative / Trade-offs:**

- Any future commercialisation of KOSMOS requires a dedicated legal review
  of the lifted files. The research-use framing provides no guarantee beyond
  the educational/portfolio use case.
- Maintaining `tui/scripts/diff-upstream.sh` is an ongoing obligation: if a
  new lifted directory is added without updating the script, the gate silently
  fails to cover the new directory.
- The FR-011 header is permanent: a substantially rewritten file that was once
  a lift requires a deliberate PR action (remove header, add inspiration
  comment) to be reclassified as KOSMOS-original. There is no automated check
  for "substantially rewritten" — this relies on maintainer judgment.
- Pinning to Claude Code 2.1.88 means that upstream improvements (bug fixes,
  performance improvements) in the Ink reconciler are not automatically
  available. The `diff-upstream.sh` stale-source warning is the signal to
  consider backporting.

---

## Alternatives Rejected

- **Separate lift-manifest file** (a YAML listing every lifted file): Rejected
  because it splits the attribution from the code. A file could be lifted and
  then its header removed without updating the manifest; the manifest-first
  approach has a higher drift risk than the header-first approach.
- **No attribution, treat lift as clean-room**: Rejected. The
  `restored-src/README.md` makes clear this is a research reconstruction, not
  a clean-room reimplementation. Treating it as such would be factually
  incorrect and legally unsafe. Violates SC-9 explicitly.
- **Rewrite all lifted files from scratch to avoid research-use concerns**:
  Rejected because (a) it would take significantly longer with no architectural
  benefit, and (b) the resulting "clean" files would still be structurally
  derived from Claude Code's design, raising the same questions without the
  honest attribution that this ADR establishes.

---

## References

- `specs/287-tui-ink-react-bun/research.md § 2.10` — reference ledger entry
  for FR-011/012/013 decision
- `specs/287-tui-ink-react-bun/plan.md § Constitution Check I + II`
- `AGENTS.md` — hard rules (TypeScript TUI layer only; source text English;
  no file > 1 MB)
- `.references/claude-code-sourcemap/` — reconstructed Claude Code 2.1.88
  source (research-use)
- `.references/gemini-cli/` — Apache-2.0 contrast case
- Spec 287 FR-011 — attribution header on every lifted file
- Spec 287 FR-012 — `tui/NOTICE` declaring research-use reconstruction
- Spec 287 FR-013 — `tui/scripts/diff-upstream.sh` CI gate
- Spec 287 SC-9 — 100% attribution compliance enforced in CI on every PR
