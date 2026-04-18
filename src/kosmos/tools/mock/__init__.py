"""Mock adapter tree for Spec 031 Five-Primitive Harness.

Six mock system sub-packages (byte- or shape-mirror-able public systems):
- data_go_kr: openapi.data.go.kr REST surface (byte mirror)
- omnione: OpenDID reference stack (byte mirror, Apache-2.0)
- barocert: developers.barocert.com SDK docs (shape mirror)
- mydata: KFTC MyData v240930 (shape mirror, mTLS/OAuth profile)
- npki_crypto: PyPinkSign crypto layer (PKCS#7/#12 only; portal session is OPAQUE)
- cbs: 3GPP TS 23.041 broadcast (byte mirror)

OPAQUE systems (gov24 submission, KEC XML signature, NPKI portal session)
live in docs/scenarios/ only — no mock adapter implementations (FR-026).

Spec 031 US2 verify adapters (T043) — one per family, registered on import:
- verify_gongdong_injeungseo: 공동인증서 / KOSCOM Joint Certificate
- verify_geumyung_injeungseo: 금융인증서 / Financial Certificate (KFTC)
- verify_ganpyeon_injeung: 간편인증 — Kakao/Naver/Toss/PASS/etc.
- verify_digital_onepass: Digital Onepass Level 1-3
- verify_mobile_id: 모바일 신분증 (mdl | resident)
- verify_mydata: 마이데이터 OAuth 2.0 + mTLS
"""

# T027 — US1 submit adapters. Import triggers self-registration in
# kosmos.primitives.submit._ADAPTER_REGISTRY at module load time.
# APPEND ONLY — do not remove or reorder existing entries.
import kosmos.tools.mock.data_go_kr.fines_pay  # noqa: F401, E402
import kosmos.tools.mock.mydata.welfare_application  # noqa: F401, E402

# T043 — US2 verify adapters. Import side-effect registers each family's
# adapter via register_verify_adapter(); imports are order-independent.
from kosmos.tools.mock import (  # noqa: F401, E402
    verify_digital_onepass,
    verify_ganpyeon_injeung,
    verify_geumyung_injeungseo,
    verify_gongdong_injeungseo,
    verify_mobile_id,
    verify_mydata,
)
