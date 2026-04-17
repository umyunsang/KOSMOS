# SPDX-License-Identifier: Apache-2.0
"""T017 / T019 / T020 — Tests for run_redactor() in kosmos.safety._redactor.

Validates:
  T017/T019: 10 pii_samples.json fixtures (2 RRN, 2 phone, 2 email,
             2 passport, 2 credit card).
  T020: SC-003 latency gate — p95 ≤ 50 ms over a 100 KB synthetic payload.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from kosmos.safety._redactor import run_redactor

# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

_FIXTURES_PATH = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "safety" / "pii_samples.json"
)

_FIXTURES: list[dict] = json.loads(_FIXTURES_PATH.read_text(encoding="utf-8"))

# Category → placeholder token mapping (must match _redactor.py internals).
_PLACEHOLDER_MAP: dict[str, str] = {
    "rrn": "<RRN>",
    "phone_kr": "<PHONE_KR>",
    "email": "<EMAIL>",
    "passport_kr": "<PASSPORT_KR>",
    "credit_card": "<CREDIT_CARD>",
}


# ---------------------------------------------------------------------------
# T017 / T019 — Per-fixture parametrized tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", _FIXTURES, ids=[f["id"] for f in _FIXTURES])
def test_redactor_fixture(fixture: dict) -> None:
    """Each pii_samples.json fixture exercises one PII category through run_redactor().

    Assertions:
    1a. For valid or non-card fixtures: result.matches contains ≥1 match with
        the expected category.
    1b. For CREDIT_CARD with luhn_valid==False: zero CREDIT_CARD matches.
    2.  For valid-Luhn / non-card: redacted_text contains the placeholder token
        and does NOT contain the raw PII substring.
    3.  For invalid-Luhn card: redacted_text is byte-identical to input_text.
    """
    category: str = fixture["category"]
    input_text: str = fixture["input_text"]
    expected_placeholder: str = fixture["expected_placeholder"]
    luhn_valid: bool | None = fixture["luhn_valid"]

    result = run_redactor(input_text)

    is_invalid_luhn_card = (category == "credit_card") and (luhn_valid is False)

    # --- Assertion 1: match count for the target category ---
    category_matches = [m for m in result.matches if m.category == category]

    if is_invalid_luhn_card:
        # FR-005: Luhn-invalid cards must NOT be redacted.
        assert len(category_matches) == 0, (
            f"[{fixture['id']}] Expected 0 CREDIT_CARD matches for Luhn-invalid card, "
            f"got {len(category_matches)}: {category_matches}"
        )
    else:
        assert len(category_matches) >= 1, (
            f"[{fixture['id']}] Expected ≥1 match for category '{category}', "
            f"got 0. Matches found: {result.matches}"
        )

    # --- Assertion 2 / 3: redacted_text content ---
    if is_invalid_luhn_card:
        # Redacted text must be byte-identical to input (no change at all).
        assert result.redacted_text == input_text, (
            f"[{fixture['id']}] Luhn-invalid card: expected redacted_text == input_text, "
            f"but got:\n  input:    {input_text!r}\n  redacted: {result.redacted_text!r}"
        )
    else:
        # Placeholder must appear in redacted text.
        assert expected_placeholder in result.redacted_text, (
            f"[{fixture['id']}] Expected placeholder {expected_placeholder!r} "
            f"in redacted_text, but got: {result.redacted_text!r}"
        )
        # Raw PII value must NOT appear in redacted text.
        # Extract the PII value: find it in input_text using the pattern.
        from kosmos.safety._patterns import _PII_PATTERNS  # noqa: PLC0415

        pattern = _PII_PATTERNS[category]
        pii_match = pattern.search(input_text)
        assert pii_match is not None, (
            f"[{fixture['id']}] Could not find raw PII in input_text using pattern "
            f"for category '{category}'. Input: {input_text!r}"
        )
        raw_value = pii_match.group()
        assert raw_value not in result.redacted_text, (
            f"[{fixture['id']}] Raw PII value {raw_value!r} still present in "
            f"redacted_text: {result.redacted_text!r}"
        )


# ---------------------------------------------------------------------------
# T020 — SC-003 latency gate: p95 ≤ 50 ms over 100 KB payload
# ---------------------------------------------------------------------------

# SC-003: run_redactor() must complete within 50 ms at p95 on a 100 KB payload.
# Gated under @pytest.mark.performance to allow CI skipping if the environment is slow.


@pytest.mark.performance
@pytest.mark.skipif(
    os.environ.get("KOSMOS_SKIP_PERF") == "1",
    reason="KOSMOS_SKIP_PERF=1 — performance gates disabled on constrained runners",
)
def test_redactor_latency_p95_100kb() -> None:  # SC-003
    """SC-003: p95 latency of run_redactor() must be ≤ 50 ms on a 100 KB payload.

    Methodology:
    - Construct a ~100 KB Korean-prose payload with 5 PII instances embedded.
    - Run run_redactor() 20 times, measure wall time per call via time.perf_counter().
    - Sort timings; assert the 95th percentile (index 18 of 20) is ≤ 50 ms.
    """
    # Build a ~100 KB payload: Korean prose repeated, with 5 PII instances.
    base_prose = (
        "이 문서는 공공 서비스 이용에 관한 안내 자료입니다. "
        "시민 여러분께서는 관련 법령에 따라 본인 확인 절차를 거쳐야 합니다. "
        "문의사항이 있으시면 담당 부서로 연락해 주시기 바랍니다. "
    )
    # 5 PII instances spread within the payload.
    pii_segments = [
        "주민등록번호 900101-1234567을 확인하였습니다. ",
        "연락처 010-1234-5678로 안내 문자를 발송하였습니다. ",
        "이메일 hong.gildong@example.kr로 결과를 전송합니다. ",
        "여권번호 M12345678이 확인되었습니다. ",
        "카드번호 4532015112830366으로 결제가 완료되었습니다. ",
    ]

    # Build ~100 KB: interleave prose blocks with PII segments.
    # Each prose repeat ~135 bytes; 5 PII segments ~220 bytes total.
    # We need roughly 100 000 bytes total.
    target_bytes = 100_000
    chunk = base_prose * 50  # ~6750 bytes per chunk
    payload_parts: list[str] = []
    current_size = 0
    pii_index = 0
    while current_size < target_bytes:
        payload_parts.append(chunk)
        current_size += len(chunk.encode("utf-8"))
        if pii_index < len(pii_segments):
            payload_parts.append(pii_segments[pii_index])
            current_size += len(pii_segments[pii_index].encode("utf-8"))
            pii_index += 1

    payload = "".join(payload_parts)
    assert len(payload.encode("utf-8")) >= 90_000, (
        f"Payload too small: {len(payload.encode('utf-8'))} bytes"
    )

    # Warm up (not measured).
    run_redactor(payload)

    # Timed runs.
    iterations = 20
    timings_ms: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        run_redactor(payload)
        t1 = time.perf_counter()
        timings_ms.append((t1 - t0) * 1000.0)

    timings_ms.sort()
    # p95 index: ceil(0.95 * 20) - 1 = ceil(19) - 1 = 18 (0-indexed)
    p95_index = int(0.95 * iterations) - 1  # index 18 for 20 runs
    p95_ms = timings_ms[p95_index]

    assert p95_ms <= 50.0, (  # SC-003
        f"SC-003 VIOLATION: p95 latency {p95_ms:.2f} ms exceeds 50 ms limit. "
        f"All timings (ms): {[f'{t:.2f}' for t in timings_ms]}"
    )
