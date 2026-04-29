# Contract — Smoke Checkpoint Protocol

**Spec**: [../spec.md](../spec.md) FR-016 / FR-017 · SC-001 / SC-002
**Data model**: [../data-model.md § E-4](../data-model.md)
**Reference**: AGENTS.md § TUI verification methodology Layers 2 + 4

---

## 1. Layer 2 — PTY expect smoke

### 1.1 Script location

`specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.expect`

### 1.2 Required behaviours

The expect script:

1. Spawns `bun run tui` from the worktree root with stdio attached to a pseudo-terminal.
2. Asserts the literal string `KOSMOS` appears in the boot output (the welcome banner).
3. Sends the citizen prompt `내 종합소득세 신고해줘\r` after a 2 s settling delay (allows session_id assignment + permission scaffold).
4. Polls the assistant_chunk stream for any text matching the regex `hometax-2026-\d{2}-\d{2}-RX-[A-Z0-9]{5}`.
5. On first match, emits the synthetic checkpoint string `CHECKPOINTreceipt token observed\n` to stdout.
6. Continues capturing for 5 s after the checkpoint to allow the LLM's full Korean response to land.
7. Sends double Ctrl-C (`\003\003`) to exit cleanly.
8. The captured pty session is teed to `specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt`.

### 1.3 Checkpoint emission rules

| Rule | Detail |
|---|---|
| **Exact byte sequence** | `CHECKPOINTreceipt token observed\n` — no leading whitespace, no ANSI codes, plain ASCII. |
| **De-duplication** | Emitted EXACTLY once per chain run. If the LLM cites the receipt twice, emit only on first detection. Implementation: use a script-local boolean flag set on first match. |
| **Timing** | The checkpoint MUST appear AFTER the receipt string but BEFORE script exit. |
| **Position in log** | The checkpoint line will be on its own line in the captured `.txt`; downstream grep tools rely on `grep -F` matching. |

### 1.4 Validation

```bash
test "$(grep -c -F 'CHECKPOINTreceipt token observed' \
  specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-pty.txt)" = "1"
```

Exit 0 = SC-002 passes. Exit non-zero (count = 0 OR count > 1) = fail.

### 1.5 Receipt regex source-of-truth

The receipt id format `hometax-YYYY-MM-DD-RX-[A-Z0-9]{5}` is produced by `mock_submit_module_hometax_taxreturn` per `specs/2296-ax-mock-adapters/data-model.md` (deterministic synthetic). The regex used in this contract:

```text
hometax-2026-\d{2}-\d{2}-RX-[A-Z0-9]{5}
```

The year `2026` is hardcoded — the smoke runs in 2026; if calendars roll, the year prefix updates in lockstep with the fixture (and a follow-up Spec adjusts both).

---

## 2. Layer 4 — vhs visual smoke

### 2.1 Script location

`specs/2298-system-prompt-rewrite/scripts/smoke-citizen-taxreturn.tape`

### 2.2 Required directives

The `.tape` file MUST contain:

```text
Output specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn.gif

Set Shell "bash"
Set FontSize 14
Set Width 1200
Set Height 700
Set TypingSpeed 50ms

Type "bun run tui"
Enter
Sleep 4s

# Keyframe 1 — boot+branding
Screenshot specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-1.png

Type "내 종합소득세 신고해줘"
Sleep 500ms

# Keyframe 2 — input-accepted (citizen prompt typed, just before Enter)
Screenshot specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-2.png

Enter
Sleep 12s

# Keyframe 3 — receipt rendered
Screenshot specs/2298-system-prompt-rewrite/smoke-citizen-taxreturn-keyframe-3.png

# Cleanup
Ctrl+C
Ctrl+C
Sleep 500ms
```

### 2.3 Keyframe assertions

| Keyframe | Expected visual content | Validation |
|---|---|---|
| `smoke-citizen-taxreturn-keyframe-1.png` | KOSMOS boot banner with `KOSMOS` brand text + UFO mascot + version line + (optional) onboarding hint. **No** input prompt activity yet. | Lead Opus Read-tool: must see the literal `KOSMOS` glyph rendered. |
| `smoke-citizen-taxreturn-keyframe-2.png` | Input area shows `내 종합소득세 신고해줘` (cursor visible, Enter NOT yet pressed). | Lead Opus Read-tool: must see the literal Korean string in the input field. |
| `smoke-citizen-taxreturn-keyframe-3.png` | Assistant response visible with `접수번호: hometax-2026-MM-DD-RX-XXXXX` cited (citation styling per `<output_style>`). | Lead Opus Read-tool: must see content matching regex `접수번호[:\s]+hometax-2026-\d{2}-\d{2}-RX-[A-Z0-9]{5}`. |

If keyframe 3 does not show a receipt id, SC-001 fails. The Sleep 12s before keyframe 3 is provisional — if the chain takes longer due to LLM latency, expand to 18s. Anything > 30s is a chain failure (TTL guard for the PTY smoke) and the rewrite is at fault.

### 2.4 vhs version requirement

vhs ≥ 0.11 (per AGENTS.md § Layer 4 — `Screenshot` directive). Verify via `vhs --version` before running.

### 2.5 Output artefacts (all committed to spec dir)

| File | Purpose |
|---|---|
| `smoke-citizen-taxreturn.gif` | Animated record of the full session — companion artefact per AGENTS.md § Layer 4 |
| `smoke-citizen-taxreturn-keyframe-1.png` | Keyframe 1 (boot) |
| `smoke-citizen-taxreturn-keyframe-2.png` | Keyframe 2 (input-accepted) |
| `smoke-citizen-taxreturn-keyframe-3.png` | Keyframe 3 (receipt rendered) |

The PR description MUST cite all 5 files (gif + 3 PNGs + the PTY .txt) per AGENTS.md § PR rule.

---

## 3. Failure Modes

| Mode | Detection | Recovery |
|---|---|---|
| TUI does not boot | Layer 2 expect timeout on `KOSMOS` banner | Investigate `bun run tui` independently; not a smoke fix |
| LLM emits no `verify` call | Layer 2 captures session but no receipt → checkpoint missing | Prompt regression — re-examine `<verify_chain_pattern>` content |
| Mock backend not registered | `mock_submit_module_hometax_taxreturn` returns error | Fix Epic ε breakage; not Epic η scope |
| vhs `Screenshot` directive unsupported | `vhs <tape>` errors at parse | Upgrade vhs to ≥ 0.11 |
| Keyframe 3 shows spinner | LLM still thinking → Sleep duration too short OR LLM regression | Extend Sleep to 18s; if still spinner, the rewrite did not reach the citizen — debug |
| Receipt id not in keyframe 3 (LLM omitted citation) | Lead Opus Read-tool inspection fails SC-001 | The rewritten prompt's `<output_style>` citation rule may be too weak; strengthen citation requirement |

## 4. Re-Run Cost

A full Layer 4 vhs run takes ~25 s wall-clock (4 s boot + 12 s chain + 9 s buffer). A full Layer 2 PTY run takes ~20 s. Both are committed to the smoke flow as part of Phase 5 acceptance — Lead Opus runs them at least once before push and re-runs after any prompt edit.

**Optimization**: `Sleep 12s` at keyframe 3 is the bottleneck. If the LLM is slower than 12s in CI, extend to 18s; do NOT shorten below 12s — chain success is the only acceptable signal.
