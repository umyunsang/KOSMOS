# SPDX-License-Identifier: Apache-2.0
"""Append-only delegation event ledger — Epic ε #2296 extension to Spec 035.

This module extends the Spec 035 consent ledger (``user_consent.py``) with
three new JSONL event kinds for the delegation-token lifecycle:

- ``DelegationIssuedEvent`` — appended by verify adapters when a token is issued.
- ``DelegationUsedEvent``   — appended by submit/lookup adapters on each token use.
- ``DelegationRevokedEvent``— appended when a citizen revokes a token.

Storage layout (per Spec 035 + data-model.md § 6):
    ``~/.kosmos/memdir/user/consent/<YYYY-MM-DD>.jsonl``

Each append is ``open(path, "a") + json.dumps() + "\\n" + flush``.  WORM
semantics: lines are never edited or deleted.  No HMAC-chain required here —
this ledger is for operational audit, not for cryptographic proof (the Spec 033
HMAC ledger at ``~/.kosmos/consent_ledger.jsonl`` handles that).

Contract: specs/2296-ax-mock-adapters/contracts/delegation-token-envelope.md § 5
Data model: specs/2296-ax-mock-adapters/data-model.md § 6
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

# Default ledger root (can be overridden in tests via helper functions).
_DEFAULT_LEDGER_ROOT: Path = Path.home() / ".kosmos" / "memdir" / "user" / "consent"


# ---------------------------------------------------------------------------
# DelegationIssuedEvent  (data-model.md § 6.1)
# ---------------------------------------------------------------------------


class DelegationIssuedEvent(BaseModel):
    """Appended by verify adapters when a delegation token is issued."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    kind: Literal["delegation_issued"] = "delegation_issued"
    ts: datetime = Field(description="UTC tz-aware event time.")
    session_id: str = Field(min_length=1, description="Non-empty UUID of the issuing session.")
    delegation_token: str = Field(
        min_length=1,
        description="Opaque token value (matches DelegationToken.delegation_token).",
    )
    scope: str = Field(
        min_length=1,
        description="Comma-joined scope string (matches DelegationToken.scope).",
    )
    expires_at: datetime = Field(description="UTC tz-aware token expiry.")
    issuer_did: str = Field(
        min_length=1,
        description="DID of the issuing verify adapter.",
    )
    verify_tool_id: str = Field(
        min_length=1,
        description="tool_id of the issuing verify adapter.",
    )
    mode: Literal["mock"] = Field(
        default="mock",
        alias="_mode",
        description="Always 'mock' for Epic ε.",
    )


# ---------------------------------------------------------------------------
# DelegationUsedEvent  (data-model.md § 6.2)
# ---------------------------------------------------------------------------


class DelegationUsedEvent(BaseModel):
    """Appended by submit/lookup adapters on each token consumption attempt."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["delegation_used"] = "delegation_used"
    ts: datetime = Field(description="UTC tz-aware event time.")
    session_id: str = Field(min_length=1, description="Non-empty UUID of the consuming session.")
    delegation_token: str = Field(
        min_length=1,
        description="References the earlier DelegationIssuedEvent.delegation_token.",
    )
    consumer_tool_id: str = Field(
        min_length=1,
        description="tool_id of the submit/lookup adapter.",
    )
    receipt_id: str | None = Field(
        default=None,
        description=(
            "Populated when consumer is a submit adapter and the call succeeded; "
            "the synthetic 접수번호."
        ),
    )
    outcome: Literal["success", "scope_violation", "expired", "session_violation", "revoked"] = (
        Field(description="Resolution of the token validation.")
    )


# ---------------------------------------------------------------------------
# DelegationRevokedEvent  (data-model.md § 6.3)
# ---------------------------------------------------------------------------


class DelegationRevokedEvent(BaseModel):
    """Appended when a citizen revokes a delegation token."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["delegation_revoked"] = "delegation_revoked"
    ts: datetime = Field(description="UTC tz-aware event time.")
    session_id: str = Field(min_length=1, description="Non-empty UUID of the revoking session.")
    delegation_token: str = Field(
        min_length=1,
        description="References the earlier DelegationIssuedEvent.delegation_token.",
    )
    reason: Literal["citizen_request", "expired", "admin_intervention"] = Field(
        description="Cause of the revocation.",
    )


# ---------------------------------------------------------------------------
# DelegationLedgerEvent — discriminated union joining the three new event kinds
# ---------------------------------------------------------------------------

DelegationLedgerEvent = Annotated[
    DelegationIssuedEvent | DelegationUsedEvent | DelegationRevokedEvent,
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------


def _ledger_path(base: Path, ts: datetime) -> Path:
    """Derive the per-day JSONL file path from a UTC datetime."""
    date_str = ts.astimezone(UTC).strftime("%Y-%m-%d")
    return base / f"{date_str}.jsonl"


def _append_event(event: BaseModel, base: Path) -> Path:
    """Append one event as a JSONL line to the per-day ledger file.

    Creates the directory tree if needed.  Uses ``open("a")`` + ``flush`` +
    ``os.fsync`` for at-least-once durability semantics.

    Returns the path of the ledger file that was written.
    """
    ts: datetime = getattr(event, "ts", datetime.now(UTC))
    path = _ledger_path(base, ts)
    base.mkdir(parents=True, exist_ok=True)
    line = event.model_dump_json(by_alias=True) + "\n"
    # Open in append mode — WORM semantics; never rewrite.
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())
    logger.debug("consent_ledger: appended %s event to %s", event.kind, path)  # type: ignore[attr-defined]
    return path


# ---------------------------------------------------------------------------
# Public helper functions
# ---------------------------------------------------------------------------


def append_delegation_issued(
    event: DelegationIssuedEvent,
    *,
    ledger_root: Path | None = None,
) -> Path:
    """Append a ``delegation_issued`` event to the per-day JSONL ledger.

    Args:
        event: The fully-constructed ``DelegationIssuedEvent``.
        ledger_root: Override ledger directory (default: ``~/.kosmos/memdir/user/consent``).

    Returns:
        Path of the ledger file that was written to.
    """
    return _append_event(event, ledger_root or _DEFAULT_LEDGER_ROOT)


def append_delegation_used(
    event: DelegationUsedEvent,
    *,
    ledger_root: Path | None = None,
) -> Path:
    """Append a ``delegation_used`` event to the per-day JSONL ledger.

    Args:
        event: The fully-constructed ``DelegationUsedEvent``.
        ledger_root: Override ledger directory (default: ``~/.kosmos/memdir/user/consent``).

    Returns:
        Path of the ledger file that was written to.
    """
    return _append_event(event, ledger_root or _DEFAULT_LEDGER_ROOT)


def append_delegation_revoked(
    event: DelegationRevokedEvent,
    *,
    ledger_root: Path | None = None,
) -> Path:
    """Append a ``delegation_revoked`` event to the per-day JSONL ledger.

    Args:
        event: The fully-constructed ``DelegationRevokedEvent``.
        ledger_root: Override ledger directory (default: ``~/.kosmos/memdir/user/consent``).

    Returns:
        Path of the ledger file that was written to.
    """
    return _append_event(event, ledger_root or _DEFAULT_LEDGER_ROOT)


def read_delegation_events(
    *,
    ledger_root: Path | None = None,
    date: datetime | None = None,
) -> list[DelegationIssuedEvent | DelegationUsedEvent | DelegationRevokedEvent]:
    """Read all delegation events from a per-day JSONL ledger file.

    Silently skips lines that fail validation (corrupt records).

    Args:
        ledger_root: Override ledger directory (default: ``~/.kosmos/memdir/user/consent``).
        date: UTC date whose ledger file to read (default: today UTC).

    Returns:
        List of parsed delegation events in file order.
    """
    from pydantic import TypeAdapter

    _event_adapter: TypeAdapter[DelegationLedgerEvent] = TypeAdapter(DelegationLedgerEvent)

    root = ledger_root or _DEFAULT_LEDGER_ROOT
    target_date = date or datetime.now(UTC)
    path = _ledger_path(root, target_date)
    if not path.exists():
        return []

    events: list[DelegationIssuedEvent | DelegationUsedEvent | DelegationRevokedEvent] = []
    with open(path, encoding="utf-8") as fh:
        for line_no, raw_line in enumerate(fh, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                event = _event_adapter.validate_json(raw_line)
                events.append(event)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "consent_ledger: skipping malformed line %d in %s: %s",
                    line_no,
                    path,
                    exc,
                )
    return events


# ---------------------------------------------------------------------------
# LedgerReader implementation backed by this module
# ---------------------------------------------------------------------------


class FileLedgerReader:
    """Implements the ``LedgerReader`` protocol using the per-day JSONL ledger files.

    Used by ``validate_delegation`` in ``kosmos.primitives.delegation``.
    """

    def __init__(self, ledger_root: Path | None = None) -> None:
        self._ledger_root = ledger_root or _DEFAULT_LEDGER_ROOT

    async def find_issuance_session(self, delegation_token: str) -> str | None:
        """Return the session_id from the matching ``delegation_issued`` event.

        Scans today's ledger file; if not found, returns ``None``.
        (Full multi-day scan is deferred — see data-model.md § 9.1 footnote.)
        """
        events = read_delegation_events(ledger_root=self._ledger_root)
        for event in events:
            if (
                isinstance(event, DelegationIssuedEvent)
                and event.delegation_token == delegation_token
            ):
                return event.session_id
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "DelegationIssuedEvent",
    "DelegationLedgerEvent",
    "DelegationRevokedEvent",
    "DelegationUsedEvent",
    "FileLedgerReader",
    "append_delegation_issued",
    "append_delegation_revoked",
    "append_delegation_used",
    "read_delegation_events",
]
