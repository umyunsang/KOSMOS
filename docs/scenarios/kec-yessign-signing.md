# 공동인증서 서명 — KEC / yessign 전자서명 OPAQUE-도메인 시나리오

> **Scope**: 시민이 KOSMOS 에서 "이 계약서에 서명해줘" 또는 "이 PDF 에 공인인증서로 서명" 같은 전자서명 요청을 했을 때의 hand-off 흐름.
> **Originating spec**: Epic ζ #2297.
> **Authoritative source**: AGENTS.md § L1-B B3.

## 어댑터를 만들지 않는 이유

공동인증서 (구 공인인증서) 의 디지털 서명은 KEC (Korea Electronic Certification Authority) 의 yessign / SignKorea 등 발급기관별 클라이언트 소프트웨어에 의존한다. 서명 ceremony 는 (a) 시민의 USB / 하드디스크 / 스마트폰의 NPKI 디렉토리에 저장된 인증서 + 개인키 파일 접근, (b) 시민이 직접 입력한 인증서 비밀번호로 개인키 복호화, (c) 서명 대상 데이터 (PDF, XML, hash) 에 PKCS#7/CMS 서명 생성 — 이 모두 시민의 로컬 단말에서 일어나야 한다. 외부 LLM 또는 외부 서비스가 인증서 비밀번호를 보거나 개인키에 접근하면 PIPA 와 전자서명법 위반이 된다. 따라서 KOSMOS 는 공동인증서 서명을 어댑터로 만들지 않고, 시민이 KEC / yessign 자체 클라이언트 또는 서명을 요구하는 부처/기관 사이트 (예: 홈택스 / 정부24) 에 직접 진입하도록 hand-off.

## Citizen narrative

1. **시민 발화**: "이 계약서에 공동인증서로 서명해줘" 또는 "PDF 에 공인인증서 서명 부탁".
2. **KOSMOS 응답**: LLM 은 즉시 hand-off — "전자서명은 시민의 단말에서 직접 진행해야 하는 작업이며 KOSMOS 가 대행할 수 없습니다. 아래 가이드를 따라 KEC 클라이언트 또는 서명을 요구하는 사이트에서 직접 서명해주세요." (어떤 verify/submit chain 도 emit 하지 않음 — 이 트리거는 chain pattern 의 trigger 화이트리스트에 들어가지 않음.)
3. **시민 작업 — 인증서 확인**: 시민이 자신의 단말 (PC 또는 스마트폰) 에 공동인증서가 설치되어 있는지 확인. 없다면 발급기관 (KEC / yessign / SignKorea 등) 에서 발급 후 단말 NPKI 폴더 또는 모바일 인증서 앱에 저장.
4. **시민 작업 — 서명 진행**: 서명 대상이 KOSMOS 가 lookup 한 문서 (예: 홈택스 신고서 PDF) 인 경우, 시민이 그 문서를 가지고 홈택스 또는 정부24 본 사이트로 이동, 거기서 제공하는 공동인증서 서명 plugin (Veraport 또는 Magicline 또는 ANYsign) 를 통해 서명. 서명 대상이 외부 계약서 PDF 인 경우 시민이 KEC 의 yessign 클라이언트 또는 인증서 발급기관별 서명 SW 를 사용해 직접 서명.
5. **시민이 KOSMOS 로 복귀**: 서명 완료된 PDF / XML 의 hash 또는 접수번호를 KOSMOS 에 입력하면 향후 lookup (예: 서명 검증 결과 조회) 에 사용 가능. Consent ledger 에 "서명은 hand-off, 결과 조회만 KOSMOS chain" 의 분리가 기록됨.

## Hand-off URL

- KEC (Korea Electronic Certification Authority): https://www.kec.co.kr/
- yessign (한국정보인증): https://www.yessign.or.kr/
- SignKorea (코스콤): https://www.signkorea.com/
- 발급기관 안내 (KISA — 한국인터넷진흥원): https://www.rootca.or.kr/
