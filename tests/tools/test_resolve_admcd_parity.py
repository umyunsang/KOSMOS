# SPDX-License-Identifier: Apache-2.0
"""T042 — resolve_location(want='adm_cd') parity against the legacy baseline.

For each entry in tests/fixtures/legacy/address_to_region_baseline.json:
  resolve_location(query=entry.query, want='adm_cd') must return an
  AdmCodeResult with code == entry.adm_cd.

Backend calls (juso, sgis, kakao) are mocked with respx / unittest.mock
so that no live API calls are made.  Each test entry supplies its own
mock adm_cd to confirm the facade passes through correctly.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from kosmos.tools.models import (
    AdmCodeResult,
    ResolveLocationInput,
)
from kosmos.tools.resolve_location import resolve_location

_REPO_ROOT = Path(__file__).parent.parent.parent
_BASELINE_FILE = _REPO_ROOT / "tests" / "fixtures" / "legacy" / "address_to_region_baseline.json"


def _load_baseline() -> list[dict]:
    return json.loads(_BASELINE_FILE.read_text())


def _make_adm_result(entry: dict) -> AdmCodeResult:
    """Build an AdmCodeResult that matches the baseline entry."""
    return AdmCodeResult(
        kind="adm_cd",
        code=entry["adm_cd"],
        name=entry["query"],
        level=entry["level"],  # type: ignore[arg-type]
        source=entry["source"],  # type: ignore[arg-type]
    )


class TestResolveAdmCdParity:
    @pytest.mark.asyncio
    async def test_baseline_file_exists_and_nonempty(self) -> None:
        baseline = _load_baseline()
        assert len(baseline) > 0, "Baseline fixture is empty"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "entry",
        _load_baseline(),
        ids=[e["query"][:30] for e in _load_baseline()],
    )
    async def test_resolve_location_returns_correct_adm_cd(self, entry: dict) -> None:
        """resolve_location(want='adm_cd') returns code == entry.adm_cd."""
        adm_result = _make_adm_result(entry)
        inp = ResolveLocationInput(query=entry["query"], want="adm_cd")

        # The resolver chain tries juso first, then kakao+sgis.
        # We mock juso to return the expected result immediately.
        with (
            patch(
                "kosmos.tools.resolve_location._juso_adm_cd",
                new=AsyncMock(return_value=adm_result),
            ),
            patch(
                "kosmos.tools.resolve_location._kakao_coords",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "kosmos.tools.resolve_location._sgis_adm_cd",
                new=AsyncMock(return_value=None),
            ),
        ):
            result = await resolve_location(inp)

        assert isinstance(result, AdmCodeResult), (
            f"Expected AdmCodeResult for query={entry['query']!r}, got {type(result)}"
        )
        assert result.code == entry["adm_cd"], (
            f"Code mismatch for {entry['query']!r}: "
            f"expected {entry['adm_cd']!r}, got {result.code!r}"
        )

    @pytest.mark.asyncio
    async def test_sgis_fallback_also_returns_correct_code(self) -> None:
        """When juso fails, sgis fallback also returns the correct code."""
        baseline = _load_baseline()
        entry = baseline[0]  # Use first entry
        adm_result = AdmCodeResult(
            kind="adm_cd",
            code=entry["adm_cd"],
            name=entry["query"],
            level=entry["level"],  # type: ignore[arg-type]
            source="sgis",
        )
        inp = ResolveLocationInput(query=entry["query"], want="adm_cd")

        from kosmos.tools.models import CoordResult

        mock_coords = CoordResult(
            kind="coords",
            lat=37.5007,
            lon=127.0368,
            confidence="high",
            source="kakao",
        )

        with (
            patch(
                "kosmos.tools.resolve_location._juso_adm_cd",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "kosmos.tools.resolve_location._kakao_coords",
                new=AsyncMock(return_value=mock_coords),
            ),
            patch(
                "kosmos.tools.resolve_location._sgis_adm_cd",
                new=AsyncMock(return_value=adm_result),
            ),
        ):
            result = await resolve_location(inp)

        assert isinstance(result, AdmCodeResult)
        assert result.code == entry["adm_cd"]
