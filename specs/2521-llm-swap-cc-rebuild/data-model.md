# Phase 1 Data Model: LLM Swap-Surface CC Byte-Copy + Bounded Swap Migration

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Date**: 2026-05-01

This Epic operates on metadata describing the rebuild process itself (not runtime data). Entities below are authored in `parity-matrix.md` and consumed by `scripts/llm_swap_parity_audit.sh`.

## E-1 — `CCSourceFile`

Read-only source-of-truth file under `.references/claude-code-sourcemap/restored-src/`.

| Field | Type | Description |
|---|---|---|
| `path` | string (absolute) | Repo-rooted path under `.references/claude-code-sourcemap/restored-src/src/` |
| `sha256` | string (64 hex) | SHA-256 of file contents at audit time |
| `line_count` | int | Total newline-delimited lines |
| `version_tag` | string | Always `"2.1.88"` per current sourcemap; embedded in audit output |

**Validation**: `sha256` MUST match `sha256sum <path> | awk '{print $1}'` at audit time. Drift in restored-src triggers a manual re-validation pass (deferred per spec § Future Work).

## E-2 — `KOSAXTargetFile`

A file in the rebuild scope. One of the 4 in-scope files.

| Field | Type | Description |
|---|---|---|
| `path` | string (absolute) | Repo-rooted path |
| `procedure` | enum {`A`, `B`} | A = byte-copy + bounded swap; B = behavior-mirror with citations |
| `cc_source_path` | string \| null | Set iff `procedure=A`; absolute CCSourceFile.path |
| `cc_analog_path` | string \| null | Set iff `procedure=B`; absolute CCSourceFile.path of structural analog |
| `swap_role` | enum {`stream-bridge`, `provider-client`, `agentic-loop`, `legacy-shim`} | Functional classification |
| `expected_byte_copy_sha256` | string \| null | Set iff `procedure=A`; equals `cc_source_path`'s SHA-256 at byte-copy commit |

**Procedure-A validation** (audit script): `sha256sum <path>` at the byte-copy commit MUST equal `expected_byte_copy_sha256`. Subsequent commits may diverge (each diff justified by SwapCommit).

**Procedure-B validation** (audit script): every function/handler in the file MUST have a docstring/comment matching pattern `CC reference:\s+\S+:\d+(-\d+)?` citing `cc_analog_path`.

## E-3 — `SwapCommit`

A git commit on the rebuild branch that applies a Step B (Procedure-A) or Step C (Procedure-B) swap modification.

| Field | Type | Description |
|---|---|---|
| `sha` | string (40 hex) | Git commit SHA |
| `category` | enum (4 values) | One of: `SWAP/llm-provider`, `SWAP/tool-domain`, `SWAP/anti-anthropic-1p`, `SWAP/identifier-rename` |
| `target_files` | List[KOSAXTargetFile.path] | Files the commit modifies |
| `cc_reference_lines` | string | Format `<cc-path>:<line-range>` citing the CC source affected |
| `kosax_target_lines` | string | Format `<kosax-path>:<line-range>` showing where the diff lands |
| `justification` | string | Free text explaining why this swap is necessary (≥1 sentence) |

**Validation** (audit script): commit subject MUST start with `swap/<category>:` (case-insensitive). Commit body MUST contain a `Refs:` line citing `cc_reference_lines`. Commits without these are flagged as drift.

**Allowed category contents**:
- `SWAP/llm-provider`: Anthropic SDK calls → KOSAX IPC bridge; Anthropic-API endpoint URLs → FriendliAI URLs; OAuth/billing call sites → no-op or removed.
- `SWAP/tool-domain`: CC dev-tool references (e.g., Bash, Edit, NotebookEdit) → KOSAX public-API primitive references.
- `SWAP/anti-anthropic-1p`: removal of claude.ai 1P features (sync, billing, telemetry) — only deletions, no replacements.
- `SWAP/identifier-rename`: Claude/Anthropic/claude.ai brand tokens → KOSAX/EXAONE/FriendliAI tokens. Pure rename diffs; no functional changes.

## E-4 — `ParityAuditOutcome`

Output of `scripts/llm_swap_parity_audit.sh` per audit run.

| Field | Type | Description |
|---|---|---|
| `run_timestamp` | string (ISO 8601) | When the audit ran |
| `branch` | string | Git branch under audit |
| `per_file` | List[FilePartialOutcome] | Per-target-file result rows |
| `unjustified_hunks` | List[DiffHunk] | Hunks not covered by any SwapCommit |
| `missing_cc_citations` | List[Function] | Procedure-B functions lacking `CC reference:` citation |
| `exit_code` | int | 0 = pass; 1 = drift detected |

### `FilePartialOutcome` sub-record

| Field | Type | Description |
|---|---|---|
| `kosax_path` | string | KOSAXTargetFile.path |
| `procedure` | enum {A, B} | inherited |
| `byte_copy_sha_match` | bool \| null | true/false for A; null for B |
| `swap_commit_count` | int | Number of swap commits affecting this file |
| `unjustified_hunk_count` | int | Hunks from `unjustified_hunks` filtered to this file |
| `missing_cc_citation_count` | int | From `missing_cc_citations` filtered to this file |

**Audit pass condition**: ALL `per_file[*]`: `byte_copy_sha_match` is true OR null AND `unjustified_hunk_count == 0` AND `missing_cc_citation_count == 0`. ANY failure → exit 1.

## E-5 — `StreamEventChannel`

Logical streaming channel used in the audit's enumeration step.

| Field | Type | Description |
|---|---|---|
| `cc_event_path` | string | Format `<cc-path>:<line>:<case-name>` (e.g., `services/api/claude.ts:2148:thinking_delta`) |
| `cc_event_kind` | enum | One of: `message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop` |
| `cc_event_subtype` | string \| null | For `content_block_start`: `text`/`thinking`/`tool_use`/`server_tool_use`. For `content_block_delta`: `text_delta`/`thinking_delta`/`signature_delta`/`input_json_delta`/`citations_delta`/`connector_text_delta`. |
| `kosax_handler_path` | string \| null | Where KOSAX handles it; null if explicitly skipped |
| `kosax_skip_reason` | string \| null | Required if `kosax_handler_path` is null |
| `byte_copied` | bool | true if handler is byte-copied from CC; false if behavior-mirrored or skipped |

**Audit enumeration step**: script greps `services/api/claude.ts` for `case '...'` blocks, builds StreamEventChannel records. Verifies each has either a KOSAX handler (file:line) or a skip-reason in a SwapCommit's justification.

## Relationships

```
CCSourceFile  (1) ──── (0..n)  KOSAXTargetFile          # via cc_source_path or cc_analog_path
CCSourceFile  (1) ──── (0..n)  StreamEventChannel        # CC handler enumeration
KOSAXTargetFile (1) ──── (0..n)  SwapCommit             # commits affecting this file
KOSAXTargetFile (1) ──── (0..n)  StreamEventChannel     # KOSAX-side handler binding
ParityAuditOutcome (1) ──── (1..n)  FilePartialOutcome   # per-file roll-up
ParityAuditOutcome (1) ──── (0..n)  DiffHunk             # unjustified diffs
ParityAuditOutcome (1) ──── (0..n)  Function             # missing citations
```

## State Transitions

`KOSAXTargetFile.procedure` is fixed per the spec FR-001 mapping table; never changes.

`SwapCommit.category` is fixed at commit creation; never changes (rebase that changes a category requires a new commit).

`ParityAuditOutcome` is recomputed per audit run; previous outcomes are not persisted (CI re-runs from scratch).

## Persistence

None at runtime — all entities exist as:
- Markdown rows in `parity-matrix.md` (canonical)
- Git commit metadata
- Audit script stdout (transient)
- Optional JSON appendix `parity-audit-output.json` (gitignored, regenerated per run)

No new database, no new on-disk schema. Aligns with spec FR-012 (zero new runtime deps).
