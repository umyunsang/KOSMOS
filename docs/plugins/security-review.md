# Security Review · PIPA §26 Trustee Acknowledgment · L3 Gate

> 본 문서의 본문은 T033 (Epic #1636) 에서 작성됩니다.
> 단, 아래 canonical PIPA §26 trustee acknowledgment text 는 T005 (Epic #1636) 에서
> `src/kosmos/plugins/canonical_acknowledgment.py:_extract_canonical_text()` 가 추출하는
> source-of-truth 이므로 Phase 1 스캐폴딩 시점부터 마커가 자리잡고 있어야 합니다.

## Current canonical SHA-256

> T005 시점에 `src/kosmos/plugins/canonical_acknowledgment.py` 가 import 시점에 자동 산출.
> 본 문서 상단에 산출된 값을 기록하는 작업은 T033 에서 수행됩니다.

(아직 산출 전 — Phase 2 T005 작업 후 갱신)

## Canonical PIPA §26 Trustee Acknowledgment Text

아래 마커 사이의 본문은 **수탁자 동의문 canonical text** 입니다.
플러그인 매니페스트의 `pipa_trustee_acknowledgment.acknowledgment_sha256` 필드는
이 텍스트의 SHA-256 (UTF-8 인코딩, `\n` 정규화, leading/trailing whitespace strip 후)
과 정확히 일치해야 합니다.

마커는 절대 변경하지 마십시오. 본문 변경 시 모든 기존 플러그인이 hash mismatch 로
거부됩니다 (drift-audit workflow 는 #1926 deferred).

<!-- CANONICAL-PIPA-ACK-START -->

본 플러그인의 기여 조직(이하 "수탁자")은 「개인정보 보호법」 제26조 및 같은 법
시행령 제28조에 따른 개인정보 처리 위탁의 수탁자로서 다음 의무를 인지하고
이행하기로 동의합니다.

1. 위탁업무의 목적과 범위 내에서만 개인정보를 처리합니다.
2. 위탁업무 처리 목적 달성에 필요한 최소한의 개인정보만을 수집·이용합니다.
3. 개인정보의 안전성 확보를 위한 기술적·관리적 조치를 이행합니다.
4. 재위탁(下수탁)은 KOSMOS 운영자(위탁자)의 사전 서면 동의 없이 수행하지 않습니다.
5. 개인정보의 처리 현황 및 안전성 확보 조치 이행 여부에 대한 KOSMOS 운영자의
   감독에 협조합니다.
6. 위탁업무 종료 시 개인정보를 지체 없이 파기하고 그 결과를 KOSMOS 운영자에게
   서면으로 통보합니다.
7. 본 의무를 위반하여 정보주체에게 손해가 발생한 경우 그 손해를 배상할 책임이
   있음을 확인합니다.

수탁자는 본 acknowledgment 의 SHA-256 해시값을 플러그인 manifest 에 기록함으로써
위 의무에 동의함을 표시합니다.

<!-- CANONICAL-PIPA-ACK-END -->

## L3 Gate Procedure (T033)

본문은 T033 에서 작성.

## L2+ Sandboxing Guidelines (FR-024)

본문은 T033 에서 작성.

## Bilingual glossary

(T033 에서 작성)

## Reference

- 「개인정보 보호법」 제26조: https://www.law.go.kr/법령/개인정보보호법/제26조
- 「개인정보 보호법 시행령」 제28조: https://www.law.go.kr/법령/개인정보보호법시행령/제28조
- Memory `project_pipa_role` (KOSMOS PIPA stance)
- `specs/1636-plugin-dx-5tier/contracts/pipa-acknowledgment.md`
