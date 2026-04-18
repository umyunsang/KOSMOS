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
