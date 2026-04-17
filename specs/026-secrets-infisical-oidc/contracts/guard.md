# Contract — `kosmos.config.guard.verify_startup`

**File**: `src/kosmos/config/guard.py`
**Wire-in site**: `src/kosmos/cli/app.py:main()` between `load_repo_dotenv()` and `setup_tracing()`.
**Related FR**: FR-001..FR-008, FR-041, FR-042 · **NFR**: NFR-001 (100 ms budget)

---

## Public surface

```python
# src/kosmos/config/guard.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Final, Literal


Env = Literal["dev", "ci", "prod"]


@dataclass(frozen=True, slots=True)
class RequiredVar:
    name: str
    consumer: str
    required_in: frozenset[Env]
    doc_anchor: str


@dataclass(frozen=True, slots=True)
class GuardDiagnostic:
    missing: tuple[str, ...]
    env: Env
    doc_url: str


def current_env() -> Env:
    """Read KOSMOS_ENV from os.environ; unknown values fall through to 'dev'."""


def check_required(env: Env | None = None) -> GuardDiagnostic | None:
    """Pure function. Returns GuardDiagnostic if any required vars missing, else None.

    Library-safe: no I/O, no logging, no sys.exit. Suitable for unit tests.
    """


def verify_startup() -> None:
    """CLI-layer wrapper. If check_required() returns a diagnostic, write a
    single-line remediation message to sys.stderr and exit with code 78.
    No-op on success (returns None).

    MUST complete within 100 ms wall-clock on cold import.
    MUST NOT write to .env, stdout, or any file.
    MUST NOT import or initialise any network client (httpx, OTel, Langfuse).
    """
```

---

## Inputs

- `os.environ` snapshot at call time (after `load_repo_dotenv()` merged `.env`).
- `KOSMOS_ENV` meta-flag (optional; default `dev`).
- Module-level `_REQUIRED_VARS: Final[tuple[RequiredVar, ...]]` — in-code source of truth (see `data-model.md §1`).

## Outputs

- **Success path**: `verify_startup()` returns `None`; no stdout/stderr emission.
- **Failure path**: single-line write to `sys.stderr` with exact grammar below, followed by `sys.exit(78)`.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Implicit success (function returns without exiting). |
| `78` | `EX_CONFIG` per `sysexits.h` — "configuration error" — one or more required env vars missing for the current `KOSMOS_ENV`. |

No other exit codes are emitted by the guard itself. (Any other non-zero code originates elsewhere.)

## stderr grammar (single line)

```
KOSMOS config error [env=<env>]: missing required variables: <VAR_1>, <VAR_2>, ..., <VAR_N>. See <doc_url>
```

Where:
- `<env>` is `dev` | `ci` | `prod` (lowercase, exact).
- `<VAR_i>` are the missing env-var names, **alphabetically sorted**, comma+space separated. Deterministic ordering (same env state → same message) is required so the output is testable and diff-able across runs.
- `<doc_url>` is `https://github.com/umyunsang/KOSMOS/blob/main/docs/configuration.md` (hard-coded in guard module). FR-005 accepts either a full URL or a repo-relative `docs/configuration.md` pointer; hard-coded full URL chosen for copy-paste usability.

**Example**:

```
KOSMOS config error [env=prod]: missing required variables: KOSMOS_FRIENDLI_TOKEN, KOSMOS_KAKAO_API_KEY. See https://github.com/umyunsang/KOSMOS/blob/main/docs/configuration.md
```

**Rules**:
- No ANSI color codes (CI terminals may not render them; grep-ability wins).
- No trailing newline beyond a single `\n` appended by `print(..., file=sys.stderr)`.
- No multi-line output.
- No secret values quoted (variable *names* only, never values).

## Semantics: "missing" definition

A variable is "missing" iff `os.environ.get(var.name, "").strip() == ""`. An empty-string value is treated as missing (FR-006, Edge Case #1). Whitespace-only values are treated as missing.

## Semantics: environment classification

1. If `os.environ.get("KOSMOS_ENV")` is exactly one of `{"dev", "ci", "prod"}` → use as `env`.
2. Otherwise (unset, empty, or any other string) → `env = "dev"`.

No logging of the fallthrough; invisible by design.

## Performance contract

- **Budget**: 100 ms wall-clock on cold Python import (NFR-001, FR-001).
- **Measurement**: `time.monotonic()` around `verify_startup()`; unit test asserts `< 0.1` seconds on CI hardware.
- **Techniques**:
  - Module-level `_REQUIRED_VARS` constant (no lazy building).
  - Zero I/O on the happy path (no `open()`, no socket, no DNS).
  - No stdlib imports that trigger heavy initialisation (`ssl`, `urllib.request`).
  - On failure path, only `sys.stderr.write` + `sys.exit` are invoked.

## Idempotence

- `verify_startup()` is safe to call multiple times (no-op on success; re-fails deterministically on failure).
- `check_required()` is pure: same `os.environ` snapshot → same return.

## Observability

- No OTel spans. The guard runs *before* `setup_tracing()`.
- No `logging` calls. stderr only.
- Test assertions MUST use the exact grammar above; any change to the grammar is a breaking change requiring spec update.

## Test matrix (for `tests/config/test_guard.py`)

| Test ID | Scenario | Expected |
|---------|----------|----------|
| T-G01 | Empty env, `KOSMOS_ENV` unset | exit 78; message lists all `required_in ⊇ {dev}` vars; env tag `dev` |
| T-G02 | All required vars set | return `None`; no stderr output |
| T-G03 | `KOSMOS_ENV=prod`, `LANGFUSE_PUBLIC_KEY` missing | exit 78; `LANGFUSE_PUBLIC_KEY` in missing list |
| T-G04 | `KOSMOS_ENV=prod`, `LANGFUSE_PUBLIC_KEY` missing but `KOSMOS_ENV=dev` reruns | T-G03 fails, then flipping env passes |
| T-G05 | Whitespace-only value for `KOSMOS_KAKAO_API_KEY` | treated as missing |
| T-G06 | Unknown `KOSMOS_ENV=staging` | treated as `dev`; no error about `prod`-only vars |
| T-G07 | 100 ms budget | `time.monotonic()` delta `< 0.1` on worst-case (all-missing) path |
| T-G08 | Missing-list ordering determinism | same input twice → identical message |
| T-G09 | Guard does not write `.env` | post-call `.env` mtime unchanged (if present) |
| T-G10 | Guard does not emit OTel spans | no span starts during `verify_startup()` |

## Non-goals (out of guard's contract)

- Validating *values* of env vars beyond "non-empty". Format validation (e.g., "must be 32-char hex") lives in pydantic-settings `@field_validator` hooks — already in `llm/config.py`. The guard is a *presence* check, not a *shape* check.
- Fetching secrets from external vaults. Infisical integration happens in CI workflow, not in the guard.
- Rewriting `.env` or writing any file. Absolute no-write contract.
