# SPDX-License-Identifier: Apache-2.0
"""Tests for PIPAConsentRecord schema + atomic read/write.

Feature: Epic H #1302 (035-onboarding-brand-port), task T023.
Contract: specs/035-onboarding-brand-port/contracts/memdir-consent-schema.md
Invariants: I-9, I-10, I-11, I-12.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from kosmos.memdir.user_consent import (
    CURRENT_CONSENT_VERSION,
    PIPAConsentRecord,
    latest_consent,
    write_consent_atomic,
)

FIXTURE_SESSION_ID = UUID("018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60")
UTC = timezone.utc


def _valid_record(ts: datetime, session_id: UUID | None = None) -> PIPAConsentRecord:
    return PIPAConsentRecord(
        consent_version=CURRENT_CONSENT_VERSION,
        timestamp=ts,
        aal_gate="AAL1",
        session_id=session_id or FIXTURE_SESSION_ID,
        citizen_confirmed=True,
    )


# ---------------------------------------------------------------------------
# I-9 — schema round-trip
# ---------------------------------------------------------------------------


def test_schema_roundtrip() -> None:
    record = _valid_record(datetime(2026, 4, 20, 14, 32, 5, tzinfo=UTC))
    dumped = record.model_dump_json()
    rehydrated = PIPAConsentRecord.model_validate_json(dumped)
    assert rehydrated == record
    assert rehydrated.schema_version == "1"


def test_decline_writes_nothing() -> None:
    """citizen_confirmed=False must fail validation (contract § 1)."""
    with pytest.raises(ValidationError):
        PIPAConsentRecord(
            consent_version="v1",
            timestamp=datetime.now(UTC),
            aal_gate="AAL1",
            session_id=FIXTURE_SESSION_ID,
            citizen_confirmed=False,  # type: ignore[arg-type]
        )


def test_rejects_non_utc_timestamp() -> None:
    kst = timezone(timedelta(hours=9))
    with pytest.raises(ValidationError):
        PIPAConsentRecord(
            consent_version="v1",
            timestamp=datetime(2026, 4, 20, 14, 32, 5, tzinfo=kst),
            aal_gate="AAL1",
            session_id=FIXTURE_SESSION_ID,
            citizen_confirmed=True,
        )


def test_rejects_bad_consent_version_pattern() -> None:
    with pytest.raises(ValidationError):
        PIPAConsentRecord(
            consent_version="1.0",  # must match ^v\d+$
            timestamp=datetime.now(UTC),
            aal_gate="AAL1",
            session_id=FIXTURE_SESSION_ID,
            citizen_confirmed=True,
        )


def test_rejects_extra_keys() -> None:
    payload = {
        "consent_version": "v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "aal_gate": "AAL1",
        "session_id": str(FIXTURE_SESSION_ID),
        "citizen_confirmed": True,
        "schema_version": "1",
        "unexpected": "value",
    }
    with pytest.raises(ValidationError):
        PIPAConsentRecord.model_validate(payload)


# ---------------------------------------------------------------------------
# I-10 — append-only semantics
# ---------------------------------------------------------------------------


def test_append_only(tmp_path: Path) -> None:
    base = tmp_path / "consent"
    first = _valid_record(datetime(2026, 4, 20, 14, 32, 5, tzinfo=UTC))
    second = _valid_record(
        datetime(2026, 4, 25, 9, 11, 42, tzinfo=UTC), session_id=uuid4()
    )

    first_path = write_consent_atomic(first, base)
    second_path = write_consent_atomic(second, base)

    assert first_path.exists()
    assert second_path.exists()
    assert first_path != second_path

    files = sorted(base.glob("*.json"))
    assert len(files) == 2
    # File bytes must be stable — neither write overwrote the other.
    assert json.loads(first_path.read_text())["session_id"] == str(
        FIXTURE_SESSION_ID
    )
    assert json.loads(second_path.read_text())["session_id"] != str(
        FIXTURE_SESSION_ID
    )


def test_write_is_atomic_tmp_removed(tmp_path: Path) -> None:
    base = tmp_path / "consent"
    record = _valid_record(datetime(2026, 4, 20, 14, 32, 5, tzinfo=UTC))
    write_consent_atomic(record, base)
    # No stray .json.tmp left over.
    tmp_files = list(base.glob("*.tmp"))
    assert tmp_files == []


# ---------------------------------------------------------------------------
# I-12 — reader semantics (latest + corrupt-skip)
# ---------------------------------------------------------------------------


def test_latest_consent_returns_most_recent(tmp_path: Path) -> None:
    base = tmp_path / "consent"
    older = _valid_record(datetime(2026, 4, 20, 14, 32, 5, tzinfo=UTC))
    newer = _valid_record(
        datetime(2026, 4, 25, 9, 11, 42, tzinfo=UTC), session_id=uuid4()
    )
    write_consent_atomic(older, base)
    write_consent_atomic(newer, base)

    result = latest_consent(base)
    assert result is not None
    assert result.timestamp == newer.timestamp


def test_latest_consent_skips_corrupt(tmp_path: Path) -> None:
    base = tmp_path / "consent"
    base.mkdir(parents=True)
    # Inject a corrupt file lexicographically AFTER the valid one — it must
    # be skipped and the valid record returned.
    valid = _valid_record(datetime(2026, 4, 20, 14, 32, 5, tzinfo=UTC))
    write_consent_atomic(valid, base)
    corrupt = base / "2099-12-31T23-59-59Z-corrupt.json"
    corrupt.write_text("not json at all")

    result = latest_consent(base)
    assert result is not None
    assert result.consent_version == "v1"


def test_latest_consent_returns_none_when_dir_missing(tmp_path: Path) -> None:
    assert latest_consent(tmp_path / "never-created") is None


def test_latest_consent_returns_none_when_dir_empty(tmp_path: Path) -> None:
    base = tmp_path / "consent"
    base.mkdir(parents=True)
    assert latest_consent(base) is None
