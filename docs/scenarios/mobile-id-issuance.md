# 모바일 신분증 발급 — 모바일ID OPAQUE-도메인 시나리오

> **Scope**: 시민이 KOSMOS 에서 "모바일 운전면허증 발급 받고 싶어" 또는 "모바일 신분증 만들어" 등 mobile-ID 발급 요청을 했을 때의 hand-off 흐름.
> **Originating spec**: Epic ζ #2297.
> **Authoritative source**: AGENTS.md § L1-B B3.

## 어댑터를 만들지 않는 이유

모바일 신분증 발급은 행정안전부의 모바일 신분증 앱 (전자정부 mDL — Mobile Driver's License, ISO/IEC 18013-5 기반) 자체 ceremony 를 통해서만 가능하다. 발급 과정에 (a) 시민의 단말 기기 보안 영역 (TEE/SE) 에 키 쌍 생성, (b) 행안부 PKI 와 attestation 교환, (c) 면허증/신분증 데이터를 단말에 sealed-storage 로 저장 — 의 3단계가 모두 단말 자체에서 일어나야 하며, 이는 LLM-callable 로 노출될 수 있는 종류의 ceremony 가 아니다. KOSMOS 는 발급 자체를 대행할 수 없고 — **이미 발급된 모바일ID 가 제시되었을 때 그 IdentityAssertion 을 verify 하는 것** 만 어댑터로 가능 (`mock_verify_module_modid` 또는 `mock_verify_mobile_id`). 따라서 KOSMOS 는 모바일ID 어댑터를 발급용으로는 만들지 않고, 검증용으로만 운영하며, 발급은 행안부 본 앱으로 hand-off.

## Citizen narrative

1. **시민 발화**: "모바일 운전면허증 발급 받고 싶어" 또는 "모바일 신분증 만들기".
2. **KOSMOS 응답 (모든 모드 동일)**: LLM 은 lookup 도 verify 도 emit 하지 않고, 즉시 hand-off 메시지 — "모바일 신분증 발급은 행정안전부 모바일 신분증 앱에서 직접 진행하셔야 합니다. KOSMOS 가 대행할 수 없는 작업입니다. 아래 안내를 확인해주세요." 시스템 프롬프트 `<verify_chain_pattern>` 의 trigger 매칭에서 "발급" 은 verify chain trigger 로 잡히지만, **모바일ID 발급** 은 어댑터가 없으므로 LLM 이 "현재 KOSMOS 가 다루는 공공 데이터로는 답할 수 없습니다" pattern 으로 fallback (system_v1.md `<tool_usage>` 마지막 paragraph). 이 시나리오 doc 자체가 LLM 이 fallback 했을 때 가리킬 hand-off 자료.
3. **시민 작업 — 앱 설치**: 시민이 안드로이드 Play Store 또는 iOS App Store 에서 "모바일 신분증" 앱 설치 — 행정안전부가 발급한 공식 앱.
4. **시민 작업 — 발급 ceremony**: 앱 내에서 본인인증 (PASS / 공동인증서 / 금융인증서 중 택1) → 동의 절차 → 단말 보안 영역에 키 페어 생성 → 행안부 서버와 attestation → 모바일 면허증/신분증 데이터를 단말에 sealed-storage 로 저장. 5분~15분 소요.
5. **시민이 KOSMOS 로 복귀**: 모바일ID 가 발급된 후, 시민은 향후 KOSMOS 의 verify chain 에서 `mock_verify_module_modid` 어댑터로 본인인증을 위임할 수 있음 (KOSMOS 가 발급된 모바일ID 의 IdentityAssertion 을 검증하는 것은 가능). Consent ledger 에 "발급은 hand-off, 검증은 KOSMOS chain 으로 위임" 의 분리가 기록됨.

## Hand-off URL

- 모바일 신분증 공식 안내 (행정안전부): https://www.mobileid.go.kr/
- 안드로이드 Play Store: https://play.google.com/store/apps/details?id=kr.go.mois.npki
- iOS App Store: https://apps.apple.com/kr/app/모바일-신분증/id6446664739
