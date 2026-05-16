# Usage Notes: 경상남도 의령군_민방위대피시설

## Wrapping Summary

- Proposed adapter ID: `data_go_kr_uiryeong_civil_defense_shelters`
- Provider: 경상남도 의령군
- Primitive: `resolve_location`
- Secondary primitive: `lookup`
- Data format: XML
- API type: REST GET
- Authentication: `ServiceKey`
- Traffic: development account 1,000 requests/day

## Endpoint

```text
GET http://data.uiryeong.go.kr/rest/uiryeongclnsshuntfclty/getUiryeongclnsshuntfcltyList
```

Provider guide also lists the service base URL:

```text
http://data.uiryeong.go.kr/rest/uiryeongclnsshuntfclty
```

## Request Parameters

| Name | Required | Sample | Meaning |
| --- | --- | --- | --- |
| `ServiceKey` | yes | issued key | data.go.kr service key |
| `pageNo` | no | `1` | page number, default 1 |
| `numOfRows` | no | `10` | page size, default 10 |
| `clns_shunt_fclty_nm` | no | `군민회관` | civil-defense shelter name |

Example:

```text
http://data.uiryeong.go.kr/rest/uiryeongclnsshuntfclty/getUiryeongclnsshuntfcltyList?ServiceKey={SERVICE_KEY}&numOfRows=10&pageNo=1
```

## Response Fields To Normalize

| Field | Meaning |
| --- | --- |
| `resultCode` | result code, `00` on success |
| `resultMsg` | result message |
| `totalCount` | total result count |
| `clns_shunt_fclty_nm` | shelter name |
| `clns_shunt_fclty_se` | shelter type, such as public-use |
| `rdnmadr` | road-name address |
| `adres` | lot-number address |
| `la` | latitude |
| `lo` | longitude |
| `clns_shunt_fclty_ar` | shelter area in square meters |
| `shunt_posbl_nmpr_co` | shelter capacity |
| `opn_at` | open status, `Y` or `N` |
| `ordtm_prcuse_ty` | ordinary-use type |
| `mgc_telno` | managing agency phone |
| `mgc_nm` | managing agency name |
| `data_stdr_de` | data standard date |

## Citizen Query Handling

For "의령군에서 가까운 민방위 대피시설 알려줘", UMMAYA should:

1. Resolve the user's location to Uiryeong-gun or ask for locality if missing.
2. Call the API with `pageNo=1` and enough `numOfRows` to retrieve the local shelter set.
3. Geocode or compare coordinates when a user location is available.
4. Return ranked shelters with address, capacity, open status, manager contact, and data date.
5. Include a safety disclaimer that the API is an official facility dataset, not a real-time evacuation order.

For "군민회관 대피시설 정보 알려줘", UMMAYA should call with `clns_shunt_fclty_nm=군민회관` and return the matched shelter fields directly.

## Adapter Notes

- Parse XML under `rfcOpenApi/header` and `rfcOpenApi/body/data/list`.
- Treat non-`00` `resultCode` as a provider error.
- Do not assume `adres`, `ordtm_prcuse_ty`, `mgc_telno`, or `mgc_nm` are always present because the spec marks several of them optional.
- Keep `ServiceKey` out of logs and fixture files.
- Live credential checks must be manual or explicitly marked `live`; never run them in CI.

