# Phase 0 — Research: 029 Phase 2 Adapters (NFA 119 + MOHW)

**Branch**: `feat/15-phase2-adapters-119-mohw`
**Spec**: [`spec.md`](./spec.md)
**Date**: 2026-04-18

This document resolves every NEEDS CLARIFICATION in the spec, validates the
deferred-items table (Constitution §VI gate), and maps each design decision to
a concrete reference source (Constitution §I gate).

---

## 1. Deferred Items Validation (Constitution §VI gate)

Spec §2 "Scope Boundaries and Deferred Items" lists eight deferred items.
Validation status:

| # | Deferred item | Tracking | Status |
|---|---|---|---|
| 1 | Live HTTP `nfa_emergency_info_service.handle()` | Phase 2 implementation PR | TRACKED (same Epic #15 completion) |
| 2 | Live HTTP `mohw_welfare_eligibility_search.handle()` | Epic #16 / Epic #20 | TRACKED |
| 3 | Layer 3 auth gate that lifts `requires_auth` short-circuit | Epic #16, Epic #20 | TRACKED |
| 4 | Scenario 2 full E2E (119 fallback path) | Epic #18 | TRACKED |
| 5 | Scenario 3 full E2E (childbirth benefits flow) | Epic #19 | TRACKED |
| 6 | Gov24 application submission after eligibility lookup | Epic #22 | TRACKED |
| 7 | Recall@5 eval set expansion for Phase 2 adapters | Epic #507 follow-on | TRACKED (parent Epic exists) |
| 8 | `nfa_safety_center_lookup` (CSV-backed nearest-station) | Spec §9 — extension path | NEEDS TRACKING — will be back-filled by `/speckit-taskstoissues` |

Scan for unregistered deferral phrases in spec prose: items §9.2 (`ssis_welfare_detail_fetch`),
§9.3 (`nfa_emg_statistics_service`), and §9.4 (`gov24_application_guide`) appear under
"Extension Path" with MVP-out-of-scope language. These are future adapters, not
deferrals of in-scope work, and are allowed under the constitution because they
do not affect the acceptance criteria of this spec. No action required beyond
adding them to the Deferred Items table as future extension points (handled by
`/speckit-taskstoissues`).

**Verdict**: Gate PASSES. Item #8 flagged as NEEDS TRACKING.

---

## 2. Reference Source Map (Constitution §I gate)

Each design decision in this plan maps to one concrete source:

| Design decision | Primary reference | File path |
|---|---|---|
| Interface-only adapter pattern (stub handler + `Layer3GateViolation`) | NMC reference adapter | `src/kosmos/tools/nmc/emergency_search.py` |
| Full-HTTP adapter pattern (httpx client, envelope parsing, fail-closed) | HIRA reference adapter | `src/kosmos/tools/hira/hospital_search.py` |
| `GovAPITool` V1–V6 validator contract | Tool models | `src/kosmos/tools/models.py` §V1–V6 |
| `TOOL_MIN_AAL` drift gate | Security audit table | `src/kosmos/security/audit.py` |
| `LookupError` / `LookupCollection` envelopes | Envelope module | `src/kosmos/tools/envelope.py`, `errors.py` |
| XML/JSON dual-format upstream handling | HIRA Content-Type guard | `src/kosmos/tools/hira/hospital_search.py` |
| `data.go.kr` error envelope detection | `PublicDataReader` (MIT) | `docs/vision.md § Reference materials` |
| Retry/backoff policy for transient upstream failures | LangGraph `RetryPolicy` + stamina | `docs/vision.md § Reference materials` |
| Pydantic v2 schema-driven registry | Pydantic AI | `docs/vision.md § Reference materials` |
| Fail-closed adapter defaults | Constitution §II | `.specify/memory/constitution.md` |
| Layer 3 auth-gate contract (FR-025, FR-026, SC-006) | Executor short-circuit | `src/kosmos/tools/executor.py` (invoke) |
| Korean domain search-hint bilingual pattern | Tool adapter guide | `docs/tool-adapters.md §Search hints` |

No decision in this spec requires an architectural pattern outside of the
already-cited references. No ADR needed.

---

## 3. Clarification Resolutions

### C1 — NFA 119 API scope [RESOLVED 2026-04-18, per spec]

Already resolved in spec §7. The tool adapts `소방청_구급정보서비스`
(`EmergencyInformationService`, 6 operations, JSON+XML, `serviceKey` auth,
`1661000` provider code). Endpoint base URL confirmed from docx TABLE 0 (service
deployment info row). Adapter name `nfa_emergency_info_service`. No further
action needed.

### C2 — SSIS life-stage / target-individual code tables [RESOLVED in Phase 0]

**Decision**: The code tables in
`research/data/ssis/지자체복지서비스_코드표(v1.0).doc` **apply at central-ministry
level** (`NationalWelfarelistV001`) as well.

**Evidence**:

1. **Identical parameter names**: The 중앙부처 API request schema
   (`research/data/ssis/활용가이드_중앙부처복지서비스(v2.2).doc` §1.1, request
   parameter table extracted 2026-04-18) uses the exact same field names as
   the 지자체 code table document:
   `lifeArray`, `trgterIndvdlArray`, `intrsThemaArray`, `srchKeyCode`.
2. **Response values match**: The 중앙부처 sample response returns
   `lifeArray=영유아, 임신·출산` and `trgterIndvdlArray=다자녀, 장애인, 저소득` —
   these are exactly codes `001 + 007` (생애주기) and `020 + 040 + 050`
   (가구상황) from the 지자체 code table.
3. **SSIS is a shared infrastructure**: The 한국사회보장정보원 (SSIS) aggregates
   both 중앙부처 and 지자체 welfare services into a single portal (bokjiro.go.kr)
   with a shared taxonomy; a divergent code table would break the portal's
   cross-search UX.
4. **No alternative code table exists**: No separate 중앙부처 code table document
   is present in `research/data/ssis/`; MOHW does not ship a distinct code list.

**Consequence for implementation**:

- `MohwWelfareEligibilitySearchInput` uses three `str | None` fields
  (`life_array`, `trgter_indvdl_array`, `intrs_thema_array`) **backed by
  Python `Enum` types** defined in a shared module
  `src/kosmos/tools/ssis/codes.py`.
- Enum values extracted from `지자체복지서비스_코드표(v1.0).doc`:
  - `LifeArrayCode`: 001 영유아, 002 아동, 003 청소년, 004 청년, 005 중장년, 006 노년, 007 임신·출산
  - `TrgterIndvdlCode`: 010 다문화·탈북민, 020 다자녀, 030 보훈대상자, 040 장애인, 050 저소득, 060 한부모·조손
  - `IntrsThemaCode`: 010 신체건강, 020 정신건강, 030 생활지원, 040 주거, 050 일자리, 060 문화·여가, 070 안전·위기, **080 임신·출산**, 090 보육, 100 교육, 110 입양·위탁, 120 보호·돌봄, 130 서민금융, 140 법률.
- **Spec correction note**: The spec's example `intrs_thema_array="010"` for
  "임신·출산" was a placeholder based on the `lifeArray=007` mental model. The
  correct code for 임신·출산 in `intrsThemaArray` is **080**. Plan artifacts use
  the correct code. No spec edit required — the spec only used it as a
  natural-language description hint; the authoritative mapping lives in
  `codes.py` enum.

### C3 — DPA template `dpa-ssis-welfare-v1` [RESOLVED — dev-phase unblocked]

**Decision**: The placeholder identifier `dpa-ssis-welfare-v1` is **sufficient
for the development-phase interface-only registration** and is **not a
production deployment blocker at this spec level**.

**Evidence**:

1. Validator V2 (`src/kosmos/tools/models.py` §V2) enforces the pattern
   `^[A-Za-z][A-Za-z0-9_-]{5,63}$`. `dpa-ssis-welfare-v1` satisfies this
   (12 chars, letter-led, dash-separated).
2. The placeholder passes load-time registration, which is what the interface-
   only phase requires.
3. The adapter's `requires_auth=True` + Layer 3 short-circuit means no upstream
   SSIS call will ever occur during the interface-only phase — so no §26
   처리위탁 occurs at runtime until Layer 3 (Epic #16 / #20) lands.

**Production-deployment prerequisite (out of scope for this spec)**:

Before `mohw_welfare_eligibility_search.handle()` is allowed to make real HTTP
calls to SSIS, a DPA template document governing KOSMOS's §26 수탁자 relationship
with SSIS MUST exist at `docs/security/dpa/dpa-ssis-welfare-v1.md` and be
referenced in `docs/security/tool-template-security-spec-v1.md`. This is a
task for the Epic that lifts the Layer 3 auth-gate short-circuit (Epic #16 or
#20). The DPA drafting task should be back-filled as a Task issue by
`/speckit-taskstoissues` under Epic #15, labelled `needs-spec` until the
template is drafted.

**Plan artifact**: The PR that merges this spec MUST add a single-line stub
at `docs/security/dpa/dpa-ssis-welfare-v1.md` with the following content:

```
# DPA Template: dpa-ssis-welfare-v1

**Status**: PLACEHOLDER — real DPA template pending Epic #16 / #20.
This file exists to reserve the identifier for validator V2 traceability.
```

This prevents a broken link from the tool registration's comment, costs nothing
to author, and makes the deferral visible in the repo.

---

## 4. Technical Approach — NFA 119

### 4.1 Endpoint confirmed (spec §4.1)

Base URL: `https://apis.data.go.kr/1661000/EmergencyInformationService/{operation}`

The docx TABLE 0 "서비스 URL" row uses `http://` — but data.go.kr has migrated to
HTTPS for all new endpoints. Adapter uses `https://` (HIRA reference adapter
already follows this pattern).

### 4.2 Operation-specific output schemas (extracted from docx TABLES 4/8/12/16/20)

| Operation | Output fields (confirmed from docx) |
|---|---|
| `getEmgPatientTransferInfo` (TABLE 4) | `sidoHqOgidNm, rsacGutFsttOgidNm, stmtYm, stmtHh, rlifAcdAsmCdNm, ptntAge, ptntSdtSeCdNm, frnrAt, ptntTyCdNm, ruptOccrPlcCdNm, rlifOccrTyCdNm, anmlInctCdNm, wmhtDamgCdNm` |
| `getEmgPatientConditionInfo` (TABLE 8) | `ruptSptmCdNm, sidoHqOgidNm, rsacGutFsttOgidNm, stmtYm, stmtHh, ptntAge, lwsBpsr, topBpsr, ptntHbco, ptntBfco, ptntOsv, ptntBht` |
| `getEmgPatientFirstaidInfo` (TABLE 12) | `sidoHqOgidNm, rsacGutFsttOgidNm, stmtYm, stmtHh, ptntAge, ptntSdtSeCdNm, fstaCdNm` |
| `getEmgVehicleDispatchInfo` (TABLE 16) | `sidoHqOgidNm, rsacGutFsttOgidNm, stmtYm, stmtHh, vctpCdNm, vhclSeCd, vhclNo, vhclStatCdNm, gotFrmtAt, vhcn, vhclGrCdNm, mnm, mdnm, gutPcnt, tnkCpct, gutOdr` |
| `getEmgVehicleInfo` (TABLE 20) | `sidoHqOgidNm, rsacGutFsttOgidNm, vhclSeCd, vhclNo, vctpCdNm, vhclStatCdNm, gotFrmtAt, vhcn, vhclGrCdNm, mnm, mdnm, bdgPcnt, tnkCpct, stde` |
| `getEmgencyActivityInfo` (TABLE 24, primary — citizen-relevant) | schema per spec §4.1 output section (patient symptom, dispatch distance, crew qualification) |

Each operation gets a dedicated Pydantic v2 model in `data-model.md` so the
adapter's `output_schema` is a discriminated union on `operation` — not the
flat `extra="allow"` relaxation shown in the spec. Since this is an
interface-only adapter, the discriminator can remain `RootModel[dict[str, Any]]`
for V1 — but per-operation models are authored so they are ready when
Layer 3 lands and can be swapped in without another planning cycle.

### 4.3 HTTP retry/backoff policy

- **Timeout**: 10 seconds (matches NMC reference, shorter than HIRA's 30 s
  because NFA's "평균 응답 시간 500 ms" per docx TABLE 2 is well under budget).
- **Retry**: None at the adapter level for the interface-only phase. When
  Layer 3 ships, use `stamina`-style exponential backoff with `max_attempts=3`,
  `initial_delay=0.5s`, `max_delay=4s`, jitter enabled. Retries apply only to
  idempotent errors: HTTP 5xx, `httpx.TimeoutException`, and the data.go.kr
  error code 22 (`LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR` — rate limit).
- **Circuit breaker**: Deferred to Layer 6 (Error Recovery) per `docs/vision.md`.
  Out of scope for this spec.

### 4.4 `data.go.kr` error envelope handling

The spec §1 Edge Cases already documents the `<OpenAPI_ServiceResponse>`
envelope. Implementation maps:

| `returnReasonCode` | Meaning | `LookupError.reason` | `retryable` |
|---|---|---|---|
| 22 | Rate limit exceeded | `rate_limited` | `True` |
| 30 | Service key unregistered | `upstream_unavailable` | `False` |
| 31 | Service key deadline exceeded | `upstream_unavailable` | `False` |
| 32 | Unregistered IP | `upstream_unavailable` | `False` |
| (other / absent) | Unknown | `upstream_unavailable` | `False` |

---

## 5. Technical Approach — MOHW (SSIS)

### 5.1 Endpoint confirmed (spec §4.2)

Base URL: `https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001`

SSIS doc (extracted via `textutil`) confirms:
- Auth: `serviceKey` query parameter (URL-encoded).
- Response format: **XML only** (the doc's "교환 데이터 표준" row shows `[O] XML   [ ] JSON`).
- Service version: 2.0, deployment date 2025-04-23.
- Rate: 30 TPS, daily quota managed by data.go.kr (1,000 calls/day on dev keys).
- Data freshness: 일 1회 (daily refresh) — matches the spec's
  `cache_ttl_seconds=0` for the interface-only phase (PII gate).

### 5.2 Request and response schema

Request parameters confirmed from SSIS doc §1.1.b. Response schema confirmed
from §1.1.c — 14 fields per service:
`servId, servNm, jurMnofNm, jurOrgNm, inqNum, servDgst, servDtlLink,
svcfrstRegTs, lifeArray, intrsThemaArray, trgterIndvdlArray, sprtCycNm,
srvPvsnNm, rprsCtadr, onapPsbltYn`.

`data-model.md` provides full Pydantic v2 models for request + response.

### 5.3 XML parsing strategy

- Use stdlib `xml.etree.ElementTree` for parsing (zero new runtime deps —
  AGENTS.md hard rule).
- Parser path: `xmltodict`-style normalization is NOT required; ElementTree
  traversal over `<wantedList>/<servList>` is sufficient.
- Single-item normalization: SSIS XML wraps a single `<servList>` element bare
  (not as `<servList>[0]`). Adapter normalizes to `list[dict]` in the same
  pattern as HIRA's `item_list = [raw_item] if isinstance(raw_item, dict) else raw_item`.

### 5.4 HTTP retry/backoff policy

- **Timeout**: 10 seconds.
- **Retry**: Same policy as NFA (see §4.3) — deferred to Layer 3 ship. Code-
  level `# TODO` comment references Epic #16 / #20.
- **Fail-closed on missing `serviceKey`**: Same as NFA — return
  `upstream_unavailable, retryable=False` immediately.

---

## 6. TOOL_MIN_AAL Integration

The current `TOOL_MIN_AAL` table (`src/kosmos/security/audit.py`) lists only
**canonical tools** (`lookup`, `resolve_location`, `check_eligibility`, etc.),
not per-adapter rows. Existing full-HTTP adapters (`hira_hospital_search`,
`nmc_emergency_search`, `kma_*`) do NOT have rows in `TOOL_MIN_AAL` because
V3 only fires when a row exists for the tool's `id`.

**Design choice for this spec**: Extend `TOOL_MIN_AAL` with the two new
adapter IDs so V3 drift-protection fires from day one. This is a deliberate
tightening relative to existing adapters. Rationale:

- The new adapters ship under the post-024 security regime (AAL + pipa_class
  + dpa_reference all load-time enforced).
- The spec explicitly states "TOOL_MIN_AAL addition required" for both
  adapters (§4.1, §4.2).
- A backfill task to add existing adapters to `TOOL_MIN_AAL` is out of scope
  here — tracked separately if needed.

`data-model.md` includes the exact `TOOL_MIN_AAL` diff.

---

## 7. Test Strategy

| Test type | NFA | MOHW | Notes |
|---|---|---|---|
| Input schema validation (happy) | YES | YES | Pydantic v2 `model_validate` with fixture params |
| Input schema validation (error) | YES | YES | `extra="forbid"`, required field missing, enum mismatch |
| `Layer3GateViolation` when `handle()` called directly | YES | YES | Defence-in-depth test |
| Executor returns `auth_required` when `session_identity=None` | YES | YES | Layer 3 gate contract |
| BM25 discovery via `lookup(mode="search")` top-5 | YES | YES | Uses `search_hint` bilingual keywords |
| `recall@5` no regression on existing eval set | — | — | Covered by `tests/eval/test_retrieval.py` smoke test |
| Live upstream call | **NONE** | **NONE** | Constitution §IV: no live `data.go.kr` in CI |
| Recorded fixture (synthetic) | `tests/fixtures/nfa119/nfa_emergency_info_service.json` | `tests/fixtures/ssis/mohw_welfare_eligibility_search.json` | Synthetic data; no real PII |

Live-call tests (`@pytest.mark.live`) are deferred with the Layer 3 ship.

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| `TOOL_MIN_AAL` extension breaks existing tests | Low | No existing test relies on the absence of these rows |
| SSIS code table drift (lifeArray / intrsThemaArray) | Low | Enums are a snapshot; SSIS version 2.0 is stable; drift detection left to live-validation Epic |
| data.go.kr migrates `nfa119` endpoint to HTTPS-only | Low | Already using `https://` — no action |
| Synthetic fixture resembles real citizen data | Low | Use spec-prescribed values: `천안동남소방서`, `출산가정 방문서비스` (known-published service names, no PII) |
| Spec example code for `intrsThemaArray` is `010` not `080` | Verified | Plan authors the correct enum; spec prose is informational |
| DPA template drafting delays Layer 3 ship | Medium | Placeholder stub file committed alongside adapter; drafting task tracked under Epic #15 |

---

## 9. Outstanding Questions

None. All blocking clarifications resolved. All deferred items tracked.
Ready to advance to `/speckit-tasks`.
