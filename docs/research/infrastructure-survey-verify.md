# Infrastructure Survey: `verify` primitive

> **Scope**. KOSMOS `verify` primitive (AuthContext 생성)의 실제 카운터파트인 한국 국가 인증 인프라 외부 계약 역공학. 특히 현재 KOSMOS가 사용 중인 `Literal["AAL1","AAL2","AAL3"]` 라벨(v1.3 Tool Template Security Spec, 본 저장소 `src/kosmos/tools/models.py` 및 Discussion #1051)이 실제 provider·규제기관이 공표하는 공식 보안등급을 **정확히 미러하는지** 검증.
>
> **Audience**. 기관 협업 전환 시 `client`만 교체하면 harness 무변경이 되도록 mock adapter를 설계하는 KOSMOS 팀원.
>
> **Non-goals**. 내부 구현(DB 스키마, HSM 배치 등) 분석 금지. 외부에서 관찰 가능한 표면만.
>
> **Constraint**. 공개 문서·법령·가이드·개발자 포털·위키만 인용. 추측 금지 — 불명 항목은 `⚠️ OPAQUE`.

---

## Executive summary

1. **KOSMOS의 AAL1/AAL2/AAL3 라벨은 실제 한국 공표 등급을 미러하지 않는다 — FAIL (mirror 원칙 위반).** NIST SP 800-63-3 AAL 체계는 한국 어느 규제기관(KISA·방통위·금융위·행안부·과기정통부)도 공식 채택·공표한 적이 없다. 검색한 모든 공개 법령·고시·가이드는 AAL 번호 대신 **provider·용도별 원어 등급 레이블**(예: "공인전자서명(구)", "간편인증", "본인확인기관 적합·조건부·부적합", "FIDO UAF 인증", "전자서명인증사업자 인정", "마이데이터 표준 API Scope", "블록체인 기반 DID 모바일신분증", eIDAS-스타일 "Low/Substantial/High" 미채택)을 사용한다. KOSMOS가 현재 붙이고 있는 AAL2/AAL3 값은 **내부적으로 번역한 추정치**이지 mirror가 아니다. [Principle VI Constitution v1.3.0 Out of Scope Declaration](../../.specify/memory/constitution.md)에 명시된 "외부 계약 표면을 바이트 수준까지 미러" 원칙과 직접 충돌한다.

2. **권고 정정안**. `auth_level: Literal["AAL1","AAL2","AAL3"]` 필드를 제거하거나, `published_tier: Literal[...]`로 리네이밍하여 provider 원어 레이블을 직접 담도록 바꾼다. NIST AAL로의 "번역"이 필요하면 별도의 파생 필드(예: `nist_aal_hint: Optional[Literal["AAL1","AAL2","AAL3"]]`)에 `# derived, advisory-only, not mirrored` 주석과 함께 둔다. 8-verb mock facade(Epic #994)는 이 리네이밍이 끝난 후에야 `verify` 계약을 확정해야 한다.

3. **6 family taxonomy — drop-in mirrorability score 요약**.

| Family | 대표 프로토콜 | 공표 레이블 | Mirror 가능성 (1–5) | 주요 gap |
|---|---|---|---|---|
| 1. 공동인증서 (NPKI) | PKCS#12 + X.509v3 (RSA-2048/SHA-256) | "(구) 공인전자서명" / "공동인증서" | 4/5 | 은행 로그인 클라이언트 스크립트(ActiveX 후속)의 정확한 challenge 포맷이 기관별 상이 |
| 2. 금융인증서 | 금결원 클라우드 + FIDO UAF 기반 | "금융인증서" (금결원 공표) | 3/5 | 발급·검증 API 전부 비공개, 은행/증권사 SDK만 공개 |
| 3. 간편인증 (PASS/카카오/네이버/토스 등) | OAuth 2.0 (OIDC 부분 채택) + 기관별 SDK | "간편인증" (전자서명법 인정 사업자) | 3/5 | BaroCert·KISA 가이드라인만 공개, 통신사·메신저 내부 flow 비공개 |
| 4. 디지털원패스 / Any-ID | SAML 2.0 + FIDO UAF v1.0 (OnePass) / 미상 (Any-ID) | "디지털원패스" EOL 2025-12-30, 후속 "정부 통합인증(Any-ID)" | 2/5 | OnePass는 종료, Any-ID 기술 스펙 공개 거의 없음 |
| 5. 모바일 신분증 | W3C VCDM 1.0 + 한국형 DID(K-DIDF/did:omn) + ISO/IEC 18013-5(mDL 일부) | "모바일 신분증" / "블록체인 DID 기반" | 3/5 | VP 포맷·검증 프로토콜은 정부 SDK 다운로드 전에는 외부 관찰 불가 |
| 6. 마이데이터 | OAuth 2.0 (RFC 6749 준용) + 표준 API Scope 목록 | "마이데이터" 각 영역(금융/공공/의료)별 | 4/5 | 공개 문서 충실, but 의료 마이데이터는 FHIR R4 SMART-on-FHIR 채택 여부 미공표 |

4. **Cross-cutting pattern**. 한국 인증 infrastructure는 (a) **용도별 수직 사일로**(금융 ≠ 공공 ≠ 의료 ≠ 통신)와 (b) **provider가 법령 준수 사실을 공표(인정·평가·지정)** 하는 구조라 NIST처럼 "authenticator 수준 통합 등급"이 존재하지 않는다. 미러링이 목적이면 KOSMOS는 provider가 공표한 레이블 그대로 저장해야 하며, 이후 orchestration layer에서 정책 의사결정이 필요할 때만 NIST AAL에 **hint-level mapping**을 attach해야 한다.

---

## Taxonomy: 6 auth families

본 조사의 family 분류는 (i) KISA `identity.kisa.or.kr` 본인확인기관 분류, (ii) 전자서명법 2020 개정 이후 "(구) 공인 / 금융 / 민간" 삼분법, (iii) 금융위·행안부·복지부 마이데이터 영역 구분을 정합한 결과이다.

| # | Family | Regulator | 근거 법령 | 주요 Provider |
|---|---|---|---|---|
| 1 | 공동인증서 (구 NPKI) | KISA 전자서명인증관리센터 | 전자서명법 (2020 개정) | KICA, KFTC(yessign), CrossCert, TradeSign, KOSCOM, ICA |
| 2 | 금융인증서 | 금융결제원(KFTC) — 금융위 감독 | 전자금융거래법, 전자금융감독규정 | KFTC(단일 issuer) |
| 3 | 간편인증 | KISA(전자서명인증사업자 인정기관), 방통위(본인확인기관 지정) | 전자서명법, 정보통신망법 §23조의3 | PASS(SKT/KT/LG U+), 카카오, 네이버, 토스, KB국민, 신한, 하나, 우리, 삼성패스 |
| 4 | 디지털원패스 → Any-ID | 행정안전부 (인공지능정부실) | 전자정부법 시행령 (대통령령 34518호, 2024-05-21 개정) | 행안부 운영 (단일) |
| 5 | 모바일 신분증 | 행정안전부 + 경찰청(운전면허) | 주민등록법, 도로교통법, 전자정부법 | 행안부(주민등록·공무원·외국인·재외국민·보훈), 경찰청(운전면허) — 플랫폼: K-DIDF/OmniOne |
| 6 | 마이데이터 | 금융위(금융) / 행안부(공공) / 복지부(의료) | 신용정보법(금융), 전자정부법(공공), 개인정보보호법, 의료법 | 금융: KFTC 중계기관; 공공: 정부24; 의료: 건강정보고속도로(보건의료정보원) |

---

## Per-family deep dives

### Family 1 — 공동인증서 (구 NPKI)

#### Protocol
PKCS#12 컨테이너(암호화된 X.509v3 인증서 + RSA 개인키). 서비스 측 handshake는 **browser → NPKI signed payload** (일반적으로 서버가 발행한 nonce를 RSA-SHA256 서명). Active-X 시대의 외부관찰 가능한 shape은 (1) 서비스가 `userID + nonce + timestamp` 포함 hash를 내려보냄, (2) client는 PKCS#7 SignedData 포맷으로 서명해 업로드, (3) 서버는 KCAC.TS.CERTPROF 준거 인증서 체인을 KISA RootCA까지 검증.

#### Handshake sequence (관찰 가능한 shape)
```
C → S  : login_init { service_id, user_id }
S → C  : challenge { nonce, session_ts, hash_alg = "SHA-256" }
C      : open PKCS#12, decrypt w/ PIN, sign (nonce||ts||user_id) w/ RSA-2048
C → S  : auth_response { signed_blob (PKCS#7 SignedData), cert_chain }
S      : validate path up to KISA RootCA (KCAC.TS.CERTVAL v1.11 경로검증),
         check CRL (KCAC.TS.CRLPROF v1.50), check subject DN match
S → C  : session_cookie  (OR) bearer_token
```
상세 준거 규격: [KCAC.TS.CERTPROF (KISA 전자서명인증관리센터 기술규격 페이지)](https://www.rootca.or.kr/kor/standard/standard01A.jsp), [KCAC.TS.CMP v1.22](https://rootca.kisa.or.kr/kcac/down/TechSpec/3.2-KCAC.TS.CMP.pdf), [KCAC.TS.CERTVAL v1.11](https://www.rootca.or.kr/kcac/down/TechSpec/5.3-KCAC.TS.CERTVAL.pdf), [KCAC.TS.CRLPROF v1.50](https://www.rootca.or.kr/kcac/down/TechSpec/1.2-KCAC.TS.CRLPROF.pdf), [KCAC.TS.DSIG (전자서명 알고리즘)](https://rootca.or.kr/kcac/down/TechSpec/2.1-KCAC.TS.DSIG.pdf).

#### Token / 인증서 format
- X.509v3, Subject DN: `C=KR, O=<CA O명>, OU=<서비스구분>, CN=<사용자표기>, serialNumber=<주민번호 hash 등>`. DN 상세는 KISA KCAC.DN 규격이 정의 (namu.wiki [공동인증서](https://namu.wiki/w/%EA%B3%B5%EB%8F%99%EC%9D%B8%EC%A6%9D%EC%84%9C) 인용; KISA 원문은 다운로드 링크 전용).
- RSA-2048 keyUsage = `digitalSignature, nonRepudiation`.
- 해시 알고리즘: SHA-256 (SHA-1은 2016년 이후 단계적 폐지).
- 저장 위치: Windows `%USERPROFILE%\AppData\LocalLow\NPKI\`, macOS `~/Library/Preferences/NPKI/`, iOS/Android 앱별 샌드박스.

#### Endpoints
NPKI는 중앙 authorize endpoint가 **없다**. 각 relying party가 독립 검증. CA별 OCSP/CRL endpoint는 KISA [인증서 신뢰 목록](https://rootca.kisa.or.kr/kor/accredited/accredited03_03.jsp)에서 배포.

#### Scope / claim catalog
X.509는 scope 개념이 없음. 대신 확장 필드에 `identifierType (RRN/CRN/BRN)`, `userPolicy OID` 수준. 세부는 KCAC.TS.CERTPROF.

#### Session lifetime, refresh
세션은 **없음 — 단발성 서명**. 인증서 유효기간 통상 1년(개인), 2–3년(법인). 재발급은 CA별 포털.

#### 공표된 assurance tier
- **"(구) 공인전자서명"** — 전자서명법 2020-12-10 개정 이전. 법적으로 "공인" 문구는 전면 삭제됨. [전자서명법 개정 배경, 모두싸인](https://blog.modusign.co.kr/insight/the_public_certificate), [법률 원문, 국가법령정보센터](https://law.go.kr/%EB%B2%95%EB%A0%B9/%EC%A0%84%EC%9E%90%EC%84%9C%EB%AA%85%EB%B2%95).
- 개정 후 공식 명칭: **"공동인증서"** (namuwiki·정책뉴스 공표). [대한민국 정책뉴스](https://www.korea.kr/news/policyNewsView.do?newsId=148880731).
- **현재 법적 지위**: 민간 전자서명 중 하나. "상대적으로 우월한 법적 효력"은 사라짐 ([Korea IT Times 보도](http://www.koreaittimes.com/news/articleView.html?idxno=97651)).

#### Error codes
비공개. 각 CA CPS(인증업무준칙)에만 기술. 한국전자인증 CrossCert 예시: [Certification Practice Statement PDF](https://www.crosscert.com/glca/file/Certification_Practice_Statement_5.3.pdf).

#### Drop-in mirrorability: 4/5
PKCS#12, X.509, RSA-SHA256, PKCS#7 SignedData 모두 공개 표준. Mock이 Python `cryptography` 라이브러리로 shape-compatible 서명을 만들 수 있다. 감점 1 — 각 relying party(은행·증권사)가 ActiveX 후속 wrapper(예: AnySign, Delfino, MagicLine)로 payload를 한번 더 감싸는 layer는 벤더 sdk 내부라 외부 관찰 불가.

#### Gaps
- ⚠️ OPAQUE: 각 은행별 로그인 페이지의 NPKI 클라이언트 wrapper (MagicLine 등) 정확한 JSON 필드명·에러 JSON 포맷. SDK EULA상 공개 불가.
- ⚠️ OPAQUE: "공동인증서 / 금융인증서" 분리 발급 시 KFTC 측 교차 검증 API.

#### Sources (Family 1)
- [전자서명법 전부개정법률 (2020.06.09 공포)](https://law.go.kr/%EB%B2%95%EB%A0%B9/%EC%A0%84%EC%9E%90%EC%84%9C%EB%AA%85%EB%B2%95)
- [KISA 전자서명인증관리센터 — (구)공인전자서명 기술규격 프로파일](https://www.rootca.or.kr/kor/standard/standard01A.jsp)
- [KCAC.TS.DSIG — 전자서명 알고리즘](https://rootca.or.kr/kcac/down/TechSpec/2.1-KCAC.TS.DSIG.pdf)
- [KCAC.TS.CERTVAL v1.11](https://www.rootca.or.kr/kcac/down/TechSpec/5.3-KCAC.TS.CERTVAL.pdf)
- [KCAC.TS.CRLPROF v1.50](https://www.rootca.or.kr/kcac/down/TechSpec/1.2-KCAC.TS.CRLPROF.pdf)
- [KCAC.TS.HSMU v2.40 — 보안토큰 기반 인증서](https://rootca.kisa.or.kr/kcac/down/TechSpec/6.3-KCAC.TS.HSMU.pdf)
- [KISA — 21년만의 공인인증서 폐지, 이글루시큐리티 해설](https://www.igloo.co.kr/security-information/21%EB%85%84%EB%A7%8C%EC%9D%98-%EA%B3%B5%EC%9D%B8%EC%9D%B8%EC%A6%9D%EC%84%9C-%ED%8F%90%EC%A7%80/)
- [한국전자인증 CPS 5.3](https://www.crosscert.com/glca/file/Certification_Practice_Statement_5.3.pdf)
- [나무위키 — 공동인증서 기술 요약](https://namu.wiki/w/%EA%B3%B5%EB%8F%99%EC%9D%B8%EC%A6%9D%EC%84%9C)

---

### Family 2 — 금융인증서

#### Protocol
금융결제원(KFTC) 단일 발급. 클라우드 저장(기기에 인증서 파일 없음). Handshake는 공개 표준 조합으로 관찰되며 (a) 금결원 클라우드가 인증서 private key custody, (b) 사용자는 6-digit PIN 또는 FIDO UAF 기반 생체로 인증, (c) relying party는 금결원 API로 검증 요청.

#### Handshake sequence (관찰 가능한 shape)
```
C → S       : login_init { service_id }
S → C       : redirect to KFTC 금융인증 endpoint
C → KFTC    : user PIN (6-digit) OR FIDO UAF biometric
KFTC → C    : short-lived authorization_code
C → S       : authorization_code
S → KFTC    : exchange code → signed assertion (JWT-style or PKCS#7)
S           : validate assertion signature, extract 식별자
```
상세는 금결원 통합포털([openapi.kftc.or.kr/service/financeAuthentication](https://openapi.kftc.or.kr/service/financeAuthentication))에서만 비인증 가입자에게 공개.

#### Token format
- 내부는 X.509 + RSA (전자서명법 준수 위해 공동인증서와 같은 암호학적 기반).
- 외부 계약 표면은 "assertion" 또는 "result_token" (JWT-like or PKCS#7) — 정확한 필드명은 금결원 API 포털 로그인 후에만 공개.

#### Endpoints
- 루트: `https://www.yeskey.or.kr/` (금결원 yessign — 금융인증서 발급/재발급 포털). [금융인증서 안내](https://www.yeskey.or.kr/?url=yeskey/yessign/certificate/finance&menuSeq=100058&upMenuSeq=100000).
- 개발자 API: [openapi.kftc.or.kr/service/financeAuthentication](https://openapi.kftc.or.kr/service/financeAuthentication) (계정 필요).

#### Scope / claim catalog
⚠️ OPAQUE — 금결원 개발자 포털 등록 후에만 공개.

#### Session lifetime, refresh
- 인증서 유효기간: **3년** (공개). [namuwiki 금융인증서](https://namu.wiki/w/%EA%B8%88%EC%9C%B5%EC%9D%B8%EC%A6%9D%EC%84%9C).
- 세션 토큰 수명: ⚠️ OPAQUE.

#### 공표된 assurance tier
- **"금융인증서"** — 금결원 공표. 정부·금융당국은 이를 NIST AAL 어느 레벨에도 공식 매핑하지 않음.
- [전자금융감독규정](https://law.go.kr/%ED%96%89%EC%A0%95%EA%B7%9C%EC%B9%99/%EC%A0%84%EC%9E%90%EA%B8%88%EC%9C%B5%EA%B0%90%EB%8F%85%EA%B7%9C%EC%A0%95) 제34조(사용자인증)는 "본인확인 등 안전한 방법으로 사용자인증을 해야 한다"고만 규정. 인증수단 1/2/3등급 체계가 **법령상 존재하지 않는다**. (2015년 "전자금융거래 인증방법 평가기준" 고시가 폐지된 후 전자금융감독규정에 통합됨. 현재 명시적인 NIST AAL-유사 등급 체계 없음.) [Kim&Chang 해설](https://www.kimchang.com/ko/insights/detail.kc?sch_section=4&idx=31385).

#### Drop-in mirrorability: 3/5
클라우드 저장 + FIDO UAF + PIN 조합이라 shape은 복합적. Public 표준 부분만 mock하면 4/5, 하지만 금결원 exchange endpoint의 정확한 assertion JSON이 비공개라 3/5.

#### Gaps
- ⚠️ OPAQUE: assertion 내부 claim 목록, error code set, FIDO 등록 관리 API.

#### Sources (Family 2)
- [금융결제원 — 금융인증서비스 소개](https://www.kftc.or.kr/service/authInfo)
- [금결원 OpenAPI 포털 — 금융인증서 서비스](https://openapi.kftc.or.kr/service/financeAuthentication)
- [yessign 금융인증서 발급](https://www.yeskey.or.kr/?url=yeskey/yessign/certificate/finance&menuSeq=100058&upMenuSeq=100000)
- [나무위키 — 금융인증서 기술 개요](https://namu.wiki/w/%EA%B8%88%EC%9C%B5%EC%9D%B8%EC%A6%9D%EC%84%9C)
- [전자금융감독규정 (국가법령정보)](https://law.go.kr/%ED%96%89%EC%A0%95%EA%B7%9C%EC%B9%99/%EC%A0%84%EC%9E%90%EA%B8%88%EC%9C%B5%EA%B0%90%EB%8F%85%EA%B7%9C%EC%A0%95)
- [Kim&Chang — 개정 전자금융감독규정](https://www.kimchang.com/ko/insights/detail.kc?sch_section=4&idx=31385)

---

### Family 3 — 간편인증

간편인증은 2020-12-10 전자서명법 개정으로 법적 지위를 얻은 민간 전자서명 서비스 집합. KISA가 인정기관, 민간 평가기관이 평가기관, 각 사업자가 공표한 "전자서명인증사업자 인정" 증명서를 보유. [KISA 전자서명인증사업자 인정·평가 제도](https://www.kisa.or.kr/1050609), [인정기관 KISA trustesign](https://trustesign.kisa.or.kr/).

#### 3A — PASS (SKT·KT·LG U+ 공통 브랜드, 개별 구현)

- **Protocol**: OAuth 2.0 (OIDC 명시 언급 없음). [SK OpenAPI PASS](https://openapi.sk.com/products/detail?svcSeq=64), [KT PASS](https://fido.kt.com/ktauthIntro), [PASS 휴대폰번호 로그인 개발자센터](https://developers.passlogin.com/docs/develop/ios).
- **Handshake**:
  ```
  RP → PASS : OAuth2 authorize (통신사 URL scheme 분기)
  PASS 앱   : 간편로그인 (PIN/지문/FaceID)
  PASS → RP : 인증코드 (URL scheme callback)
  RP → PASS : code → access_token
  ```
- **Endpoints**: 통신사별 상이. SKT `oauth2.sktelecom.com` (public doc에 분기). KT/LGU+는 비공개 세부.
- **Scope**: `ci` (연계정보), `di` (중복가입확인정보), `name`, `birth`, `gender`, `mobile_carrier`. 공식 catalog는 각 통신사 B2B 포털 가입 후.
- **공표 tier**: "PASS 인증서", "FIDO 기반 간편인증". AAL 매핑 없음.
- **Mirrorability**: 3/5 — OAuth2 shape은 미러 용이, 통신사 분기·callback scheme 3개 동시 관리 필요.

#### 3B — 카카오 인증 / 카카오뱅크 인증서

- **Protocol**: OAuth 2.0 + OIDC (`OpenID Connect 1.0` 지원 명시, [Works Mobile doc](https://developers.worksmobile.com/kr/docs/auth-oauth) 참조; 카카오 자체 로그인은 OIDC 호환).
- **인증서 API**: BaroCert 플랫폼 통해 외부 접근. [카카오 본인인증 API - BaroCert](https://developers.barocert.com/reference/kakao/java/identity/api), [전자서명 API](https://auth.kakaobank.com/guide/guideDigitalSignPage).
- **Handshake**:
  ```
  RP → BaroCert : requestIdentity { clientCode, signer info, returnURL }
  BaroCert → Kakao Talk push : 전자서명 요청
  User           : 카카오톡 "인증하기" → PIN/생체
  Kakao → BaroCert → RP : receiptID + signed result (SHA-256 + 서버 공개키 검증)
  ```
- **공표 tier**: "카카오뱅크 인증서", "카카오톡 지갑 인증". 전자서명법 인정 사업자. AAL 없음.
- **Mirrorability**: 3/5 — BaroCert API가 공개 SDK라 shape은 미러 가능, 그러나 RP가 직접 카카오 API를 부르는 대신 BaroCert 중계를 강제하는 점은 KOSMOS mock에서 추가 중계층을 모델링해야 한다.

#### 3C — 네이버 인증 / 토스 인증

동일 패턴(BaroCert 또는 자체 developer 포털). [BaroCert naver 레퍼런스](https://developers.barocert.com/reference/naver/java/identity/api).

#### 3D — 은행 앱 인증서 (KB·신한·하나·우리·삼성패스)

- **Protocol**: 은행별 자체 공동인증서/금융인증서 확장 + 앱 PIN·생체. OIDC 명시 채택 사례 없음. 각 은행 서드파티 연동 시 **"간편인증 API"** 이름으로 BaroCert·드림시큐리티·KICA 등 중계.
- **공표 tier**: "KB모바일 인증서", "신한인증서" 등 자체 브랜드. AAL 매핑 없음.
- **Mirrorability**: 2/5 — 각 은행이 별도 계약 기반 SDK 배포, 공개 외부 계약 표면이 얇음.

#### Family 3 공통 공표 assurance 체계
- **전자서명법 §8 전자서명인증사업자 운영기준** ⇒ 평가·인정. 평가 결과 "적합" ⇒ 인정 증명서 발급. **NIST AAL-like 수치 등급 없음.** [KISA 전자서명인증사업자 인정·평가제도](https://www.kisa.or.kr/1050609), [trustesign.kisa.or.kr 인정기관 안내](https://trustesign.kisa.or.kr/intro/info).
- **정보통신망법 §23조의3 본인확인기관 지정** ⇒ 방통위 고시 2022-1호 평가. 심사: 87개 항목 중 21개 중요 + 2개 계량 + 총점 800/1000. 결과 **"지정 / 조건부지정 / 미지정"** 삼분법. ([방통위 고시 해설](https://m.boannews.com/html/detail.html?idx=103922), [KISA 본인확인 지원포털 지정기준](https://identity.kisa.or.kr/web/main/contents/M050-03)).

#### Sources (Family 3)
- [KISA 전자서명인증사업자 인정·평가제도](https://www.kisa.or.kr/1050609)
- [trustesign.kisa.or.kr 인정기관](https://trustesign.kisa.or.kr/)
- [KISA 본인확인기관 지정기준](https://identity.kisa.or.kr/web/main/contents/M050-03)
- [방통위 고시 2022-1호 해설 — 보안뉴스](https://m.boannews.com/html/detail.html?idx=103922)
- [방통위 2025 신규 본인확인기관 지정 심사 공고](https://zdnet.co.kr/view/?no=20250320144442)
- [SK OpenAPI PASS 상세](https://openapi.sk.com/products/detail?svcSeq=64)
- [KT PASS/FIDO 소개](https://fido.kt.com/ktauthIntro)
- [PASS Login 개발자센터](https://developers.passlogin.com/docs/develop/ios)
- [BaroCert 통합 플랫폼](https://www.barocert.com/)
- [BaroCert Kakao Identity API](https://developers.barocert.com/reference/kakao/java/identity/api)
- [BaroCert Naver Identity API](https://developers.barocert.com/reference/naver/java/identity/api)
- [카카오뱅크 본인확인 API 가이드](https://auth.kakaobank.com/guide/guideIdentificationPage)
- [카카오뱅크 전자서명 API 가이드](https://auth.kakaobank.com/guide/guideDigitalSignPage)
- [국세청 홈택스 간편인증 사용자 매뉴얼 (2025.09)](https://hometax.speedycdn.net/dn_dir/webdown/%EA%B0%84%ED%8E%B8%EC%9D%B8%EC%A6%9D%EB%A1%9C%EA%B7%B8%EC%9D%B8%EC%9E%90%EC%84%B8%ED%9E%88%EB%B3%B4%EA%B8%B0.pdf)

---

### Family 4 — 디지털원패스 → Any-ID

#### 4A — 디지털원패스 (EOL 2025-12-30)

- **Protocol**: **SAML 2.0** (eGovFrame doc 명시). FIDO UAF v1.0 통합 인증 획득. [eGovFrame 디지털원패스](https://www.egovframe.go.kr/wiki/doku.php?id=egovframework:com:v4.0:uat:%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4), [SAML 예제 사이트](https://saml.egaf2017.com/).
- **Authenticators**: 모바일(지문/안면/패턴/PIN/공동인증서), PC 공동인증서, SMS. [위키백과 디지털원패스](https://ko.wikipedia.org/wiki/%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4).
- **Handshake (SAML)**:
  ```
  User → SP    : access resource
  SP → User    : redirect to IdP (AuthnRequest)
  User → IdP   : login (FIDO UAF or cert)
  IdP → SP     : SAMLResponse (Assertion)
  SP           : validate signature, create session
  ```
- **Termination**: **2025-12-30 서비스 종료, 2026-01-30 개인정보 전량 삭제** ([IFEZ 공지](https://www.ifez.go.kr/main/pst/view.do?pst_id=noti01&pst_sn=668873&search=), [도로교통공단 공지](https://www.koroad.or.kr/main/board/1/304186/board_view.do), [질병관리청 공지](https://is.kdca.go.kr/isc/popupmain/onepassnotices.html)).
- **공표 tier**: 없음 (단일 통합 브랜드). FIDO UAF v1.0 획득만 공표.
- **Mirrorability**: **N/A — 서비스 종료.** KOSMOS는 이를 미러할 이유가 없다.

#### 4B — 정부 통합인증 Any-ID (후속)

- **Protocol**: ⚠️ OPAQUE — 공식 개발자 문서 URL 공개되지 않음. 행안부 보도자료는 "다양한 인증수단(모바일신분증·간편인증) 선택 이용"만 명시.
- **Endpoints**: `https://www.anyid.go.kr/` (포털), `https://ptl.anyid.go.kr/` (연계 포털).
- **Legal basis**: 전자정부법 시행령 대통령령 제34518호 (2024-05-21 개정). [행안부 Any-ID 소개](https://www.mois.go.kr/frt/sub/a06/b04/easyCertification/screen.do).
- **Coverage (2026-04 현재)**: 94개 공공기관. [나무위키 정부 통합인증](https://namu.wiki/w/%EC%A0%95%EB%B6%80%20%ED%86%B5%ED%95%A9%EC%9D%B8%EC%A6%9D).
- **공표 tier**: 없음. "간편인증" 배너 레이블만.
- **Mirrorability**: 2/5 — 연계 기관은 이미 94개지만 외부 연동 기술문서가 공개되지 않음. KOSMOS는 "Any-ID redirect happens, then delegated method determines assurance"로 mock 구조만 둘 수 있음.

#### Sources (Family 4)
- [행안부 정부 통합인증(Any-ID) 안내](https://www.mois.go.kr/frt/sub/a06/b04/easyCertification/screen.do)
- [Any-ID 포털](https://www.anyid.go.kr/)
- [Any-ID 연계 포털](https://ptl.anyid.go.kr/)
- [eGovFrame 디지털원패스 연동 가이드 (SAML)](https://www.egovframe.go.kr/wiki/doku.php?id=egovframework:com:v4.0:uat:%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4)
- [위키백과 — 디지털원패스](https://ko.wikipedia.org/wiki/%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4)
- [나무위키 — 디지털원패스](https://namu.wiki/w/%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4)
- [IFEZ — 디지털원패스 종료 안내](https://www.ifez.go.kr/main/pst/view.do?pst_id=noti01&pst_sn=668873&search=)
- [도로교통공단 — 디지털원패스 종료 공지](https://www.koroad.or.kr/main/board/1/304186/board_view.do)

---

### Family 5 — 모바일 신분증

#### Protocol
**한국형 DID (K-DIDF) + W3C Verifiable Credentials Data Model 1.0/2.0**. 일부(모바일 운전면허증)는 **ISO/IEC 18013-5:2021** mDL 상호운용성도 병행 개발. 플랫폼은 라온시큐어 OmniOne(`did:omn:`) 기반이며 2022년부터 모바일 운전면허증 상용, 2024-12 모바일 주민등록증 전국 서비스로 확대.

- **Issuer**: 행안부(주민등록·공무원·외국인·재외국민·보훈), 경찰청(운전면허).
- **Platform operator**: 행안부 산하 운영 + 한국조폐공사(KOMSCO) 인프라.
- **User wallet**: 공식 앱 "모바일신분증"(Google Play `kr.go.mobileid`). 별도 "모바일 신분증 검증앱" (`kr.go.verify.mobileid`).

#### Handshake sequence (VP 기반)
```
Verifier → Holder : present_request { required_claims, challenge, verifier_did }
Holder App       : 지문/FaceID + PIN → VP 서명 (EdDSA or RSA)
Holder → Verifier: VP (W3C format — JSON-LD or JWT VP)
Verifier         : resolve did:omn: on K-DIDF ledger, verify signature, ZKP 선택적
Verifier → Holder: result (accept/reject)
```
QR 코드 모드 + BLE 근접 모드 (ISO 18013-5 device retrieval) 모두 지원 ([Wikipedia mDL](https://en.wikipedia.org/wiki/Mobile_driver's_license)).

#### Token / credential format
- **Verifiable Credential**: W3C VCDM 1.0 (이후 2.0 병행). `issuer`, `issuanceDate`, `expirationDate`, `credentialSubject`, `proof`. [W3C VC Data Model (KR 번역)](https://ssimeetupkorea.github.io/vc-data-model/).
- **DID method**: `did:omn:` (라온시큐어 OmniOne). `did:web` 게이트웨이 일부 공개. [OmniOne Enterprise Brochure PDF](https://www.omnione.net/layout/files/service/2/file_1/OmniOne%20Enterprise_Brochure%20_%EA%B5%AD%EB%AC%B8%20(2024).pdf).
- **VP**: OpenID for Verifiable Presentations draft 23 부분 채택 (국내 파일럿 — 공식 채택 아직 미확정). [OpenID4VP draft 23](https://openid.net/specs/openid-4-verifiable-presentations-1_0-23.html).

#### Endpoints
- Issuance / management: [모바일 신분증 포털](https://www.mobileid.go.kr/), [개발지원센터](https://dev.mobileid.go.kr/).
- Verification SDK: 정부 공식 SDK 다운로드 (개발지원센터 가입 후) + 라온시큐어 OmniOne CX.
- 블록체인 엔드포인트: K-DIDF ledger(비공개 consortium). [opendid.org 커뮤니티](https://opendid.org/).

#### Scope / claim catalog
- 모바일 운전면허증 credentialSubject: `birthDate`, `licenseNumber`, `licenseType`(1종/2종 구분), `issueDate`, `expirationDate`, `condition` (보조기기 등), `photo` (선택 공개).
- 모바일 주민등록증: `name`, `birthDate`, `address`, `RRN hash`(ZKP 사용 권장), `photo`.
- **Selective disclosure** (예: 술집이 "만 19세 이상" 만 확인) 지원 — ZKP 기반, 상세는 SDK에서만.

#### Session lifetime, refresh
- VC 유효기간: 실물 면허증·주민증과 동일 (운전면허 10년, 주민증은 만료 없음).
- VP는 단발성 (challenge-response), 세션 재사용 개념 없음.

#### 공표된 assurance tier
- **"블록체인 기반 DID 모바일 신분증"** — 행안부 공표. 실물과 **동일한 법적 효력** 명시 (도로교통법 개정으로 2022 보장). [도로교통공단 운전면허 가이드](https://www.safedriving.or.kr/guide/larGuide10.do?menuCode=MN-PO-12111).
- NIST AAL 명시 없음. ISO 18013-5 mDL은 별도 assurance framework(ISO/IEC 29115) 권장하나 국내 공표 없음.

#### Drop-in mirrorability: 3/5
W3C VCDM·ISO 18013-5는 공개 표준 → mock은 표준 라이브러리(예: Python `didkit`, `pydid`)로 shape-compatible VP 생성 가능. 감점 — `did:omn` resolver는 K-DIDF 원장 비공개라 완전 미러 불가 (did method 자체는 표준이지만 실제 서명 검증은 consortium endpoint 콜 필요).

#### Gaps
- ⚠️ OPAQUE: K-DIDF consortium ledger 노드 목록·합의 알고리즘.
- ⚠️ OPAQUE: 정부 SDK 내부 VP 포맷 선택 (JSON-LD vs JWT VP vs SD-JWT) — 공식 가이드 문서 공개 제한.

#### Sources (Family 5)
- [행안부 모바일 신분증](https://www.mois.go.kr/frt/sub/a06/b04/mobileId/screen.do)
- [모바일 신분증 포털](https://www.mobileid.go.kr/)
- [개발지원센터](https://dev.mobileid.go.kr/)
- [Google Play — 모바일 신분증 앱](https://play.google.com/store/apps/details?id=kr.go.mobileid)
- [Google Play — 모바일 신분증 검증앱](https://play.google.com/store/apps/details?id=kr.go.verify.mobileid)
- [Wikipedia — 모바일 운전면허증](https://ko.wikipedia.org/wiki/%EB%AA%A8%EB%B0%94%EC%9D%BC_%EC%9A%B4%EC%A0%84%EB%A9%B4%ED%97%88%EC%A6%9D)
- [eGovFrame — 모바일 운전면허증](https://www.egovframe.go.kr/wiki/doku.php?id=egovframework:com:v4.1:sec:%EB%AA%A8%EB%B0%94%EC%9D%BC_%EC%9A%B4%EC%A0%84%EB%A9%B4%ED%97%88%EC%A6%9D)
- [ISO/IEC 18013-5:2021](https://www.iso.org/standard/69084.html)
- [ISO/IEC 18013-5 samples PDF](https://cdn.standards.iteh.ai/samples/69084/9b2e0bf21d5e4a26aa1a587e29aa63a9/ISO-IEC-18013-5-2021.pdf)
- [ISO/IEC TS 18013-7:2024 mDL add-on](https://www.iso.org/standard/82772.html)
- [W3C Verifiable Credentials 1.0 (KR 번역)](https://ssimeetupkorea.github.io/vc-data-model/)
- [OpenID for Verifiable Presentations draft 23](https://openid.net/specs/openid-4-verifiable-presentations-1_0-23.html)
- [OmniOne Enterprise Brochure (KR) 2024](https://www.omnione.net/layout/files/service/2/file_1/OmniOne%20Enterprise_Brochure%20_%EA%B5%AD%EB%AC%B8%20(2024).pdf)
- [opendid.org — 한국디지털인증협회](https://opendid.org/)

---

### Family 6 — 마이데이터

세 수직 도메인: **금융(6A) / 공공(6B) / 의료(6C)**. 공통 원칙은 RFC 6749 OAuth 2.0 준용 + scope 명세 + 전송요구(consent) → 정보제공자 API 호출.

#### 6A — 금융 마이데이터 (금융위 · KFTC 중계)

- **Protocol**: **OAuth 2.0 (RFC 6749 준용)**. [마이데이터 데이터 표준 API 인증규격](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0102).
- **Token lifetimes**: access_token ≤ **90일**, refresh_token ≤ **1년**. 초기 발급 후 1년 내 정보주체 재동의 없이 갱신 가능. [마이데이터 개별인증 API](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0201?id=7).
- **Endpoints**: 각 정보제공자(은행·카드·증권·보험) 별 `/oauth/2.0/authorize`, `/oauth/2.0/token` (표준 명세).
- **Scope catalog (부분)**:
  - `bank.list` (계좌목록), `bank.invest` (투자상품), `bank.irp` (개인형 IRP)
  - `card.list`, `card.transactions`
  - `invest.list`, `invest.detail` (증권)
  - `insu.list`, `insu.detail` (보험)
  - `capital.list` (여신)
  - `efin.list` (선불전자지급)
  - 예시: "bank.list bank.invest bank.irp" (공백 구분). [마이데이터 표준 scope 예시](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0201?id=7).
- **Integrated auth**: [통합인증 API](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0202?id=12) — 중계기관(금결원) 경유 one-stop consent.
- **공표 tier**: "마이데이터 표준 API" (금융위 가이드라인 + 신용정보법). AAL 없음.
- **Mirrorability**: 4/5 — RFC 6749 + 공식 scope catalog 공개, mock 용이.

#### 6B — 공공 마이데이터 (행안부 · 정부24)

- **Protocol**: 전송요구 기반 API. [공공 마이데이터 서비스 수행 가이드 v1.5 (2025.08)](https://adm.mydata.go.kr/images/guide.pdf).
- **Endpoints**: [정부24 마이데이터](https://www.gov.kr/portal/mydata/myDataIntroduction?Mcode=11258), [공공 마이데이터 업무포털](https://adm.mydata.go.kr/).
- **Scope**: 주민등록등본, 가족관계증명서, 소득증명 등 **"행정정보 항목 코드"** 기준. 금융 scope와 체계 다름.
- **공표 tier**: "공공 마이데이터". 행안부 공표.
- **Mirrorability**: 3/5 — 가이드 문서 공개, 그러나 OAuth 2.0 정확한 flow (authorization_code grant 여부) 명시 부족.

#### 6C — 의료 마이데이터 (복지부 · 건강정보고속도로 / MyHealthway)

- **Protocol**: ⚠️ 부분 OPAQUE. 공식 웹은 "국가표준 FHIR" 중계로 기술하나, SMART-on-FHIR 채택 여부는 명시 없음. [건강정보 고속도로 API 안내](https://www.myhealthway.go.kr/portal/index?page=Individual/Portal/MediMyData/MydataApi).
- **Endpoints**: `https://www.myhealthway.go.kr/` 포털 + 활용 서비스 가입.
- **Resource**: FHIR R4 리소스(Patient, Observation, Condition, MedicationStatement, Immunization 등) 추정. 정확한 프로파일은 한국보건의료정보원 가입 후 공개.
- **공표 tier**: "의료 마이데이터 / PHR". AAL 없음.
- **Mirrorability**: 3/5 — FHIR 자체는 공개 표준이라 mock 용이, 한국 특화 프로파일은 비공개라 감점.

#### Sources (Family 6)
- [마이데이터 데이터 표준 API 인증규격 (금융)](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0102)
- [마이데이터 개별인증 API](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0201?id=7)
- [마이데이터 통합인증 API](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0202?id=12)
- [마이데이터 표준 API 기본 규격](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0101)
- [마이데이터 지원 API](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0301?id=8)
- [금결원 마이데이터 API](https://mydata.kftc.or.kr/web/mydataApi/api)
- [행안부 공공 마이데이터 활성화](https://mois.go.kr/frt/sub/a06/b02/digitalOpendataMydata/screen.do)
- [공공 마이데이터 서비스 수행 가이드 v1.5 (2025.08)](https://adm.mydata.go.kr/images/guide.pdf)
- [공공 마이데이터 서비스 수행 가이드 02](https://adm.mydata.go.kr/images/guide02.pdf)
- [건강정보 고속도로 포털](https://www.myhealthway.go.kr/portal/)
- [건강정보 고속도로 API 소개](https://www.myhealthway.go.kr/portal/index?page=Individual/Portal/MediMyData/MydataApi)
- [건강정보 고속도로 서비스 소개](https://www.myhealthway.go.kr/portal/index?page=Individual/Portal/MediMyData/MydataService)
- [한국보건의료정보원 - 개인건강기록(PHR)](https://k-his.or.kr/menu.es?mid=a10204000000)
- [복지부 — 의료 마이데이터 플랫폼 운영](https://www.mohw.go.kr/board.es?mid=a10101060000&bid=0050&act=view&list_no=1479940)
- [RFC 6749 — OAuth 2.0 Authorization Framework](https://datatracker.ietf.org/doc/html/rfc6749)

---

## AAL mirror verification (critical)

### 1. NIST SP 800-63-3 AAL 공식 정의 (기준 프레임워크)

NIST SP 800-63B §4.2–§4.4에서 AAL은 인증 **세션 수준 보증(authenticator assurance)** 이며 신원확인(IAL)·연합(FAL)과 직교한다. 원문 SHALL 문장 발췌:

- **AAL1**: "AAL1 authentication SHALL occur by the use of any of the following authenticator types" (memorized secret, look-up secret, OOB device, OTP, cryptographic software/hardware). "Cryptographic authenticators used at AAL1 SHALL use approved cryptography."
- **AAL2**: "At AAL2, authentication SHALL occur by the use of **either a multi-factor authenticator or a combination of two single-factor authenticators**." "Approved cryptographic techniques are required at AAL2 and above." "At least one authenticator used at AAL2 SHALL be **replay resistant**." 재인증 12시간 / 비활성 30분.
- **AAL3**: "AAL3 authentication SHALL occur by the use of one of a combination of authenticators" 요구. "AAL3 additionally requires the use of a **hardware-based authenticator** and **verifier impersonation resistance**." FIPS 140 Level 2 이상(물리 Level 3) 검증 필수. 재인증 12시간 / 비활성 15분.

출처: [NIST SP 800-63B Authenticator Assurance Levels](https://pages.nist.gov/800-63-3/sp800-63b.html), [NIST 800-63-3 Implementation Resources — AAL table](https://pages.nist.gov/800-63-3-Implementation-Resources/63B/AAL/). 차기 버전 [NIST SP 800-63-4 draft](https://pages.nist.gov/800-63-4/sp800-63.html) 및 [NIST SP 800-63B-4 AAL](https://pages.nist.gov/800-63-4/sp800-63b/aal/)은 패스키·동기화 인증 반영 개정안이나 한국 미채택.

### 2. 한국 등가 프레임워크 — **존재하지 않는다**

조사한 모든 한국 인증 관련 공식 문서에서 **NIST AAL 3단계 체계를 그대로 채택한 규정은 없다**. 관련 프레임워크는 서로 다른 축을 사용한다:

| 한국 프레임워크 | 축(axis) | 공표 레이블 | NIST AAL과의 관계 |
|---|---|---|---|
| 전자서명법 (2020 개정) | 서비스 사업자 인정 | "전자서명인증사업자 인정 / 미인정", "운영기준 적합" | 사업자 수준 gate — authenticator 수준 등급 없음 |
| 전자금융감독규정 §34 | 안전성 기준 | "사용자인증 / 거래인증 / 단말인증" 기능 구분 | AAL-유사 3단계 수치 등급 **삭제**(2015년 "인증방법 등급제" 폐지 후 통합) |
| 정보통신망법 §23조의3 + 방통위 고시 2022-1 | 본인확인기관 지정 | "지정 / 조건부지정 / 미지정" | 기관 지정 등급 — authenticator 등급 아님 |
| ISMS-P (KISA) | 관리체계 인증 | "ISMS / ISMS-P 인증 / 미인증" | 관리체계 ISO 27001-유사 — authenticator 레벨 아님 |
| CSAP (클라우드) | 클라우드 보안등급 | "상/중/하" (클라우드 자체 등급) | 클라우드 환경 등급, 인증 수단 등급 아님 |
| FIDO UAF/U2F/CTAP2 인증 | FIDO Alliance 제품 인증 | "FIDO UAF v1.0 인증", "FIDO2 인증" | 제품 인증(interop) — NIST AAL ≠ FIDO cert |
| eIDAS "Low/Substantial/High" | EU 상호인정 | **한국 미채택** | N/A |

### 3. Provider별 실제 공표 레이블 수집

| Family/Provider | 공표 원어 레이블 | 공표 주체 | 인용 |
|---|---|---|---|
| 공동인증서 | "(구) 공인전자서명" → "공동인증서" | 전자서명법, KISA | [KISA rootca.or.kr](https://rootca.kisa.or.kr/kor/accredited/accredited03_01View.jsp?seqno=1) |
| 금융인증서 | "금융인증서" | 금결원 | [KFTC authInfo](https://www.kftc.or.kr/service/authInfo) |
| PASS (통신3사) | "PASS 인증서", "FIDO 기반 간편인증" | 각 통신사, KISA 인정 | [SK OpenAPI PASS](https://openapi.sk.com/products/detail?svcSeq=64), [KT PASS](https://fido.kt.com/ktauthIntro) |
| 카카오 인증 | "카카오 인증", "카카오뱅크 인증서" | 카카오, 전자서명법 인정 | [kakaobank guide](https://auth.kakaobank.com/guide/guideIdentificationPage) |
| 네이버 인증 | "네이버 인증" | 네이버, 전자서명법 인정 | [BaroCert naver](https://developers.barocert.com/reference/naver/java/identity/api) |
| 토스 인증 | "토스 인증" | 토스, 전자서명법 인정 | BaroCert |
| 은행 앱 인증서 | "KB모바일 인증서" / "신한인증서" 등 각 은행 명 | 각 은행 | 은행 공식 — 포털 내부 |
| 디지털원패스 | "디지털원패스", "FIDO UAF v1.0" | 행안부 | [eGovFrame onepass](https://www.egovframe.go.kr/wiki/doku.php?id=egovframework:com:v4.0:uat:%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4) — **EOL 2025-12-30** |
| Any-ID | "정부 통합인증(Any-ID)" | 행안부 | [MOIS Any-ID](https://www.mois.go.kr/frt/sub/a06/b04/easyCertification/screen.do) |
| 모바일 운전면허증 | "모바일 운전면허증", "블록체인 기반 DID" | 경찰청, 행안부 | [MOIS mobileID](https://www.mois.go.kr/frt/sub/a06/b04/mobileId/screen.do), [도로교통공단 가이드](https://www.safedriving.or.kr/guide/larGuide10.do) |
| 모바일 주민등록증 | "모바일 주민등록증" | 행안부 | [mobileid.go.kr](https://www.mobileid.go.kr/) |
| 금융 마이데이터 | "마이데이터 표준 API", scope 단위 (`bank.list` 등) | 금융위, 금결원 | [developers.mydatakorea.org](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0101) |
| 공공 마이데이터 | "공공 마이데이터" | 행안부 | [adm.mydata.go.kr](https://adm.mydata.go.kr/images/guide.pdf) |
| 의료 마이데이터 | "의료 마이데이터 / PHR" | 복지부, 보건의료정보원 | [myhealthway.go.kr](https://www.myhealthway.go.kr/portal/) |

**AAL1/AAL2/AAL3이라는 레이블은 위 어떤 provider 공표에도 나타나지 않는다.**

### 4. KOSMOS 현재 할당 vs 공표 등급 대조

Discussion #1051 제시안 (원문):

| Family | KOSMOS AAL | 공표 실제 레이블 | Mirror? |
|---|---|---|---|
| 공동인증서 | AAL3 | "(구) 공인전자서명" / "공동인증서" | **FAIL** — 번역 라벨 |
| 금융인증서 | AAL3 | "금융인증서" | **FAIL** — 번역 라벨 |
| 간편인증 | AAL2 | "간편인증" / 각 provider 브랜드 | **FAIL** — 번역 라벨 |
| 디지털원패스 | AAL2 | "디지털원패스 (EOL)" / "Any-ID" | **FAIL** — 번역 라벨 + 대상 종료 |
| 모바일 신분증 | AAL2 | "모바일 신분증 / 블록체인 DID" | **FAIL** — 번역 라벨 |
| 마이데이터 | AAL2 | "마이데이터 표준 API" | **FAIL** — AAL은 인증 레벨, 마이데이터는 **인가/전송 범위** 체계라 카테고리 오류 |

### 5. Mismatch 분석

A. **Category mismatch**. 마이데이터는 "인증 수단"이 아니라 **"데이터 전송 권한(인가)"** 체계다. OAuth 2.0 scope catalog이지 authenticator taxonomy가 아니다. KOSMOS가 여기에 `auth_level: AAL2`를 붙이는 것은 NIST가 정의한 AAL의 semantic(authenticator strength)과 전혀 다른 축에 label을 찍는 것이다.

B. **Translation, not mirror**. "공동인증서 = AAL3"은 NIST가 요구하는 FIPS 140 Level 2 이상 하드웨어 보증·verifier impersonation resistance를 한국 CA가 공식적으로 주장·인증받은 적이 **없다**. 공동인증서는 PKCS#12 소프트키로도 발급 가능하며(파일 저장), 이는 NIST 기준상 AAL2 software-crypto 수준에 가깝다. 즉 KOSMOS의 "AAL3" 라벨은 **번역자(KOSMOS 팀)의 해석치**일 뿐 공표된 사실과 매핑이 없다.

C. **Ambiguity collapse**. "간편인증 = AAL2"는 실제로는 PASS(SMS + SIM 기반)와 카카오(앱 기반 PIN/생체)를 동일 등급으로 취급하는데, NIST 기준으로 SMS는 SP 800-63B §5.1.3.3에서 **"RESTRICTED"** 분류이며 AAL2에서도 권장되지 않는 수단이다. PASS를 AAL2로 라벨링하는 것은 NIST 자체 가이드라인과도 충돌한다.

D. **Mirror principle violation**. Constitution v1.3.0 Principle VI("외부 계약 표면을 바이트 수준까지 미러")에 따르면, mock adapter가 실제 provider로 교체될 때 harness가 손대지 않아야 한다. 실제 provider는 "금융인증서"라는 문자열을 공표하는데 KOSMOS가 "AAL3"으로 저장해 두면 교체 시점에 매핑 테이블이 필요해진다 — 이는 mirror가 아니라 **translation layer**이다.

### 6. 권고 수정안 (mirror-conformant)

#### 6-1. 필드 리네이밍

`src/kosmos/tools/models.py` 및 `docs/security/tool-template-security-spec-v1.md`에서:

```python
# Before (v1.1, translation — FAIL)
auth_level: Literal["AAL1", "AAL2", "AAL3"]

# After (proposed v1.2, mirror — PASS)
published_tier: Literal[
    # Family 1
    "공동인증서",              # 구 공인전자서명
    # Family 2
    "금융인증서",
    # Family 3
    "PASS",                   # 통신3사 공통 브랜드
    "카카오인증",
    "네이버인증",
    "토스인증",
    "삼성패스",
    "은행앱인증서",            # KB/신한/하나/우리 하위 분기는 sub-field
    # Family 4
    "디지털원패스",            # EOL 2025-12-30 — 미러만 유지
    "정부통합인증_AnyID",
    # Family 5
    "모바일운전면허증",
    "모바일주민등록증",
    "모바일외국인등록증",
    "모바일국가보훈등록증",
    "모바일재외국민신원증명서",
    # Family 6 — 사실상 '인가' 축이므로 다른 필드로 분리 권장
    "마이데이터_금융",
    "마이데이터_공공",
    "마이데이터_의료",
]
```

#### 6-2. 파생 hint 필드 (선택)

Orchestration layer가 정책 결정에 NIST AAL-like 수치가 필요하면 advisory-only 파생 값을 별도로 둔다:

```python
# Derived, advisory-only, NOT mirrored from provider
nist_aal_hint: Optional[Literal["AAL1", "AAL2", "AAL3"]] = Field(
    default=None,
    description=(
        "KOSMOS 내부 해석치. Provider가 공표한 값이 아니다. "
        "NIST SP 800-63B 기준 best-effort 추정이며, 정책 결정의 유일한 근거로 쓰지 말 것. "
        "공식 carve-out이 수립되기 전까지는 `published_tier`를 우선한다."
    ),
)
```

#### 6-3. 마이데이터 카테고리 분리

마이데이터는 authenticator 축이 아니므로 별도 필드로 분리:

```python
mydata_category: Optional[Literal["금융", "공공", "의료"]] = None
mydata_scope: list[str] = Field(default_factory=list)  # e.g., ["bank.list", "bank.invest"]
```

#### 6-4. Tool Template Security Spec v1.2 갱신

docs/security/tool-template-security-spec-v1.md에서 Principle VI(Out of Scope Declaration) 및 Spec 031 Mock Facade 8-verb Expansion에 이 mirror 원칙을 **반드시** 포함. 현재 v1.1 "auth_level" 매트릭스 섹션은 deprecated로 표기하고 `published_tier` 매트릭스로 재작성.

#### 6-5. Epic #994 (Mock Facade 8-verb) 선행 조건

8-verb 중 `verify`의 계약 확정 전에 위 리네이밍을 먼저 merge해야 한다. 그렇지 않으면 mock과 실제 provider 교체 시 harness coupling이 발생한다 (mirror 원칙 위반).

### 7. 최종 판정

**FAIL (mirror 원칙 위반).** KOSMOS 현재 `auth_level: Literal["AAL1","AAL2","AAL3"]`는 실제 한국 공표 등급을 미러하지 않는 **번역 레이블**이며, Constitution v1.3.0 Principle VI에 정의된 mirror 원칙과 직접 충돌한다. 위 §6 권고대로 `published_tier` + 선택적 `nist_aal_hint`로 분리해야 한다.

---

## Cross-cutting patterns

1. **No unified assurance framework.** 한국은 NIST SP 800-63 · eIDAS 같은 **수평 통합 보증 레벨 체계**를 채택하지 않았다. 대신 (a) 전자서명법(서명 주체 인정), (b) 전자금융감독규정(금융 거래 안전성), (c) 정보통신망법(본인확인기관 지정), (d) 개인정보보호법(처리 요건)의 **수직 사일로**가 독립 운영된다. 이는 정치적·역사적 산물이며 단기에 변할 징후 없음.

2. **Protocol heterogeneity**. OAuth 2.0 (마이데이터·PASS·카카오 OIDC), SAML 2.0 (디지털원패스), PKCS#7/PKCS#12 (공동/금융인증서), W3C VC + K-DIDF (모바일 신분증), ISO 18013-5 (mDL 일부)가 공존. 단일 Python 라이브러리로 전부 커버 불가 — KOSMOS mock은 family별 서브모듈 구조가 불가피.

3. **Intermediary pattern**. 간편인증 대부분(카카오/네이버/토스)이 BaroCert·KICA·드림시큐리티 등 **aggregator**를 거친다. 마이데이터 금융도 KFTC **중계기관** 경유. KOSMOS mock은 (RP → aggregator → provider) 3-tier 토폴로지를 family 3·6에서는 기본으로 모델링해야 한다.

4. **Reauthentication timing 미공표**. NIST AAL2/AAL3가 규정한 12h 세션 재인증 · 15/30분 비활성 컷오프는 대응 레이블이 한국에 없다. 각 service가 자율 판정. Mock은 "unspecified, RP 재량"으로 두는 게 맞다.

5. **Legal basis — 미러 여부에 독립**. 공표된 법적 지위(전자서명법상 효력·도로교통법상 실물 동등)는 mock이 흉내낼 수 있는 축이 아니다. KOSMOS는 `legal_basis` 필드에 "전자서명법", "도로교통법 제80조" 등 원문 인용만 저장하고 실제 법적 효력은 disclaim해야 한다(이미 `docs/tool-adapters.md` 패턴과 정합).

6. **Mobile-first**. 모든 family에서 데스크톱 브라우저 플로우는 모바일 앱 콜백에 의존한다(공동인증서 PC 로그인조차 모바일 앱 승인을 요구하는 은행이 증가). KOSMOS mock은 "out-of-band device notification"을 first-class로 다뤄야 한다.

---

## Unknowns matrix (⚠️ OPAQUE)

| Topic | Missing artifact | Why it matters | Acquisition plan |
|---|---|---|---|
| 공동인증서 각 은행 wrapper(AnySign/MagicLine) | 정확한 JSON/바이너리 payload | Byte-level mirror 불가 | Institutional disclosure 필요 (MOU) |
| 금융인증서 exchange endpoint assertion | JWT/PKCS#7 claim 목록 | Mock에서 검증 절차 미완 | 금결원 OpenAPI 가입 후 sandbox |
| Any-ID 기술 사양 | IdP protocol (OIDC vs SAML vs 자체) | EOL된 OnePass 후속 미러 공백 | 행안부 개발자 포털 개설 대기 |
| K-DIDF consortium ledger | 노드 목록, 합의 알고리즘 | `did:omn:` resolve 완전 모사 불가 | opendid.org 공개 SDK 분석 + 협력 |
| 의료 마이데이터 FHIR 프로파일 | 한국형 FHIR IG (StructureDefinition) | VP/API 정확한 필드 미확정 | 건강정보 고속도로 API 활용 신청 |
| 은행별 인증서(KB/신한/하나/우리) SDK | 각 은행 내부 포맷 | 간편인증 family 3D 완전 모사 불가 | 개별 은행 B2B 계약 |
| 본인확인기관 "계량평가" 2개 항목 | 구체 평가지표 | 규제 대응 레이블 정확도 | 방통위 고시 원문 다운로드 |
| 전자금융감독규정 별표 2-2 | 인증수단 등급 원문 | "인증방법 등급" 폐지/통합 상세 | 국가법령정보센터 PDF 획득 |

---

## References

### NIST·국제 표준
- [NIST SP 800-63B — Authentication & Lifecycle Management](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [NIST SP 800-63-3 — Digital Identity Guidelines (main)](https://pages.nist.gov/800-63-3/sp800-63-3.html)
- [NIST SP 800-63-4 draft](https://pages.nist.gov/800-63-4/sp800-63.html)
- [NIST SP 800-63B-4 AAL](https://pages.nist.gov/800-63-4/sp800-63b/aal/)
- [NIST 800-63-3 Implementation Resources — AAL](https://pages.nist.gov/800-63-3-Implementation-Resources/63B/AAL/)
- [ISO/IEC 18013-5:2021 mDL](https://www.iso.org/standard/69084.html)
- [ISO/IEC 18013-5 sample PDF](https://cdn.standards.iteh.ai/samples/69084/9b2e0bf21d5e4a26aa1a587e29aa63a9/ISO-IEC-18013-5-2021.pdf)
- [ISO/IEC TS 18013-7:2024 mDL add-on](https://www.iso.org/standard/82772.html)
- [W3C Verifiable Credentials Data Model 1.0 (KR 번역)](https://ssimeetupkorea.github.io/vc-data-model/)
- [OpenID for Verifiable Presentations 1.0](https://openid.net/specs/openid-4-verifiable-presentations-1_0.html)
- [OpenID4VP draft 23](https://openid.net/specs/openid-4-verifiable-presentations-1_0-23.html)
- [RFC 6749 — OAuth 2.0](https://datatracker.ietf.org/doc/html/rfc6749)
- [FIDO Alliance 개요 (KR)](https://fidoalliance.org/overview/?lang=ko)
- [eIDAS Levels of Assurance — European Commission](https://ec.europa.eu/digital-building-blocks/sites/spaces/DIGITAL/pages/467110081/eIDAS+Levels+of+Assurance)

### 법령·고시·가이드
- [전자서명법 (국가법령정보센터)](https://law.go.kr/%EB%B2%95%EB%A0%B9/%EC%A0%84%EC%9E%90%EC%84%9C%EB%AA%85%EB%B2%95)
- [전자금융감독규정 (국가법령정보센터)](https://law.go.kr/%ED%96%89%EC%A0%95%EA%B7%9C%EC%B9%99/%EC%A0%84%EC%9E%90%EA%B8%88%EC%9C%B5%EA%B0%90%EB%8F%85%EA%B7%9C%EC%A0%95)
- [전자금융거래법 (국가법령정보센터)](https://www.law.go.kr/%EB%B2%95%EB%A0%B9/%EC%A0%84%EC%9E%90%EA%B8%88%EC%9C%B5%EA%B1%B0%EB%9E%98%EB%B2%95)
- [방통위 고시 2022-1호 — 본인확인기관 지정 기준 개정 해설](https://m.boannews.com/html/detail.html?idx=103922)
- [Kim&Chang — 전자금융감독규정 개정 해설](https://www.kimchang.com/ko/insights/detail.kc?sch_section=4&idx=31385)

### KISA / 정부 포털
- [KISA 전자서명인증사업자 인정·평가 제도](https://www.kisa.or.kr/1050609)
- [KISA 전자서명인증관리센터 — 기술규격 프로파일 목록](https://www.rootca.or.kr/kor/standard/standard01A.jsp)
- [KISA 본인확인 지원포털 — 지정기준](https://identity.kisa.or.kr/web/main/contents/M050-03)
- [KISA 본인확인 지원포털 — 본인확인기관 현황](https://identity.kisa.or.kr/web/main/contents/M010-03)
- [KISA ISMS-P 인증기준 안내서 (PDF)](https://www.isac.or.kr/upload/ISMS-P%20%EC%9D%B8%EC%A6%9D%EA%B8%B0%EC%A4%80%20%EC%95%88%EB%82%B4%EC%84%9C(2022.4.22).pdf)
- [KISA 전자서명인증사업자 인정기관 trustesign](https://trustesign.kisa.or.kr/)
- [KISA trustesign 인정기관 소개](https://trustesign.kisa.or.kr/intro/info)
- [행정안전부 정부 통합인증(Any-ID) 안내](https://www.mois.go.kr/frt/sub/a06/b04/easyCertification/screen.do)
- [행정안전부 모바일 신분증 안내](https://www.mois.go.kr/frt/sub/a06/b04/mobileId/screen.do)
- [행정안전부 공공 마이데이터](https://mois.go.kr/frt/sub/a06/b02/digitalOpendataMydata/screen.do)
- [행정안전부 — 디지털 신원 인증 시대 개막 보도자료](https://www.mois.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=106515)
- [모바일 신분증 포털](https://www.mobileid.go.kr/)
- [모바일 신분증 개발지원센터](https://dev.mobileid.go.kr/)
- [건강정보 고속도로 포털](https://www.myhealthway.go.kr/portal/)
- [건강정보 고속도로 API 가이드](https://www.myhealthway.go.kr/portal/index?page=Individual/Portal/MediMyData/MydataApi)
- [정부24 마이데이터 소개](https://www.gov.kr/portal/mydata/myDataIntroduction?Mcode=11258)
- [공공 마이데이터 업무포털 — 가이드 v1.5](https://adm.mydata.go.kr/images/guide.pdf)

### CA / 서비스 원문
- [KCAC.TS.DSIG — 전자서명 알고리즘](https://rootca.or.kr/kcac/down/TechSpec/2.1-KCAC.TS.DSIG.pdf)
- [KCAC.TS.CERTVAL v1.11](https://www.rootca.or.kr/kcac/down/TechSpec/5.3-KCAC.TS.CERTVAL.pdf)
- [KCAC.TS.CRLPROF v1.50](https://www.rootca.or.kr/kcac/down/TechSpec/1.2-KCAC.TS.CRLPROF.pdf)
- [KCAC.TS.CMP v1.22](https://rootca.kisa.or.kr/kcac/down/TechSpec/3.2-KCAC.TS.CMP.pdf)
- [KCAC.TS.HSMU v2.40](https://rootca.kisa.or.kr/kcac/down/TechSpec/6.3-KCAC.TS.HSMU.pdf)
- [한국전자인증 CrossCert CPS 5.3](https://www.crosscert.com/glca/file/Certification_Practice_Statement_5.3.pdf)
- [금결원 금융인증 서비스](https://www.kftc.or.kr/service/authInfo)
- [금결원 OpenAPI — 금융인증](https://openapi.kftc.or.kr/service/financeAuthentication)
- [yessign 금융인증서](https://www.yeskey.or.kr/?url=yeskey/yessign/certificate/finance&menuSeq=100058&upMenuSeq=100000)
- [SK OpenAPI PASS](https://openapi.sk.com/products/detail?svcSeq=64)
- [KT PASS/FIDO](https://fido.kt.com/ktauthIntro)
- [PASS 휴대폰번호 로그인 개발자센터](https://developers.passlogin.com/docs/develop/ios)
- [BaroCert 통합 플랫폼](https://www.barocert.com/)
- [BaroCert 카카오 본인인증 API](https://developers.barocert.com/reference/kakao/java/identity/api)
- [BaroCert 네이버 본인인증 API](https://developers.barocert.com/reference/naver/java/identity/api)
- [카카오뱅크 본인확인 API 가이드](https://auth.kakaobank.com/guide/guideIdentificationPage)
- [카카오뱅크 전자서명 API 가이드](https://auth.kakaobank.com/guide/guideDigitalSignPage)
- [국세청 홈택스 간편인증 매뉴얼 (2025.09)](https://hometax.speedycdn.net/dn_dir/webdown/%EA%B0%84%ED%8E%B8%EC%9D%B8%EC%A6%9D%EB%A1%9C%EA%B7%B8%EC%9D%B8%EC%9E%90%EC%84%B8%ED%9E%88%EB%B3%B4%EA%B8%B0.pdf)
- [마이데이터 데이터 표준 API 인증규격 (금융)](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0102)
- [마이데이터 개별인증 API](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0201?id=7)
- [마이데이터 통합인증 API](https://developers.mydatakorea.org/mdtb/apg/mac/bas/FSAG0202?id=12)
- [마이데이터 표준 API 기본 규격](https://developers.mydatakorea.org/mdtb/apg/dgi/bas/FSAG0101)
- [금결원 마이데이터 API](https://mydata.kftc.or.kr/web/mydataApi/api)
- [복지부 — 의료 마이데이터 플랫폼 운영](https://www.mohw.go.kr/board.es?mid=a10101060000&bid=0050&act=view&list_no=1479940)
- [한국보건의료정보원 — 개인건강기록(PHR)](https://k-his.or.kr/menu.es?mid=a10204000000)

### eGovFrame / 연동 가이드
- [eGovFrame 디지털원패스 연동 (SAML)](https://www.egovframe.go.kr/wiki/doku.php?id=egovframework:com:v4.0:uat:%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4)
- [eGovFrame 모바일 운전면허증 연동 v4.1](https://www.egovframe.go.kr/wiki/doku.php?id=egovframework:com:v4.1:sec:%EB%AA%A8%EB%B0%94%EC%9D%BC_%EC%9A%B4%EC%A0%84%EB%A9%B4%ED%97%88%EC%A6%9D)
- [행정전자서명(GPKI) 인증관리센터](https://www.gpki.go.kr/)
- [GPKI 프로파일·알고리즘 상세서 PDF](https://www.gpki.go.kr/upload/download/1.3-GPKI-CPS%20Profile%20and%20Algorithm.pdf)

### EOL / 종료 공지
- [IFEZ — 디지털원패스 종료 안내 (2025-12-30)](https://www.ifez.go.kr/main/pst/view.do?pst_id=noti01&pst_sn=668873&search=)
- [도로교통공단 — 디지털원패스 서비스 종료 안내](https://www.koroad.or.kr/main/board/1/304186/board_view.do)
- [질병관리청 — 디지털원패스 로그인 종료 안내](https://is.kdca.go.kr/isc/popupmain/onepassnotices.html)

### 보도·해설
- [대한민국 정책뉴스 — 공인전자서명 21년만 폐지](https://www.korea.kr/news/policyNewsView.do?newsId=148880731)
- [Korea IT Times — 공인인증서 폐지 기사](http://www.koreaittimes.com/news/articleView.html?idxno=97651)
- [전자신문 — "굿바이 공인인증서"](https://m.etnews.com/20201209000179)
- [이글루시큐리티 — 21년만의 공인인증서 폐지](https://www.igloo.co.kr/security-information/21%EB%85%84%EB%A7%8C%EC%9D%98-%EA%B3%B5%EC%9D%B8%EC%9D%B8%EC%A6%9D%EC%84%9C-%ED%8F%90%EC%A7%80/)
- [ZDNet Korea — 본인확인기관 지정 심사 2025](https://zdnet.co.kr/view/?no=20250320144442)

### 커뮤니티·위키 (참고용, 1차 출처는 법령·포털)
- [나무위키 — 공동인증서](https://namu.wiki/w/%EA%B3%B5%EB%8F%99%EC%9D%B8%EC%A6%9D%EC%84%9C)
- [나무위키 — 금융인증서](https://namu.wiki/w/%EA%B8%88%EC%9C%B5%EC%9D%B8%EC%A6%9D%EC%84%9C)
- [나무위키 — 디지털원패스](https://namu.wiki/w/%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4)
- [나무위키 — 정부 통합인증](https://namu.wiki/w/%EC%A0%95%EB%B6%80%20%ED%86%B5%ED%95%A9%EC%9D%B8%EC%A6%9D)
- [나무위키 — PASS](https://namu.wiki/w/PASS)
- [위키백과 — 디지털원패스](https://ko.wikipedia.org/wiki/%EB%94%94%EC%A7%80%ED%84%B8%EC%9B%90%ED%8C%A8%EC%8A%A4)
- [위키백과 — 모바일 운전면허증](https://ko.wikipedia.org/wiki/%EB%AA%A8%EB%B0%94%EC%9D%BC_%EC%9A%B4%EC%A0%84%EB%A9%B4%ED%97%88%EC%A6%9D)
- [Wikipedia — Mobile driver's license](https://en.wikipedia.org/wiki/Mobile_driver's_license)
- [OmniOne Enterprise Brochure 2024 (KR)](https://www.omnione.net/layout/files/service/2/file_1/OmniOne%20Enterprise_Brochure%20_%EA%B5%AD%EB%AC%B8%20(2024).pdf)
- [opendid.org — 디지털 운전면허증 글로벌 표준화 기고](https://opendid.org/bbs/view.php?idx=12003&code=press&cat_code=2)

### KOSMOS 내부 참조 (정합성)
- `/Users/um-yunsang/KOSMOS/.specify/memory/constitution.md` — Principle VI Out of Scope Declaration
- `/Users/um-yunsang/KOSMOS/docs/security/tool-template-security-spec-v1.md` — 현재 auth_level 매트릭스(수정 대상)
- `/Users/um-yunsang/KOSMOS/src/kosmos/tools/models.py` — `GovAPITool.auth_level` 필드(수정 대상)
- `/Users/um-yunsang/KOSMOS/specs/031-mock-facade-8verb/` — 본 리서치가 차단하는 `verify` 계약 정의 spec
