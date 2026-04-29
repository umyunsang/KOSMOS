# 종합소득세 신고 — 홈택스 OPAQUE-도메인 시나리오

> **Scope**: 시민이 KOSMOS 에서 "종합소득세 신고해줘" 라고 요청했을 때, 어디까지 KOSMOS 가 chain 으로 처리하고, 어디서 홈택스 자체 UI 로 hand-off 하는지를 narrative 로 기록한다.
> **Originating spec**: Epic ζ #2297 (`specs/2297-zeta-e2e-smoke/spec.md`).
> **Authoritative source**: AGENTS.md § L1-B B3 ("OPAQUE domains are never wrapped — LLM hands off via `docs/scenarios/`").

## 어댑터를 만들지 않는 이유

홈택스 종합소득세 신고는 (a) 본인인증 (모바일ID / 공동인증서 / 금융인증서), (b) 신고서 작성 (사전 채움 + 직접 입력), (c) 전자서명 + 제출 의 3단계로 구성된다. 단계 (a) 는 KOSMOS verify primitive 로 위임 가능하며, 단계 (b) 의 사전 채움 데이터는 lookup primitive 로 가져올 수 있다. 그러나 **단계 (c) 의 실제 신고 제출은 홈택스 자체의 OPAQUE 채널** — 국세청 내부 신고시스템에 직접 결합된 PKCS#7 전자서명 페이로드를 요구하며, 외부 LLM-callable 으로 노출된 적이 없다. 따라서 KOSMOS 는 (a)+(b) 까지만 chain 으로 처리하고, (c) 는 홈택스 본 UI 로 hand-off 한다. (단, **Mock-mode demo 에서는** `mock_submit_module_hometax_taxreturn` 어댑터가 합성 접수번호 `hometax-YYYY-MM-DD-RX-XXXXX` 을 반환한다 — 이는 데모 목적의 fixture 이지 실제 제출이 아니다.)

## Citizen narrative

1. **시민 발화**: "종합소득세 신고해줘" — KOSMOS TUI 에 한국어 자연어로 입력.
2. **KOSMOS 응답 (Mock-mode)**: LLM 이 시스템 프롬프트의 chain pattern 을 따라 `verify(tool_id="mock_verify_module_modid", params={scope_list, purpose_ko, purpose_en})` → `lookup(mode="fetch", tool_id="mock_lookup_module_hometax_simplified", params={delegation_context})` → `submit(tool_id="mock_submit_module_hometax_taxreturn", params={delegation_context, ...})` 를 emit. 합성 접수번호 `hometax-2026-MM-DD-RX-XXXXX` 가 시민에게 표시.
3. **Live-mode 전환 (실제 운영 단계)**: KOSMOS 는 단계 2 의 lookup 결과 (사전 채움 데이터) 까지만 자체 chain 으로 처리하고, submit 단계에서 홈택스의 deep-link URL `https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml` (또는 정부24 통합 진입점) 를 시민에게 안내 — TUI 에 "홈택스에서 신고를 마무리해주세요" 메시지 + 클릭 가능한 URL.
4. **시민 작업 (홈택스 UI 내)**: 시민이 홈택스 본 사이트로 이동, 단계 2 의 사전 채움 데이터를 확인 + 부족분 직접 입력 + 공인인증서로 전자서명 + 신고서 제출. 홈택스가 발급한 접수번호를 받음.
5. **시민이 KOSMOS 로 복귀**: 시민이 받은 접수번호를 TUI 에 다시 입력하면 KOSMOS 가 향후 lookup (예: 신고 처리 상태 조회) 에 사용. KOSMOS 자체 audit ledger (`~/.kosmos/memdir/user/consent/<YYYY-MM-DD>.jsonl`) 에 hand-off 시점 + 복귀 접수번호 가 기록되어 시민이 "내가 무엇을 언제 위임했는가" 를 추적 가능.

## Hand-off URL

- 종합소득세 신고 진입점 (메인): https://www.hometax.go.kr/
- 모바일 종합소득세 신고 앱 (손택스): https://m.hometax.go.kr/
- 비회원 신고 (간편 인증 우선): https://www.hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml
