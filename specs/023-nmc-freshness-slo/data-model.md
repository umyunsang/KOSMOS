# Phase 1 Data Model: NMC Freshness SLO Enforcement

**Date**: 2026-04-16
**Branch**: `023-nmc-freshness-slo`

## Entity Changes

### Modified: LookupMeta (src/kosmos/tools/models.py)

Add `freshness_status` optional field to the existing metadata model.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| source | str | (required) | tool_id of the adapter |
| fetched_at | datetime | (required) | UTC timestamp |
| request_id | str | (required) | UUID for tracing |
| elapsed_ms | int (ge=0) | (required) | Elapsed time in milliseconds |
| rate_limit_remaining | int \| None | None | Remaining rate-limit slots |
| **freshness_status** | **Literal["fresh"] \| None** | **None** | **New. Set to "fresh" when NMC hvidate passes freshness check. None for non-NMC adapters or when freshness is not applicable.** |

**Validation rules**: `freshness_status` must be either the literal string `"fresh"` or `None`. No other values are permitted. Pydantic v2 `Literal` type enforces this at validation time.

**Backward compatibility**: Default is `None`, so existing adapters and tests are unaffected. JSON serialization with `exclude_none=True` omits the field entirely for non-NMC responses.

### New: FreshnessResult (src/kosmos/tools/nmc/freshness.py)

Internal utility type representing the result of a freshness check.

| Field | Type | Description |
|-------|------|-------------|
| is_fresh | bool | Whether the data passed the freshness threshold |
| data_age_minutes | float | Age of the hvidate in minutes |
| threshold_minutes | int | Configured freshness threshold |
| hvidate_raw | str \| None | Original hvidate string (for error messages) |

This is an internal dataclass, not part of the LookupOutput contract. It is consumed only by the NMC adapter handler.

### Existing (no changes): LookupErrorReason (src/kosmos/tools/errors.py)

`stale_data` variant already present in the enum:

```python
class LookupErrorReason(StrEnum):
    stale_data = "stale_data"   # Already exists
```

### Existing (no changes): KosmosSettings (src/kosmos/settings.py)

`nmc_freshness_minutes` already defined:

```python
nmc_freshness_minutes: int = Field(default=30, ge=1, le=1440)
```

## State Transitions

```
NMC Response Received
    │
    ├── hvidate present and parseable
    │   ├── age <= threshold_minutes → freshness_status = "fresh" → return data envelope
    │   └── age > threshold_minutes  → return LookupError(reason="stale_data")
    │
    └── hvidate missing/empty/unparseable → return LookupError(reason="stale_data")
```

## Relationships

```
KosmosSettings.nmc_freshness_minutes
    ↓ (read at check time)
check_freshness(hvidate_str, threshold_minutes)
    ↓ (returns FreshnessResult)
NMC adapter handle()
    ├── fresh → inject freshness_status into response dict → envelope.normalize()
    └── stale → return LookupError dict → envelope.normalize()
```
