# ADR-001: Geocoding Provider Selection — Kakao Local API

**Status**: Accepted
**Date**: 2026-04-14
**Epic**: #288 (KOSMOS Geocoding Adapter)

---

## Context

KOSMOS tools (KOROAD accident search, KMA weather APIs) require precise Korean
administrative region codes (SidoCode, GugunCode) and KMA 5 km grid coordinates
(nx, ny).  Free-form address strings are the natural user-facing input, so a
geocoding service is needed to bridge the two.

Candidate providers evaluated:

| Provider | Coverage | Auth | Rate Limit | License |
|----------|----------|------|------------|---------|
| Kakao Local API | Comprehensive Korean addresses | REST API key | 300k/day free | Commercial (free tier) |
| Naver Maps API | Comprehensive Korean addresses | Client ID + Secret | 100k/day free | Commercial (free tier) |
| OpenStreetMap Nominatim | World coverage, Korea partial | None | 1 req/s | ODbL (open) |
| data.go.kr 도로명주소 API | Official Korean road addresses | data.go.kr key | Shared quota | Government open data |

---

## Decision

**Use Kakao Local API** (`dapi.kakao.com/v2/local/search/address.json`) as the
primary geocoding provider.

**Key selection criteria:**

1. **Korean address quality**: Kakao Maps has native Korean address parsing and
   returns structured `region_1depth_name` / `region_2depth_name` fields that
   map directly to SidoCode / GugunCode without additional parsing.

2. **Single API key**: Kakao Local API is authenticated via a single REST API
   key (`KOSMOS_KAKAO_API_KEY`), fitting the KOSMOS `KOSMOS_` env-var convention.
   This is independent of the `KOSMOS_DATA_GO_KR_API_KEY` used by KOROAD/KMA.

3. **Coordinate quality**: Returns `(x, y)` as longitude/latitude decimal strings
   with sufficient precision for the KMA 5 km LCC grid conversion.

4. **Road address preference**: Returns both legacy (구주소) and road address
   (도로명주소) blocks; the road address block is preferred for region name
   extraction as it uses up-to-date administrative names.

5. **Error taxonomy**: HTTP 401 (auth expired) and HTTP 429 (rate limit) map
   cleanly to `ToolExecutionError` subtypes; timeouts (5s) trigger the static
   KMA table fallback.

---

## Consequences

**Positive**:
- `address_to_region` and `address_to_grid` resolve Korean addresses with high
  accuracy, enabling natural-language region selection for KOROAD/KMA tools.
- Post-2023 administrative name changes (강원특별자치도, 전북특별자치도) are handled
  correctly by Kakao's native address normalisation.
- Static table fallback (`kma.grid_coords.lookup_grid`) ensures weather grid
  lookup remains functional when the Kakao API is unavailable.

**Negative / Trade-offs**:
- Adds a new dependency on a commercial API (`KOSMOS_KAKAO_API_KEY`).  This key
  must be managed separately from `KOSMOS_DATA_GO_KR_API_KEY`.
- Kakao's free tier (300k calls/day) is adequate for the current load model but
  must be monitored as usage scales.
- `is_personal_data=False` justified: address lookup returns public geographic
  data, not user-linked PII.  The queried address string itself is transient and
  not logged beyond DEBUG level.

**Fallback strategy**:
- On Kakao timeout, `address_to_grid` falls back to the static
  `REGION_TO_GRID` table via `kma.grid_coords.lookup_grid()`.
- `address_to_region` does not apply fallback (no static region-code table
  with sufficient coverage); callers receive `sido_code=None` and must handle
  the no-match case.

---

## Alternatives Rejected

- **Naver Maps**: Requires two separate credentials (Client-ID + Secret header),
  increasing secret-management complexity.
- **Nominatim**: 1 req/s rate limit is insufficient; Korean address structure
  quality is lower than Kakao/Naver.
- **data.go.kr road address API**: Shares the `KOSMOS_DATA_GO_KR_API_KEY` quota
  but returns raw jibun/road text, requiring additional parsing to extract
  region codes.  Kakao's structured response is simpler.

---

## References

- `docs/vision.md` § Layer 3 (Tool Adapters)
- `src/kosmos/tools/koroad/code_tables.py` — SidoCode, GugunCode enums
- `src/kosmos/tools/kma/grid_coords.py` — REGION_TO_GRID, latlon_to_grid
- `specs/015-geocoding-adapter/spec.md` — full feature specification
