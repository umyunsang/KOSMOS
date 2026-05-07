# Data Model — Secrets & Config (Epic #468)

**Date**: 2026-04-17 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

This is a configuration-schema Epic, not a persistence Epic. The "entities" below are **in-memory data structures** consumed by the startup guard and the audit scripts. No database, no files persisted by our code. The only on-disk artefacts are the source Markdown registry (`docs/configuration.md`) and the CI workflow file (`.github/workflows/ci.yml`), both human-edited or script-generated.

---

## 1. `RequiredVar`

Represents a `KOSAX_*` (or allowlisted non-`KOSAX_*`, i.e. `LANGFUSE_*`) environment variable that the guard checks for non-empty presence at CLI start-up.

**Fields**:

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `name` | `str` | matches `^(KOSAX|LANGFUSE)_[A-Z0-9_]+$` | exact env var name |
| `consumer` | `str` | non-empty | module path that reads this var (e.g., `kosax.settings.KosaxSettings`) |
| `required_in` | `frozenset[Literal["dev", "ci", "prod"]]` | non-empty subset | environments where this var MUST be non-empty |
| `doc_anchor` | `str` | non-empty | slug into `docs/configuration.md` (e.g., `#kosax_kakao_api_key`) |

**Invariants**:
- `name` MUST start with `KOSAX_` unless explicitly allowlisted (currently `LANGFUSE_*` only; FR-040).
- `required_in` MUST contain at least one environment; a var with no required environments is a `ConditionalVar`, not `RequiredVar`.

**Examples**:

```python
RequiredVar(
    name="KOSAX_KAKAO_API_KEY",
    consumer="kosax.settings.KosaxSettings.kakao_api_key",
    required_in=frozenset({"dev", "ci", "prod"}),
    doc_anchor="#kosax_kakao_api_key",
)
RequiredVar(
    name="KOSAX_FRIENDLI_TOKEN",
    consumer="kosax.llm.config.LLMClientConfig.token",
    required_in=frozenset({"dev", "ci", "prod"}),
    doc_anchor="#kosax_friendli_token",
)
```

---

## 2. `ConditionalVar`

Represents a variable that becomes required *only* when `KOSAX_ENV` takes a specific value. Distinct from `RequiredVar` because `required_in` semantics differ: `ConditionalVar` allows empty `required_in` for dev while still being catalogued.

**Fields** (superset of `RequiredVar`):

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `name` | `str` | as `RequiredVar` | |
| `consumer` | `str` | non-empty | |
| `required_in` | `frozenset[Literal["dev", "ci", "prod"]]` | **may be empty** | environments where this var is required |
| `conditional_note` | `str` | non-empty | human-readable reason the var is conditional (e.g., "required only when OTEL export is enabled") |
| `owner_epic` | `str` | matches `^#\d+$` | GitHub Epic that owns this var's code wiring |
| `doc_anchor` | `str` | non-empty | |

**Examples**:

```python
ConditionalVar(
    name="LANGFUSE_PUBLIC_KEY",
    consumer="kosax.observability.langfuse (#501)",
    required_in=frozenset({"prod"}),
    conditional_note="Required only in prod where Langfuse export is on; dev/ci use OTel no-op.",
    owner_epic="#501",
    doc_anchor="#langfuse_public_key",
)
```

---

## 3. `DeprecatedVar`

Represents a legacy variable name that the codebase still honours for backward compatibility but is scheduled for removal.

**Fields**:

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `name` | `str` | as `RequiredVar` | |
| `consumer` | `str` | non-empty | last module path that honours the legacy fallback |
| `replacement` | `str` | non-empty | canonical replacement var name |
| `removal_target` | `str` | non-empty | `"NEEDS TRACKING"` or `"post-#NNN"` |
| `doc_anchor` | `str` | non-empty | |

**Examples**:

```python
DeprecatedVar(
    name="KOSAX_API_KEY",
    consumer="kosax.permissions.credentials.resolve_credential (global fallback)",
    replacement="per-provider: KOSAX_KAKAO_API_KEY / KOSAX_DATA_GO_KR_API_KEY",
    removal_target="NEEDS TRACKING — post-#468",
    doc_anchor="#kosax_api_key-deprecated",
)
```

The guard treats `DeprecatedVar` like `ConditionalVar` with empty `required_in`: catalogued, audited, but never triggers a start-up failure on absence.

---

## 4. `OverrideFamily`

Represents the `KOSAX_<TOOL_ID>_API_KEY` per-tool override pattern. Not a single var — a **pattern** the audit script must recognise without flagging each concrete expansion as undocumented.

**Fields**:

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `pattern` | `str` | matches `^KOSAX_\{[A-Z_]+\}_[A-Z_]+$` | template with `{TOOL_ID}` placeholder |
| `consumer` | `str` | non-empty | `kosax.permissions.credentials._tool_specific_var` |
| `expansion_fn` | `str` | non-empty | `lambda tool_id: f"KOSAX_{tool_id.upper()}_API_KEY"` |
| `doc_anchor` | `str` | non-empty | |

**Examples**:

```python
OverrideFamily(
    pattern="KOSAX_{TOOL_ID}_API_KEY",
    consumer="kosax.permissions.credentials._tool_specific_var",
    expansion_fn="lambda tool_id: f'KOSAX_{tool_id.upper()}_API_KEY'",
    doc_anchor="#per-tool-override-pattern",
)
```

The audit script treats any env var name matching the expansion as covered by this family, suppressing "undocumented" false positives.

---

## 5. Registry Table Schema (`docs/configuration.md`)

Human-facing Markdown table. Exactly these columns, in this order, to guarantee `audit-env-registry.py` can parse deterministically:

```markdown
| Variable | Required | Default | Range / Format | Consumed by | Source doc |
|----------|----------|---------|----------------|-------------|------------|
| `KOSAX_KAKAO_API_KEY` | yes (all envs) | — | 32-char hex | `kosax.settings` | Kakao Developers Console |
| `KOSAX_FRIENDLI_TOKEN` | yes (all envs) | — | bearer token | `kosax.llm.config` | FriendliAI Suite |
| `LANGFUSE_PUBLIC_KEY` | yes (prod only, #501) | — | `pk-lf-…` | `kosax.observability` | Langfuse Cloud |
| `KOSAX_API_KEY` | **deprecated** | — | — | `kosax.permissions.credentials` (legacy fallback) | — |
| … | | | | | |
```

**Schema rules** (enforced by audit script FR-020/FR-023):
- Column headers MUST match exactly (case-sensitive).
- Variable names MUST be wrapped in backticks.
- `Required` column values MUST be one of: `yes (all envs)`, `yes (prod only, #NNN)`, `yes (ci+prod)`, `conditional (see note)`, `no (opt-in)`, `**deprecated**`.
- Every variable appearing via `rg 'KOSAX_[A-Z_]+'` in `src/`, `.github/workflows/ci.yml`, `.env.example` MUST have a row (or match an `OverrideFamily` pattern).

---

## 6. Full Registry Surface (for Phase 2 population)

17 `KOSAX_*` vars confirmed via `rg -hoE "KOSAX_[A-Z_]+" src/ --type py | sort -u`:

| # | Variable | Source module |
|---|----------|---------------|
| 1 | `KOSAX_API_KEY` | `permissions/credentials.py` (deprecated) |
| 2 | `KOSAX_CLI_HISTORY_SIZE` | `cli/config.py` |
| 3 | `KOSAX_CLI_SHOW_USAGE` | `cli/config.py` |
| 4 | `KOSAX_CLI_THEME` | `cli/` (theme) |
| 5 | `KOSAX_CLI_WELCOME_BANNER` | `cli/config.py` |
| 6 | `KOSAX_DATA_GO_KR_API_KEY` | `settings.py` |
| 7 | `KOSAX_FRIENDLI_BASE_URL` | `llm/config.py` |
| 8 | `KOSAX_FRIENDLI_MODEL` | `llm/config.py` |
| 9 | `KOSAX_FRIENDLI_TOKEN` | `llm/config.py` |
| 10 | `KOSAX_JUSO_CONFM_KEY` | `settings.py` |
| 11 | `KOSAX_KAKAO_API_KEY` | `settings.py` + `permissions/credentials.py` |
| 12 | `KOSAX_KOROAD_ACCIDENT_SEARCH_API_KEY` | `permissions/credentials.py` (OverrideFamily expansion) |
| 13 | `KOSAX_KOROAD_API_KEY` | `.github/workflows/ci.yml` test placeholder |
| 14 | `KOSAX_LLM_SESSION_BUDGET` | `llm/config.py` |
| 15 | `KOSAX_LOOKUP_TOPK` | `settings.py` |
| 16 | `KOSAX_SGIS_KEY` | `settings.py` |
| 17 | `KOSAX_SGIS_SECRET` | `settings.py` |

Plus `KOSAX_THEME` (legacy CLI theme var) observed in `cli/` — include as `DeprecatedVar` if not actively read; or `RequiredVar` with `required_in=frozenset()` if opt-in.

Plus allowlisted `LANGFUSE_*`: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (#501-owned conditional).

Plus `KOSAX_OTEL_ENDPOINT` (#501-owned conditional).

Plus `KOSAX_NMC_FRESHNESS_MINUTES` (#507-owned; appears in `settings.py`).

Plus `KOSAX_ENV` itself (meta-flag; always optional, default `dev`).

**Expected registry row count**: 18–22 (17 scanned + `KOSAX_ENV` + 2 `LANGFUSE_*` + `KOSAX_OTEL_ENDPOINT` + 1 override-family-pattern row + optional Langfuse host).

---

## 7. Audit Drift Report Shape

Output of `scripts/audit-env-registry.py` on drift detection:

```json
{
  "schema_version": "1",
  "generated_at": "2026-04-17T12:34:56Z",
  "verdict": "drift" | "clean",
  "findings": {
    "in_code_not_in_registry": [
      {"name": "KOSAX_NEW_THING", "source_files": ["src/kosax/foo.py:42"]}
    ],
    "in_registry_not_in_code": [
      {"name": "KOSAX_OLD_THING", "registry_line": 87}
    ],
    "prefix_violations": [
      {"name": "MY_BAD_VAR", "source_files": ["src/kosax/bar.py:10"],
       "reason": "not KOSAX_ prefixed and not in LANGFUSE_ allowlist"}
    ],
    "override_family_unmatched": []
  }
}
```

Exit code semantics specified in `contracts/audit-env-registry.md`.

---

## 8. State transitions

There are no long-lived states. Configuration is read once at CLI start (via pydantic-settings + the guard's snapshot), and neither the guard nor the audit scripts mutate it. The only "transitions" are:

1. **Missing → Present**: contributor edits `.env`; next CLI launch sees the var. Guard passes.
2. **Active → Deprecated**: registry row's `Required` column edited to `**deprecated**`; var moves from `RequiredVar` list to `DeprecatedVar` list in `src/kosax/config/guard.py`. Normal PR flow.
3. **Allowlist change**: `LANGFUSE_*` exemption would require constitution-level discussion; not in this Epic's scope.

No DB schema, no migrations, no versioning beyond `schema_version` in the drift-report JSON (bumped only on breaking schema changes).
