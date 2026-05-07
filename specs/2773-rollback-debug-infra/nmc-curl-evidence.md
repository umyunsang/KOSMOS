# NMC Live Contract Curl Evidence

Date: 2026-05-06

Purpose: document the live contract evidence behind the `nmc_emergency_search`
operation split. This evidence is from direct `curl` probes only; no helper
script was used for endpoint/key/parameter validation.

## Local Official Source

- `~/Downloads/NIA-IFT-OpenAPI활용가이드-01.국립중앙의료원-응급의료정보조회서비스_V4 (2).hwp`
- `getEgytLcinfoInqire`: required `WGS84_LON`, `WGS84_LAT`; optional `pageNo`, `numOfRows`.
- `getEgytListInfoInqire`: optional `Q0`, `Q1`, `QN`, `ORD`, `pageNo`, `numOfRows`.

## Sanitized Curl Probes

Kakao keyword search resolved `하단역` to the official station POI:

```bash
curl -sS -G 'https://dapi.kakao.com/v2/local/search/keyword.json' \
  -H "Authorization: KakaoAK ${KOSMOS_KAKAO_API_KEY}" \
  --data-urlencode 'query=하단역' \
  --data-urlencode 'size=1'
```

Result summary: `total=63`, first result `하단역 부산1호선`, `x=128.966786546793`, `y=35.1062385683347`.

Kakao coord2regioncode resolved the coordinate to both legal and administrative regions:

```bash
curl -sS -G 'https://dapi.kakao.com/v2/local/geo/coord2regioncode.json' \
  -H "Authorization: KakaoAK ${KOSMOS_KAKAO_API_KEY}" \
  --data-urlencode 'x=128.966786546793' \
  --data-urlencode 'y=35.1062385683347' \
  --data-urlencode 'input_coord=WGS84' \
  --data-urlencode 'output_coord=WGS84'
```

Result summary: `total=2`; legal row `부산광역시/사하구/하단동`, code `2638010300`; admin row `부산광역시/사하구/하단2동`, code `2638056200`.

NMC coordinate operation accepted the key and official parameters but returned no Hadan rows:

```bash
curl -sS -G 'https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytLcinfoInqire' \
  --data-urlencode "serviceKey=${KOSMOS_DATA_GO_KR_API_KEY}" \
  --data-urlencode 'WGS84_LON=128.966786546793' \
  --data-urlencode 'WGS84_LAT=35.1062385683347' \
  --data-urlencode 'pageNo=1' \
  --data-urlencode 'numOfRows=5' \
  --data-urlencode '_type=json'
```

Result summary: `resultCode=00`, `resultMsg=NORMAL SERVICE.`, `totalCount=0`, `items=""`.

NMC regional list operation accepted the same key and returned the expected Saha-gu ER row:

```bash
curl -sS -G 'https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytListInfoInqire' \
  --data-urlencode "serviceKey=${KOSMOS_DATA_GO_KR_API_KEY}" \
  --data-urlencode 'Q0=부산광역시' \
  --data-urlencode 'Q1=사하구' \
  --data-urlencode 'ORD=ADDR' \
  --data-urlencode 'pageNo=1' \
  --data-urlencode 'numOfRows=10' \
  --data-urlencode '_type=json'
```

Result summary: `resultCode=00`, `resultMsg=NORMAL SERVICE.`, `totalCount=1`, first item `큐병원`, `dutyTel3=051-207-4044`, `dutyEmclsName=응급실운영신고기관`, `wgs84Lat=35.10658381193713`, `wgs84Lon=128.96489218029475`.

## Design Consequence

The coordinate operation returning `totalCount=0` is not a credential,
endpoint, or parameter failure. It is an operation-coverage mismatch for this
citizen scenario. KOSMOS therefore models the two official NMC operations
explicitly via `mode="coordinate"` and `mode="region"`. It does not implement
an automatic fallback from one operation to the other.
