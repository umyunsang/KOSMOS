# SC-009 Korean Reviewer Signoff Evidence

> 측정일: 2026-04-26
> 측정자: Lead 자동화 (umyunsang)
> Status: **DEFERRED** — non-blocking for PR merge (per tasks.md T072)

## SC-009 정의

```
SC-009 success criterion: a native-Korean-speaking reviewer who has
NEVER touched KOSMOS completes the quickstart (with English source
files closed) and lands a green pytest within 30 minutes (SC-001
budget). Validates that the Korean-primary documentation is
self-sufficient.
```

## 현재 상태

본 epic 의 PR 작성자 (umyunsang) 는 native Korean speaker 이지만 KOSMOS 를 처음부터 작성한 lead — **외부 reviewer 자격이 아닙니다**. SC-009 의 본질은 "처음 보는 Korean speaker 가 영문 source 없이 Korean 문서만으로 quickstart 완주 가능한가" 이므로 self-review 는 invalid.

## Deferred 사유

1. **Reviewer 풀 부재**: 현재 KOSMOS 에 외부 native-Korean reviewer 가 commit 한 PR 이 없습니다 (SC-008 baseline = 0).
2. **3개월 자연 발견**: SC-008 의 3개월 외부 contributor 측정 사이클과 동일한 시간대에 자연스러운 외부 reviewer 가 발생할 가능성이 높음.
3. **Non-blocking**: tasks.md T072 가 명시적으로 "deferred-checkbox if no reviewer available, tracked but non-blocking for PR merge" 라고 적시.

## 추적 방법

다음 사건이 발생하면 SC-009 evidence 갱신:
- Native Korean speaker 가 GitHub Discussion / Issue / PR 에 한국어로 처음 contribute.
- Reviewer 가 quickstart.ko.md 를 따라가며 timing 측정 결과를 issue / PR 코멘트로 post.

이 evidence 파일에 측정 결과 + reviewer 의 signoff 를 추가 commit.

## 검증 가능한 proxy 측정

SC-009 자체는 외부 reviewer 가 필요하지만, *Korean documentation self-sufficiency* 는 다음으로 부분 검증 가능:

### Proxy 1: 9개 가이드 모두 Bilingual glossary 포함 (FR-006)

```
✓ docs/plugins/quickstart.ko.md
✓ docs/plugins/architecture.md
✓ docs/plugins/pydantic-schema.md
✓ docs/plugins/search-hint.md
✓ docs/plugins/permission-tier.md
✓ docs/plugins/data-go-kr.md
✓ docs/plugins/live-vs-mock.md
✓ docs/plugins/security-review.md
✓ docs/plugins/testing.md
```

→ 9/9 ✅ (T067 audit).

### Proxy 2: Quickstart 자동화 단계 (1+2) timing — SC-001

`specs/1636-plugin-dx-5tier/quickstart-timing-evidence.md` 의 측정값 2.49초 (240초 budget 대비 96× 여유). 한국어 walkthrough 가 짧지 않은데도 자동화 부분이 budget 내 — Korean reviewer 가 사람 단계 (3-7, 9) 를 budget 내 완수할 가능성 높음.

### Proxy 3: 가이드 cross-link 정합성

각 가이드의 `## Reference` 섹션이 다른 가이드 / spec / source code 를 정확히 가리키는지 점검:

```sh
# 모든 internal link 가 valid 한지 검증 (deferred — Phase 8 polish 외 별도)
uv run python scripts/check_md_links.py docs/plugins/  # 가상의 미래 도구
```

## SC-009 PASS 기준 (재측정 시)

```
✓ Native Korean speaker (KOSMOS 처음 보는 사람)
✓ 영문 source 파일 (quickstart.md, spec.md 등) 닫고 한국어 가이드만 사용
✓ git clone → uv sync → 9-step walkthrough → 50-item green
✓ Wall-clock ≤ 30분
```

## 결론

SC-009 ⏳ **DEFERRED**. Korean 가이드의 self-sufficiency 는 proxy measurements (Bilingual glossary 9/9 ✓ + 자동화 timing 96× margin ✓) 로 부분 검증 완료. 외부 reviewer 발생 시 본 evidence 에 signoff 추가.
