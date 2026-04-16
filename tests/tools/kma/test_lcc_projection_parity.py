# SPDX-License-Identifier: Apache-2.0
"""T043 — LCC projection parity tests.

Verifies that latlon_to_lcc produces (nx, ny) within ±1 cell of the
expected values recorded in the synthesized baseline fixture, and that
the KMA canonical reference point (서울청사) matches exactly.

Fixture provenance: tests/fixtures/legacy/address_to_grid_baseline.json
  (synthesized from KMA VilageFcstInfoService_2.0 technical guide, 2021-12).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kosmos.tools.kma.projection import KMADomainError, latlon_to_lcc

_REPO_ROOT = Path(__file__).parent.parent.parent.parent
_BASELINE_FILE = _REPO_ROOT / "tests" / "fixtures" / "legacy" / "address_to_grid_baseline.json"


def _load_baseline() -> list[dict]:
    return json.loads(_BASELINE_FILE.read_text())


# ---------------------------------------------------------------------------
# Canonical reference test
# ---------------------------------------------------------------------------


class TestCanonicalSeoulGovOffice:
    """Canonical LCC output for the 서울청사 coordinate pair.

    The KMA formula (RE=6371.00877, GRID=5.0, SLAT1=30, SLAT2=60,
    OLON=126, OLAT=38, XO=43, YO=136) produces (nx=62, ny=128) for
    (lat=37.5665, lon=127.0495).  This result is confirmed by the
    existing ``latlon_to_grid`` reference implementation in
    ``kosmos.tools.kma.grid_coords`` which uses identical constants.
    """

    def test_seoulcheong_matches_reference_implementation(self) -> None:
        """latlon_to_lcc and latlon_to_grid must agree on the canonical point."""
        from kosmos.tools.kma.grid_coords import latlon_to_grid

        nx_ref, ny_ref = latlon_to_grid(37.5665, 127.0495)
        nx_lcc, ny_lcc = latlon_to_lcc(37.5665, 127.0495)

        assert nx_lcc == nx_ref, f"nx mismatch: lcc={nx_lcc}, reference={nx_ref}"
        assert ny_lcc == ny_ref, f"ny mismatch: lcc={ny_lcc}, reference={ny_ref}"

        # Confirm the specific values (both implementations agree)
        assert nx_lcc == 62, f"Expected nx=62, got {nx_lcc}"
        assert ny_lcc == 128, f"Expected ny=128, got {ny_lcc}"


# ---------------------------------------------------------------------------
# Baseline fixture parity tests (±1 cell tolerance)
# ---------------------------------------------------------------------------


class TestBaselineParity:
    def test_all_baseline_points_within_one_cell(self) -> None:
        """All baseline points must resolve to within ±1 grid cell."""
        baseline = _load_baseline()
        failures: list[str] = []

        for entry in baseline:
            lat: float = entry["lat"]
            lon: float = entry["lon"]
            expected_nx: int = entry["nx"]
            expected_ny: int = entry["ny"]
            description: str = entry.get("description", f"({lat}, {lon})")

            nx, ny = latlon_to_lcc(lat, lon)
            dx = abs(nx - expected_nx)
            dy = abs(ny - expected_ny)

            if dx > 1 or dy > 1:
                failures.append(
                    f"{description}: got ({nx}, {ny}), expected ({expected_nx}, {expected_ny}), "
                    f"delta=({dx}, {dy})"
                )

        assert not failures, "LCC parity failures:\n" + "\n".join(failures)

    def test_baseline_file_exists_and_nonempty(self) -> None:
        baseline = _load_baseline()
        assert len(baseline) > 0, "Baseline fixture is empty"


# ---------------------------------------------------------------------------
# Domain error tests
# ---------------------------------------------------------------------------


class TestDomainError:
    def test_lat_too_low_raises(self) -> None:
        with pytest.raises(KMADomainError):
            latlon_to_lcc(10.0, 127.0)  # below lat_min=22

    def test_lat_too_high_raises(self) -> None:
        with pytest.raises(KMADomainError):
            latlon_to_lcc(50.0, 127.0)  # above lat_max=46

    def test_lon_too_low_raises(self) -> None:
        with pytest.raises(KMADomainError):
            latlon_to_lcc(37.0, 100.0)  # below lon_min=108

    def test_lon_too_high_raises(self) -> None:
        with pytest.raises(KMADomainError):
            latlon_to_lcc(37.0, 150.0)  # above lon_max=146

    def test_valid_boundary_does_not_raise(self) -> None:
        # At minimum valid corner
        nx, ny = latlon_to_lcc(22.0, 108.0)
        assert isinstance(nx, int) and isinstance(ny, int)

    def test_domain_error_carries_coordinates(self) -> None:
        with pytest.raises(KMADomainError) as exc_info:
            latlon_to_lcc(5.0, 127.0)
        err = exc_info.value
        assert err.lat == pytest.approx(5.0)
        assert err.lon == pytest.approx(127.0)
