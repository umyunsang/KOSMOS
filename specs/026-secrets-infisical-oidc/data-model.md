# Data Model — Secrets & Config (Epic #468)

**Date**: 2026-04-17 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

This is a configuration-schema Epic, not a persistence Epic. The "entities" below are **in-memory data structures** consumed by the startup guard and the audit scripts. No database, no files persisted by our code. The only on-disk artefacts are the source Markdown registry (`docs/configuration.md`) and the CI workflow file (`.github/workflows/ci.yml`), both human-edited or script-generated.

---

## 1. `RequiredVar`

Represents a `KOSMOS_*` (or allowlisted non-`KOSMOS_*`, i.e. `LANGFUSE_*`) environment variable that the guard checks for non-empty presence at CLI start-up.

**Fields**:

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `name` | `str` | matches `^(KOSMOS|LANGFUSE)_[A-Z0-9_]+$` | exact env var name |
| `consumer` | `str` | non-empty | module path that reads this var (e.g., `kosmos.settings.KosmosSettings`) |
| `required_in` | `frozenset[Literal["dev", "ci", "prod"]]` | non-empty subset | environments where this var MUST be non-empty |
| `doc_anchor` | `str` | non-empty | slug into `docs/configuration.md` (e.g., `#kosmos_kakao_api_key`) |

**Invariants**:
- `name` MUST start with `KOSMOS_` unless explicitly allowlisted (currently `LANGFUSE_*` only; FR-040).
- `required_in` MUST contain at least one environment; a var with no required environments is a `ConditionalVar`, not `RequiredVar`.

**Examples**:

```python
RequiredVar(
    name="KOSMOS_KAKAO_API_KEY",
    consumer="kosmos.settings.KosmosSettings.kakao_api_key",
    required_in=frozenset({"dev", "ci", "prod"}),
    doc_anchor="#kosmos_kakao_api_key",
)
RequiredVar(
    name="KOSMOS_FRIENDLI_TOKEN",
    consumer="kosmos.llm.config.LLMClientConfig.token",
    required_in=frozenset({"dev", "ci", "prod"}),
    doc_anchor="#kosmos_friendli_token",
)
```

---

## 2. `ConditionalVar`

Represents a variable that becomes required *only* when `KOSMOS_ENV` takes a specific value. Distinct from `RequiredVar` because `required_in` semantics differ: `ConditionalVar` allows empty `required_in` for dev while still being catalogued.

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
    consumer="kosmos.observability.langfuse (#501)",
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
    name="KOSMOS_API_KEY",
    consumer="kosmos.permissions.credentials.resolve_credential (global fallback)",
    replacement="per-provider: KOSMOS_KAKAO_API_KEY / KOSMOS_DATA_GO_KR_API_KEY",
    removal_target="NEEDS TRACKING — post-#468",
    doc_anchor="#kosmos_api_key-deprecated",
)
```

The guard treats `DeprecatedVar` like `ConditionalVar` with empty `required_in`: catalogued, audited, but never triggers a start-up failure on absence.

---

## 4. `OverrideFamily`

Represents the `KOSMOS_<TOOL_ID>_API_KEY` per-tool override pattern. Not a single var — a **pattern** the audit script must recognise without flagging each concrete expansion as undocumented.

**Fields**:

| Field | Type | Constraints | Purpose |
|-------|------|-------------|---------|
| `pattern` | `str` | matches `^KOSMOS_\{[A-Z_]+\}_[A-Z_]+$` | template with `{TOOL_ID}` placeholder |
| `consumer` | `str` | non-empty | `kosmos.permissions.credentials._tool_specific_var` |
| `expansion_fn` | `str` | non-empty | `lambda tool_id: f"KOSMOS_{tool_id.upper()}_API_KEY"` |
| `doc_anchor` | `str` | non-empty | |

**Examples**:

```python
OverrideFamily(
    pattern="KOSMOS_{TOOL_ID}_API_KEY",
    consumer="kosmos.permissions.credentials._tool_specific_var",
    expansion_fn="lambda tool_id: f'KOSMOS_{tool_id.upper()}_API_KEY'",
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
| `KOSMOS_KAKAO_API_KEY` | yes (all envs) | — | 32-char hex | `kosmos.settings` | Kakao Developers Console |
| `KOSMOS_FRIENDLI_TOKEN` | yes (all envs) | — | bearer token | `kosmos.llm.config` | FriendliAI Suite |
| `LANGFUSE_PUBLIC_KEY` | yes (prod only, #501) | — | `pk-lf-…` | `kosmos.observability` | Langfuse Cloud |
| `KOSMOS_API_KEY` | **deprecated** | — | — | `kosmos.permissions.credentials` (legacy fallback) | — |
| … | | | | | |
```

**Schema rules** (enforced by audit script FR-020/FR-023):
- Column headers MUST match exactly (case-sensitive).
- Variable names MUST be wrapped in backticks.
- `Required` column values MUST be one of: `yes (all envs)`, `yes (prod only, #NNN)`, `yes (ci+prod)`, `conditional (see note)`, `no (opt-in)`, `**deprecated**`.
- Every variable appearing via `rg 'KOSMOS_[A-Z_]+'` in `src/`, `.github/workflows/ci.yml`, `.env.example` MUST have a row (or match an `OverrideFamily` pattern).

---

## 6. Full Registry Surface (for Phase 2 population)

17 `KOSMOS_*` vars confirmed via `rg -hoE "KOSMOS_[A-Z_]+" src/ --type py | sort -u`:

| # | Variable | Source module |
|---|----------|---------------|
| 1 | `KOSMOS_API_KEY` | `permissions/credentials.py` (deprecated) |
| 2 | `KOSMOS_CLI_HISTORY_SIZE` | `cli/config.py` |
| 3 | `KOSMOS_CLI_SHOW_USAGE` | `cli/config.py` |
| 4 | `KOSMOS_CLI_THEME` | `cli/` (theme) |
| 5 | `KOSMOS_CLI_WELCOME_BANNER` | `cli/config.py` |
| 6 | `KOSMOS_DATA_GO_KR_API_KEY` | `settings.py` |
| 7 | `KOSMOS_FRIENDLI_BASE_URL` | `llm/config.py` |
| 8 | `KOSMOS_FRIENDLI_MODEL` | `llm/config.py` |
| 9 | `KOSMOS_FRIENDLI_TOKEN` | `llm/config.py` |
| 10 | `KOSMOS_JUSO_CONFM_KEY` | `settings.py` |
| 11 | `KOSMOS_KAKAO_API_KEY` | `settings.py` + `permissions/credentials.py` |
| 12 | `KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY` | `permissions/credentials.py` (OverrideFamily expansion) |
| 13 | `KOSMOS_KOROAD_API_KEY` | `.github/workflows/ci.yml` test placeholder |
| 14 | `KOSMOS_LLM_SESSION_BUDGET` | `llm/config.py` |
| 15 | `KOSMOS_LOOKUP_TOPK` | `settings.py` |
| 16 | `KOSMOS_SGIS_KEY` | `settings.py` |
| 17 | `KOSMOS_SGIS_SECRET` | `settings.py` |

Plus `KOSMOS_THEME` (legacy CLI theme var) observed in `cli/` — include as `DeprecatedVar` if not actively read; or `RequiredVar` with `required_in=frozenset()` if opt-in.

Plus allowlisted `LANGFUSE_*`: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (#501-owned conditional).

Plus `KOSMOS_OTEL_ENDPOINT` (#501-owned conditional).

Plus `KOSMOS_NMC_FRESHNESS_MINUTES` (#507-owned; appears in `settings.py`).

Plus `KOSMOS_ENV` itself (meta-flag; always optional, default `dev`).

**Expected registry row count**: 18–22 (17 scanned + `KOSMOS_ENV` + 2 `LANGFUSE_*` + `KOSMOS_OTEL_ENDPOINT` + 1 override-family-pattern row + optional Langfuse host).

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
      {"name": "KOSMOS_NEW_THING", "source_files": ["src/kosmos/foo.py:42"]}
    ],
    "in_registry_not_in_code": [
      {"name": "KOSMOS_OLD_THING", "registry_line": 87}
    ],
    "prefix_violations": [
      {"name": "MY_BAD_VAR", "source_files": ["src/kosmos/bar.py:10"],
       "reason": "not KOSMOS_ prefixed and not in LANGFUSE_ allowlist"}
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
2. **Active → Deprecated**: registry row's `Required` column edited to `**deprecated**`; var moves from `RequiredVar` list to `DeprecatedVar` list in `src/kosmos/config/guard.py`. Normal PR flow.
3. **Allowlist change**: `LANGFUSE_*` exemption would require constitution-level discussion; not in this Epic's scope.

No DB schema, no migrations, no versioning beyond `schema_version` in the drift-report JSON (bumped only on breaking schema changes).
