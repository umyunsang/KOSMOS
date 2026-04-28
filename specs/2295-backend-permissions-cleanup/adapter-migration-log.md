# Adapter Migration Log — Epic δ #2295 Backend Permissions Cleanup + AdapterRealDomainPolicy

**Date**: 2026-04-29 · **Spec**: [spec.md](./spec.md) · **Branch**: `2295-backend-permissions-cleanup`
**Authority**: AGENTS.md § CORE THESIS · `.specify/memory/constitution.md § II + § III`

---

## Residue Deletions

Files deleted from `src/kosmos/permissions/` (Spec 033 KOSMOS-invented residue).

| path | importers | disposition | migration_target |
|------|-----------|-------------|-----------------|
| `src/kosmos/permissions/aal_backstop.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/adapter_metadata.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/bypass.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/cli.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/credentials.py` | `src/kosmos/recovery/auth_refresh.py`, `src/kosmos/permissions/steps/step1_config.py` | delete | callers deleted |
| `src/kosmos/permissions/killswitch.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/mode_bypass.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/mode_default.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/models.py` | multiple — see src/kosmos/cli/repl.py, engine/*, tests/* | delete | SessionContext etc. removed |
| `src/kosmos/permissions/modes.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/pipeline.py` | engine/*, cli/app.py, tests/* | delete | callers deleted |
| `src/kosmos/permissions/pipeline_v2.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/prompt.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/rules.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/session_boot.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/synthesis_guard.py` | (tracked below) | delete | callers deleted |
| `src/kosmos/permissions/steps/` (directory) | pipeline.py only | delete | directory deleted |

---

## Spec 035 Receipt Set

Files preserved in `src/kosmos/permissions/` (Spec 035 receipt set).

| path | role | references |
|------|------|-----------|
| `src/kosmos/permissions/ledger.py` | Append-only consent receipt ledger | [Spec 035, Spec 1636] |
| `src/kosmos/permissions/action_digest.py` | Citizen action → SHA-256 digest | [Spec 035] |
| `src/kosmos/permissions/hmac_key.py` | HMAC signing key management | [Spec 035] |
| `src/kosmos/permissions/canonical_json.py` | RFC 8785 JCS canonical JSON | [Spec 035] |
| `src/kosmos/permissions/audit_coupling.py` | Audit ledger ↔ OTEL coupling | [Spec 035, Spec 021] |
| `src/kosmos/permissions/ledger_verify.py` | Receipt chain verification | [Spec 035] |
| `src/kosmos/permissions/otel_emit.py` | OTEL span emission adapter | [Spec 021] |
| `src/kosmos/permissions/otel_integration.py` | OTEL integration bootstrap | [Spec 021] |

---

## Adapter Migrations

18 adapter metadata migrations — KOSMOS-invented fields removed + `policy: AdapterRealDomainPolicy` added.

| adapter_id | adapter_path | agency | removed_fields | policy.real_classification_url | policy.citizen_facing_gate | policy_url_verified |
|-----------|-------------|--------|---------------|-------------------------------|---------------------------|---------------------|
| `koroad_accident_hazard_search` | `src/kosmos/tools/koroad/accident_hazard_search.py` | 도로교통공단 (KOROAD) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.koroad.or.kr/main/web/policy/data_use.do` | read-only | false (TODO) |
| `koroad_accident_search` | `src/kosmos/tools/koroad/koroad_accident_search.py` | 도로교통공단 (KOROAD) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.koroad.or.kr/main/web/policy/data_use.do` | read-only | false (TODO) |
| `kma_current_observation` | `src/kosmos/tools/kma/kma_current_observation.py` | 기상청 (KMA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.kma.go.kr/data/policy.html` | read-only | false (TODO) |
| `kma_weather_alert_status` | `src/kosmos/tools/kma/kma_weather_alert_status.py` | 기상청 (KMA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.kma.go.kr/data/policy.html` | read-only | false (TODO) |
| `kma_ultra_short_term_forecast` | `src/kosmos/tools/kma/kma_ultra_short_term_forecast.py` | 기상청 (KMA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.kma.go.kr/data/policy.html` | read-only | false (TODO) |
| `kma_forecast_fetch` | `src/kosmos/tools/kma/forecast_fetch.py` | 기상청 (KMA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.kma.go.kr/data/policy.html` | read-only | false (TODO) |
| `kma_pre_warning` | `src/kosmos/tools/kma/kma_pre_warning.py` | 기상청 (KMA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.kma.go.kr/data/policy.html` | read-only | false (TODO) |
| `kma_short_term_forecast` | `src/kosmos/tools/kma/kma_short_term_forecast.py` | 기상청 (KMA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.kma.go.kr/data/policy.html` | read-only | false (TODO) |
| `hira_hospital_search` | `src/kosmos/tools/hira/hospital_search.py` | 건강보험심사평가원 (HIRA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.hira.or.kr/bbs/informationNotice.do?pgmid=HIRAA030011000000` | read-only | false (TODO) |
| `nmc_emergency_search` | `src/kosmos/tools/nmc/emergency_search.py` | 국립의료원 응급의료 (NMC) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.nemc.or.kr/info/dataInfoView.do` | read-only | false (TODO) |
| `nfa_emergency_info` | `src/kosmos/tools/nfa119/emergency_info_service.py` | 소방청 (NFA) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.nfa.go.kr/nfa/main/contents.do?menuKey=66` | read-only | false (TODO) |
| `mohw_welfare_eligibility_search` | `src/kosmos/tools/ssis/welfare_eligibility_search.py` | 보건복지부 (MOHW) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://www.mohw.go.kr/react/policy/index.jsp?PAR_MENU_ID=06&MENU_ID=06` | read-only | false (TODO) |
| `mock_verify_mydata` | `src/kosmos/tools/mock/verify_mydata.py` | 마이데이터 (Mock) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://example.gov.kr/policy/mydata` | login | false # TODO: verify URL |
| `mock_verify_mobile_id` | `src/kosmos/tools/mock/verify_mobile_id.py` | 모바일신분증 (Mock) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://example.gov.kr/policy/mobile-id` | login | false # TODO: verify URL |
| `mock_verify_gongdong_injeungseo` | `src/kosmos/tools/mock/verify_gongdong_injeungseo.py` | 공동인증서 (Mock) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://example.gov.kr/policy/npki` | sign | false # TODO: verify URL |
| `mock_verify_geumyung_injeungseo` | `src/kosmos/tools/mock/verify_geumyung_injeungseo.py` | 금융인증서 (Mock) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://example.gov.kr/policy/geumyung-cert` | sign | false # TODO: verify URL |
| `mock_verify_ganpyeon_injeung` | `src/kosmos/tools/mock/verify_ganpyeon_injeung.py` | 간편인증 (Mock) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://example.gov.kr/policy/ganpyeon-injeung` | login | false # TODO: verify URL |
| `mock_verify_digital_onepass` | `src/kosmos/tools/mock/verify_digital_onepass.py` | 디지털원패스 (Mock) | auth_level, pipa_class, is_irreversible, dpa_reference, requires_auth, is_personal_data | `https://example.gov.kr/policy/digital-onepass` | login | false # TODO: verify URL |
