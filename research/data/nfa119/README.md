# NFA 119 API reference materials

Source files used for spec `029-phase2-adapters-119-mohw`.

| File | Issuer | API catalog ID | Retrieved | License |
|------|--------|----------------|-----------|---------|
| `공공데이터 오픈API 활용가이드(소방청_구급정보).docx` | 소방청 (NFA) | data.go.kr 15099423 | 2026-04-18 | KOGL Type 1 (출처표시) |
| `공공데이터 오픈API 활용가이드(소방청_구급통계).docx` | 소방청 (NFA) | data.go.kr 15099428 | 2026-04-18 | KOGL Type 1 |
| `부산광역시_119소방출동정보.docx` | 부산광역시 | data.go.kr 15087824 | 2026-04-18 | KOGL Type 1 |
| `소방청_119안전센터 현황_20250701.csv` | 소방청 (NFA) | data.go.kr 15065056 | 2026-04-18 | KOGL Type 1 |

## Endpoints (primary candidate for Phase 2 adapter)

- **소방청_구급정보서비스**: `https://apis.data.go.kr/1661000/EmergencyInformationService`
- **소방청_구급통계서비스**: `https://apis.data.go.kr/1661000/EmergencyStatisticsService`

The CSV file is the nationwide 119 safety-center directory (address + coordinates) and is used as a locally-joinable lookup to complement the HTTP APIs.

## Notes

- `.docx` files are parsed by spec agents via `python-docx`; no PDF conversion performed.
- All files are < 1 MB; KOGL Type 1 permits redistribution with attribution.
- Do not commit API keys alongside these files; keys belong in Infisical (see `specs/026-secrets-infisical-oidc/`).
