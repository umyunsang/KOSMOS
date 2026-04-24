# Quickstart: P0 · Baseline Runnable 로컬 검증

**Audience**: KOSMOS 기여자 (본 Epic 의 작업자 + 리뷰어 + 후속 Epic 의 신규
기여자).
**시간 예산**: 5 분 (SC-005 목표).
**전제**: macOS (ARM64) + Bun v1.2.x 설치됨.

---

## 1) 의존성 설치 (SC-002)

```bash
cd tui
bun install
```

**기대 결과**: 0 warning, 0 error, lockfile 업데이트. 아래 5 개 패키지가 새로
설치됨:

- `@commander-js/extra-typings`
- `chalk`
- `lodash-es`
- `chokidar`
- `@anthropic-ai/sdk`

**실패 시 triage**:
- `error: missing dependency "foo"` → `tui/package.json` 에 누락 (FR-001 회귀)
- `Cannot find module '…'` → `tsconfig.json paths` 매핑 누락 (FR-003 / FR-004)

---

## 2) 스플래시 렌더 확인 (SC-001 · US1)

```bash
cd tui
bun run src/main.tsx
```

**기대 결과**:
1. 프로세스 시작 후 500ms 이내 CC 베이스라인 스플래시가 터미널에 그려짐.
2. 최소 3 초 동안 크래시 없이 유지됨.
3. `Ctrl+C` 로 종료 시 exit code 0 (또는 130 — SIGINT 관례) 반환.
4. stderr 에 uncaught exception 스택트레이스 0 건.

**실패 시 triage**:
- `Error: Cannot find module 'bun:bundle'` → FR-003 회귀 (stub 경로 매핑 누락)
- `Error: Cannot find module 'src/services/...'` → FR-004 회귀 (tsconfig paths
  `src/*` 매핑 누락)
- `TypeError: X is not a function` · spinner 멈춤 · 무반응 → FR-005 회귀
  (main.tsx 의 부트스트랩 사이드이펙트 중 하나가 네트워크/FS 에서 블록)
- 외부 API 호출 시도 로그 → FR-008 회귀 (부트스트랩 egress 0 위반)

---

## 3) 테스트 회귀 floor 확인 (SC-003 · US2)

```bash
cd tui
bun test
```

**기대 결과**: `Passed: ≥540` (upstream baseline 549 대비 ≥98%).

**실패 시 triage**:
- 통과 수가 현재 449 에서 크게 변동 없음 → FR-001/FR-003/FR-007 중 하나가
  실패 (의존성·stub·이중 중첩 중 근본 원인 파악)
- 통과 수가 540 ≤ X < 549 → 허용 gap (Phase 2 task 에서 개별 triage)
- 통과 수 > 549 → 의심스러움 (snapshot drift? 상류 baseline 재확인 필요)

---

## 4) feature() stub 동작 단위 확인 (US3)

```bash
cd tui
bun test tests/unit/stubs/bun-bundle.test.ts
```

**기대 결과**: `feature("KAIROS") === false`, `feature("UNKNOWN") === false`,
예외 throw 없음. (FR-003 수용 기준.)

---

## 5) 부트스트랩 egress 0 검증 (SC-004 · FR-008)

(선택적, 리뷰어 권장) 네트워크 인터페이스를 캡처하며 `bun run src/main.tsx`
실행:

```bash
# 터미널 A
sudo tcpdump -i any -n -c 50 'tcp and (host api.anthropic.com or host api.growthbook.io)' 2>&1 &
# 터미널 B (3 초 대기 후)
cd tui && timeout 3 bun run src/main.tsx ; echo "exit=$?"
```

**기대 결과**: tcpdump 출력에 Anthropic / GrowthBook / 외부 telemetry 호스트
대상 TCP SYN 패킷 0 건.

---

## 자주 쓰는 확장 check

- `bun x tsc --noEmit` — 타입 체크 (CI gate) · 0 error
- `bun run tui:smoke` — Epic #287 에서 포팅된 smoke 스크립트 (가능 시 실행)
- 이중 중첩 디렉터리 회귀 확인:

  ```bash
  test ! -d tui/src/constants/constants && \
  test ! -d tui/src/services/services && echo "flatten OK"
  ```

---

## 문제 신고

- 회귀 발견 시 `Closes #1632` 가 달린 PR 에 reviewer 로서 change request.
- P1+ 책임 범위 이슈면 comment 로 noted → Epic #1633 (dead code elimination)
  에 forwarding.
