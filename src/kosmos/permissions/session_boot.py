# SPDX-License-Identifier: Apache-2.0
"""Session-restart behavior for the KOSMOS permission subsystem — Spec 033 T037.

Invariants enforced here:

M3 / PR1 (mode never persists)
    ``reset_session_state()`` always returns ``mode = "default"``.  The active
    ``PermissionMode`` is *never* stored in ``permissions.json`` and is
    therefore reset to ``default`` on every process restart.

FR-C02 (fail-closed on schema violation)
    If ``permissions.json`` fails schema validation (or has wrong permissions),
    ``SessionBootState.rules_loaded`` is ``False``, ``failed_reason`` carries
    the error description, and the caller receives an empty rule store.  The
    harness MUST fall back to ``default`` mode with prompt-always in this case.

User-scope retention
    ``user``-scope rules are loaded from disk (if the file is valid).
    ``session`` and ``project`` rules are always cleared on restart — they are
    in-memory only (Spec 033 FR-C01).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from kosmos.permissions.modes import PermissionMode
from kosmos.permissions.rules import RuleStore, RuleStorePermissionsError, RuleStoreSchemaError

__all__ = [
    "SessionBootState",
    "reset_session_state",
]

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SessionBootState — result of reset_session_state()
# ---------------------------------------------------------------------------


class SessionBootState(BaseModel):
    """Result returned by ``reset_session_state()``.

    Contains the freshly-loaded ``RuleStore`` and the mode to use for this
    session.  ``mode`` is always ``"default"`` (Invariant M3/PR1).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: PermissionMode = "default"
    """Active permission mode.  Always ``"default"`` on restart (M3/PR1)."""

    rule_store: RuleStore
    """Freshly initialised rule store.  May be empty on validation failure."""

    rules_loaded: bool
    """True when ``permissions.json`` was present and passed validation."""

    failed_reason: Annotated[str, Field(min_length=1)] | None = None
    """Human-readable failure reason when ``rules_loaded`` is False.
    ``None`` when ``rules_loaded`` is True."""

    user_rule_count: int = 0
    """Number of user-scope rules loaded from disk."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------
# reset_session_state — main entry point
# ---------------------------------------------------------------------------


def reset_session_state(store_path: Path) -> SessionBootState:
    """Reload the persistent rule store and reset the session mode to ``default``.

    Called at every process/session startup.  Implements Invariants M3/PR1
    and FR-C02.

    Behaviour:
    1. Instantiate a fresh ``RuleStore`` bound to *store_path*.
    2. Call ``RuleStore.load()`` to read and validate ``permissions.json``.
       - If the file is absent: ``rules_loaded=True`` (no error — empty store
         is valid first-run state).
       - If the file exists but has wrong mode: ``rules_loaded=False``,
         ``failed_reason`` carries the error.
       - If the file exists but fails schema validation: ``rules_loaded=False``,
         ``failed_reason`` carries the error.
    3. ``mode`` is ALWAYS ``"default"`` regardless of what was in the file
       (Invariant M3/PR1).

    Args:
        store_path: Absolute path to ``permissions.json``.

    Returns:
        A ``SessionBootState`` describing the boot outcome.  The caller MUST
        check ``rules_loaded`` and fall back to prompt-always if ``False``.
    """
    rule_store = RuleStore(store_path)

    try:
        rule_store.load()
    except RuleStorePermissionsError as exc:
        logger.warning("permissions.json has wrong mode — failing closed: %s", exc)
        return SessionBootState(
            mode="default",
            rule_store=rule_store,
            rules_loaded=False,
            failed_reason=str(exc),
            user_rule_count=0,
        )
    except RuleStoreSchemaError as exc:
        logger.warning("permissions.json failed schema validation — failing closed: %s", exc)
        return SessionBootState(
            mode="default",
            rule_store=rule_store,
            rules_loaded=False,
            failed_reason=str(exc),
            user_rule_count=0,
        )

    # Absent file is valid (first-run state); rules_loaded=True with 0 rules.
    user_count = len(rule_store.list_rules(scope="user"))
    logger.debug("Session boot: mode=default, rules_loaded=True, user_rule_count=%d", user_count)
    return SessionBootState(
        mode="default",
        rule_store=rule_store,
        rules_loaded=True,
        failed_reason=None,
        user_rule_count=user_count,
    )
