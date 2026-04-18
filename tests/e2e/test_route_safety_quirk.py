# SPDX-License-Identifier: Apache-2.0
"""E2E quirk tests for Scenario 1 Route Safety (030 rebase).

Covers User Story 4: KOROAD year-aware administrative code quirks.

The KOROAD API changed administrative codes in 2023:
- 강원 siDo 42 → 51 (as of 2023-01-01, "강원특별자치도" renaming)
- 전북 siDo 45 → 52 (as of 2023-07-01, "전북특별자치도" renaming)

Tests verify that:
- 2023 queries with adm_cd prefix "42" → koroad adapter uses siDo=51 (fixture siDo=51).
- 2023 queries with adm_cd prefix "45" → koroad adapter uses siDo=52 (fixture siDo=52).
- 2022 queries with adm_cd prefix "42" → no remapping, siDo=42 stays (fixture siDo=42).
"""

from __future__ import annotations

import pytest

from tests.e2e.conftest import run_scenario


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario_id,expected_response_kw,description",
    [
        (
            "quirk_2023_gangwon",
            ["강원", "춘천", "사고", "위험"],
            "2023 강원도 quirk: adm_cd 42xxx → siDo=51 in KOROAD API call",
        ),
        (
            "quirk_2023_jeonbuk",
            ["전북", "전주", "사고", "위험"],
            "2023 전북 quirk: adm_cd 45xxx → siDo=52 in KOROAD API call",
        ),
        (
            "quirk_2022_control",
            ["강원", "춘천", "사고", "위험"],
            "2022 control: adm_cd 42xxx → siDo=42 (no substitution)",
        ),
    ],
)
async def test_koroad_year_quirk(
    scenario_id: str,
    expected_response_kw: list[str],
    description: str,
) -> None:
    """US4 AC1-3: KOROAD year-aware adm_cd remapping exercised end-to-end.

    The mock HTTP seam routes KOROAD requests to year/siDo-specific fixture
    tapes. If the adapter fails to apply the correct code mapping, the
    fixture file won't be found and AssertionError is raised by _mock_get.

    The final response must contain a Korean reference to the correct region.
    """
    report = await run_scenario(scenario_id)  # type: ignore[arg-type]

    assert report.stop_reason == "end_turn", (
        f"[{scenario_id}] Expected stop_reason='end_turn', got {report.stop_reason!r}"
    )

    assert report.final_response, f"[{scenario_id}] final_response must not be empty"

    response_text = report.final_response
    assert any(kw in response_text for kw in expected_response_kw), (
        f"[{scenario_id}] {description}\n"
        f"Expected one of {expected_response_kw} in final_response: "
        f"{response_text[:300]!r}"
    )
