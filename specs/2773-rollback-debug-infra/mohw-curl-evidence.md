# MOHW SSIS curl Evidence — 2026-05-06

Purpose: verify `mohw_welfare_eligibility_search` live request parameters before changing adapter metadata or real-use scenarios. Live API checks were performed with direct `curl`, not scripts.

Endpoint:

```text
https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001
```

## One-Parent Keyword

```bash
curl -A "Mozilla/5.0" -G \
  "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001" \
  --data-urlencode "serviceKey=${KOSAX_DATA_GO_KR_API_KEY}" \
  --data-urlencode "callTp=L" \
  --data-urlencode "srchKeyCode=003" \
  --data-urlencode "searchWrd=한부모" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=3" \
  --data-urlencode "orderBy=popular"
```

Observed:

- HTTP 200
- `resultCode=0`
- `resultMessage=SUCCESS`
- `totalCount=55`
- First record: `WLF00000024` / `아이돌봄서비스` / `trgterIndvdlArray=다문화·탈북민,다자녀,장애인,한부모·조손`

## One-Parent Code

```bash
curl -A "Mozilla/5.0" -G \
  "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001" \
  --data-urlencode "serviceKey=${KOSAX_DATA_GO_KR_API_KEY}" \
  --data-urlencode "callTp=L" \
  --data-urlencode "srchKeyCode=003" \
  --data-urlencode "trgterIndvdlArray=060" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=3" \
  --data-urlencode "orderBy=popular"
```

Observed:

- HTTP 200
- `resultCode=0`
- `resultMessage=SUCCESS`
- `totalCount=51`
- First record target tag includes `한부모·조손`

## One-Parent Child Support

```bash
curl -A "Mozilla/5.0" -G \
  "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001" \
  --data-urlencode "serviceKey=${KOSAX_DATA_GO_KR_API_KEY}" \
  --data-urlencode "callTp=L" \
  --data-urlencode "srchKeyCode=003" \
  --data-urlencode "searchWrd=아동양육비" \
  --data-urlencode "trgterIndvdlArray=060" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=5" \
  --data-urlencode "orderBy=popular"
```

Observed:

- HTTP 200
- `resultCode=0`
- `resultMessage=SUCCESS`
- `totalCount=3`
- First record: `WLF00001068` / `한부모가족 아동양육비 지원`
- `jurMnofNm=성평등가족부`
- `jurOrgNm=가족지원과`
- `onapPsbltYn=Y`
- `rprsCtadr=1577-4206`
- `servDgst=저소득 한부모가족 및 조손가족이 가족의 기능을 유지하고 안정된 생활을 할 수 있도록 아동 양육비를 지원합니다.`

## One-parent child support by full official title

```bash
curl -sS -w "\nHTTP_STATUS:%{http_code}\n" \
  -A "Mozilla/5.0" \
  -G "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001" \
  --data-urlencode "serviceKey=<redacted>" \
  --data-urlencode "callTp=L" \
  --data-urlencode "srchKeyCode=003" \
  --data-urlencode "searchWrd=한부모가족 아동양육비 지원" \
  --data-urlencode "trgterIndvdlArray=060" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=1" \
  --data-urlencode "orderBy=popular"
```

Observed:

- HTTP 200
- `resultCode=0`
- `resultMessage=SUCCESS`
- `totalCount=2`
- First record: `WLF00001068` / `한부모가족 아동양육비 지원`
- `jurMnofNm=성평등가족부`
- `jurOrgNm=가족지원과`
- `onapPsbltYn=Y`
- `rprsCtadr=1577-4206`

Conclusion: the valid SSIS parameter for 한부모/조손 is `trgterIndvdlArray=060`. `lifeArray` is only for life-stage codes and must not be used for household type routing.

## One-parent child support with erroneous lifeArray

Direct regression check after the PTY run showed the exact failing LLM call:

```bash
curl -sS -A "Mozilla/5.0" -G \
  "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001" \
  --data-urlencode "serviceKey=<redacted>" \
  --data-urlencode "callTp=L" \
  --data-urlencode "srchKeyCode=003" \
  --data-urlencode "searchWrd=한부모가족 아동양육비" \
  --data-urlencode "lifeArray=002" \
  --data-urlencode "trgterIndvdlArray=060" \
  --data-urlencode "onapPsbltYn=Y" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=3" \
  --data-urlencode "orderBy=popular"
```

Observed:

- HTTP 200
- `totalCount=0`
- `resultCode=40`
- `resultMessage=NO DATA FOUND`

Removing only `lifeArray=002` from the same request returned:

- HTTP 200
- `totalCount=1`
- `resultCode=0`
- `resultMessage=SUCCESS`
- First record: `WLF00001068` / `한부모가족 아동양육비 지원`

## One-parent child support shorthand from PTY trace

`welfare-application-scope-normalize-2026-05-06` captured the model shortening the
citizen-supplied service phrase from `한부모가족 아동양육비` to `한부모 아동양육비`:

```text
GET ... searchWrd=%ED%95%9C%EB%B6%80%EB%AA%A8+%EC%95%84%EB%8F%99%EC%96%91%EC%9C%A1%EB%B9%84&trgterIndvdlArray=060
```

Observed in `backend.log`:

- HTTP 200
- `resultCode=40`
- `resultMessage=NO DATA FOUND`

The exact full-family phrase was already proven above to return `WLF00001068`.
The adapter now canonicalizes this narrow shorthand to `한부모가족 아동양육비`
when `trgter_indvdl_array='060'`, rather than issuing a second live query.

## Endpoint quota blocker after regression probes

After the shorthand fix, a direct one-row curl probe for the canonical query was
run before another PTY capture:

```bash
curl -sS -A "Mozilla/5.0" -G \
  "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001" \
  --data-urlencode "serviceKey=<redacted>" \
  --data-urlencode "callTp=L" \
  --data-urlencode "srchKeyCode=003" \
  --data-urlencode "searchWrd=한부모가족 아동양육비" \
  --data-urlencode "trgterIndvdlArray=060" \
  --data-urlencode "onapPsbltYn=Y" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=1" \
  --data-urlencode "orderBy=popular"
```

Observed:

- HTTP 429
- Body: `API token quota exceeded`

The same redacted direct curl was retried after the TUI P1 dead-code cleanup on
2026-05-06 and still returned:

```text
API token quota exceeded

HTTP_STATUS:429
```

The canonical one-parent child-support curl was checked again after the
permission-denial v6 real-use recovery and the full local gate pass on
2026-05-06. It still returned the same quota blocker:

```text
API token quota exceeded

HTTP_STATUS:429
```

Conclusion: do not re-run the WELFARE PTY happy path until the data.go.kr token
quota resets or a separate live key is configured. The packaging blocker is
external endpoint quota, not the local input-schema guard.

## Quota reset verification — 2026-05-07

After the Asia/Seoul date rolled to 2026-05-07, the canonical one-row curl
probe was re-run before resuming the WELFARE happy-path PTY scenario:

```bash
curl -sS -w "\nHTTP_STATUS:%{http_code}\n" \
  -A "Mozilla/5.0" \
  -G "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfarelistV001" \
  --data-urlencode "serviceKey=<redacted>" \
  --data-urlencode "callTp=L" \
  --data-urlencode "srchKeyCode=003" \
  --data-urlencode "searchWrd=한부모가족 아동양육비" \
  --data-urlencode "trgterIndvdlArray=060" \
  --data-urlencode "onapPsbltYn=Y" \
  --data-urlencode "pageNo=1" \
  --data-urlencode "numOfRows=1" \
  --data-urlencode "orderBy=popular"
```

Observed:

- HTTP 200
- `resultCode=0`
- `resultMessage=SUCCESS`
- `totalCount=1`
- First record: `WLF00001068` / `한부모가족 아동양육비 지원`
- `jurMnofNm=성평등가족부`
- `jurOrgNm=가족지원과`
- `onapPsbltYn=Y`
- `rprsCtadr=1577-4206`

Conclusion: the previous blocker was endpoint quota. The live contract is
available again for a WELFARE happy-path PTY rerun.
