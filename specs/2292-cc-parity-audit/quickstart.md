# Quickstart — CC Parity Audit (Epic α)

**Date**: 2026-04-29
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Data Model**: [data-model.md](./data-model.md)

본 quickstart 는 audit 를 처음부터 재실행하려는 reviewer 를 위한 절차서다. 산출물 reproducibility (FR-006 / SC-005) 의 1차 박제이며, `scripts/*.sh|*.py` 가 2차 박제다.

---

## 0. 사전 조건

- macOS 또는 Linux dev 환경 (Bash + GNU/BSD coreutils 모두 호환).
- Python 3.12+ (stdlib 만 사용).
- repo root = `/Users/um-yunsang/KOSMOS` 또는 동등.
- `tui/src/` (KOSMOS 입력) 와 `.references/claude-code-sourcemap/restored-src/src/` (CC 입력) 양쪽 존재 확인:
  ```bash
  test -d tui/src && test -d .references/claude-code-sourcemap/restored-src/src && echo OK
  ```

신규 의존성 설치 단계 0 — 모든 도구는 시스템에 이미 존재.

---

## 1. R1 단계 — 파일 list 산출 (`enumerate-files.sh`)

**목표**: 1,531 byte-identical / 73 SDK-import-only-diff / 212 modified / 274 KOSMOS-only / 68 CC-only 5 카테고리 list 를 deterministic 산출.

### 명령

```bash
specs/2292-cc-parity-audit/scripts/enumerate-files.sh
```

### 내부 동작

1. `find tui/src -type f \( -name '*.ts' -o -name '*.tsx' \)` → KOSMOS 파일 set.
2. `find .references/claude-code-sourcemap/restored-src/src -type f \( -name '*.ts' -o -name '*.tsx' \)` → CC 파일 set.
3. `comm` + `diff -rq` 로 매칭/비매칭 분리.
4. `LC_ALL=C sort` 로 환경 비의존 정렬.
5. 5 카테고리 결과를 `data/enumerated-{keep-byte-identical|import-candidate|modified|kosmos-only|cc-only}.txt` 에 박제.

### 검증

```bash
wc -l specs/2292-cc-parity-audit/data/enumerated-*.txt
# 예상: 1,531 / 73 / 212 / 274 / 68 (drift 시 plan.md FR-010 정정)
```

### 예상 runtime

≈10–30 초.

---

## 2. R2 단계 — 50 표본 hash spot-check (`spot-check-50.py`)

**목표**: byte-identical 모집단 1,531 에서 50 random sample 추출 + sha256 비교.

### 명령

```bash
python3 specs/2292-cc-parity-audit/scripts/spot-check-50.py
```

### 시드 + 결정성

- 시드 = `2292` (Epic 번호, 의미 부여)
- Python `random.Random(2292)` 의 `sample(population, 50)` 은 Python 3.x 보장 stable algorithm (Mersenne Twister)
- 모집단 list = `data/enumerated-keep-byte-identical.txt` 의 정렬된 순서 그대로

### 산출물

- `data/spot-check-results.json` — 50 entry, 각 `{kosmos_path, cc_source_path, kosmos_sha256, cc_sha256, hash_match, sampling_seed: 2292, sampling_index: 0..49}`.
- markdown 표는 `cc-parity-audit.md § Spot-Check (50)` 에 self-contained 박제 (시드 유실 방어).

### 검증

```bash
jq 'length' specs/2292-cc-parity-audit/data/spot-check-results.json     # → 50
jq '[.[] | select(.hash_match == false)] | length' \
   specs/2292-cc-parity-audit/data/spot-check-results.json              # → 0 if pure parity
```

`hash_match == false` 행 발견시 자동으로 `data/modified-212-classification.json` 에 reclassify entry 추가 (R4 단계 처리).

### 예상 runtime

수 초.

---

## 3. R3 단계 — 73 SDK-import-only-diff 검증 (`verify-import-diff.sh`)

**목표**: 73 후보 파일 each 가 import 라인 외 본문 변경이 없는지 자동 검증.

### 명령

```bash
specs/2292-cc-parity-audit/scripts/verify-import-diff.sh
```

### 내부 동작

각 파일 쌍에 대해:
```bash
diff <(grep -v -E '^\s*(import|from|export\s+\*\s+from|export\s*\{[^}]*\}\s+from)\b' tui/src/X) \
     <(grep -v -E '^\s*(import|from|export\s+\*\s+from|export\s*\{[^}]*\}\s+from)\b' .references/.../X)
```

위 명령이 빈 출력이면 import-only diff 확정. 비-empty 면 `body_diff_present = true` + `reclassified_to_modified = true`.

### 산출물

`data/import-verify-results.json` — 73 entry, [data-model.md § ImportDiffEntry](./data-model.md#3-importdiffentry--sdk-import-only-diff-73-검증-1-행) 스키마.

### 검증

```bash
jq 'length' data/import-verify-results.json                           # → 73
jq '[.[] | select(.reclassified_to_modified)] | length' data/import-verify-results.json
# → 일반적으로 0 또는 한 자리수. 다수면 cc-source-scope-audit § 1.1 가설 정정 필요.
```

### 예상 runtime

≈30 초–2 분 (73 × diff).

---

## 4. R4 단계 — 212 modified 분류 (`classify-modified.py`)

**목표**: 212 modified 파일 각각 (a) 디렉토리 패턴, (b) git history, (c) import scan 3 시그널로 자동 분류 → `Legitimate / Cleanup-needed / Suspicious`.

### 명령

```bash
python3 specs/2292-cc-parity-audit/scripts/classify-modified.py
```

### 내부 동작

[research.md § R-4](./research.md#r-4--212-modified-파일-분류-휴리스틱-legitimate--cleanup-needed--suspicious) 의 휴리스틱 표 그대로 구현. KOSMOS-known 잔재 path / 토큰 list (Spec 1633 영향 영역, `claude.ts`, `verifyApiKey`, `@anthropic-ai/`) 는 스크립트 상단 상수.

### 산출물

- `data/modified-212-classification.json` — 212 entry, [data-model.md § AuditEntry](./data-model.md#1-auditentry--modified-file-1-행) 스키마.
- `data/suspicious-transfer.json` — Suspicious 부분집합을 Epic β/δ 로 라우팅한 list.

### 검증

```bash
jq 'length' data/modified-212-classification.json                     # → 212
jq '[.[] | .classification] | unique' data/modified-212-classification.json
# → ["Cleanup-needed", "Legitimate", "Suspicious"]
jq '[.[] | select(.classification == "Suspicious")] | length' data/modified-212-classification.json
# → 산출물 본문에 명시 (예상 5–25)
jq '[.[] | select(.classification == "Suspicious" and .notes == null)] | length' data/modified-212-classification.json
# → 0 (FR-001 + Story 1.3 강제)
```

### 예상 runtime

≈1–3 분 (git log 호출 포함).

---

## 5. R5 단계 — markdown 산출물 조립 (`compose-audit-md.py`)

**목표**: 4 단계 산출물 JSON 들을 `cc-parity-audit.md` 단일 markdown 으로 조립.

### 명령

```bash
python3 specs/2292-cc-parity-audit/scripts/compose-audit-md.py
```

### 내부 동작

JSON appendix → markdown 표 변환. 표 cell 에 `data/*.json` deep link 박제. 본문 narrative (Authority / 결론 / Suspicious 라우팅) 는 사람이 직접 작성한 템플릿 헤더 위에 자동 표가 합류.

### 산출물

`specs/2292-cc-parity-audit/cc-parity-audit.md` — Epic α 의 최종 deliverable.

### 검증

```bash
grep -c '^| ' specs/2292-cc-parity-audit/cc-parity-audit.md   # 표 행 수, 212+50+73+suspicious 합산 일치
```

### 예상 runtime

수 초.

---

## 6. 한 번에 재실행

```bash
cd /Users/um-yunsang/KOSMOS
specs/2292-cc-parity-audit/scripts/enumerate-files.sh           # R1
python3 specs/2292-cc-parity-audit/scripts/spot-check-50.py     # R2
specs/2292-cc-parity-audit/scripts/verify-import-diff.sh        # R3
python3 specs/2292-cc-parity-audit/scripts/classify-modified.py # R4
python3 specs/2292-cc-parity-audit/scripts/compose-audit-md.py  # R5
```

총 예상 runtime ≈5 분.

---

## 7. Read-only invariant 자기 검증

R1–R5 실행 후:

```bash
git -C /Users/um-yunsang/KOSMOS status --short -- ':!specs/2292-cc-parity-audit'
# → 어떤 출력도 없어야 함 (FR-007 / SC-006)
```

`specs/2292-cc-parity-audit/` 외부 변경이 발견되면 audit 무효 → 변경 revert + 원인 조사.

---

## 8. Drift 정정 절차

R1 산출 5 카테고리 행 수가 `cc-source-scope-audit § 1.1, § 1.2` 의 (1,531 / 73 / 212 / 274 / 68) 과 다르면 drift 발생. 정정 절차:

1. drift delta 계산 (예: modified 212 → 215).
2. `cc-parity-audit.md § Drift Notes` 섹션에 시점 + delta + 추정 원인 기록.
3. 표 헤더 행 수를 새 숫자로 갱신.
4. spec.md FR-001 / FR-010 의 `212` 숫자는 그대로 두고, `cc-parity-audit.md` 가 더 권위 있는 audit 시점 numeric 으로 작동.
