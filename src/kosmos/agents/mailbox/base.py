# SPDX-License-Identifier: Apache-2.0
"""Mailbox abstract base class for agent IPC.

The Mailbox interface is kept abstract so that a future Redis Streams
backend can be substituted without changing coordinator or worker code.
The FileMailbox is the Phase 2 concrete implementation.

FR traces: FR-014, FR-022, data-model.md §4.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from kosmos.agents.mailbox.messages import AgentMessage


class Mailbox(ABC):
    """Abstract interface for agent message delivery.

    All implementations MUST guarantee:
    - At-least-once delivery: send() MUST persist the message before returning.
    - Per-sender FIFO ordering within receive() and replay_unread().
    - Strict routing by recipient: messages MUST only be yielded to the
      declared recipient (FR-025 — lateral permission flow prevention).
    - Overflow at KOSMOS_AGENT_MAILBOX_MAX_MESSAGES with MailboxOverflowError.

    Phase 3 (Epic #21) will add a RedisStreamsMailbox that conforms to
    this same ABC without requiring coordinator/worker changes.
    """

    @abstractmethod
    async def send(self, message: AgentMessage) -> None:
        """Deliver a message with at-least-once guarantee.

        The send() call MUST NOT return until the message has been
        durably stored (fsync'd for file backend, acked for Redis).

        Raises:
            MailboxOverflowError: per-session message cap exceeded.
            MailboxWriteError: filesystem unwritable or fsync failed.
        """

    @abstractmethod
    def receive(self, recipient: str) -> AsyncIterator[AgentMessage]:
        """Yield messages addressed to recipient in per-sender FIFO order.

        Cross-sender ordering is unspecified. This method blocks
        indefinitely when no messages are pending — callers MUST use
        asyncio.wait_for() for timeouts.

        Only messages where message.recipient == recipient are yielded.
        """

    @abstractmethod
    def replay_unread(self, recipient: str) -> AsyncIterator[AgentMessage]:
        """On coordinator startup: yield unread messages from prior runs.

        Messages are marked consumed after successful processing so that
        subsequent replays do not re-emit them (FR-019). Corrupted or
        partially-written message files are skipped with a WARNING log
        and do not cause the replay to crash (FR-020).

        Only messages where message.recipient == recipient are yielded.
        """
