# KMA APIHub Structured Adapters

Spec 2800 registers KMA APIHub structured `typ02/openApi` operations as
read-only `find` adapters.

## Scope

- Source host: `https://apihub.kma.go.kr`
- API family: `/api/typ02/openApi/<service>/<operation>`
- Cataloged operations: 85
- Active registered operations: 78
- Credential env var: `UMMAYA_KMA_API_HUB_AUTH_KEY`
- Auth query parameter: `authKey`
- Legacy `UMMAYA_DATA_GO_KR_API_KEY` / `serviceKey`: not accepted for this
  adapter family

## Catalog Evidence

The 2026-05-24 APIHub catalog pass found 235 sample URLs across category pages.
The evidence file is
[`specs/2800-kma-apihub-openapi-adapters/evidence/apihub-catalog-2026-05-24.md`](../../../specs/2800-kma-apihub-openapi-adapters/evidence/apihub-catalog-2026-05-24.md).
Only 85 structured `typ02/openApi` operations are cataloged here. The remaining
`typ01`, `typ03`, `typ05`, `typ06`, and `typ09` URL families have different
response contracts and are tracked separately.

The 2026-05-24 follow-up portal pass submitted the remaining utilization
application forms that were visible in the logged-in Chrome session. A later My
Page verification showed `87` approved utilization entries: all `85` structured
`/openApi` operations plus two non-structured `/url` operations. The structured
catalog therefore marks all wrapped APIHub operations as `approved`.

Seven operations are retained in the catalog but are not registered as active
callable tools:

- Three `GtsInfoService` operations are marked `upstream_unavailable` because
  direct `curl` probes on 2026-05-25 returned `resultCode=02` / `DB_ERROR`.
- Four UM `NwpModelInfoService` operations are marked `retired`. The official
  APIHub numerical-model page states UM model production ended after
  `2026-03-31`, and direct `curl` probes on 2026-05-25 returned
  `resultCode=99` with the same production-stopped message.

If KMA still returns HTTP 401 or 403 for an active operation, the adapter
reports the upstream authorization failure instead of falling back to
data.go.kr or fabricating weather data.

## Runtime Shape

Each generated adapter:

- exposes KMA request parameters as snake_case Pydantic fields
- omits `authKey` from model-visible input
- injects `authKey` from `UMMAYA_KMA_API_HUB_AUTH_KEY`
- parses KMA XML or JSON `response.header/body/items.item`
- returns a `LookupRecord` envelope through the existing `ToolExecutor`

For cataloged GTS `GtsInfoService` operations, `tm` and `stnId` are
model-required fields if the operation is re-enabled. The official request
table gives defaults for `numOfRows`, `pageNo`, and `dataType`, but not for the
GTS station identifier.

Specialized citizen-weather tools remain the preferred user-facing route for
forecast/current-weather questions:

- `kma_forecast_fetch`
- `kma_current_observation`
- `kma_short_term_forecast`
- `kma_ultra_short_term_forecast`

The generic APIHub wrappers are broad coverage adapters, not replacements for
the specialized weather chain.
