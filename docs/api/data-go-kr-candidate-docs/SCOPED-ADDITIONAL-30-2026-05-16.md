# data.go.kr Additional 30 Candidate Intake (2026-05-16)

Reference bootstrap:
- UMMAYA thesis/docs: `docs/vision.md` keeps `data.go.kr` as one adapter family under the broader Korean public-service tool surface; active primitives are `find`, `locate`, `send`, and `check`.
- Tool-system requirements: `docs/requirements/ummaya-migration-tree.md` requires each callable agency module to be classified as Live, Mock, or scenario-only with adapter-level policy citations.
- Existing adapter catalog: `docs/api/README.md` defines adapter documentation expectations and keeps live API calls out of CI.
- CC restored-source reference: `.references/claude-code-sourcemap/restored-src/src/Tool.ts` and `.references/claude-code-sourcemap/restored-src/src/tools/MCPTool/MCPTool.ts` remain the later implementation contract reference.
- External primary source: official `data.go.kr` main page and detail pages observed on 2026-05-16. Computer Use verified the main-page category/provider discovery UI before this batch was collected.

This is an intake artifact only. It does not authorize adapter code changes and does not prove live callability. Each candidate still needs a direct sanitized `curl` probe after usage application/key availability.

## Diversity Counts

Categories:
- : 2
- 공공행정: 2
- 과학기술: 2
- 교육: 2
- 국토관리: 2
- 농축수산: 2
- 문화관광: 2
- 보건의료: 2
- 사회복지: 2
- 산업고용: 2
- 식품건강: 2
- 재난안전: 2
- 재정금융: 2
- 통일외교안보: 2
- 환경기상: 2

Provider types:
- : 2
- 공공기관: 14
- 국가행정기관: 12
- 자치행정기관: 2

## Candidate Table

| # | ID | Category | Provider type | Provider | Candidate | Primitive | Swagger | Docs |
|---:|---|---|---|---|---|---|---:|---:|
| 1 | `15158666` | 교육 | 공공기관 | 한국대학교육협의회 | 한국대학교육협의회_대학별 학과정보_GW | `find` | yes | 0 |
| 2 | `15158665` | 교육 | 공공기관 | 한국대학교육협의회 | 한국대학교육협의회_대학 및 전문대학정보_GW | `find` | yes | 0 |
| 3 | `15012966` | 국토관리 | 국가행정기관 | 국토교통부 | 국토교통부_회계감사보고서 정보 | `check` | yes | 0 |
| 4 | `15108378` | 국토관리 | 국가행정기관 | 국토교통부 | 국토교통부_마이홈포털 예비입주자 대기현황 조회서비스 | `send/find` | yes | 1 |
| 5 | `15129459` | 공공행정 | 국가행정기관 | 조달청 | 조달청_나라장터 계약과정통합공개서비스 Update | `find` | yes | 1 |
| 6 | `15129469` | 공공행정 | 국가행정기관 | 조달청 | 조달청_누리장터 민간계약정보 서비스 Update | `find` | yes | 1 |
| 7 | `15126397` | 재정금융 | 공공기관 | 한국자산관리공사 | 한국자산관리공사_국유부동산 매각현황 조회서비스 Update | `check` | yes | 0 |
| 8 | `15157413` | 재정금융 | 공공기관 | 한국예탁결제원 | 한국예탁결제원_주식정보서비스_GW | `find` | yes | 0 |
| 9 | `15157874` | 산업고용 | 공공기관 | 한국지역난방공사 | 한국지역난방공사_전기판매량 조회 서비스(GW) | `find` | yes | 0 |
| 10 | `15156698` | 산업고용 | 공공기관 | 한국서부발전(주) | 한국서부발전(주)_(AI친화)AI 디지털트윈 개발용 플랜트 운전 정보 조회 서비스 | `check` | yes | 0 |
| 11 | `15098826` | 사회복지 | 국가행정기관 | 보건복지부 | 보건복지부_보건·복지현황_독거장애인 서비스 지원 현황 | `find` | no | 1 |
| 12 | `15098827` | 사회복지 | 국가행정기관 | 보건복지부 | 보건복지부_보건·복지현황_독거노인 수 | `find` | no | 1 |
| 13 | `15154949` | 식품건강 | 국가행정기관 | 행정안전부 | 행정안전부_자원환경_건물위생관리업 조회서비스 | `locate/find` | yes | 1 |
| 14 | `15155028` | 식품건강 | 국가행정기관 | 행정안전부 | 행정안전부_기타_담배도매업 조회서비스 | `locate/find` | yes | 1 |
| 15 | `15157491` | 문화관광 | 공공기관 | 부산시설공단 | 부산시설공단_한마음스포츠센터 생활체육 프로그램 정보 조회 서비스 | `check` | yes | 0 |
| 16 | `15157481` | 문화관광 | 공공기관 | 부산시설공단 | 부산시설공단_공원시설 현황 조회 서비스 | `find` | yes | 0 |
| 17 | `15095149` | 보건의료 | 국가행정기관 | 기상청 | 기상청_영향예보_조회서비스 Update | `find` | yes | 1 |
| 18 | `15001698` | 보건의료 | 공공기관 | 건강보험심사평가원 | 건강보험심사평가원_병원정보서비스 | `find` | yes | 1 |
| 19 | `15155046` | 재난안전 | 국가행정기관 | 행정안전부 | 행정안전부_안전비상벨위치정보 조회서비스 | `locate/find` | yes | 1 |
| 20 | `15058257` | 재난안전 | 공공기관 | 한국도로교통공단 | 한국도로교통공단_고속도로 구간별 도로위험지수 | `check` | no | 1 |
| 21 | `15158982` | 환경기상 | 자치행정기관 | 대구광역시 | 대구광역시_시설정보 조회 서비스_GW | `locate/find` | yes | 0 |
| 22 | `15158981` | 환경기상 | 자치행정기관 | 대구광역시 | 대구광역시_유량정보 조회 서비스_GW | `check` | yes | 0 |
| 23 | `15085289` | 과학기술 | 국가행정기관 | 기상청 | 기상청_꽃가루농도위험지수 조회서비스(3.0) | `check` | yes | 1 |
| 24 | `15035122` | 과학기술 | 국가행정기관 | 과학기술정보통신부 우정사업본부 | 과학기술정보통신부 우정사업본부_우체국 종적 조회 | `check` | no | 1 |
| 25 | `15158646` | 농축수산 | 공공기관 | 한국농업기술진흥원 | 한국농업기술진흥원_보육업체소개_GW Update | `check` | yes | 0 |
| 26 | `15158640` | 농축수산 | 공공기관 | 한국농업기술진흥원 | 한국농업기술진흥원_종자생산현황_GW Update | `check` | yes | 0 |
| 27 | `15158400` | 통일외교안보 | 공공기관 | 한국국제협력단 | 한국국제협력단_통계정보조회 | `find` | yes | 0 |
| 28 | `15158399` | 통일외교안보 | 공공기관 | 한국국제협력단 | 한국국제협력단_사업정보(분야,국가)조회 | `check` | yes | 0 |
| 29 | `15158633` |  |  |  | 대전교통공사_부정승차정보 조회 서비스 | `send/find` | yes | 0 |
| 30 | `15141085` |  |  |  | 헌법재판소_판례정보 조회 서비스 | `check` | yes | 0 |

## Application Status

No additional batch applications were submitted yet. The application step creates or updates data.go.kr API usage access records, so I must get explicit action-time confirmation before clicking/submitting those forms through Computer Use.
