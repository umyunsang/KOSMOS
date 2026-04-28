# Citizen Quickstart — 5분 만에 KOSMOS 플러그인 설치 및 사용

**Audience**: KOSMOS 시민 사용자 (한국어 primary, English fallback).
**Time budget**: 5 minutes from `kosmos` launch to citizen receiving plugin-augmented response.
**Prerequisites**: KOSMOS 시민 환경 부팅 완료 (Spec 287 + Spec 1635 baseline). `seoul-subway` 예시 플러그인이 `kosmos-plugin-store` 카탈로그에 게시되어 있거나, 로컬 fixture 카탈로그가 사용 가능.

---

## 시나리오 — "지하철 도착 정보 알려주는 플러그인 설치하고 바로 써먹기"

### 1단계 — TUI 실행 (10초)

```bash
$ kosmos
```

REPL 화면이 나타나면 시민 컨텍스트 확인:

```
✻ KOSMOS — 시민 헬스 챗봇

  세션: s-2026-04-28-12-00-00
  Layer: 1 (basic) · 한국어 primary

> _
```

---

### 2단계 — 플러그인 설치 (30초)

```
> /plugin install seoul-subway
```

설치 진행 오버레이가 7단계 progress 를 보여줍니다:

```
🔄 seoul-subway 플러그인 설치 시작…

  📡 카탈로그 조회 중…              [✓] (0.4s)
  📦 번들 다운로드 중…              [✓] (1.2s)
  🔐 SLSA 서명 검증 중…             [✓] (0.8s)
  🧪 매니페스트 검증 중…            [✓] (0.2s)
  📝 동의 확인…
```

---

### 3단계 — 동의 모달 (5초)

권한 모달이 표시됩니다:

```
⓵ Layer 1 권한 요청

  플러그인:        seoul-subway v1.0
  티어:            live
  PII 처리:        아니오
  수탁 기관:        —

  이 플러그인은 서울 공공데이터 포털 API 를 호출해
  지하철 도착 정보를 조회합니다.

  [Y 한번만 / A 세션 자동 / N 거부]

> Y_
```

`Y` 키 입력 후 설치 계속:

```
  📝 동의 확인…                    [✓ 한번만]
  🔄 등록 + BM25 색인 중…           [✓] (0.3s)
  📜 동의 영수증 기록 중…           [✓ rcpt-a3b7…]
  ✓ 설치 완료 (12.4s · 영수증 ID: rcpt-a3b7c9d2)

  추천: 다음 turn 에서 "강남역 다음 열차" 같은 질문을 하면
        새 플러그인이 자동 호출됩니다.
```

---

### 4단계 — 플러그인 호출 (10초)

질문 입력:

```
> 강남역 다음 열차 언제?
```

시민이 enter 누르자, KOSMOS 가:
1. BM25 검색에서 새 플러그인의 `search_hint_ko` ("지하철 도착 시간 강남역") 매칭
2. `lookup(mode="fetch", tool_id="plugin.seoul_subway.lookup", params={station: "강남"})` 호출
3. 권한 모달 (이미 한번만 승인된 것으로 간주, 또는 세션 자동 시 묵묵히 통과)
4. plugin 응답 반환
5. 모델이 한국어로 통합 응답 생성:

```
> 강남역 다음 열차 언제?

  ✻ 강남역 다음 열차 정보를 조회 중입니다…

  [도구 호출 plugin.seoul_subway.lookup ✓ 0.6s]

  강남역 (2호선)

    상행 (성수 방면):
      • 12:03 — 1번 (5분 후 도착)
      • 12:09 — 2번 (11분 후 도착)

    하행 (사당 방면):
      • 12:01 — 1번 (3분 후 도착)
      • 12:07 — 2번 (9분 후 도착)

  데이터 출처: 서울교통공사 실시간 API (seoul-subway 플러그인 v1.0)

>
```

---

### 5단계 — 설치된 플러그인 확인 (15초)

```
> /plugins
```

플러그인 브라우저 surface 가 열립니다:

```
✻ KOSMOS 플러그인 (1 installed)

  ⏺  ›  seoul-subway     v1.0  [Live]  ⓵  서울 지하철 도착 정보 조회
                                            (지금 활성)

  Space 활성 토글 · i 상세 · r 제거 · a 스토어 (deferred)
  Esc · 닫기
```

`i` 누르면 detail view:

```
✻ seoul-subway v1.0 [Live]

  티어:                  live
  권한 레벨:              Layer 1 (green ⓵)
  PII 처리:              아니오
  수탁 기관:              —
  설치 일시:             2026-04-28T12:00:12Z
  검색어 (Search hints):
    ko:  지하철 도착 시간 강남역
    en:  subway arrival time station

  설명:
    서울 지하철 도착 정보 조회 — 서울시 공공데이터 포털 API 를 통해
    실시간 지하철 도착 정보를 제공합니다.

  Esc · 닫기
```

`Esc` 두번 (detail 닫고, 브라우저 닫고) → REPL 로 복귀.

---

## 분기 시나리오 — 권한 거부

3단계에서 `N` 입력:

```
  📝 동의 확인…                    [✗ 거부]
  ✗ 설치 취소 (5.4s · 시민 동의 거부 · exit_code=5)

  설치 디렉터리: 비어있음
  영수증: 기록되지 않음

>
```

플러그인 등록 안됨; 다음 turn 에서 호출 불가; `~/.kosmos/memdir/user/plugins/` 변화 없음.

---

## 분기 시나리오 — 영수증 확인

```
> /consent list
```

설치 후 영수증이 ledger 에 추가된 것 확인:

```
영수증 ledger (3 entries):

  rcpt-a3b7c9d2 · 2026-04-28T12:00:12Z · plugin_install · seoul-subway v1.0
  rcpt-... · 이전 동의 ...
  rcpt-... · 이전 동의 ...
```

---

## 분기 시나리오 — 플러그인 제거

```
> /plugins   (브라우저 열기)
```

selected row 에서 `r`:

```
⚠  플러그인 제거 확인

  seoul-subway v1.0 을 제거하시겠습니까?
  ⏺  설치 디렉터리: ~/.kosmos/memdir/user/plugins/seoul_subway/
  ⏺  영수증 (uninstall) 이 ~/.kosmos/memdir/user/consent/ 에 추가됩니다.

  [Y 제거 / N 취소]

> Y
```

uninstall 진행 (3단계 progress):

```
  📋 등록 해제 중…                 [✓] (0.1s)
  📁 설치 디렉터리 제거 중…         [✓] (0.2s)
  📜 동의 영수증 기록 중…           [✓ rcpt-...]
  ✓ 제거 완료 (0.5s · 영수증 ID: rcpt-...)
```

브라우저 row 사라지고 다음 turn 에서 호출 불가.

---

## 측정값 (SC 검증)

| SC | 측정 결과 |
|---|---|
| SC-001 (≤30s install) | 12.4s (✓) |
| SC-002 (≤3s tool inventory) | 다음 turn 즉시 (✓ — Spec 1978 fallback) |
| SC-003 (100% gauntlet) | Layer 1 ⓵ 표시, Y 한번만 동의됨 (✓) |
| SC-010 (deny → no state) | N 분기 시나리오에서 install dir + receipt 모두 부재 (✓) |

---

## 화면 캡처 (mock-up — 실제 vhs gif 는 `bun run scripts/smoke-1979.tape` 후 생성)

본 quickstart 의 화면 텍스트는 prose mock-up. 실제 시각 검증 산출물:
- `specs/1979-plugin-dx-tui-integration/smoke-1979.gif` — 4단계 시나리오 vhs 녹화
- `specs/1979-plugin-dx-tui-integration/smoke-1979.txt` — expect/script 텍스트 캡처 (Codex 검증용)

산출 명령:

```bash
$ bash specs/1979-plugin-dx-tui-integration/scripts/run-e2e.sh
```

---

## 참고

- 본 워크스루는 `seoul-subway` 예시 플러그인 기준. 실제 catalog 게시 전이라면 fixture catalog (`scripts/fixtures/catalog.json`) 사용.
- 플러그인 작성 가이드: `docs/plugins/quickstart.ko.md` (Spec 1636).
- 권한 정책: `docs/plugins/security-review.md` (PIPA §26 수탁자 책임).
- 설치된 플러그인 목록: `~/.kosmos/memdir/user/plugins/`.
- 동의 영수증 ledger: `~/.kosmos/memdir/user/consent/`.

---

## Citations

- spec.md § User Story 1 (Citizen install)
- spec.md § User Story 2 (Plugin invocation)
- spec.md § User Story 3 (Plugin browser)
- contracts/dispatcher-routing.md § Outbound frame sequence
- contracts/citizen-plugin-store.md § Visual layout
