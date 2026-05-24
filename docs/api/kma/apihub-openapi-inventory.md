# KMA API Hub OpenAPI Inventory

This inventory records the KMA API Hub structured OpenAPI surface that should
drive future UMMAYA adapter wrapping. It is based on the official KMA API Hub
category pages and the logged-in Chrome verification performed on 2026-05-24.

Scope:

- Host: `https://apihub.kma.go.kr`
- Structured OpenAPI pattern: `/api/typ02/openApi/<service>/<operation>`
- Credential query parameter: `authKey`
- UMMAYA credential env var: `UMMAYA_KMA_API_HUB_AUTH_KEY`
- Out of scope for this structured inventory: `typ01/url`, `typ03/cgi`,
  `typ05`, `typ06`, image, binary, and download endpoints. These require
  separate adapter contracts because they do not share the `typ02/openApi`
  envelope pattern.

## Category Counts

| seqApi | Category | Structured `typ02/openApi` endpoints |
|---:|---|---:|
| 2 | Ground observation | 12 |
| 3 | Marine observation | 14 |
| 4 | Upper-air observation | 6 |
| 5 | Radar | 2 |
| 6 | Satellite | 20 |
| 7 | Earthquake/volcano | 2 |
| 8 | Typhoon | 1 |
| 9 | Numerical model | 8 |
| 10 | Forecast/warning | 7 |
| 971 | Convergence weather | 0 |
| 14 | Aviation weather | 10 |
| 12 | World weather | 3 |
|  | Total cataloged | 85 |
|  | Active registered | 78 |

## Endpoint List

### seqApi=2 Ground Observation

- `SfcYearlyInfoService/getYearSumry`
- `SfcYearlyInfoService/getYearSumry2`
- `SfcYearlyInfoService/getAvgTaAnamaly`
- `SfcYearlyInfoService/getRnAnamaly`
- `SfcYearlyInfoService/getStnPhnmnData`
- `SfcYearlyInfoService/getStnPhnmnData2`
- `SfcYearlyInfoService/getStnPhnmnData3`
- `SfcMtlyInfoService/getNote`
- `SfcMtlyInfoService/getSfcStnLstTbl`
- `SfcMtlyInfoService/getMmSumry`
- `SfcMtlyInfoService/getMmSumry2`
- `SfcMtlyInfoService/getDailyWthrData`

### seqApi=3 Marine Observation

- `SeaMtlyInfoService/getNote`
- `SeaMtlyInfoService/getBuoyLstTbl`
- `SeaMtlyInfoService/getLhawsLstTbl`
- `SeaMtlyInfoService/getWaveBuoyLstTbl`
- `SeaMtlyInfoService/getObsOpenYear`
- `SeaMtlyInfoService/getBuoyMmSumry`
- `SeaMtlyInfoService/getBuoyMmSumry2`
- `SeaMtlyInfoService/getDailyBuoy`
- `SeaMtlyInfoService/getLhawsMmSumry`
- `SeaMtlyInfoService/getLhawsMmSumry2`
- `SeaMtlyInfoService/getDailyLhaws`
- `SeaMtlyInfoService/getWaveBuoyMmSumry`
- `SeaMtlyInfoService/getWaveBuoyMmSumry2`
- `SeaMtlyInfoService/getDailyWaveBuoy`

### seqApi=4 Upper-Air Observation

- `UppMtlyInfoService/getNote`
- `UppMtlyInfoService/getUppLstTbl`
- `UppMtlyInfoService/getStdIsbrsfValue`
- `UppMtlyInfoService/getMaxWind`
- `UppMtlyInfoService/getTaHmLevel`
- `UppMtlyInfoService/getWindLevel`

### seqApi=5 Radar

- `WthrRadarInfoService/getCompCappiQcdAll`
- `WthrRadarInfoService/getCompCappiQcdArea`

### seqApi=6 Satellite

- `CloudSatlitInfoService/getGk2aclaArea`
- `CloudSatlitInfoService/getGk2adcoewArea`
- `CloudSatlitInfoService/getGk2afogArea`
- `CloudSatlitInfoService/getGk2aappsArea`
- `CloudSatlitInfoService/getGk2acldArea`
- `CloudSatlitInfoService/getGk2aclaAll`
- `CloudSatlitInfoService/getGk2adcoewAll`
- `CloudSatlitInfoService/getGk2afogAll`
- `CloudSatlitInfoService/getGk2aappsAll`
- `CloudSatlitInfoService/getGk2acldAll`
- `WthrSatlitInfoService/getGk2aIrAll`
- `WthrSatlitInfoService/getGk2aNrAll`
- `WthrSatlitInfoService/getGk2aSwAll`
- `WthrSatlitInfoService/getGk2aViAll`
- `WthrSatlitInfoService/getGk2aWvAll`
- `WthrSatlitInfoService/getGk2aIrArea`
- `WthrSatlitInfoService/getGk2aNrArea`
- `WthrSatlitInfoService/getGk2aSwArea`
- `WthrSatlitInfoService/getGk2aViArea`
- `WthrSatlitInfoService/getGk2aWvArea`

### seqApi=7 Earthquake/Volcano

- `EqkInfoService/getEqkMsgList`
- `EqkInfoService/getEqkMsg`

### seqApi=8 Typhoon

- `SfcYearlyInfoService/getTyphoonList`

### seqApi=9 Numerical Model

- `KIMModelInfoService/getKIMLdapsUnisAll`
- `KIMModelInfoService/getKIMRdapsUnisAll`
- `KIMModelInfoService/getKIMLdapsUnisArea`
- `KIMModelInfoService/getKIMRdapsUnisArea`
- `NwpModelInfoService/getLdapsUnisAll` — cataloged, retired, not registered
- `NwpModelInfoService/getLdapsUnisArea` — cataloged, retired, not registered
- `NwpModelInfoService/getRdapsUnisAll` — cataloged, retired, not registered
- `NwpModelInfoService/getRdapsUnisArea` — cataloged, retired, not registered

### seqApi=10 Forecast/Warning

- `VilageFcstMsgService/getWthrSituation`
- `VilageFcstMsgService/getLandFcst`
- `VilageFcstMsgService/getSeaFcst`
- `VilageFcstInfoService_2.0/getUltraSrtNcst`
- `VilageFcstInfoService_2.0/getUltraSrtFcst`
- `VilageFcstInfoService_2.0/getVilageFcst`
- `VilageFcstInfoService_2.0/getFcstVersion`

### seqApi=14 Aviation Weather

- `AmmIwxxmService/getMetar`
- `SfcYearlyInfoService/getrAirStnLstTbl`
- `SfcYearlyInfoService/getAirStnInfo`
- `SfcYearlyInfoService/getAirStnInfo2`
- `SfcYearlyInfoService/getAirStnInfo3`
- `SfcYearlyInfoService/getSfcStnLstTbl`
- `SfcYearlyInfoService/getNote`
- `SfcMtlyInfoService/getDailyAirData`
- `SfcMtlyInfoService/getrAirStnLstTbl`
- `SfcMtlyInfoService/getAirNote`

### seqApi=12 World Weather

- `GtsInfoService/getBuoy` — cataloged, upstream unavailable, not registered
- `GtsInfoService/getSynop` — cataloged, upstream unavailable, not registered
- `GtsInfoService/getTemp` — cataloged, upstream unavailable, not registered

## Wrapping Notes

- The existing UMMAYA VilageFcst adapters now use KMA API Hub `authKey`.
- The three structured GTS endpoints are not part of the active tool surface
  because live APIHub probes return `resultCode=02` / `DB_ERROR`.
- The four UM `NwpModelInfoService` structured endpoints are not part of the
  active tool surface because APIHub documents UM model production as ended
  after 2026-03-31 and live probes return `resultCode=99`.
- GTS `stnId` is required for the cataloged structured GTS operations; only
  `numOfRows`, `pageNo`, and `dataType` have documented defaults on the
  official GTS request table.
- API utilization approval is separate from key issuance. A key can exist but
  still receive KMA API Hub 403 responses until the relevant API usage
  application is approved.
- `typ01/url/wrn_*` warning endpoints on API Hub are not part of this
  structured inventory. They should be handled by a separate spec because the
  response shape differs from the existing data.go.kr `WthrWrnInfoService`
  JSON/XML envelope.
