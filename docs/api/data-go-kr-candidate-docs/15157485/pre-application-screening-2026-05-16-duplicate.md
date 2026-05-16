# Pre-application Screening: data.go.kr API 15157485

- Date: 2026-05-16
- Portal URL: https://www.data.go.kr/data/15157485/openapi.do
- API name: 부산시설공단_장례비산출 정보 조회 서비스
- Provider: 부산시설공단
- Category: 사회복지 - 사회복지일반
- Portal base URL shown: `https://apis.data.go.kr/B552587/FuneralCostsService_v2`
- Portal operations shown: `getFCAreaList_v2`, `getFCGoods_v2`, `getFCItem_v2`, `getFCOffering_v2`, `getFCGPrice_v2`, `getFCTotal_v2`

## Citizen-query fit

| Citizen natural-language query | UMMAYA interpretation | API route | Citizen-facing answer enabled |
| --- | --- | --- | --- |
| 부산 영락공원에서 장례를 치르면 공공 장사시설 비용이 얼마나 나와? | Funeral cost lookup for a public facility | Use area, goods, item, offering, guest-cost, and total-cost endpoints | Itemized public funeral cost estimate |
| 장례식장 사용료와 장례용품 가격을 항목별로 알려줘. | Public funeral fee and goods lookup | Use `getFCAreaList_v2`, `getFCGoods_v2`, `getFCItem_v2` | Official fee and goods price list |
| 장례 지원 신청 전에 예상 비용을 정리해줘. | Cost context before welfare/support workflow | Use `getFCTotal_v2` with supporting fee endpoints | Cost summary that can be composed with welfare guidance |

## Screening result

Rejected for this additional-candidate collection because the same data.go.kr API ID is already an active UMMAYA verified adapter:

- Existing adapter: `bfc_funeral_area_fee`
- Existing catalog entry: `docs/api/verified-data-go-kr/README.md`
- Existing schema: `docs/api/schemas/bfc_funeral_area_fee.json`
- Existing spec references: `specs/2797-data-go-kr-verified-adapters/spec.md`

This API is a strong UMMAYA fit, but it is not counted as a new additional API candidate and no new utilization application was submitted.
