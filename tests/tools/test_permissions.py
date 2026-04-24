# SPDX-License-Identifier: Apache-2.0
"""T012 — Unit tests for compute_permission_tier() totality (Spec 1634 FR-011)."""

from __future__ import annotations

import pytest

from kosmos.tools.permissions import compute_permission_tier


class TestComputePermissionTierTotality:
    """Every (auth_level, is_irreversible) combination returns a value in {1,2,3}."""

    @pytest.mark.parametrize(
        "auth_level,is_irreversible,expected",
        [
            ("public", False, 1),
            ("public", True, 3),
            ("AAL1", False, 1),
            ("AAL1", True, 3),
            ("AAL2", False, 2),
            ("AAL2", True, 3),
            ("AAL3", False, 3),
            ("AAL3", True, 3),
        ],
    )
    def test_mapping(self, auth_level, is_irreversible, expected):
        assert compute_permission_tier(auth_level, is_irreversible) == expected

    def test_totality_all_combinations_return_valid_tier(self):
        """Every combination from the closed AALLevel x bool domain returns 1/2/3."""
        for al in ("public", "AAL1", "AAL2", "AAL3"):
            for ir in (False, True):
                tier = compute_permission_tier(al, ir)
                assert tier in (1, 2, 3), f"{al}/{ir} -> {tier}"


class TestComputePermissionTierInvariants:
    """Irreversibility always wins over AAL; AAL mapping is preserved otherwise."""

    def test_irreversibility_overrides_lower_AAL(self):
        for al in ("public", "AAL1", "AAL2"):
            assert compute_permission_tier(al, True) == 3

    def test_non_irreversible_follows_AAL_mapping(self):
        assert compute_permission_tier("public", False) == 1
        assert compute_permission_tier("AAL1", False) == 1
        assert compute_permission_tier("AAL2", False) == 2
        assert compute_permission_tier("AAL3", False) == 3


class TestComputePermissionTierDefensive:
    """Unknown auth_level raises ValueError -- defensive branch."""

    def test_unknown_auth_level_raises(self):
        with pytest.raises(ValueError, match="Unknown auth_level"):
            compute_permission_tier("AAL9", False)  # type: ignore[arg-type]
