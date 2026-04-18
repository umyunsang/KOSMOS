# Tool Adapter: `mohw_welfare_eligibility_search`

**Provider**: 한국사회보장정보원 (SSIS) / 보건복지부 (MOHW)
**Tool ID**: `mohw_welfare_eligibility_search`
**Status**: Interface-only stub — live HTTP implementation pending Epic #16 / #20 (Layer 3 auth gate)

---

## Overview

Welfare service catalog search via the SSIS `NationalWelfarelistV001` endpoint.
Returns a ranked list of 중앙부처 welfare services matching life stage, household type,
interest theme, age bracket, or free-text keyword.

Use for questions like "출산 보조금 뭐 있어?" or "am I eligible for childbirth benefits?".

---

## Endpoint

```
GET https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001
```

**Authentication**: `serviceKey` query parameter (URL-encoded).
**Response format**: XML (SSIS v2.2 — JSON is not supported by this endpoint).
XML parsing via stdlib `xml.etree.ElementTree` is deferred to Layer 3 implementation.

---

## Request Parameters

| Field | Type | Description |
|---|---|---|
| `search_wrd` | `str \| None` | Free-text keyword (Korean preferred). Example: `출산` |
| `srch_key_code` | `SrchKeyCode` | Search field: `001` name, `002` summary, `003` both (default) |
| `life_array` | `LifeArrayCode \| None` | Life-stage code. `007` = 임신·출산 |
| `trgter_indvdl_array` | `TrgterIndvdlCode \| None` | Household type code. `020` = 다자녀 |
| `intrs_thema_array` | `IntrsThemaCode \| None` | Interest theme code. **`080` = 임신·출산** (authoritative) |
| `age` | `int \| None` | Citizen age (0–150). PII-adjacent — consent required |
| `onap_psblt_yn` | `"Y" \| "N" \| None` | Filter to online-applicable services when `"Y"` |
| `order_by` | `OrderBy` | Sort: `popular` (default) or `date` |
| `page_no` | `int` | Page number (1–1000). Default 1 |
| `num_of_rows` | `int` | Results per page (1–500). Default 10 |

**Note on `intrs_thema_array`**: The authoritative SSIS code for 임신·출산 is `"080"`.
Earlier spec drafts used `"010"` as a placeholder — `"010"` maps to 신체건강 in the
actual SSIS code table. Always use `"080"` for pregnancy/childbirth queries.

Code table source: `research/data/ssis/지자체복지서비스_코드표(v1.0).doc`

---

## Security Metadata

| Field | Value |
|---|---|
| `auth_type` | `api_key` |
| `auth_level` | `AAL2` |
| `pipa_class` | `personal` |
| `is_irreversible` | `False` |
| `dpa_reference` | `dpa-ssis-welfare-v1` |
| `requires_auth` | `True` |
| `is_personal_data` | `True` |
| `cache_ttl_seconds` | `0` (welfare service catalog changes; no caching) |
| `rate_limit_per_minute` | `10` |

**Why AAL2**: Query parameters (`age`, `lifeArray`, `trgterIndvdlArray`) encode
personal demographic signals even when no name or ID is submitted. AAL2 aligns
with the `check_eligibility` canonical tool pattern.

**DPA reference**: `dpa-ssis-welfare-v1` — placeholder pending Epic #16/#20.
See `docs/security/dpa/dpa-ssis-welfare-v1.md`.

---

## TOOL_MIN_AAL

```python
"mohw_welfare_eligibility_search": "AAL2"
```

Added in spec 029. V3 drift-protection fires from first registration.

---

## Interface-Only Status

`handle()` raises `Layer3GateViolation` unconditionally. The Layer 3 auth-gate in
`executor.invoke()` short-circuits `requires_auth=True` calls before `handle()` is
reached (FR-025, FR-026, SC-006). Unauthenticated sessions receive
`LookupError(reason="auth_required")` with zero upstream HTTP calls.

Live XML implementation will be added when Layer 3 ships (Epic #16 / #20).

---

## Scenario 3 Contract

Until Layer 3 ships, this adapter's sole externally-observable behavior is:

```
LookupError(reason="auth_required", retryable=False)
```

This is the **exact shape** that Epic #19 (Scenario 3 E2E: childbirth benefits flow)
replay-asserts. The contract is frozen in
`tests/tools/ssis/test_mohw_welfare_eligibility_search.py::test_executor_auth_required_matches_scenario3_contract`.

Epic #19 MUST NOT change the expected error shape without updating this test and
re-approving the adapter spec.

See: `specs/029-phase2-adapters-119-mohw/spec.md §1 User Story 3`

---

## Source Reference

- `research/data/ssis/활용가이드_중앙부처복지서비스(v2.2).doc`
  (SSIS endpoint URL, request/response parameter tables, XML format)
- `research/data/ssis/지자체복지서비스_코드표(v1.0).doc`
  (life-stage, target-individual, and interest-theme code tables)
- Spec: `specs/029-phase2-adapters-119-mohw/spec.md §4.2`
