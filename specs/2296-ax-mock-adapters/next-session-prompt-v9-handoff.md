# 다음 세션 시작 프롬프트 — Initiative #2290 핸드오프 v9 (Epic η #2298 무한 spinner fix mandate)

**작성일**: 2026-04-30 (Epic ε #2296 머지 + Codex P1 #2395 / #2446 closed 직후)
**상태**: Epic α + β + γ + δ + ε 머지 완료. **Epic η #2298 OPEN, ζ #2297 OPEN.** η가 ζ의 prerequisite이 됨.

---

## 머지 결과

| 항목 | commit |
|---|---|
| Epic ε #2296 AX-mock-adapters + dispatcher fix | `be9b368` (PR #2445, squash) |
| Codex P1 #2395 (adapter manifest IPC sync) | resolved + auto-closed |
| Codex P1 #2446 (verify dispatch wiring) | resolved + auto-closed |
| 50 sub-issues (45 task + 4 deferred + #2446) | closed |

머지 후 main HEAD 상태: 11-arm AuthContext discriminated union, 22-arm IPCFrame union, 16-entry main ToolRegistry (12 Live + 2 MVP-surface + 2 lookup mocks), 18 mock surface in per-primitive sub-registries, full dispatcher wiring through `verify(family_hint=...)` for all 11 families.

---

## 다음 작업: Epic η #2298 — System Prompt Rewrite (이제 load-bearing)

원래 `optional`로 마킹되어 있었으나, Epic ε ship 과정에서 **vhs smoke 무한 spinner 진단** 결과 **ζ의 prerequisite이 됨**.

### 무한 spinner의 진짜 원인 (Epic ε에서 확인)

`prompts/system_v1.md` 현재 정책 (line 18 인용):
```
호출 가능한 도구는 정확히 두 가지뿐입니다 — `resolve_location` 과 `lookup`.
```

→ LLM은 **`verify(...)` / `submit(...)` / `subscribe(...)` primitive를 emit 자체가 금지됨**. 시민이 "내 종합소득세 신고해줘" query를 보내도 LLM은 `lookup`으로만 풀려고 시도 → 적합한 어댑터 없으면 "Hatching… / Boogieing…" 상태로 무한 thinking. dispatcher (#2446) 고친 후에도 LLM이 verify를 호출 안 하니 chain 자체가 시작 안 됨.

### Epic η가 반드시 고쳐야 하는 4가지

1. **4 primitive 모두 호출 가능 명시** — `resolve_location` + `lookup` + `verify` + `submit` + `subscribe`. 현재 2개로 lock된 표현 제거.
2. **11 verify family 카탈로그** — 6 기존 (`gongdong_injeungseo`, `geumyung_injeungseo`, `ganpyeon_injeung`, `mobile_id`, `mydata`, `digital_onepass` ← 삭제됨) + 5 신규 (`simple_auth_module`, `modid`, `kec`, `geumyung_module`, `any_id_sso`). LLM이 `verify(family_hint=...)`로 어떤 값을 보낼 수 있는지 알아야 함.
3. **시민 OPAQUE-domain chain 패턴 학습** — "시민이 `종합소득세 신고`/`민원 제출`/`마이데이터 액션` 요청 시 `verify` → `lookup` → `submit` 순서로 호출하라" + 구체 예시. 현재 system prompt에 이 패턴 0건.
4. **DelegationToken 어휘** — `scope_list` 인자 사용법, `scope` grammar (`<verb>:<adapter_family>.<action>` 콤마 결합), `purpose_ko/en` 인자.

### Acceptance criteria (반드시 검증)

- **vhs Layer 4 smoke 재캡처**: keyframe 3에 `접수번호: hometax-YYYY-MM-DD-RX-XXXXX` 패턴이 텍스트로 표시되어야 함. Lead Opus가 Read tool로 직접 시각 확인.
- **PTY Layer 2 smoke**: `CHECKPOINTreceipt token observed` 가 출력되어야 함 (`NOTE` 아님).
- **Spec 026 prompt manifest hash 업데이트** — `prompts/manifest.yaml` SHA-256 재계산. 부트 시 fail-closed 통과 확인.
- **shadow-eval workflow 통과** (Spec 026): twin-run on `prompts/**` PR이 fixture-only로 deployment.environment=main|shadow attribute 분리 emit + 통과.
- **Spec 2152 invariants 보존**: 기존 `<role>` / `<core_rules>` / `<output_style>` XML tags 구조 유지.
- **shadow-eval 시나리오에 5 신규 family 모두 다음 케이스 추가**: 시민 query → LLM이 올바른 family_hint 선택 → typed AuthContext 리턴 확인.
- **Regression**: 기존 `lookup` 시나리오 (날씨, 응급실, 병원 등) 여전히 동작.

### 참고 자료 (Phase 0 research에서 인용 필수)

- `prompts/system_v1.md` 현재 (line 18 lock 표현 + line 20-22 lookup 2단계 패턴)
- `specs/2152-system-prompt-redesign/spec.md` — 직전 system prompt 재설계 spec, XML-tag scaffolding 출처
- `specs/2296-ax-mock-adapters/contracts/delegation-token-envelope.md § 1-3` — scope grammar + 시민 chain canonical sequence
- `specs/1979-plugin-dx-tui-integration/delegation-flow-design.md § 12.4` — citizen verify→lookup→submit 흐름도 (FINAL canonical)
- `src/kosmos/primitives/verify.py` — 11-arm AuthContext union + 11 family literal values
- `src/kosmos/tools/registry.py:68-93` — 18-label `PublishedTier` Literal (5 신규 추가됨)
- `tests/integration/test_e2e_citizen_taxreturn_chain.py` — 시민 chain integration test (현재 in-process로만 검증, LLM-driven smoke는 #2298 후 비로소 동작)
- `tests/integration/test_verify_module_dispatch.py` — 6 dispatch test (Epic ε에서 추가)

### Codex P1 piggyback 후보

없음. Epic η는 prompt-only 변경. Spec 026 prompt manifest 재계산만 신경.

### 추정 task budget

15-25 tasks 예상 (≤ 90 cap, 50%+ headroom). 작은 Epic.
- Phase 1 Setup (1-2 tasks)
- Phase 2 Foundational: prompts/system_v1.md 재작성 + manifest hash 업데이트 (3-5 tasks)
- Phase 3 US1 Citizen-chain teaching: 5 verify family + 3 submit module + 2 lookup module을 system prompt에 추가 (5-7 tasks)
- Phase 4 shadow-eval fixtures: 5 신규 시나리오 (5 tasks)
- Phase 5 Smoke 재캡처 + Regression check (3-5 tasks)
- Phase 6 Polish + PR (3 tasks)

---

## 다음 세션 진입

```bash
cd /Users/um-yunsang/KOSMOS && git pull --ff-only
git worktree add ../KOSMOS-w-2298 -b 2298-system-prompt-rewrite
cd ../KOSMOS-w-2298
# /speckit-specify Epic η — system prompt teaching the LLM about
# 4 primitives + 11 verify families + citizen verify→lookup→submit chain
# pattern + delegation token vocabulary. The infinite-spinner gate.
```

### Lead Opus 첫 명령

```
/clear → 새 conversation
이 파일 (specs/2296-ax-mock-adapters/next-session-prompt-v9-handoff.md) 읽고
Epic η #2298 resume. 무한 spinner 문제 명시적으로 해결.
```

---

## 불변 규칙 (v8에서 그대로 carry)

1. **1 Lead Opus = 1 Epic** (Layer 1 parallelism).
2. **Sonnet teammate 단위 = task/task-group** (≤ 5 task / ≤ 10 file).
3. **push/PR/CI/Codex = Lead** (sequential).
4. **Codex P1/P2 처리**: P2 = 즉시 fix + reply. P1 (architecture mismatch) = deferred sub-issue + spec.md 백필 + reply.
5. **PR title subject 첫 글자 lowercase** (Conventional Commits action).
6. **`gh issue close --quiet` 금지** — silent fail. flag 빼고 close.
7. **vhs Layer 4 mandatory** — `.tape` + 3+ Screenshot PNG + Lead 시각 Read 검증.
8. **이슈 추적 = GraphQL Sub-Issues API only** (closure verify 는 REST per-issue).
9. **신규 dep 0** (AGENTS.md hard rule).
10. **🆕 prompt 변경 시 manifest hash 재계산 + shadow-eval 통과 의무** (Spec 026 hard gate).
