# KOSMOS UI Wireframes

Interactive wireframe previews rendered via Ink — 터미널에서 직접 비교 가능.

## 파일 구성

| File | 목적 | 상태 |
|---|---|---|
| `_shared.mjs` | CC-style primitives (Box · Text · CondensedLogo · Feed · Notice · ToolUseBlock 등) | — |
| `proposal-iv.mjs` | UI-D wireframe 확정 · 5 states | ✅ 확정 |
| `ufo-mascot-proposal.mjs` | UFO 마스코트 · 보라 팔레트 | ✅ 확정 |
| **`ui-b-repl-main.mjs`** | UI-B · REPL Main L2 (streaming / scroll / markdown / errors / context / autocomplete) | 제안 중 |
| **`ui-c-permission.mjs`** | UI-C · Permission Gauntlet L2 (Layer 1/2/3 · receipt · history · revoke · mode switch) | 제안 중 |
| **`ui-e-auxiliary.mjs`** | UI-E · 보조 surface L2 (Help · Config · Plugin · Export · History) | 제안 중 |
| **`ui-a-onboarding.mjs`** | UI-A · Onboarding L2 (5 steps · i18n · a11y · revoke) | 제안 중 |
| **`ui-d-extensions.mjs`** | UI-D · Ministry Agent L2 확장 (D.1 /agents 상세 · D.2 swarm 임계치) | 제안 중 |

## Run

```bash
cd tui

# 확정된 wireframe
bun ../docs/wireframes/proposal-iv.mjs       # UI 5 states
bun ../docs/wireframes/ufo-mascot-proposal.mjs  # UFO 마스코트

# L2 드릴다운 (선택 대기)
bun ../docs/wireframes/ui-b-repl-main.mjs    # REPL Main
bun ../docs/wireframes/ui-c-permission.mjs   # Permission
bun ../docs/wireframes/ui-e-auxiliary.mjs    # Aux surface
bun ../docs/wireframes/ui-a-onboarding.mjs   # Onboarding
bun ../docs/wireframes/ui-d-extensions.mjs   # Ministry agent D.1/D.2
```

## UI 요구사항 트리 (L2 결정 포인트)

```
UI-ROOT
├── UI-A Onboarding       · A.1 (5-step 레이아웃) · A.2 재실행 · A.3 i18n · A.4 a11y · A.5 revoke
├── UI-B REPL Main        · B.1 streaming · B.2 scroll · B.3 markdown · B.4 errors · B.5 context · B.6 autocomplete
├── UI-C Permission       · C.1 Layer 색 · C.2 modal · C.3 history · C.4 revoke · C.5 mode switch
├── UI-D Ministry Agent   · (proposal-iv 확정) · D.1 /agents 상세 · D.2 swarm 임계치
└── UI-E 보조 surface      · E.1 Help · E.2 Config · E.3 Plugin · E.4 Export · E.5 History
```

## Design rules (전체 공통)

- **0 new component classes** — CC-ported primitives만 사용
- CC 시각 언어: round rule · dim hint · bordered notice · 3×9 마스코트 footprint
- 한국어 primary · 영어 보조 (ministry code 약어만)
- Mock UI 노출 안 함 (live와 동일 시각 처리)
- Root 4 primitive 예약어 (`lookup` · `submit` · `verify` · `subscribe`)

## See also

- `docs/vision.md` (아키텍처 Layer 정의)
- `CLAUDE.md § Architecture pillars`
- `.references/claude-code-sourcemap/restored-src/src/components/LogoV2/` (CC 원본)
