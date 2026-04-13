# SPDX-License-Identifier: Apache-2.0
"""Tests for latlon_to_grid() in kosmos.tools.kma.grid_coords."""

from __future__ import annotations

from kosmos.tools.kma.grid_coords import latlon_to_grid


class TestLatLonToGrid:
    """Validate KMA Lambert Conformal Conic conversion against known reference points."""

    def test_seoul_city_hall(self):
        """Seoul City Hall (37.5665, 126.9780) → expected KMA grid ~(60, 127)."""
        nx, ny = latlon_to_grid(37.5665, 126.9780)
        # Allow ±2 grid cells for floating-point variation
        assert abs(nx - 60) <= 2, f"nx={nx} expected ~60"
        assert abs(ny - 127) <= 2, f"ny={ny} expected ~127"

    def test_busan_haeundae(self):
        """Busan Haeundae beach (35.1588, 129.1603) → expected KMA grid ~(99, 76)."""
        nx, ny = latlon_to_grid(35.1588, 129.1603)
        assert abs(nx - 99) <= 2, f"nx={nx} expected ~99"
        assert abs(ny - 76) <= 2, f"ny={ny} expected ~76"

    def test_seocho_coords(self):
        """Seocho (37.5039, 127.0089) → nx near 61, ny near 124."""
        nx, ny = latlon_to_grid(37.5039, 127.0089)
        assert abs(nx - 61) <= 2, f"nx={nx} expected ~61"
        assert abs(ny - 124) <= 2, f"ny={ny} expected ~124"

    def test_gangnam_coords(self):
        """Gangnam (37.5002, 127.0362) → nx near 61, ny near 125."""
        nx, ny = latlon_to_grid(37.5002, 127.0362)
        assert abs(nx - 61) <= 2, f"nx={nx} expected ~61"
        assert abs(ny - 125) <= 2, f"ny={ny} expected ~125"

    def test_returns_tuple_of_ints(self):
        nx, ny = latlon_to_grid(37.5665, 126.9780)
        assert isinstance(nx, int)
        assert isinstance(ny, int)

    def test_jeju_island(self):
        """Jeju Island center (33.4890, 126.4983) → expected KMA grid ~(52, 38)."""
        nx, ny = latlon_to_grid(33.4890, 126.4983)
        assert abs(nx - 52) <= 3, f"nx={nx} expected ~52"
        assert abs(ny - 38) <= 3, f"ny={ny} expected ~38"
