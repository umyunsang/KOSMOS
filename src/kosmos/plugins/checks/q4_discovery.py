# SPDX-License-Identifier: Apache-2.0
"""Q4 — Discovery & docs (8 checks).

Korean morphology check (Q4-HINT-NOUNS) reuses the existing Kiwipiepy
tokenizer from Spec 022. The other 7 checks are string / file presence
heuristics on the manifest + README.ko.md.
"""

from __future__ import annotations

import re
from pathlib import Path

from kosmos.plugins.checks.framework import CheckContext, CheckOutcome, failed, passed

# 한국어 명사 추출은 Kiwipiepy 가 (Spec 022) 이미 의존성에 들어 있어 별도 추가 없이 사용.
# 명사 카운트 ≥ 3 룰은 R-1 Q4-HINT-NOUNS 의 권고치.

_MIN_KOREAN_NOUNS = 3
_MIN_README_LEN = 500


_MINISTRY_NAMES_KO: tuple[str, ...] = (
    "도로교통공단",
    "기상청",
    "국립중앙의료원",
    "건강보험심사평가원",
    "소방청",
    "보건복지부",
    "국토교통부",
    "행정안전부",
    "한국교통안전공단",
    "식품의약품안전처",
    "정부24",
    "서울",
    "부산",
    "우정사업본부",
    "우체국",
    "통계청",
    "국세청",
    "한국전력",
    "교육부",
    "여성가족부",
    "법무부",
    "환경부",
    "국방부",
    "외교부",
    "공공",
)


def _ensure_manifest(ctx: CheckContext, check_id: str) -> CheckOutcome | None:
    if ctx.manifest is None:
        return failed(
            ko=f"manifest 검증 실패로 {check_id} 확인 불가",
            en=f"cannot run {check_id} — manifest failed validation",
        )
    return None


def check_hint_ko(ctx: CheckContext) -> CheckOutcome:
    """Q4-HINT-KO — search_hint_ko non-empty."""
    blocked = _ensure_manifest(ctx, "Q4-HINT-KO")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if not ctx.manifest.search_hint_ko.strip():
        return failed(
            ko="search_hint_ko 가 비어 있음",
            en="search_hint_ko is empty",
        )
    return passed()


def check_hint_en(ctx: CheckContext) -> CheckOutcome:
    """Q4-HINT-EN — search_hint_en non-empty."""
    blocked = _ensure_manifest(ctx, "Q4-HINT-EN")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if not ctx.manifest.search_hint_en.strip():
        return failed(
            ko="search_hint_en 이 비어 있음",
            en="search_hint_en is empty",
        )
    return passed()


def check_hint_nouns(ctx: CheckContext) -> CheckOutcome:
    """Q4-HINT-NOUNS — search_hint_ko ≥ 3 Korean nouns via Kiwipiepy.

    Falls back to a regex-based Korean-word count if Kiwipiepy fails to
    initialise (e.g. in a network-blocked CI environment that cannot
    download the model on first use).
    """
    blocked = _ensure_manifest(ctx, "Q4-HINT-NOUNS")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    text = ctx.manifest.search_hint_ko

    nouns: list[str]
    try:
        from kiwipiepy import Kiwi  # noqa: PLC0415

        kiwi = Kiwi()
        nouns = [tok.form for tok in kiwi.tokenize(text) if tok.tag.startswith("N")]
    except Exception:
        # Fallback: count distinct sequences of 2+ Korean characters.
        nouns = list({m for m in re.findall(r"[가-힣]{2,}", text)})

    if len(nouns) < _MIN_KOREAN_NOUNS:
        return failed(
            ko=(
                f"search_hint_ko 한국어 명사 ≥ {_MIN_KOREAN_NOUNS} 개 권장 "
                f"(현재 {len(nouns)} 개)"
            ),
            en=(
                f"search_hint_ko should have ≥ {_MIN_KOREAN_NOUNS} Korean nouns "
                f"(got {len(nouns)})"
            ),
        )
    return passed()


def check_hint_ministry(ctx: CheckContext) -> CheckOutcome:
    """Q4-HINT-MINISTRY — search_hint_ko mentions a ministry/agency name."""
    blocked = _ensure_manifest(ctx, "Q4-HINT-MINISTRY")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    text = ctx.manifest.search_hint_ko
    if not any(name in text for name in _MINISTRY_NAMES_KO):
        return failed(
            ko=(
                "search_hint_ko 에 부처 / 기관 / 지자체 이름 포함 권장 "
                "(예: 도로교통공단, 서울, 우정사업본부)"
            ),
            en=(
                "search_hint_ko should mention a ministry / agency / city "
                "(e.g. 도로교통공단, 서울, 우정사업본부)"
            ),
        )
    return passed()


def check_name_ko(ctx: CheckContext) -> CheckOutcome:
    """Q4-NAME-KO — adapter.tool_id is plugin-namespaced (already enforced).

    For Korean display name we inspect the embedded GovAPITool's name_ko
    when available; we cannot easily do so from the manifest alone since
    it lives on the registered tool. We approximate by ensuring the
    ko-side hint exists in Korean script.
    """
    blocked = _ensure_manifest(ctx, "Q4-NAME-KO")
    if blocked:
        return blocked
    assert ctx.manifest is not None
    if not re.search(r"[가-힣]", ctx.manifest.search_hint_ko):
        return failed(
            ko="한국어 표시 텍스트가 search_hint_ko 에 없음",
            en="no Korean script found in search_hint_ko",
        )
    return passed()


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def check_cite(ctx: CheckContext) -> CheckOutcome:
    """Q4-CITE — README.ko.md cites at least one canonical reference URL.

    Heuristic: look for a URL pointing to KOSMOS docs, the source spec
    page, or a public data portal.
    """
    text = _read_text(ctx.plugin_root / "README.ko.md") or ""
    if not re.search(r"https?://[^\s)]+", text):
        return failed(
            ko="README.ko.md 에 외부 참조 URL 이 없음 (Q4-CITE)",
            en="README.ko.md has no citation URL (Q4-CITE)",
        )
    return passed()


def check_readme_ko(ctx: CheckContext) -> CheckOutcome:
    """Q4-README-KO — README.ko.md exists."""
    if not (ctx.plugin_root / "README.ko.md").is_file():
        return failed(
            ko="README.ko.md 가 없음 (Q4-README-KO)",
            en="README.ko.md is missing (Q4-README-KO)",
        )
    return passed()


def check_readme_min_len(ctx: CheckContext) -> CheckOutcome:
    """Q4-README-MIN-LEN — README.ko.md ≥ 500 chars."""
    text = _read_text(ctx.plugin_root / "README.ko.md") or ""
    if len(text) < _MIN_README_LEN:
        return failed(
            ko=(
                f"README.ko.md 가 {_MIN_README_LEN} 자 미만 "
                f"(현재 {len(text)} 자)"
            ),
            en=(
                f"README.ko.md is shorter than {_MIN_README_LEN} chars "
                f"(got {len(text)})"
            ),
        )
    return passed()


__all__ = [
    "check_hint_ko",
    "check_hint_en",
    "check_hint_nouns",
    "check_hint_ministry",
    "check_name_ko",
    "check_cite",
    "check_readme_ko",
    "check_readme_min_len",
]
