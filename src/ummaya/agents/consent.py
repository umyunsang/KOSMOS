# SPDX-License-Identifier: Apache-2.0
"""ConsentGateway abstract base class and always-grant stub.

The ConsentGateway is the integration point between the coordinator and
the citizen consent mechanism. The real TUI integration is #287; this
module ships the stub used during development and testing (FR-027).

FR traces: FR-027, research.md D7 + C10.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class ConsentGateway(ABC):
    """Abstract interface for citizen consent prompting.

    The coordinator calls request_consent() when a worker has raised
    LookupError(reason="auth_required"). The real implementation (#287)
    renders a TUI prompt; the stub always grants.

    A single async method is the entire public contract so that the
    real TUI gateway can swap in without changing coordinator code.
    """

    @abstractmethod
    async def request_consent(self, tool_id: str, correlation_id: UUID) -> bool:
        """Prompt the citizen for consent to invoke a protected tool.

        Args:
            tool_id: The tool ID that requires auth (e.g. 'nmc_emergency_search').
            correlation_id: The correlation_id of the originating worker request.

        Returns:
            True if the citizen grants consent; False if denied.
        """


class AlwaysGrantConsentGateway(ConsentGateway):
    """Unconditional-grant stub for development and testing.

    WARNING: This implementation MUST NOT be used in production. The real
    TUI integration is Epic #287. Swap this out before any Phase 2 deploy.
    """

    async def request_consent(self, tool_id: str, correlation_id: UUID) -> bool:
        """Always return True — unconditional grant for testing purposes."""
        return True
