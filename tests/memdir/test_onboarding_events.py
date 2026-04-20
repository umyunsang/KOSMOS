# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.memdir.onboarding_events (Epic H #1302, B1 remediation).

Round-trips the stdio envelope shape emitted by the TUI
(`Onboarding.tsx::defaultWriteConsentRecord` + `defaultWriteScopeRecord`)
through the Python handler and confirms each envelope lands as an atomic
write on the memdir USER tier.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from kosmos.memdir.onboarding_events import (
    OnboardingEventError,
    UnknownOnboardingEventError,
    handle_onboarding_event,
)

FIXTURE_SESSION = "018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60"


def _consent_envelope() -> dict[str, object]:
    return {
        "event": "onboarding.write_consent_record",
        "payload": {
            "consent_version": "v1",
            "timestamp": "2026-04-20T14:32:05Z",
            "aal_gate": "AAL1",
            "session_id": FIXTURE_SESSION,
            "citizen_confirmed": True,
            "schema_version": "1",
        },
        "ts": datetime.now(UTC).isoformat(),
    }


def _scope_envelope() -> dict[str, object]:
    return {
        "event": "onboarding.write_scope_record",
        "payload": {
            "scope_version": "v1",
            "timestamp": "2026-04-20T14:33:17Z",
            "session_id": FIXTURE_SESSION,
            "ministries": [
                {"ministry_code": "KOROAD", "opt_in": True},
                {"ministry_code": "KMA", "opt_in": True},
                {"ministry_code": "HIRA", "opt_in": False},
                {"ministry_code": "NMC", "opt_in": False},
            ],
            "schema_version": "1",
        },
        "ts": datetime.now(UTC).isoformat(),
    }


def test_consent_event_lands_atomic_write(tmp_path: Path) -> None:
    result = handle_onboarding_event(_consent_envelope(), memdir_root=tmp_path)
    assert result["event"] == "onboarding.write_consent_record"
    written = Path(result["written_path"])
    assert written.exists()
    body = json.loads(written.read_text())
    assert body["session_id"] == FIXTURE_SESSION
    assert body["aal_gate"] == "AAL1"
    assert body["citizen_confirmed"] is True


def test_scope_event_lands_atomic_write(tmp_path: Path) -> None:
    result = handle_onboarding_event(_scope_envelope(), memdir_root=tmp_path)
    assert result["event"] == "onboarding.write_scope_record"
    written = Path(result["written_path"])
    assert written.exists()
    body = json.loads(written.read_text())
    assert body["scope_version"] == "v1"
    assert len({m["ministry_code"] for m in body["ministries"]}) == 4


def test_unknown_event_rejected(tmp_path: Path) -> None:
    envelope = {
        "event": "onboarding.nonsense",
        "payload": {"foo": "bar"},
    }
    with pytest.raises(UnknownOnboardingEventError):
        handle_onboarding_event(envelope, memdir_root=tmp_path)


def test_invalid_envelope_shape_rejected(tmp_path: Path) -> None:
    # Missing event field.
    with pytest.raises(OnboardingEventError):
        handle_onboarding_event({"payload": {}}, memdir_root=tmp_path)
    # payload not a dict.
    with pytest.raises(OnboardingEventError):
        handle_onboarding_event(
            {"event": "onboarding.write_consent_record", "payload": "oops"},
            memdir_root=tmp_path,
        )


def test_invalid_payload_blocks_write(tmp_path: Path) -> None:
    bad = _consent_envelope()
    # citizen_confirmed=False is never allowed — must not write a record.
    bad["payload"] = {**bad["payload"], "citizen_confirmed": False}  # type: ignore[dict-item]
    with pytest.raises(OnboardingEventError):
        handle_onboarding_event(bad, memdir_root=tmp_path)
    assert not (tmp_path / "user" / "consent").exists() or not list(
        (tmp_path / "user" / "consent").glob("*.json")
    )


def test_path_traversal_session_id_rejected(tmp_path: Path) -> None:
    bad = _consent_envelope()
    bad["payload"] = {**bad["payload"], "session_id": "../../../etc/passwd"}  # type: ignore[dict-item]
    with pytest.raises(OnboardingEventError):
        handle_onboarding_event(bad, memdir_root=tmp_path)


def test_roundtrip_matches_atomic_writer_paths(tmp_path: Path) -> None:
    """Handler output matches direct `write_*_atomic()` output structure."""
    result = handle_onboarding_event(_consent_envelope(), memdir_root=tmp_path)
    path = Path(result["written_path"])
    assert path.parent == tmp_path / "user" / "consent"
    # Filename should include the UUIDv7-formatted session_id.
    assert FIXTURE_SESSION in path.name
    # And end in .json (no leftover .tmp).
    assert path.suffix == ".json"


def test_uuid_normalisation_preserved(tmp_path: Path) -> None:
    """Pydantic parses UUID strings to UUID objects; handler round-trips cleanly."""
    result = handle_onboarding_event(_consent_envelope(), memdir_root=tmp_path)
    path = Path(result["written_path"])
    body = json.loads(path.read_text())
    # Validate the session_id in the written JSON parses as a UUID.
    UUID(body["session_id"])
