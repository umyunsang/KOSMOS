# Timeline — KOSMOS v0.1-alpha 개발 일정

> Chapter 6 (프로젝트 관리 및 일정) Gantt 데이터.
> 작성일: 2026-04-26

---

## 1. 주요 이정표

| 날짜 | 이정표 | Epic / PR |
|---|---|---|
| 2026-04-11 | Initial commit — Project scaffold | c15040c |
| 2026-04-14 | P0 Baseline Runnable 완료 | #1632 merged |
| 2026-04-15 | FriendliAI Tier 1 확정 (60 RPM) | — |
| 2026-04-19 | P1+P2 Dead code + FriendliAI 통합 완료 | #1706 merged |
| 2026-04-20 | P3 Tool system wiring 완료 | #1758 merged |
| 2026-04-22 | P4 UI L2 Citizen port 완료 | #1847 merged |
| 2026-04-24 | kosmos-migration-tree.md 사용자 승인 | — |
| 2026-04-24 | P5 Plugin DX 5-tier 완료 | #1927 merged |
| 2026-04-26 | P6 Docs + smoke 완료 | #1977 merged |
| 2026-04-26 | **v0.1-alpha 출시** | Initiative #1631 closed |

---

## 2. Phase별 기간

| Phase | 시작 | 완료 | 기간 |
|---|---|---|---|
| P0 Baseline | 2026-04-11 | 2026-04-14 | 3일 |
| P1+P2 Provider | 2026-04-14 | 2026-04-19 | 5일 |
| P3 Tool System | 2026-04-19 | 2026-04-20 | 1일 |
| P4 UI L2 | 2026-04-20 | 2026-04-22 | 2일 |
| P5 Plugin DX | 2026-04-22 | 2026-04-24 | 2일 |
| P6 Docs + Smoke | 2026-04-24 | 2026-04-26 | 2일 |
| **Total** | **2026-04-11** | **2026-04-26** | **15일** |

---

## 3. Gantt 데이터 (HTML slide용)

```
Phase       | Apr 11 | Apr 13 | Apr 15 | Apr 17 | Apr 19 | Apr 21 | Apr 23 | Apr 25 | Apr 26
------------|--------|--------|--------|--------|--------|--------|--------|--------|-------
P0 Baseline |========|=       |        |        |        |        |        |        |
P1+P2       |        |        |========|======= |=       |        |        |        |
P3 Tool     |        |        |        |        |========|        |        |        |
P4 UI L2    |        |        |        |        |        |========|        |        |
P5 Plugin   |        |        |        |        |        |        |========|        |
P6 Docs     |        |        |        |        |        |        |        |========|★
```

---

## 4. 향후 로드맵 (v0.1-alpha 이후)

| 분기 | 항목 | Deferred Issue |
|---|---|---|
| Q2 2026 | Live API regression 스위트 | #1972 |
| Q2 2026 | In-TUI 마켓플레이스 브라우저 | #1973 |
| Q2 2026 | KSC 2026 발표 (이 자료) | — |
| Q3 2026 | Mobile/Web 포팅 탐색 | #1974 |
| Q3 2026 | EXAONE fine-tuning 데이터셋 | #1975 |
| Q4 2026 | 정부 파일럿 MOU 검토 | #1976 |
| Q4 2026 | 추가 부처 어댑터 (교육부·국세청) | TBD |

---

## 5. 누적 통계 타임라인

| 날짜 | Commits | PRs | Specs | Tests |
|---|---|---|---|---|
| 2026-04-14 (P0 done) | ~30 | ~10 | 5 | ~100 |
| 2026-04-19 (P2 done) | ~80 | ~30 | 15 | ~300 |
| 2026-04-22 (P4 done) | ~140 | ~60 | 28 | ~700 |
| 2026-04-26 (v0.1-alpha) | 194 | 79 | 38 | 935 |
