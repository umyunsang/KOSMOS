# KOSMOS Plugin System

Ministries, agencies, and citizen developers contribute KOSMOS tool adapters via the plugin system.  
Target audience: 공공기관 개발자 · 지자체 · 시민 기여자 · 민간 제휴 기관.

## Five-tier developer-experience package

| Tier | Deliverable | Status |
|---|---|---|
| **Tier 1 · Start** | `kosmos-plugin-template` 저장소 · `kosmos plugin init <name>` CLI · `quickstart.ko.md` / `quickstart.en.md` | planned |
| **Tier 2 · Guide** | `architecture.md` · `pydantic-schema.md` · `search-hint.md` · `permission-tier.md` · `data-go-kr.md` · `live-vs-mock.md` · `testing.md` | planned |
| **Tier 3 · Examples** | `kosmos-plugin-seoul-subway` (지하철) · `kosmos-plugin-post-office` (우체국) · `kosmos-plugin-nts-homtax` (홈택스 Mock) · `kosmos-plugin-nhis-check` (건강검진) | planned |
| **Tier 4 · Submit** | `.github/ISSUE_TEMPLATE/plugin-submission.yml` · `.github/workflows/plugin-validation.yml` · `review-checklist.md` (50 items) · `security-review.md` | planned |
| **Tier 5 · Registry** | 중앙 카탈로그 · `kosmos plugin list` / `kosmos plugin install` · 서명 검증 · 버전 관리 | planned |

Full requirements: `docs/vision.md` + 2026-04-24 requirements-tree approval (L1-B B8 "Full 5-tier DX package").

## Plugin contract (summary)

Every plugin SHALL:

1. **Implement the shared `Tool.ts` interface** (TS+Python registration both supported). The interface declares `id · name_ko · primitive · permission_tier · ministry · mode(live|mock) · input_schema · output_schema · search_hint · pipa_class · auth_level` among other fields (see `docs/tool-adapters.md`).
2. **Use the reserved-name discipline** — root primitives `lookup` · `submit` · `verify` · `subscribe` are reserved. Plugins may introduce new verbs, but MUST namespace as `plugin.<plugin_id>.<verb>`.
3. **Declare permission at the adapter level** — no primitive-level default. Layer 1 / 2 / 3 per adapter.
4. **Ship a manifest (`plugin-manifest.yaml`)** declaring: permission tiers, PII handling, data retention, dependency tree, KOSMOS runtime version compatibility.
5. **Include a PIPA custodian statement** when the plugin processes personal data — the contributing organisation accepts §26 custodian responsibility. Template in `security-review.md`.
6. **Pass the validation workflow** before merge — JSON-Schema conformance, permission-tier linting, search-hint bilingual check, secret scan, SBOM.

## Documentation language policy

Korean is primary. English is secondary.

Rationale: 공공기관 기여자 대상이므로 한국어로 먼저 작성하고, 영문은 cross-border 기여자를 위한 보조 번역.

## See also

- `docs/vision.md` § Layer 2 (Tool System) and § Inspiration
- `docs/tool-adapters.md` — adapter field reference
- `docs/api/` — built-in adapter specifications (per ministry)
- `AGENTS.md § Plugin contributors`
