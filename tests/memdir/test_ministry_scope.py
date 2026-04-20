# SPDX-License-Identifier: Apache-2.0
"""Tests for MinistryScopeAcknowledgment schema + atomic read/write.

Feature: Epic H #1302 (035-onboarding-brand-port), task T031.
Contract: specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md
Invariants: I-13, I-14, I-15, I-16.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from kosmos.memdir.ministry_scope import (
    CURRENT_SCOPE_VERSION,
    MINISTRY_CODES,
    MinistryOptIn,
    MinistryScopeAcknowledgment,
    latest_scope,
    opt_in_lookup,
    write_scope_atomic,
)

UTC = timezone.utc
FIXTURE_SESSION = UUID("018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60")


def _valid_ministries(
    overrides: dict[str, bool] | None = None,
) -> frozenset[MinistryOptIn]:
    defaults = {code: True for code in MINISTRY_CODES}
    if overrides:
        defaults.update(overrides)
    return frozenset(
        MinistryOptIn(ministry_code=code, opt_in=optin)
        for code, optin in defaults.items()
    )


def _valid_record(
    ts: datetime | None = None,
    session_id: UUID | None = None,
    ministries: frozenset[MinistryOptIn] | None = None,
) -> MinistryScopeAcknowledgment:
    return MinistryScopeAcknowledgment(
        scope_version=CURRENT_SCOPE_VERSION,
        timestamp=ts or datetime(2026, 4, 20, 14, 33, 17, tzinfo=UTC),
        session_id=session_id or FIXTURE_SESSION,
        ministries=ministries or _valid_ministries(),
    )


# ---------------------------------------------------------------------------
# I-13 — schema round-trip
# ---------------------------------------------------------------------------


def test_schema_roundtrip() -> None:
    record = _valid_record()
    dumped = record.model_dump_json()
    rehydrated = MinistryScopeAcknowledgment.model_validate_json(dumped)
    assert rehydrated == record


# ---------------------------------------------------------------------------
# I-14 — four-unique invariant
# ---------------------------------------------------------------------------


def test_four_unique_rejects_three_item_list() -> None:
    three = frozenset(
        MinistryOptIn(ministry_code=code, opt_in=True)
        for code in ["KOROAD", "KMA", "HIRA"]
    )
    with pytest.raises(ValidationError):
        _valid_record(ministries=three)


def test_four_unique_rejects_duplicate_codes() -> None:
    # Two KOROAD entries — differing opt_in — frozenset dedupes by hash so
    # the resulting set has 4 entries but only 3 unique codes. Validator
    # must catch this.
    dup = frozenset(
        [
            MinistryOptIn(ministry_code="KOROAD", opt_in=True),
            MinistryOptIn(ministry_code="KOROAD", opt_in=False),
            MinistryOptIn(ministry_code="KMA", opt_in=True),
            MinistryOptIn(ministry_code="HIRA", opt_in=True),
        ]
    )
    with pytest.raises(ValidationError):
        _valid_record(ministries=dup)


def test_four_unique_rejects_extra_code() -> None:
    # Pydantic should reject "DGA" at the Literal check before the after-
    # validator even fires.
    with pytest.raises(ValidationError):
        MinistryOptIn(ministry_code="DGA", opt_in=True)  # type: ignore[arg-type]


def test_opt_in_lookup_returns_correct_state() -> None:
    record = _valid_record(
        ministries=_valid_ministries({"HIRA": False, "NMC": False})
    )
    assert opt_in_lookup(record, "KOROAD") is True
    assert opt_in_lookup(record, "KMA") is True
    assert opt_in_lookup(record, "HIRA") is False
    assert opt_in_lookup(record, "NMC") is False


def test_rejects_non_utc_timestamp() -> None:
    from datetime import timedelta

    kst = timezone(timedelta(hours=9))
    with pytest.raises(ValidationError):
        MinistryScopeAcknowledgment(
            scope_version="v1",
            timestamp=datetime(2026, 4, 20, 14, 33, 17, tzinfo=kst),
            session_id=FIXTURE_SESSION,
            ministries=_valid_ministries(),
        )


# ---------------------------------------------------------------------------
# I-15 — append-only
# ---------------------------------------------------------------------------


def test_append_only(tmp_path: Path) -> None:
    base = tmp_path / "ministry-scope"
    first = _valid_record()
    second = _valid_record(
        ts=datetime(2026, 4, 25, 9, 11, 42, tzinfo=UTC), session_id=uuid4()
    )
    p1 = write_scope_atomic(first, base)
    p2 = write_scope_atomic(second, base)
    assert p1.exists() and p2.exists() and p1 != p2
    assert len(list(base.glob("*.json"))) == 2
    assert len(list(base.glob("*.tmp"))) == 0


# ---------------------------------------------------------------------------
# I-16 — latest reader
# ---------------------------------------------------------------------------


def test_latest_scope_returns_most_recent(tmp_path: Path) -> None:
    base = tmp_path / "ministry-scope"
    older = _valid_record()
    newer = _valid_record(
        ts=datetime(2026, 4, 25, 9, 11, 42, tzinfo=UTC), session_id=uuid4()
    )
    write_scope_atomic(older, base)
    write_scope_atomic(newer, base)
    result = latest_scope(base)
    assert result is not None
    assert result.timestamp == newer.timestamp


def test_latest_scope_returns_none_when_dir_missing(tmp_path: Path) -> None:
    assert latest_scope(tmp_path / "never-created") is None


def test_latest_scope_skips_corrupt(tmp_path: Path) -> None:
    base = tmp_path / "ministry-scope"
    write_scope_atomic(_valid_record(), base)
    corrupt = base / "2099-12-31T23-59-59Z-corrupt.json"
    corrupt.write_text("not json")
    result = latest_scope(base)
    assert result is not None
    assert result.scope_version == "v1"
