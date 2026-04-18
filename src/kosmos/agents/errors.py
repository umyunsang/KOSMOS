# SPDX-License-Identifier: Apache-2.0
"""Agent exception hierarchy for the Agent Swarm Core (Layer 4).

All exceptions are raised with structured messages so callers can log
or convert them without string parsing.

FR traces: Edge Cases + FR-021 + FR-026 (data-model.md §6).
"""

from __future__ import annotations


class AgentConfigurationError(ValueError):
    """AgentContext rejected at spawn — e.g., empty specialist_role,
    tool registry containing tools other than lookup/resolve_location.

    This is a programmer error; it indicates the coordinator was called
    with invalid parameters and MUST NOT be caught silently.
    """


class AgentIsolationViolationError(RuntimeError):
    """Detected an attempt to mutate state shared across workers.

    Raised by the coordinator when it detects that a worker is trying to
    share mutable state with another worker. All workers MUST receive
    isolated AgentContext objects (FR-002).
    """


class MailboxOverflowError(RuntimeError):
    """Per-session mailbox message cap exceeded (FR-021).

    Raised immediately when a send() call would push the per-session
    message count above KOSMOS_AGENT_MAILBOX_MAX_MESSAGES. No retry,
    no silent drop.
    """


class MailboxWriteError(IOError):
    """Filesystem unwritable, fsync failed, or mailbox root uninitialisable.

    Raised immediately — the FileMailbox MUST NOT retry or silently
    discard messages. The caller (Coordinator or Worker) decides what to do.
    """


class PermissionDeniedError(RuntimeError):
    """Raised inside the worker when ConsentGateway returns False.

    Caught by Worker.run() and converted into an `error` message to the
    coordinator (FR-026). Not propagated to the outer caller.
    """
