# Contract: `scripts/llm_swap_parity_audit.sh`

**Type**: POSIX shell CLI
**Status**: scaffold (Phase 1 deliverable; full implementation during /speckit-implement)
**Spec FR**: FR-004 (CI gate); FR-005 (citation verification); FR-006 (byte-copy SHA verification)

## Invocation

```sh
scripts/llm_swap_parity_audit.sh [--json] [--strict] [--verbose]
```

| Flag | Effect |
|---|---|
| `--json` | Emit ParityAuditOutcome as JSON to stdout (data-model E-4 schema). Default is human-readable Markdown. |
| `--strict` | Exit 1 on any warning (e.g., a swap commit with missing `Refs:` line, even if category prefix is correct). Default exits 1 only on hard failure. |
| `--verbose` | Print every SwapCommit's classification + every StreamEventChannel match. |

## Required environment

- `git` (for commit walking)
- `sha256sum` (Linux) or `shasum -a 256` (macOS) — script auto-detects
- `find`, `grep`, `awk`, `sort` — POSIX standard

No new runtime dependencies (spec FR-012).

## Stdout format (default Markdown)

```text
## LLM Swap-Surface Parity Audit

**Branch**: 2521-llm-swap-cc-rebuild
**Run**: 2026-05-01T12:34:56Z

### Per-file outcomes

| KOSMOS file | Procedure | Byte-copy SHA match | Swap commits | Unjustified hunks | Missing citations |
|---|---|---|---|---|---|
| tui/src/services/api/claude.ts | A | ✅ | 12 | 0 | n/a |
| tui/src/ipc/llmClient.ts | B | n/a | 4 | 0 | 0 |
| src/kosmos/llm/client.py | B | n/a | 8 | 0 | 0 |
| src/kosmos/ipc/stdio.py | B | n/a | 6 | 0 | 0 |

### Stream-event channel coverage (CC services/api/claude.ts:1980-2295)

| CC event | KOSMOS handler | Status |
|---|---|---|
| message_start (1980) | claude.ts:1980 | ✅ byte-copied |
| content_block_start text (2019) | claude.ts:2019 | ✅ byte-copied |
| content_block_start thinking (2030) | claude.ts:2030 | ✅ byte-copied |
| content_block_start tool_use (1997) | claude.ts:1997 | ✅ byte-copied |
| content_block_start server_tool_use (2003) | (skipped) | ⏭ KOSMOS-N/A: server-side tools not used |
| content_block_delta text_delta (2113) | claude.ts:2113 | ✅ byte-copied |
| content_block_delta thinking_delta (2148) | claude.ts:2148 | ✅ byte-copied |
| content_block_delta signature_delta (2127) | (skipped) | ⏭ KOSMOS-N/A: K-EXAONE does not emit signatures |
| ...

### Summary

**Result**: ✅ PASS
**Total swap commits**: 30
**Drift events (unjustified hunks)**: 0
**Missing CC citations**: 0
```

## Stdout format (`--json`)

```json
{
  "run_timestamp": "2026-05-01T12:34:56Z",
  "branch": "2521-llm-swap-cc-rebuild",
  "per_file": [
    {
      "kosmos_path": "tui/src/services/api/claude.ts",
      "procedure": "A",
      "byte_copy_sha_match": true,
      "swap_commit_count": 12,
      "unjustified_hunk_count": 0,
      "missing_cc_citation_count": 0
    }
  ],
  "unjustified_hunks": [],
  "missing_cc_citations": [],
  "stream_channel_coverage": [
    {
      "cc_event_path": "services/api/claude.ts:2148:thinking_delta",
      "cc_event_kind": "content_block_delta",
      "cc_event_subtype": "thinking_delta",
      "kosmos_handler_path": "tui/src/services/api/claude.ts:2148",
      "kosmos_skip_reason": null,
      "byte_copied": true
    }
  ],
  "exit_code": 0
}
```

## Exit codes

| Code | Meaning | Conditions |
|---|---|---|
| 0 | PASS | All per-file outcomes pass; no unjustified hunks; no missing citations |
| 1 | DRIFT | Any unjustified hunk found OR byte-copy SHA mismatch OR missing citation OR (with `--strict`) any warning |
| 2 | TOOL ERROR | Required binary not found (e.g., sha256sum) OR git not in repo |
| 78 | CONFIG ERROR | EX_CONFIG — script invoked from wrong directory or branch state malformed |

## Algorithm (high level)

1. Resolve repo root (`git rev-parse --show-toplevel`); cd there.
2. Resolve current branch.
3. For each KOSMOSTargetFile (parsed from `parity-matrix.md`):
   a. If `procedure=A`: compute `sha256sum <kosmos_path>` AT byte-copy commit (parsed from git log subject `byte-copy(2521): import CC <cc_source_path>`); compare with `sha256sum <cc_source_path>`. Mismatch → mark `byte_copy_sha_match=false`.
   b. For each commit between byte-copy and HEAD touching this file: parse subject for `swap/<category>:`. Reject category-less commits. Tally `swap_commit_count`.
   c. Compute `git diff <byte_copy_sha>..HEAD -- <kosmos_path>`; for each hunk, find which SwapCommit owns it. Hunks owned by NO commit (e.g., merge commits without category) → add to `unjustified_hunks`.
   d. If `procedure=B`: grep file for `CC reference:\s+\S+:\d+` pattern; any function/handler in file lacking the pattern → add to `missing_cc_citations`.
4. Enumerate StreamEventChannel from `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts:1980-2295` using `awk` on `case '...'` blocks. For each channel, find KOSMOS handler (grep for the same `case '...'` token in target files) OR a `// SKIPPED — KOSMOS-N/A:` comment.
5. Aggregate into ParityAuditOutcome; emit per `--json` flag.

## CI integration

Add to existing CI workflow (`.github/workflows/`):

```yaml
- name: LLM swap-surface parity audit
  run: scripts/llm_swap_parity_audit.sh --strict
```

Failure blocks merge. Audit re-runs whenever any of the 4 in-scope files OR `parity-matrix.md` OR `.references/claude-code-sourcemap/restored-src/` changes.

## Local invocation example

```sh
$ scripts/llm_swap_parity_audit.sh
## LLM Swap-Surface Parity Audit
...
**Result**: ✅ PASS

$ scripts/llm_swap_parity_audit.sh --json | jq '.exit_code'
0
```
