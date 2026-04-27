# Quickstart: P1 Dead Anthropic Model Matrix Removal

**Branch**: `2112-dead-anthropic-models` | **Date**: 2026-04-28
**Audience**: Codex automated reviewer · human reviewer · future maintainer
**Time budget**: ≤ 5 minutes (static audits) + ≤ 5 minutes (test baseline) + ≤ 2 minutes (manual smoke)

This quickstart walks a reviewer through verifying that the deletion of the Anthropic model dispatch matrix from KOSMOS's TUI layer was successful and that all preserved invariants (Python `LLMClient` truth values) still hold.

---

## Prerequisites

- macOS / Linux terminal at the repo root.
- Bun ≥ 1.2.x installed (`bun --version`).
- `uv` ≥ 0.5 installed (`uv --version`).
- Repo clone with branch `2112-dead-anthropic-models` checked out (or the merged commit).
- For C9 smoke: `KOSMOS_FRIENDLI_TOKEN` set in `.env` or environment.

---

## 1 · Static audit chain (1 minute)

Run the following in order. Every command must exit cleanly with the expected output.

### 1.1 File-deletion check (C2)

```bash
test ! -f tui/src/services/mockRateLimits.ts && echo "C2.1 PASS"
test ! -f tui/src/services/rateLimitMocking.ts && echo "C2.2 PASS"
```

Expect:
```
C2.1 PASS
C2.2 PASS
```

### 1.2 Regex 0-hit audit (C1)

```bash
rg -n -i 'claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic' \
   tui/src/utils/model/ \
   tui/src/services/mockRateLimits.ts \
   tui/src/services/rateLimitMocking.ts 2>/dev/null
```

Expect: empty stdout. (After deletion, the two services files are not found; `rg` reports nothing.)

### 1.3 Single source-of-truth audit (C3)

```bash
rg -n 'K-EXAONE-236B-A23B' --type ts --type py | sort -u
```

Expect: ≤ 3 lines, only at `src/kosmos/llm/config.py:37`, `tui/src/utils/model/model.ts:179`, `tui/src/utils/model/model.ts:187`.

### 1.4 Python preservation audits (C4 / C5 / C6)

```bash
echo "--- C4: sampling defaults ---"
rg -n 'temperature: float = 1\.0|top_p: float = 0\.95|presence_penalty: float = 0\.0|max_tokens: int = 1024' src/kosmos/llm/client.py
echo "--- C5: rate-limit retry ---"
rg -n 'class RetryPolicy|_compute_rate_limit_delay|_is_rate_limit_envelope|_complete_with_retry|_stream_with_retry' src/kosmos/llm/client.py
echo "--- C6: enable_thinking ---"
rg -n 'KOSMOS_K_EXAONE_THINKING|chat_template_kwargs' src/kosmos/llm/client.py
```

Expect: C4 ≥ 8 matches, C5 ≥ 5 matches, C6 ≥ 2 matches.

### 1.5 Dependency-set audit (C7)

```bash
git diff main...HEAD -- tui/package.json pyproject.toml | rg -E '^\+\s*"[^"]+"\s*:' | head -20
```

Expect: empty stdout (no added dependency lines).

### 1.6 LOC reduction audit (C10)

```bash
wc -l tui/src/utils/model/modelOptions.ts tui/src/utils/model/model.ts
```

Expect: total ≤ 1 211 LOC across both files.

### 1.7 Helper alias annotations (C11)

```bash
rg -n -B1 -A3 'getDefaultSonnetModel|getDefaultOpusModel|getDefaultHaikuModel' tui/src/utils/model/model.ts
```

Expect: each occurrence is either absent OR wrapped with `[Deferred to P2 — issue #NNN]` annotation.

---

## 2 · Test baseline (3-5 minutes)

### 2.1 Bun test suite

```bash
cd tui && bun test 2>&1 | tail -3 && cd ..
```

Expect: `984 pass` (or higher) `0 fail` `0 errors`.

### 2.2 Python pytest suite

```bash
uv run pytest 2>&1 | tail -3
```

Expect: `437 passed` (or higher).

---

## 3 · Citizen smoke run via expect text-log (2 minutes, automated)

Per memory `feedback_vhs_tui_smoke` (TUI text-log smoke): the smoke is recorded as a plain-text log so Codex and human reviewers can grep it directly. GIF/PNG would be binary and not LLM-readable.

### 3.1 Run the smoke recipe

```bash
chmod +x specs/2112-dead-anthropic-models/smoke.expect
specs/2112-dead-anthropic-models/smoke.expect
```

This produces `specs/2112-dead-anthropic-models/smoke.txt` (text log with ANSI escape sequences).

### 3.2 Audit the log via grep

```bash
echo "Korean reply present:" && grep -E '[가-힣]' specs/2112-dead-anthropic-models/smoke.txt | head -3
echo "Lookup tool-call present:" && grep -E 'lookup|resolve_location' specs/2112-dead-anthropic-models/smoke.txt | head -3
echo "Legacy rate-limit absent:" && grep -F 'anthropic-ratelimit-unified' specs/2112-dead-anthropic-models/smoke.txt && echo FAIL || echo PASS
echo "Legacy model name absent:" && grep -Ei 'claude-3|claude-opus|claude-sonnet|claude-haiku' specs/2112-dead-anthropic-models/smoke.txt && echo FAIL || echo PASS
```

All four lines must end with either Hangul output (first two) or `PASS` (last two).

### 3.3 Manual fallback (`expect` not available)

If `expect` is missing on the reviewer's machine:

```bash
{
  sleep 5; printf 'Hi\r'
  sleep 12; printf '강남역 어디?\r'
  sleep 45; printf '/quit\r'
} | bun run tui 2>&1 | tee specs/2112-dead-anthropic-models/smoke.txt
```

Then run the same C9.1–C9.4 grep commands. Note "manual fallback (no expect)" in PR description.

---

## 4 · If anything fails

| Failure | Likely cause | Remedy |
|---|---|---|
| C1 reports a match | An Anthropic ID survived the deletion | grep the matching line, delete or replace with K-EXAONE constant |
| C2 reports either file still exists | The file was not deleted from git | `git rm <file>` and amend the commit |
| C3 reports more than 3 lines | A new K-EXAONE literal was introduced | Use `getDefaultMainLoopModel()` instead of inlining the string |
| C4–C6 report fewer matches than expected | Python `LLMClient` truth values were inadvertently changed | revert `src/kosmos/llm/{config.py,client.py}` to `main` |
| C7 reports added dependency lines | A new package was added | revert `tui/package.json` / `pyproject.toml` dep change; AGENTS.md hard-rule violation |
| C10 reports LOC > 1 211 | Pruning was insufficient | review surviving Anthropic dispatch in `model.ts` / `modelOptions.ts` |
| C11 reports missing annotations | The FR-006 caller-reach rule was not honoured | add `// [Deferred to P2 — issue #NNN]` to each preserved alias |
| C8 bun test count drops | A test was broken or removed | restore the test or document the removal in the PR body |
| C8 pytest count drops | Python regression | revert any unintended changes under `src/kosmos/` |
| C9 Korean reply does not paint | TUI runtime regression | run `bun run tui --debug`, attach log to PR |

---

## 5 · For Codex automated review

Codex inline-review pattern (per AGENTS.md § Code review):

1. Codex flags issues with `[P1]` / `[P2]` / `[P3]` severity badges.
2. For each finding:
   - **P1**: address in this PR (push a fix commit).
   - **P2**: either address now or open a sub-issue with `[Deferred]` prefix.
   - **P3**: acknowledge with reply; defer if non-blocking.
3. Re-run static audit chain (1.1-1.7) after each push.

After all P1 items are resolved and audit chain stays green, the PR is ready for merge.
