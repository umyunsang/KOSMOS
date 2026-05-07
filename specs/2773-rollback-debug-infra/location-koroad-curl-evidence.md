# Location + KOROAD Curl Evidence — 2026-05-06

Purpose: prove the real upstream request contracts before changing adapter code. Secrets are redacted; commands show environment-variable expansion only.

## Kakao keyword: `강남역`

```bash
curl -sS -G --max-time 20 \
  "https://dapi.kakao.com/v2/local/search/keyword.json" \
  -H "Authorization: KakaoAK ${KOSMOS_KAKAO_API_KEY}" \
  --data-urlencode "query=강남역" \
  --data-urlencode "size=1"
```

Observed:

```json
{
  "http_code": 200,
  "place_name": "강남역 2호선",
  "address_name": "서울 강남구 역삼동 858",
  "road_address_name": "서울 강남구 강남대로 지하 396",
  "x": "127.02800140627488",
  "y": "37.49808633653005",
  "total_count": 2577
}
```

## Kakao coord2regioncode from `강남역` coordinates

```bash
curl -sS -G --max-time 20 \
  "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json" \
  -H "Authorization: KakaoAK ${KOSMOS_KAKAO_API_KEY}" \
  --data-urlencode "x=127.02800140627488" \
  --data-urlencode "y=37.49808633653005" \
  --data-urlencode "input_coord=WGS84"
```

Observed:

```json
{
  "http_code": 200,
  "total_count": 2,
  "documents": [
    {
      "region_type": "B",
      "code": "1168010100",
      "address_name": "서울특별시 강남구 역삼동"
    },
    {
      "region_type": "H",
      "code": "1168064000",
      "address_name": "서울특별시 강남구 역삼1동"
    }
  ]
}
```

Conclusion: for POI/station queries where Kakao `search/address` may be empty, the official chain is `search/keyword` coordinates → `coord2regioncode`, not a guessed administrative code.

## KOROAD hazard endpoint pagination

Initial raw curl with curl's default User-Agent returned:

```json
{"http_code": 400, "body": "Request Blocked"}
```

The same request with browser-like or `python-httpx/0.28.1` User-Agent succeeds. This isolates the 400 to data.go.kr edge filtering for curl's default UA, not to endpoint/key/parameter invalidity.

```bash
curl -sS -A "Mozilla/5.0" -G --max-time 20 \
  "https://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg" \
  --data-urlencode "serviceKey=${KOSMOS_DATA_GO_KR_API_KEY}" \
  --data-urlencode "searchYearCd=2025119" \
  --data-urlencode "siDo=11" \
  --data-urlencode "guGun=680" \
  --data-urlencode "numOfRows=1" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "type=json"
```

Observed:

```json
{
  "http_code": 200,
  "resultCode": "00",
  "resultMsg": "NORMAL_CODE",
  "totalCount": 3,
  "numOfRows": 1,
  "pageNo": 1,
  "first_spot_nm": "서울 강남구 논현동(신사역교차로 부근)"
}
```

The same endpoint accepts `numOfRows=20` and returns `resultCode="00"`, `totalCount=3`, `pageNo=1`; the service echoes `numOfRows=3` because only three records exist for that query.
