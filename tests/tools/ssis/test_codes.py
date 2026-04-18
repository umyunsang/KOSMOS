# SPDX-License-Identifier: Apache-2.0
"""Enum coverage tests for SSIS code tables — spec 029 T009.

Asserts:
- Each enum has the expected member count.
- Every value is a zero-padded decimal string or short keyword exactly
  matching data-model.md §1.
"""

from __future__ import annotations

from kosmos.tools.ssis.codes import (
    CallType,
    IntrsThemaCode,
    LifeArrayCode,
    OrderBy,
    SrchKeyCode,
    TrgterIndvdlCode,
)


class TestSrchKeyCode:
    """SrchKeyCode — 3 members."""

    def test_member_count(self) -> None:
        assert len(SrchKeyCode) == 3

    def test_values(self) -> None:
        assert SrchKeyCode.name == "001"
        assert SrchKeyCode.summary == "002"
        assert SrchKeyCode.all_fields == "003"

    def test_all_zero_padded_decimal(self) -> None:
        for member in SrchKeyCode:
            assert member.value.isdigit(), f"Expected decimal string, got {member.value!r}"


class TestCallType:
    """CallType — 2 members."""

    def test_member_count(self) -> None:
        assert len(CallType) == 2

    def test_values(self) -> None:
        assert CallType.list_ == "L"
        assert CallType.detail == "D"

    def test_single_char_values(self) -> None:
        for member in CallType:
            assert len(member.value) == 1


class TestOrderBy:
    """OrderBy — 2 members."""

    def test_member_count(self) -> None:
        assert len(OrderBy) == 2

    def test_values(self) -> None:
        assert OrderBy.date == "date"
        assert OrderBy.popular == "popular"

    def test_keyword_values(self) -> None:
        for member in OrderBy:
            assert member.value.isalpha(), f"Expected keyword, got {member.value!r}"


class TestLifeArrayCode:
    """LifeArrayCode — 7 members."""

    def test_member_count(self) -> None:
        assert len(LifeArrayCode) == 7

    def test_values(self) -> None:
        assert LifeArrayCode.infant == "001"
        assert LifeArrayCode.child == "002"
        assert LifeArrayCode.teen == "003"
        assert LifeArrayCode.young_adult == "004"
        assert LifeArrayCode.middle_aged == "005"
        assert LifeArrayCode.elderly == "006"
        assert LifeArrayCode.pregnancy_birth == "007"

    def test_sequential_decimal_codes(self) -> None:
        values = sorted(int(m.value) for m in LifeArrayCode)
        assert values == list(range(1, 8))


class TestTrgterIndvdlCode:
    """TrgterIndvdlCode — 6 members."""

    def test_member_count(self) -> None:
        assert len(TrgterIndvdlCode) == 6

    def test_values(self) -> None:
        assert TrgterIndvdlCode.multicultural == "010"
        assert TrgterIndvdlCode.multichild == "020"
        assert TrgterIndvdlCode.veteran == "030"
        assert TrgterIndvdlCode.disabled == "040"
        assert TrgterIndvdlCode.low_income == "050"
        assert TrgterIndvdlCode.single_parent == "060"

    def test_all_zero_padded_decimal(self) -> None:
        for member in TrgterIndvdlCode:
            assert member.value.isdigit(), f"Expected decimal string, got {member.value!r}"
            assert len(member.value) == 3


class TestIntrsThemaCode:
    """IntrsThemaCode — 14 members."""

    def test_member_count(self) -> None:
        assert len(IntrsThemaCode) == 14

    def test_pregnancy_birth_is_080(self) -> None:
        """Authoritative 임신·출산 code for intrsThemaArray is 080 (spec 029 note)."""
        assert IntrsThemaCode.pregnancy_birth == "080"

    def test_values(self) -> None:
        assert IntrsThemaCode.physical_health == "010"
        assert IntrsThemaCode.mental_health == "020"
        assert IntrsThemaCode.livelihood == "030"
        assert IntrsThemaCode.housing == "040"
        assert IntrsThemaCode.employment == "050"
        assert IntrsThemaCode.culture_leisure == "060"
        assert IntrsThemaCode.safety_crisis == "070"
        assert IntrsThemaCode.pregnancy_birth == "080"
        assert IntrsThemaCode.childcare == "090"
        assert IntrsThemaCode.education == "100"
        assert IntrsThemaCode.adoption_foster == "110"
        assert IntrsThemaCode.care_support == "120"
        assert IntrsThemaCode.small_finance == "130"
        assert IntrsThemaCode.legal == "140"

    def test_all_zero_padded_decimal(self) -> None:
        for member in IntrsThemaCode:
            assert member.value.isdigit(), f"Expected decimal string, got {member.value!r}"

    def test_sequential_by_tens(self) -> None:
        values = sorted(int(m.value) for m in IntrsThemaCode)
        assert values == [10 * i for i in range(1, 15)]
