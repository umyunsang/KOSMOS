# SPDX-License-Identifier: Apache-2.0
"""Ministry-scope acknowledgment record + atomic reader/writer.

Feature: Epic H #1302 (035-onboarding-brand-port), task T026.
Contract: specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md
Invariants: I-13, I-14, I-15, I-16.

The ministries frozenset is enforced to have exactly the four Phase 1
codes {KOROAD, KMA, HIRA, NMC} at both Pydantic validation time and at
CI-level (a registry-wide regression scan runs as part of the Brand
Guardian gate).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

__all__ = [
    "CURRENT_SCOPE_VERSION",
    "MINISTRY_CODES",
    "MinistryCode",
    "MinistryOptIn",
    "MinistryScopeAcknowledgment",
    "latest_scope",
    "write_scope_atomic",
]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Type alias + canonical roster (drives validator in `_check_four_unique`)
# ---------------------------------------------------------------------------

MinistryCode = Literal["KOROAD", "KMA", "HIRA", "NMC"]

MINISTRY_CODES: frozenset[MinistryCode] = frozenset(
    ("KOROAD", "KMA", "HIRA", "NMC")
)

CURRENT_SCOPE_VERSION = "v1"


class MinistryOptIn(BaseModel):
    """Citizen opt-in state for a single Phase 1 ministry."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ministry_code: MinistryCode
    opt_in: bool


class MinistryScopeAcknowledgment(BaseModel):
    """Append-only ministry-scope record (contract § 1-§ 2)."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    scope_version: str = Field(pattern=r"^v\d+$")
    timestamp: datetime
    session_id: UUID
    ministries: frozenset[MinistryOptIn]
    schema_version: Literal["1"] = "1"

    @field_validator("timestamp")
    @classmethod
    def _enforce_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(
            value
        ):
            raise ValueError(
                "MinistryScopeAcknowledgment.timestamp must be timezone-aware UTC"
            )
        return value

    @model_validator(mode="after")
    def _check_four_unique(self) -> MinistryScopeAcknowledgment:
        codes = {m.ministry_code for m in self.ministries}
        if codes != MINISTRY_CODES:
            raise ValueError(
                f"ministries must cover {sorted(MINISTRY_CODES)}, got {sorted(codes)}"
            )
        if len(self.ministries) != 4:
            raise ValueError(
                f"ministries must have exactly 4 entries, got {len(self.ministries)}"
            )
        return self


def opt_in_lookup(
    ack: MinistryScopeAcknowledgment,
    ministry: MinistryCode,
) -> bool:
    """Return the opt-in state for `ministry`; False when missing (fail-closed)."""
    for entry in ack.ministries:
        if entry.ministry_code == ministry:
            return entry.opt_in
    return False


# ---------------------------------------------------------------------------
# Atomic write + file naming (mirrors user_consent.py)
# ---------------------------------------------------------------------------


def _record_filename(record: MinistryScopeAcknowledgment) -> str:
    ts_iso = record.timestamp.astimezone(UTC).strftime(
        "%Y-%m-%dT%H-%M-%SZ"
    )
    return f"{ts_iso}-{record.session_id}.json"


def write_scope_atomic(
    record: MinistryScopeAcknowledgment,
    base: Path,
) -> Path:
    """Atomically write `record` to `base` (creates dir if missing)."""
    base.mkdir(parents=True, exist_ok=True)
    filename = _record_filename(record)
    final_path = base / filename
    tmp_path = final_path.with_suffix(".json.tmp")
    payload = record.model_dump_json()

    fd = os.open(
        tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600
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


def latest_scope(base: Path) -> MinistryScopeAcknowledgment | None:
    if not base.exists():
        return None
    try:
        candidates = sorted(base.glob("*.json"), reverse=True)
    except OSError:
        # Broken symlink, permission-denied, or raced-deletion of `base` —
        # fail-closed at the reader boundary so the caller sees `None` and
        # the router treats it as "no record" (refusal path).
        logger.debug("latest_scope: unable to enumerate %s", base, exc_info=True)
        return None
    for path in candidates:
        try:
            raw = path.read_text(encoding="utf-8")
            return MinistryScopeAcknowledgment.model_validate_json(raw)
        except (ValidationError, OSError, json.JSONDecodeError):
            logger.debug("skipping unreadable scope record: %s", path)
            continue
    return None
