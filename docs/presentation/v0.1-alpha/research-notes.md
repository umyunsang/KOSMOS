# Research Notes — Chapter 2 데이터 출처

> Chapter 2 (기존 문제 및 차별성) 에 사용된 객관적 데이터의 외부 출처 목록.
> 작성일: 2026-04-26

---

## 1. 한국 공공 API 시장 규모

### 1.1 data.go.kr 활용 현황

- **출처**: 행안부, 「공공데이터 활용 현황」, 2024-12-31
- **URL**: https://www.data.go.kr/data/15076332/fileData.do
- **데이터 포인트**:
  - 등록 공공 데이터셋: 100,000건+
  - 민간 API 활용 건수: 7,579만 건 (2024년 기준)
  - 등록 오픈 API 수: 5,000+

### 1.2 e-나라지표 공공데이터 활용

- **출처**: e-나라지표, 「공공데이터 제공 및 이용 현황」
- **URL**: https://www.index.go.kr/unify/idx-info.do?idxCd=2844
- **데이터 포인트**:
  - 공공데이터 포털 등록 데이터셋 연도별 추이
  - API 호출 건수 연도별 추이

### 1.3 OECD OURdata 지수

- **출처**: 행안부, OECD OURdata 지수 발표 자료
- **URL**: https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000015&nttId=103547
- **데이터 포인트**:
  - 2023 OECD OURdata 지수 1위 (개방 가용성·접근성·지원 종합)

---

## 2. AI 정책 정합

### 2.1 대한민국 AI 행동계획 2026-2028

- **출처**: 국가인공지능전략위원회, 『대한민국 인공지능 행동계획』
- **발표일**: 2026-02-25
- **참조 가능 링크**: https://www.smartcity.go.kr (업로드본)
- **내부 참조**: `docs/references/korea-ai-action-plan-2026-2028.pdf`
- **핵심 인용**:
  - 전략분야 7 공공AX, 원칙 8: "모든 민원을 AI를 활용해 단일창구로 접수/처리하고, 국민은 신속히 결과를 제공받는다." (p.96)
  - 원칙 9 (과제 58): "Open API와 OpenMCP를 제공해 민간에서도 공공서비스를 손쉽게 결합해서 국민들에게 제공할 수 있어야 한다." (p.97)
  - 원칙 5: "정부가 보유한 어떤 서류도 국민에게 서면 제출을 요구하지 않으며, 이는 열람승인으로 모두 대체한다." (p.96)

---

## 3. 기존 한국 공공 챗봇 현황

### 3.1 정부24 AI 챗봇

- **출처**: 전자신문 (etnews) 보도, 2026-04
- **URL**: https://www.etnews.com (검색: "정부24 AI 챗봇" 2026-04)
- **특징**: 단일 부처(행안부 민원서비스) 중심 FAQ 기반, 고정 답변

### 3.2 네이버 CLOVA 공공서비스

- **출처**: 네이버 클라우드 공식 블로그 / CLOVA 개발자 문서
- **URL**: https://www.ncloud.com/product/aiService/clovaStudio
- **특징**: NLP 안내 봇, 실시간 API 데이터 연결 구조 없음

### 3.3 카카오 i 공공

- **출처**: 카카오엔터프라이즈 공식 문서
- **URL**: https://kakaoenterprise.com/solution/kakao-i-connect-center
- **특징**: NLP 기반 안내, LLM 도구 루프 부재

---

## 4. LLM 스택

### 4.1 K-EXAONE-236B-A23B

- **출처**: LG AI Research, HuggingFace 모델 카드
- **URL**: https://huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B
- **데이터 포인트**:
  - 236B 파라미터, A23B 활성화 (MoE 구조)
  - 한국어 특화 + 행정·공공서비스 도메인 강화
  - OpenAI-compatible function calling 지원

### 4.2 FriendliAI Serverless

- **출처**: FriendliAI 공식 블로그
- **URL**: https://friendli.ai/blog/k-exaone-on-serverless
- **데이터 포인트**:
  - KOSMOS 사용 Tier 1: 60 RPM
  - OpenAI-compatible API endpoint

---

## 5. PIPA (개인정보보호법) 참조

- **출처**: 개인정보보호위원회, 「개인정보 보호법」 §26 (수탁자 책임)
- **URL**: https://www.law.go.kr/법령/개인정보보호법
- **KOSMOS 적용**: 플러그인이 `processes_pii: true` 선언 시 §26 수탁자 SHA-256 해시 게이트 적용

---

## 주의사항

- 모든 수치는 발표 시점(2026-04-26) 기준으로 재확인 권장
- 정부24 AI 챗봇 관련 etnews 기사는 정확한 URL 제공 불가 (검색 필요)
- AI Action Plan PDF는 `docs/references/`에 보관된 내부 사본 사용
