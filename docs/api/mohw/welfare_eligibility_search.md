---
tool_id: mohw_welfare_eligibility_search
primitive: lookup
tier: live
permission_tier: 3
---

# mohw_welfare_eligibility_search

## Overview

Searches the SSIS (한국사회보장정보원) central-ministry welfare service catalog for services matching life stage, household type, interest theme, age, or keyword, returning a ranked list with service ID, name, ministry, summary, and bokjiro.go.kr detail link.

| Field | Value |
|---|---|
| Classification | Live · Permission tier 3 |
| Source | Ministry of Health and Welfare (MOHW) via Korea Social Security Information Service (SSIS) / data.go.kr |
| Primitive | `lookup` |
| Module | `src/kosmos/tools/ssis/welfare_eligibility_search.py` |

## Envelope

**Input model**: `MohwWelfareEligibilitySearchInput` defined at `src/kosmos/tools/ssis/welfare_eligibility_search.py:41–110`.

| Field | Type | Required | Description |
|---|---|---|---|
| `search_wrd` | `str \| None` (max 100 chars) | no | Free-text keyword in Korean. Example: `출산` for childbirth benefits. Omit to filter by codes only. |
| `srch_key_code` | `SrchKeyCode` (default `all_fields`) | no | Which fields to search: `001` name, `002` summary, `003` both. |
| `life_array` | `LifeArrayCode \| None` | no | Life-stage filter. Example: `007` for 임신·출산. |
| `trgter_indvdl_array` | `TrgterIndvdlCode \| None` | no | Target individual/household-type filter. Example: `020` for 다자녀. |
| `intrs_thema_array` | `IntrsThemaCode \| None` | no | Interest-theme filter. Example: `080` for 임신·출산; `010` for 신체건강. |
| `age` | `int \| None` (0–150) | no | Citizen age in years for age-eligibility filtering. Do NOT request from the citizen without consent — this field is part of the `is_personal_data=True` surface. |
| `onap_psblt_yn` | `Literal["Y", "N"] \| None` | no | Filter to online-applicable services only when `"Y"`. Omit for both online and offline. |
| `order_by` | `OrderBy` (default `popular`) | no | Sort order: `popular` (조회 수) or `date` (등록순). |
| `page_no` | `int` (1–1000, default 1) | no | Page number. SSIS caps at 1000. |
| `num_of_rows` | `int` (1–500, default 10) | no | Records per page. Maximum 500 per SSIS API contract. |
| `call_tp` | `Literal["L"]` (fixed) | no | Fixed to `"L"` (list). Do not override. |

**Output model**: `MohwWelfareEligibilitySearchOutput` defined at `src/kosmos/tools/ssis/welfare_eligibility_search.py:139–149`.

| Field | Type | Required | Description |
|---|---|---|---|
| `result_code` | `str` | yes | Result code (`"0"` = SUCCESS in SSIS v2.0). |
| `result_message` | `str` | yes | Human-readable result message. |
| `page_no` | `int` | yes | Requested page number. |
| `num_of_rows` | `int` | yes | Rows per page. |
| `total_count` | `int` | yes | Total matching welfare services. |
| `items` | `list[SsisWelfareServiceItem]` | yes | Welfare service records. Empty list when no services match. |

Each `SsisWelfareServiceItem` (defined at lines 117–137) carries:

| Field | Type | Required | Description |
|---|---|---|---|
| `servId` | `str` | yes | Service ID (e.g., `WLF00001188`). |
| `servNm` | `str` | yes | Service name (서비스명). |
| `jurMnofNm` | `str` | yes | Ministry name (소관부처명). |
| `jurOrgNm` | `str \| None` | no | Bureau name (소관조직명). |
| `inqNum` | `str \| None` | no | View count (raw string). |
| `servDgst` | `str \| None` | no | Service summary (서비스 요약). |
| `servDtlLink` | `str \| None` | no | Detail link (bokjiro.go.kr URL). |
| `svcfrstRegTs` | `str \| None` | no | Service registration date. |
| `lifeArray` | `str \| None` | no | Life stage tags (comma-separated). |
| `intrsThemaArray` | `str \| None` | no | Interest theme tags. |
| `trgterIndvdlArray` | `str \| None` | no | Target household type tags. |
| `sprtCycNm` | `str \| None` | no | Support cycle (e.g., `1회성`). |
| `srvPvsnNm` | `str \| None` | no | Provision type (e.g., `전자바우처`). |
| `rprsCtadr` | `str \| None` | no | Contact information. |
| `onapPsbltYn` | `Literal["Y", "N"] \| None` | no | Online application available. |

## Search hints

- 한국어: `복지서비스`, `출산`, `보조금`, `복지혜택`, `신청`, `사회보장정보원`, `보건복지부`, `임산부 지원`, `육아`, `장애인 복지`
- English: `welfare benefit`, `eligibility search`, `childbirth subsidy`, `MOHW`, `SSIS`, `social security Korea`, `welfare service catalog`, `government benefit`

## Endpoint

- **data.go.kr endpoint**: `B554287/NationalWelfareInformationsV001/NationalWelfarelistV001`
- **Source URL**: https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001
- **Authentication**: API key via `KOSMOS_DATA_GO_KR_API_KEY` (per Constitution IV)

> **Implementation status**: The HTTP handler is an interface-only stub pending Layer 3 auth gate provisioning (Epic #16/#20). The `handle()` function raises `Layer3GateViolation` as a defence-in-depth backstop. The full output models (`SsisWelfareServiceItem` + `MohwWelfareEligibilitySearchOutput`) are authored and ready for live handler wiring. The upstream response format is XML per SSIS v2.2 §1.1; XML parsing is deferred to the live handler implementation.

## Permission tier rationale

This adapter is classified as Permission tier 3 because welfare eligibility queries inherently involve personal data: `age`, life stage (`life_array`), household type (`trgter_indvdl_array`), and interest themes collectively constitute a citizen profile that is sensitive under PIPA §23 (`pipa_class="personal"`, `is_personal_data=True`, `auth_level="AAL2"`). Querying welfare eligibility services for a specific citizen requires their informed consent and authenticated identity. Under Spec 033, tier 3 applies to tools that process citizen-specific personal data in a way that could affect their rights or entitlements. The `dpa_reference="dpa-ssis-welfare-v1"` is required per Spec 024. The Layer 3 auth-gate in `executor.invoke()` short-circuits all unauthenticated calls to `LookupError(reason="auth_required")` before `handle()` is reached (FR-025, FR-026, SC-006). The `age` field must never be requested from a citizen without explicit consent.

## Worked example

### Input envelope

```json
{
  "mode": "fetch",
  "tool_id": "mohw_welfare_eligibility_search",
  "params": {
    "search_wrd": "출산",
    "life_array": "007",
    "intrs_thema_array": "080",
    "onap_psblt_yn": "Y",
    "order_by": "popular",
    "page_no": 1,
    "num_of_rows": 5
  }
}
```

### Output envelope (success)

```json
{
  "tool_id": "mohw_welfare_eligibility_search",
  "result": {
    "result_code": "0",
    "result_message": "정상 처리되었습니다.",
    "page_no": 1,
    "num_of_rows": 5,
    "total_count": 38,
    "items": [
      {
        "servId": "WLF00001188",
        "servNm": "첫만남이용권",
        "jurMnofNm": "보건복지부",
        "jurOrgNm": "인구아동정책관",
        "servDgst": "출생 아동에게 200만원 상당의 바우처를 지급하여 초기 양육 비용을 지원합니다.",
        "servDtlLink": "https://www.bokjiro.go.kr/ssis-tbu/twataa/wlfareInfo/moveTWAT52011M.do?wlfareInfoId=WLF00001188",
        "onapPsbltYn": "Y",
        "sprtCycNm": "1회성",
        "srvPvsnNm": "전자바우처"
      }
    ]
  }
}
```

### Output envelope (unauthenticated — fail-closed)

When the caller has no valid session identity, the Layer 3 auth-gate rejects the call before `handle()` is reached:

```json
{
  "tool_id": "mohw_welfare_eligibility_search",
  "result": {
    "kind": "error",
    "reason": "auth_required",
    "message": "mohw_welfare_eligibility_search requires citizen authentication (requires_auth=True). Please log in to continue.",
    "retryable": false
  }
}
```

### Conversation snippet

```text
Citizen: 출산 관련 정부 복지 혜택이 뭐가 있는지 알고 싶어요.
KOSMOS: 출산·임신 관련 온라인 신청 가능한 복지 서비스 38개를 찾았습니다. 가장 많이 조회된 서비스는 '첫만남이용권'으로, 출생 아동에게 200만원 상당의 바우처를 1회 지급합니다. 상세 내용은 bokjiro.go.kr에서 확인하실 수 있습니다. 더 많은 서비스 목록을 보시겠습니까? (참고: 본인 인증 후 나이·가구 유형 조건을 설정하면 더 정확한 결과를 드릴 수 있습니다.)
```

## Constraints

- **Rate limit**: `rate_limit_per_minute=10`; data.go.kr daily quota applies per API key.
- **Freshness window**: `cache_ttl_seconds=0` — no client-side caching. Welfare service catalog updates are managed by SSIS and may occur at any time.
- **Fixture coverage gaps**: Live handler is not yet implemented — the current stub raises `Layer3GateViolation`. The upstream wire format is XML (SSIS v2.2 §1.1); XML parsing and normalization are deferred to the live handler. The authored output models (`SsisWelfareServiceItem`, `MohwWelfareEligibilitySearchOutput`) cover the documented SSIS NationalWelfarelistV001 field set.
- **Error envelope examples**:
  - Unauthenticated call (Layer 3 gate): `LookupError(reason="auth_required")` before `handle()` is reached.
  - Defence-in-depth (handle() reached without auth): `Layer3GateViolation` raised.
  - `age` field: Must not be collected from a citizen without explicit consent — the LLM description enforces this constraint at the model layer.
  - `intrs_thema_array` note: The authoritative 임신·출산 code for `intrsThemaArray` is `"080"`, not `"010"` — see source module docstring at line 68.
