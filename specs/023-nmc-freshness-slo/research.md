# Phase 0 Research: NMC Freshness SLO Enforcement

**Date**: 2026-04-16
**Branch**: `023-nmc-freshness-slo`

## Research Tasks

### R1: hvidate Field Format

**Question**: What datetime format does the NMC `hvidate` field use?

**Finding**: The NMC real-time bed availability API (`/api/nmc/v1/realtime-beds`) returns `hvidate` as a Korean datetime string. Based on `data.go.kr` NMC API documentation and PublicDataReader wire format analysis (vision.md reference), the field uses `YYYY-MM-DD HH:MM:SS` format (e.g., `"2026-04-16 14:30:00"`). Timezone is implicitly KST (Asia/Seoul, UTC+9).

**Decision**: Parse `hvidate` with `datetime.strptime()` using `"%Y-%m-%d %H:%M:%S"` format, then localize to KST before comparison. If parsing fails, treat as stale (fail-closed per Constitution § II).

**Alternatives considered**:
- ISO 8601 parsing with `datetime.fromisoformat()`: Rejected — NMC uses space-separated format, not `T` separator.
- `dateutil.parser.parse()`: Rejected — introduces a new dependency (`python-dateutil`), violates "no new dependencies" constraint.

### R2: Freshness Check Insertion Point

**Question**: Where in the adapter pipeline should freshness validation occur?

**Finding**: The current pipeline is: `lookup(fetch)` → `executor.invoke()` → auth gate → adapter handler → `envelope.normalize()` → return. The freshness check is NMC-specific (depends on `hvidate` field semantics), so it should NOT live in the generic executor or envelope normalizer.

**Decision**: Implement freshness validation as a utility function in `src/kosmos/tools/nmc/freshness.py`. The NMC adapter handler calls this utility after parsing the upstream response. If stale, the handler returns a `LookupError` dict directly (pre-envelope); if fresh, it injects `freshness_status: "fresh"` into the response dict before returning to the executor.

**Alternatives considered**:
- Post-processing hook in `executor.invoke()`: Rejected — couples NMC-specific logic to the generic executor.
- Middleware in `envelope.normalize()`: Rejected — normalizer should not have adapter-specific knowledge.
- Decorator on adapter handler: Rejected — over-engineered for a single adapter.

**Reference**: Layer 2 Tool System design (vision.md) — adapter-specific logic stays in adapter modules; generic pipeline stays generic.

### R3: freshness_status Envelope Metadata

**Question**: Where should `freshness_status` appear in the response envelope?

**Finding**: `LookupMeta` (defined in `models.py`) is injected into every `lookup(mode='fetch')` response by `envelope.normalize()`. Adding `freshness_status` to `LookupMeta` makes it available on all envelope variants (LookupRecord, LookupCollection, LookupTimeseries) without changing each variant individually.

**Decision**: Add `freshness_status: Literal["fresh"] | None = None` to `LookupMeta`. Only NMC adapters (and future adapters with freshness semantics) populate this field. Non-NMC adapters leave it as `None` (omitted in JSON serialization).

**Alternatives considered**:
- NMC-specific response model: Rejected — breaks the uniform 5-variant discriminated union contract.
- Separate metadata dict outside LookupMeta: Rejected — fragments the metadata namespace.
- `Literal["fresh", "stale"]`: Rejected for the envelope field — stale responses return a LookupError, not a successful envelope, so `"stale"` would never appear in a successful response's meta. Keeping only `"fresh" | None` is honest.

### R4: Stale Data Error Envelope Construction

**Question**: How should the stale_data error be constructed?

**Finding**: `make_error_envelope()` in `envelope.py` already constructs `LookupError` envelopes with full `LookupMeta`. `LookupErrorReason.stale_data` is already in the enum. The adapter handler can return a dict matching the `LookupError` shape, and `envelope.normalize()` will validate and pass it through.

**Decision**: The freshness utility returns either:
- `None` when data is fresh (caller proceeds normally)
- A `dict` matching `LookupError` shape when data is stale (caller returns this directly)

The caller (adapter handler) passes the stale error dict through the normal envelope normalization path. The error message includes the data age and configured threshold for LLM transparency.

**Alternatives considered**:
- Raise a custom exception and catch in executor: Rejected — the executor already handles adapter exceptions generically; a freshness-specific exception would need special-casing.
- Return a sentinel value: Rejected — less explicit than returning the full error envelope dict.

### R5: Timezone Handling

**Question**: How to handle the timezone comparison between `hvidate` (KST) and the current time?

**Decision**: Use `datetime.now(tz=ZoneInfo("Asia/Seoul"))` for the current time and parse `hvidate` as KST. Both operands are timezone-aware, making the comparison safe. `ZoneInfo` is stdlib (Python 3.9+), no dependency needed.

**Alternatives considered**:
- Compare in UTC: Equivalent result but requires converting KST hvidate to UTC first — extra step with no benefit.
- Use naive datetimes: Rejected — timezone-naive comparison is error-prone.

## Deferred Items Validation

Spec section "Scope Boundaries & Deferred Items" states: "No items deferred — all requirements are addressed in this epic."

Scanned spec.md for unregistered deferral patterns (`separate epic`, `future epic`, `Phase 2+`, `v2`, `deferred to`, `later release`, `out of scope for v1`): **No matches found.**

**Validation result**: PASS — no untracked deferrals.
