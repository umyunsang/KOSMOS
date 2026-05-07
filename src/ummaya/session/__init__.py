# SPDX-License-Identifier: Apache-2.0
"""UMMAYA session persistence package.

Provides append-only JSONL session storage and a high-level
:class:`~ummaya.session.manager.SessionManager` for REPL integration.

Typical usage::

    from ummaya.session import SessionManager, SessionMetadata, SessionEntry

    manager = SessionManager()
    metadata = await manager.new_session()

Public API
----------
.. autosummary::

   SessionMetadata
   SessionEntry
   SessionManager
"""

from __future__ import annotations

from ummaya.session.manager import SessionManager, auto_title
from ummaya.session.models import SessionEntry, SessionMetadata
from ummaya.session.store import (
    create_session,
    delete_session,
    get_session_metadata,
    list_sessions,
    load_session,
    save_entry,
    update_session_metadata,
)

__all__ = [
    "SessionEntry",
    "SessionManager",
    "SessionMetadata",
    "auto_title",
    "create_session",
    "delete_session",
    "get_session_metadata",
    "list_sessions",
    "load_session",
    "save_entry",
    "update_session_metadata",
]
