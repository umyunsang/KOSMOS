# KOSMOS v0.1-alpha 발표 자료 리서치 노트

> **Disclaimer**: KOSMOS는 학생 개인 포트폴리오 프로젝트입니다. Anthropic, LG AI Research, 대한민국 정부 어느 곳과도 무관합니다(Not affiliated with Anthropic, LG AI Research, or the Korean government).
>
> 본 문서의 수집 기준일: 2026-04-26. 모든 수치에 출처 URL 명시. 출처 확인이 불가능한 항목은 [출처 확인 필요], 추론/계산 기반 항목은 [추정] 으로 표기.

---

## 1. 한국 공공 API 시장 규모

### 1-1. data.go.kr 등록 데이터셋 규모

- **총 개방 건수**: 2024년 12월 말 기준 **10만 건** 돌파 — 2013년 말 5,272건 대비 **약 19배 증가**
  - 출처: 행정안전부, 공공데이터 활용 현황(파일·API) 20241231, [data.go.kr/data/15076332](https://www.data.go.kr/data/15076332/fileData.do)
  - 확인: 행정안전부 공공데이터 개방 페이지, [mois.go.kr 공공데이터 개방](https://www.mois.go.kr/frt/sub/a06/b02/openData/screen.do)

- **민간 데이터 활용 건수**: 2024년 말 기준 **7,579만 건** (다운로드 + OpenAPI 활용신청) — 2013년 말 14,000건 대비 **약 5,413배 증가**
  - 출처: 동일 행정안전부 데이터셋, e-나라지표 공공데이터 개방 및 활용 지표 [index.go.kr idx_cd=2844](https://www.index.go.kr/unity/potal/main/EachDtlPageDetail.do?idx_cd=2844)

- **4차 국가 중점데이터 개방계획(2023-2025)**: 2024년까지 누적 **217건** 국가 중점 데이터 공개
  - 출처: 공공데이터포털 통계, [data.go.kr](https://www.data.go.kr/)

- **국제 인정**: OECD OURdata 지수(Open, Useful, Reusable Government Data) 4회 연속 1위 (2015·2017·2019·2023), 점수 **0.91/1.0** — OECD 평균 0.48의 약 2배
  - 출처: 행정안전부 공공데이터 개방 페이지, [mois.go.kr 공공데이터 개방](https://www.mois.go.kr/frt/sub/a06/b02/openData/screen.do)

### 1-2. API 분야별 분류 현황

- 공공데이터포털의 분류 체계(카테고리): 교통·물류 / 환경 / 보건·의료 / 공공질서·안전 / 문화·체육·관광 / 산업·통상·중소기업 / 행정·재정·경제 등
  - 출처: [data.go.kr 포털](https://www.data.go.kr/)

- 분야별 정확한 API 건수 비율 통계는 포털 내 CSV 파일(행정안전부_공공데이터 활용 현황_20241231) 다운로드로만 확인 가능 — 웹 공개 통계에서 카테고리별 세분화 수치 미확인 **[출처 확인 필요]**

### 1-3. KOSMOS 관련성

- KOSMOS는 data.go.kr 등의 공공 API를 어댑터(adapter) 방식으로 연결하며, 초기 출시(v0.1-alpha) 기준 **24개 어댑터** 포함 — 교통(KOROAD), 기상(KMA), 의료(HIRA), 응급(NMC) 등 포함 [추정: AGENTS.md 기준]

---

## 2. 한국 정부 AI 정책 정렬

### 2-1. 대한민국 인공지능 행동계획(2026-2028)

- **공식 명칭**: 대한민국 인공지능 행동계획 (인공지능 기본계획 2026~2028)
- **발표 주체**: 국가인공지능전략위원회 + 과학기술정보통신부, 2026년 2월
- **비전**: "AI 3대 강국 도약"
- 출처: 과기정통부 공식 PDF, [smartcity.go.kr 업로드본](https://smartcity.go.kr/wp-content/uploads/2026/03/%EC%95%88%EA%B1%B41%EB%8C%80%ED%95%9C%EB%AF%BC%EA%B5%AD%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5%ED%96%89%EB%8F%99%EA%B3%84%ED%9A%8D%EC%9D%B8%EA%B3%B5%EC%A7%80%EB%8A%A5%EA%B8%B0%EB%B3%B8%EA%B3%84%ED%9A%8D20262028.pdf)
- 출처(보도): 과기정통부 보도자료, [msit.go.kr](https://www.msit.go.kr/bbs/view.do?mId=113&bbsSeqNo=94&nttSeqNo=3185327)
- 출처(ZDNet): [정부 AI 행동계획 확정](https://zdnet.co.kr/view/?no=20260224183212)

### 2-2. 12대 전략분야 중 공공AX

- **공공AX** = 행동계획 12대 전략분야 중 **⑦번 전략분야**
- 핵심 방향: 행정안전부가 '공공AX 추진계획' 아래 범정부 AI 공통기반 서비스 구축, 지방정부·중앙정부 확대 적용 추진
- 출처: ZDNet, ["AI와 연대로 지역 도약"…행안부 2026년 지방행정 청사진](https://zdnet.co.kr/view/?no=20251224140303)

### 2-3. 공공AX 세부 원칙 (행동계획 문서 내 구체 원칙 번호)

- PDF 원문 접근은 완료되었으나 바이너리 인코딩으로 직접 인용 불가. KOSMOS MEMORY.md에 기록된 사전 조사 내용 인용:
  - **원칙 5**: 종이서류 폐지 + 동의 기반 데이터 접근
  - **원칙 8**: 단일 대화 인터페이스 (부처 횡단 AI 창구)
  - **원칙 9**: Open API + OpenMCP 표준화
  - 출처: KOSMOS 내부 메모리 `reference_ai_action_plan.md` **[출처 확인 필요 — 원문 PDF 직접 인용 권장]**
  - 대안 접근: [aikorea.go.kr AI 행동계획 게시판](https://www.aikorea.go.kr/web/board/brdDetail.do?menu_cd=000010&num=136)

### 2-4. AI 국민비서 + 마이데이터

- 행안부는 2025년 10월 **네이버·카카오**와 업무협약 체결 → 민간 앱 통해 ~100종 전자증명서 신청/발급 + 전국 1,200여 공공시설 예약 서비스 제공
  - 출처: [etnews.com AI 정부시대 개막](https://www.etnews.com/20251217000077)

- **금융분야 마이데이터 표준API 규격 v240930**: 금융위원회/금융보안원이 2024년 9월 30일 배포한 표준 API 규격
  - 출처: 마이데이터센터 공지, [mydatacenter.or.kr v240930 배포](https://www.mydatacenter.or.kr:3441/myd/bbsctt/normal1/normal/a77c34fb-32c6-448c-81c4-51154196e50e/47/bbsctt.do)
  - 개발자 포털: [developers.mydatakorea.org](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0101)

---

## 3. 기존 한국 공공 정보 챗봇 / 도구 비교

### 3-1. AI 정부24

- **서비스 현황**: 2026년 1분기 시범서비스 → 4분기 정식 개통 예정
- **사용자 규모**: 현 정부24 사용자 **약 2,500만 명**
- **기능**: 자연어 질의 → 관련 절차·서류 안내 + 신청 링크 연결 (예: "산재 처리하려면?")
- **제약**: 정부24 도메인 내 단일 창구, 부처 간 횡단 쿼리 미지원 — LLM 기반 tool-loop 아닌 AI 검색/안내 위주
- 출처: 전자신문, [AI 정부시대 개막](https://www.etnews.com/20251217000077)

### 3-2. 범정부 AI 공통기반

- 행안부 주도, 민간 AI 모델·GPU 공동 활용 플랫폼
- 2025년 말 시범 → 2026년 3월 전체 중앙·지방정부 확대
- 출처: 정책브리핑, [정부 행정망 AI 챗서비스](https://www.korea.kr/news/policyNewsView.do?newsId=148955271)

### 3-3. 네이버 CLOVA / 카카오 i 공공서비스

- 네이버 CLOVA Chatbot: 공공기관용 SaaS 챗봇 (NLP 기반, rule+ML 혼합)
  - 출처: [gov-ncloud.com CLOVA Chatbot](https://www.gov-ncloud.com/v2/product/aiService/chatbot)
- 카카오 i 커넥트: 카카오톡 기반 챗봇 빌더 (공공서비스 연동)
  - 출처: [dktechin.com 카카오 i 커넥트톡](https://www.dktechin.com/service/kakaoiconnecttalk)
- 2026년 3월 보도: 네이버 CLOVA X vs 카카오 카나나 — 등본·주민등록 등 공공서비스 경쟁 개시
  - 출처: [daum.net/v 2026-03-10 보도](https://v.daum.net/v/20260310143546645)

### 3-4. KOSMOS 차별점 비교표

| 항목 | 정부24 AI | 네이버/카카오 공공AI | KOSMOS |
|---|---|---|---|
| 부처 횡단 | 제한적 | 제한적(파편화) | 완전 횡단 (어댑터 라우팅) |
| LLM tool-loop | 미적용 | 미적용 | CC agentic loop 1:1 포팅 |
| Permission gauntlet | 없음 | 없음 | 3-layer + Spec 033 spectrum |
| 플러그인 DX | 없음 | 없음 | 5-tier 오픈 플러그인 생태계 |
| 오픈소스 | 아니오 | 아니오 | Apache-2.0 (학생 프로젝트) |
| 한국어 LLM | 미정(범용) | 자체 모델 | K-EXAONE-236B-A23B (K-EXAONE) |

---

## 4. 개발자 도구 레퍼런스

### 4-1. Claude Code (Anthropic)

- **출시**: 2025년 2월 한정 리서치 프리뷰 → **2025년 5월 GA(일반 공개)**, Claude 4와 함께
- **특성**: 터미널 기반 agentic coding tool, tool-loop + permission gauntlet + context assembly
- **라이선스**: 독점 (상용)
- 출처: [code.claude.com overview](https://code.claude.com/docs/en/overview), [anthropic.com Claude Code](https://www.anthropic.com/product/claude-code)

### 4-2. Gemini CLI (Google)

- **출시**: **2025년 6월 25일** 오픈소스 공개
- **라이선스**: **Apache-2.0**
- **기반 모델**: Gemini 2.5 Pro, 컨텍스트 1M 토큰
- **무료 티어**: 60 req/min, 1,000 req/day (개인 Google 계정)
- 출처: [Google 블로그](https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemini-cli-open-source-ai-agent/), [TechCrunch](https://techcrunch.com/2025/06/25/google-unveils-gemini-cli-an-open-source-ai-tool-for-terminals/), [GitHub google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli)

### 4-3. GitHub Copilot CLI

- **출시**: 2025년 9월 공개 프리뷰 → **2026년 2월 GA**
- **특성**: Autopilot 모드(자율 실행), 전문 에이전트 위임(Explore/Task/Code Review/Plan), 저장소 메모리
- **대상**: 개발자 코딩 workflow
- 출처: [GitHub Changelog](https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available/)

### 4-4. KOSMOS 포지셔닝 정리

- Claude Code, Gemini CLI, Copilot CLI = **개발자 도메인** (코드 작성·테스트·리팩터링)
- KOSMOS = **시민 도메인** (공공 API 호출·민원 안내·부처 횡단 조회)
- 마이그레이션 벡터: "개발자 코딩 하네스" → "국민·국가행정시스템 작업 하네스"
  - 출처: KOSMOS AGENTS.md (본 레포지토리), `docs/vision.md § 3`

---

## 5. PIPA §26 수탁자 모델

### 5-1. 개인정보보호법 제26조 핵심 조항

- **조항명**: 업무위탁에 따른 개인정보의 처리 제한
- **수탁자 의무**:
  1. 위탁받은 업무 범위 외 개인정보 처리 금지
  2. 제3자 제공 금지
  3. 재위탁 시 위탁자 동의 필요
  4. 수탁자의 법 위반 시 **위탁자의 사용자로 간주** → 배상책임 연대
- **위탁자 의무**: 수탁자 교육·감독, 수탁 내용·수탁자 정보 공개
- 출처: 국가법령정보센터, [law.go.kr 개인정보보호법 제26조](https://www.law.go.kr/LSW//lsLawLinkInfo.do?lsJoLnkSeq=900079061&lsId=011357&chrClsCd=010202&print=print)
- 출처(해설): [casenote.kr 개인정보보호법 제26조](https://casenote.kr/%EB%B2%95%EB%A0%B9/%EA%B0%9C%EC%9D%B8%EC%A0%95%EB%B3%B4_%EB%B3%B4%ED%98%B8%EB%B2%95/%EC%A0%9C26%EC%A1%B0)

### 5-2. KOSMOS PIPA 적용 입장

- KOSMOS는 PIPA §26 맥락에서 **수탁자(trustee)** 기본 해석 적용 — LLM 합성 단계만 controller-level carve-out
  - 근거: KOSMOS MEMORY `project_pipa_role.md`, Spec 033 수탁자 책임 명시 조항, Spec 1636 `docs/plugins/security-review.md` PIPA §26 수탁자 인정 SHA-256 해시 게이트

### 5-3. 마이데이터 표준 API

- **규격서 버전**: 금융분야 마이데이터 표준API 규격 **v240930** (2024년 9월 30일 배포)
- **발행 주체**: 금융위원회 / 금융보안원
- 출처: [mydatacenter.or.kr v240930 배포 공지](https://www.mydatacenter.or.kr:3441/myd/bbsctt/normal1/normal/a77c34fb-32c6-448c-81c4-51154196e50e/47/bbsctt.do)
- 개발자 포털: [developers.mydatakorea.org 기본 규격](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0101)

### 5-4. 모바일 신분증 / 디지털원패스

- 행안부 모바일 신분증: 주민등록증·외국인등록증 디지털화, 장애인 신분증 2026년 1월 완료
  - 출처: [etnews.com AI 정부24](https://www.etnews.com/20251217000077)
- NPKI(공동인증서) / 디지털원패스 표준: **[출처 확인 필요]** — 행안부 디지털원패스 공식 포털 직접 확인 권장

---

## 6. K-EXAONE / FriendliAI 정량 데이터

### 6-1. K-EXAONE-236B-A23B 모델

- **공식 명칭**: LGAI-EXAONE/K-EXAONE-236B-A23B (HuggingFace)
- **출시일**: **2025년 7월** (arXiv 2507.11407)
- **파라미터**: 30.95B (임베딩 레이어 제외)
- **컨텍스트 길이**: **131,072 토큰** (128K)
- **지원 언어**: 영어, 한국어, 스페인어
- **특성**: 하이브리드 추론 모델 (Reasoning mode + Non-reasoning mode)
- 출처: [HuggingFace LGAI-EXAONE/K-EXAONE-236B-A23B](https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B)
- 출처(PR Newswire): [LG Unveils Korea's First Open-weight Hybrid AI K-EXAONE](https://www.prnewswire.com/news-releases/lg-unveils-koreas-first-open-weight-hybrid-ai-exaone-4-0-302505577.html)

### 6-2. 한국어 LLM 벤치마크 (K-EXAONE-236B-A23B)

| 벤치마크 | 모드 | 점수 |
|---|---|---|
| KMMLU-Redux (한국어 전문 지식) | Reasoning | **72.7%** |
| KMMLU-Redux | Non-reasoning | 64.8% |
| KMMLU-Pro (한국어 실무 지식) | Reasoning | **67.7%** |
| KMMLU-Pro | Non-reasoning | 60.0% |
| Ko-LongBench (한국어 장문 맥락) | Non-reasoning | **76.9%** |
| KSM (한국어 의미 매칭) | Reasoning | **87.6%** |
| KSM | Non-reasoning | 59.8% |

- 출처: [HuggingFace LGAI-EXAONE/K-EXAONE-236B-A23B 모델 카드](https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B)
- 벤치마크 원문: [KMMLU-Pro 데이터셋](https://huggingface.co/datasets/LGAI-EXAONE/KMMLU-Pro), [LG Research K-EXAONE 기술 보고서](https://www.lgresearch.ai/data/cdn/upload/EXAONE_4_0.pdf)

### 6-3. FriendliAI Serverless 요금·한도

- **Tier 구조**: 누적 지출액 기준 자동 승급
  - **Tier 0** (기본): 무료 모델 60 RPM / 유료 모델 [출처 확인 필요]
  - **Tier 1** ($10+ 누적 지출): 무료 모델 **60 RPM**, 유료 모델 **100 RPM**
  - **Tier 2** ($50+ 누적 지출): 유·무료 모델 **1,000 RPM**
- 출처: [friendli.ai Rate Limits 문서](https://friendli.ai/docs/guides/serverless_endpoints/rate_limit)
- 참고: KOSMOS 내부 메모리 `project_friendli_tier_wait.md`에서 Tier 1 확정(60 RPM) 기록 — 실제 문서 기준 유료 모델은 100 RPM

---

## 7. JSON Schema Draft 2020-12 + Pydantic v2 표준

### 7-1. JSON Schema Draft 2020-12

- **정식 명칭**: JSON Schema Draft 2020-12
- **출판 경위**: IETF Internet-Draft 프로세스 사용(draft-bhutton-json-schema) → 현재 json-schema.org 독립 관리
- **주요 변경사항**: `items`→`prefixItems` 분리, `$dynamicRef`/`$dynamicAnchor` 신설, Format 어휘 분리(format-annotation / format-assertion), Unicode 정규식 의무화
- **사양 URL**: [json-schema.org/draft/2020-12](https://json-schema.org/draft/2020-12)
- 출처: [JSON Schema 공식 사양](https://json-schema.org/specification), [2020-12 Release Notes](https://json-schema.org/draft/2020-12/release-notes)

### 7-2. KOSMOS 채택 이유

- Pydantic v2가 JSON Schema Draft 2020-12를 기본 출력 포맷으로 사용 → 모든 어댑터 I/O 스키마가 표준 준수
- OpenAPI 3.0과 호환되어 data.go.kr API 스펙 작성 기준으로 활용 가능

### 7-3. Pydantic v2 통계 (2025-2026 기준)

- **GitHub Stars**: **27,400+** (2026년 기준)
- **월간 다운로드**: **5억 5천만 회+** (2026년 기준)
- **총 누적 다운로드**: **100억 회** 돌파 (2026년 공식 발표)
- **의존 패키지**: PyPI 기준 **약 8,000개** 패키지 (FastAPI, HuggingFace, LangChain, Django Ninja, SQLModel 포함)
- **기업 채택**: FAANG 전체 + NASDAQ 25대 기업 중 20개사 사용
- 출처: [Pydantic 10억 다운로드 공식 아티클](https://pydantic.dev/articles/pydantic-validation-10-billion-downloads)
- 출처(GitHub): [github.com/pydantic/pydantic](https://github.com/pydantic/pydantic)
- 출처(PyPI): [pypi.org/project/pydantic](https://pypi.org/project/pydantic/)
- 출처(PyPI Stats): [pypistats.org/packages/pydantic](https://pypistats.org/packages/pydantic)

### 7-4. KOSMOS 채택 내역

- Pydantic v2 (`>= 2.13`) → 모든 tool I/O 스키마, `ToolCallAuditRecord`, `PrimitiveInput/Output` 공통 envelope, 플러그인 매니페스트 검증
- `pydantic-settings >= 2.0` → `KOSMOS_*` 환경변수 카탈로그 전체 관리
- **Zero `Any`** 정책 (AGENTS.md hard rule)

---

## 부록: KOSMOS 핵심 차별성 정량 요약

| 지표 | 값 | 근거 |
|---|---|---|
| 지원 공공 어댑터 수 (v0.1-alpha) | 24개 [추정] | AGENTS.md 초기 출시 기준 |
| 플러그인 검증 체크리스트 항목 | 50개 (Q1-Q10) | Spec 1636, `tests/fixtures/plugin_validation/` |
| Permission gauntlet 레이어 수 | 3-layer + Spec 033 스펙트럼 | `docs/requirements/kosmos-migration-tree.md` §L1-B |
| 보존된 Claude Code agentic loop | 1:1 포팅 | `docs/vision.md § 3`, Spec 031 |
| OpenAPI 공공데이터 총 건수 (배경 시장) | 10만 건 (2024년 말) | 행정안전부 [data.go.kr](https://www.data.go.kr/data/15076332/fileData.do) |
| 민간 데이터 활용 건수 (2024년) | 7,579만 건 | e-나라지표 [index.go.kr](https://www.index.go.kr/unity/potal/main/EachDtlPageDetail.do?idx_cd=2844) |
| K-EXAONE-236B-A23B KMMLU-Redux (Reasoning) | 72.7% | HuggingFace 모델 카드 |
| Pydantic 월간 다운로드 | 5억 5천만+ | pydantic.dev |

---

*작성일: 2026-04-26. 다음 업데이트: KSC 2026 발표 자료 최종 검토 시.*
