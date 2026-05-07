# NFA 119 Curl Evidence — 2026-05-06

Purpose: prove the live NFA EmergencyInformationService request contract before changing the real-use scenario and adapter metadata. Secrets are redacted; the command shows environment-variable expansion only.

## 구급활동정보 `getEmgencyActivityInfo`

```bash
curl -sS -A "Mozilla/5.0" -G --max-time 20 \
  "https://apis.data.go.kr/1661000/EmergencyInformationService/getEmgencyActivityInfo" \
  --data-urlencode "serviceKey=${KOSAX_DATA_GO_KR_API_KEY}" \
  --data-urlencode "rsacGutFsttOgidNm=천안동남소방서" \
  --data-urlencode "gutYm=202112" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=1" \
  --data-urlencode "resultType=json"
```

Observed:

```json
{
  "http_code": 200,
  "resultCode": "00",
  "resultMsg": "NORMAL SERVICE",
  "totalCount": 1351,
  "numOfRows": 1,
  "pageNo": 1,
  "first": {
    "sidoHqOgidNm": "충청남도소방본부",
    "rsacGutFsttOgidNm": "천안동남소방서",
    "gutYm": "202112",
    "gutHh": "11",
    "ruptSptmCdNm": "기타",
    "ptntAge": "50~59세"
  }
}
```

Conclusion: the correct live NFA contract is statistical lookup with a concrete station and month. It is not a gas-safety-rules or AED-location API.
