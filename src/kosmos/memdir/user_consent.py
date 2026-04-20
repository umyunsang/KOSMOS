# SPDX-License-Identifier: Apache-2.0
"""PIPA consent record + atomic reader/writer for the memdir USER tier.

Feature: Epic H #1302 (035-onboarding-brand-port).
Contract: specs/035-onboarding-brand-port/contracts/memdir-consent-schema.md

The record is append-only — every citizen consent event (including consent
version bumps) writes a NEW file.  Declines never write a record (the
`citizen_confirmed: Literal[True]` constraint guarantees this at the schema
layer).

Storage layout:
    ~/.kosmos/memdir/user/consent/<ts-utc>-<session_uuidv7>.json

Atomic write: tmp file + fsync + os.rename (pattern from Spec 027 mailbox).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

__all__ = [
    "AuthenticatorAssuranceLevel",
    "CURRENT_CONSENT_VERSION",
    "PIPAConsentRecord",
    "latest_consent",
    "write_consent_atomic",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias — shared by Spec 033 permission records (inline Literal)
# ---------------------------------------------------------------------------

AuthenticatorAssuranceLevel = Literal["AAL1", "AAL2", "AAL3"]

# ---------------------------------------------------------------------------
# Version constant (bumping invalidates all prior records)
# ---------------------------------------------------------------------------

CURRENT_CONSENT_VERSION = "v1"


class PIPAConsentRecord(BaseModel):
    """Append-only PIPA consent record (contracts/memdir-consent-schema.md § 1-§ 2)."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    consent_version: str = Field(pattern=r"^v\d+$")
    timestamp: datetime
    aal_gate: AuthenticatorAssuranceLevel
    session_id: UUID
    citizen_confirmed: Literal[True]
    schema_version: Literal["1"] = "1"

    @field_validator("timestamp")
    @classmethod
    def _enforce_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("PIPAConsentRecord.timestamp must be timezone-aware UTC")
        return value


# ---------------------------------------------------------------------------
# File-name + storage
# ---------------------------------------------------------------------------


def _record_filename(record: PIPAConsentRecord) -> str:
    """Derives the append-only filename:

        <iso8601-utc-colons-as-dashes>-<session_uuidv7>.json

    Matches contract § 4 pattern.  Example:
        2026-04-20T14-32-05Z-018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60.json
    """
    ts_iso = record.timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    return f"{ts_iso}-{record.session_id}.json"


def write_consent_atomic(record: PIPAConsentRecord, base: Path) -> Path:
    """Atomically write `record` to `base` (creates the dir if missing).

    Sequence: serialize → write tmp → fsync → os.rename → return final path.
    Raises `OSError` on filesystem failures (caller handles user-visible
    Korean error rendering per contract § 4 sidenote).
    """
    base.mkdir(parents=True, exist_ok=True)
    filename = _record_filename(record)
    final_path = base / filename
    tmp_path = final_path.with_suffix(".json.tmp")
    payload = record.model_dump_json()

    fd = os.open(
        tmp_path,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
        0o600,
    )
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(tmp_path, final_path)
    return final_path


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


def latest_consent(base: Path) -> PIPAConsentRecord | None:
    """Return the most recent valid PIPAConsentRecord under `base`.

    Scans descending filename order (filenames are UTC-timestamp-prefixed so
    lexicographic sort == chronological sort).  Skips records that fail
    validation (corrupt on disk) per contract § 5; never repairs them.
    Fails-closed on filesystem errors (broken symlink, permission-denied).
    """
    if not base.exists():
        return None
    try:
        candidates = sorted(base.glob("*.json"), reverse=True)
    except OSError:
        logger.debug("latest_consent: unable to enumerate %s", base, exc_info=True)
        return None
    for path in candidates:
        try:
            raw = path.read_text(encoding="utf-8")
            return PIPAConsentRecord.model_validate_json(raw)
        except (ValidationError, OSError, json.JSONDecodeError):
            logger.debug("skipping unreadable consent record: %s", path)
            continue
    return None
