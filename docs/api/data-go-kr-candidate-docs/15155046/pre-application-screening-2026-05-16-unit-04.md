# Pre-Application Screening: 행정안전부_안전비상벨위치정보 조회서비스

- Unit: `04`
- Goal status: additional new UMMAYA data.go.kr candidate for the 100-new-API goal
- Source: <https://www.data.go.kr/data/15155046/openapi.do>
- data.go.kr ID: `15155046`
- Provider: 행정안전부
- Category: 공공질서및안전 - 안전관리
- Discovery path: data.go.kr main category navigation -> `재난안전` -> Open API list
- Duplicate check: no active UMMAYA adapter or non-candidate local reference found for `15155046`, `안전비상벨위치정보`, `emergency_call_box_info`, `비상벨`, or `방범용벨` outside the candidate-docs scratch area.
- Selection result: pass

## Citizen Query Fit

| Citizen natural-language query | UMMAYA interpretation | API request strategy | Response fields used | Citizen-facing answer |
|---|---|---|---|---|
| "내 주변 비상벨 위치 알려줘." | Resolve the user's address or current area, then find safety emergency bells near that area. | `GET /info` with `cond[LCTN_ROAD_NM_ADDR::LIKE]` for road-address fragments and pagination. If only coordinates are available, use `locate` first and rank returned WGS84 coordinates client-side. | `INSTL_PSTN`, `LCTN_ROAD_NM_ADDR`, `LCTN_LOTNO_ADDR`, `WGS84_LAT`, `WGS84_LOT`, `MNG_INST_NM`, `MNG_INST_TELNO` | Return nearby emergency bell locations, addresses, map coordinates, and managing agency contact. |
| "밤길에 경찰 연계 비상벨 있는 곳 찾아줘." | Find emergency bells and prioritize those linked to police. | Same endpoint, then filter/rank by `POLC_LINK_EN` and location fields. | `POLC_LINK_EN`, `LINK_MTH`, `INSTL_PLC_TYPE`, `EXTRA_FWK`, address and coordinate fields | Explain which nearby bells are police-linked and what extra function or link method is recorded. |
| "아이 통학길 주변에 방범용 비상벨이 있는지 확인해줘." | Use school/route address fragments to check installed safety bells along the route. | Use road-address LIKE for each resolved route area; paginate and de-duplicate by management number. | `SFTY_EMRGNCBLL_MNG_NO`, `INSTL_PRPS`, `INSTL_PLC_TYPE`, `INSTL_PSTN`, `LAST_CHCK_YMD`, `LAST_CHCK_RSLT_SE` | Summarize installed bells, purpose/location type, and latest inspection date/result when available. |

## UMMAYA Adapter Judgment

- Candidate adapter id: `mois_emergency_call_box_lookup`
- Primitive: `find`, with `locate` pre-processing for citizen addresses and area names
- Why it belongs in UMMAYA: it turns a common safety query into a location-grounded public-service response using nationwide, standard-format data rather than a generic web search.
- Expected usage: high for safety, night walking, child-route, campus, and housing-area questions; likely intermittent but broadly applicable across municipalities.
- Frequency estimate: moderate citizen-demand utility; the endpoint is read-only, daily updated, and development traffic is listed as 10,000 calls.
- Caveat: the description mentions EPSG:5174, while the response schema exposes WGS84 latitude/longitude fields. Adapter documentation should preserve both facts and validate sample coordinates before live classification.

## Official Contract Evidence

- Base URL: `https://apis.data.go.kr/1741000/emergency_call_box_info`
- Operation: `GET /info`
- Required params: `serviceKey`, `pageNo`, `numOfRows`
- Optional params: `returnType`, `cond[DAT_UPDT_PNT::GTE]`, `cond[DAT_UPDT_PNT::LT]`, `cond[LCTN_ROAD_NM_ADDR::LIKE]`, `cond[SFTY_EMRGNCBLL_INSTL_YR::GTE]`, `cond[OPN_ATMY_GRP_CD::EQ]`, `cond[DAT_CRTR_YMD::GTE]`, `cond[DAT_CRTR_YMD::LT]`
- Main response fields: `OPN_ATMY_GRP_CD`, `MNG_NO`, `SFTY_EMRGNCBLL_MNG_NO`, `INSTL_PRPS`, `INSTL_PLC_TYPE`, `INSTL_PSTN`, `LCTN_ROAD_NM_ADDR`, `LCTN_LOTNO_ADDR`, `WGS84_LAT`, `WGS84_LOT`, `LINK_MTH`, `POLC_LINK_EN`, `SECCO_LINK_EN`, `MNGOFC_LINK_EN`, `EXTRA_FWK`, `SFTY_EMRGNCBLL_INSTL_YR`, `LAST_CHCK_YMD`, `LAST_CHCK_RSLT_SE`, `MNG_INST_NM`, `MNG_INST_TELNO`, `DAT_CRTR_YMD`

## Captured Artifacts

- `data-go-kr-detail.html`
- `data-go-kr-inline-swagger.json`
- `gateway_swagger_guide.pdf`
- `openapi-schemaorg.json`
- `개방자치단체코드_영업상태코드.xlsx`
