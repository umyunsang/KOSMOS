# Quickstart: NMC Freshness SLO Enforcement

**Branch**: `023-nmc-freshness-slo`

## What This Feature Does

Adds freshness validation to the NMC emergency room adapter. When NMC API responses contain a `hvidate` timestamp older than the configured threshold, the system rejects the data with a structured `stale_data` error instead of silently delivering outdated emergency room information.

## Files to Modify

| File | Change |
|------|--------|
| `src/kosmos/tools/models.py` | Add `freshness_status: Literal["fresh"] \| None = None` to `LookupMeta` |
| `src/kosmos/tools/nmc/freshness.py` | New file: `check_freshness()` utility function |
| `src/kosmos/tools/nmc/emergency_search.py` | Integrate freshness check into adapter handler |

## Files to Create (Tests)

| File | Purpose |
|------|---------|
| `tests/tools/nmc/test_freshness_validation.py` | Unit tests for freshness utility |
| `tests/fixtures/nmc/fresh_response.json` | Fixture: hvidate within threshold |
| `tests/fixtures/nmc/stale_response.json` | Fixture: hvidate beyond threshold |

## Files NOT Modified

| File | Reason |
|------|--------|
| `src/kosmos/settings.py` | `nmc_freshness_minutes` already defined |
| `src/kosmos/tools/errors.py` | `LookupErrorReason.stale_data` already in enum |
| `src/kosmos/tools/envelope.py` | No adapter-specific logic; stays generic |
| `src/kosmos/tools/executor.py` | No NMC-specific logic; stays generic |

## How to Test

```bash
# Run freshness-specific tests
uv run pytest tests/tools/nmc/test_freshness_validation.py -v

# Run all NMC tests
uv run pytest tests/tools/nmc/ -v

# Run full test suite to verify no regressions
uv run pytest
```

## Key Design Decisions

1. **Freshness check in adapter, not executor**: NMC-specific `hvidate` semantics stay in the NMC package.
2. **fail-closed on parse errors**: Missing/unparseable `hvidate` → stale (Constitution § II).
3. **`freshness_status` on LookupMeta**: Optional field, None for non-NMC adapters, "fresh" when validated.
4. **Stale → LookupError, not degraded data**: Users never see stale emergency data.
