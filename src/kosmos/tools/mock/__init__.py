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
"""

# T027 — US1 submit adapters. Import triggers self-registration in
# kosmos.primitives.submit._ADAPTER_REGISTRY at module load time.
# APPEND ONLY — do not remove or reorder existing entries.
import kosmos.tools.mock.data_go_kr.fines_pay  # noqa: F401, E402
import kosmos.tools.mock.mydata.welfare_application  # noqa: F401, E402
