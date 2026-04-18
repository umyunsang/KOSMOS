# SPDX-License-Identifier: Apache-2.0
"""kosmos.agents — Agent Swarm Core public API.

Spec: specs/027-agent-swarm-core/spec.md
Epic: #13
"""

from kosmos.agents.consent import AlwaysGrantConsentGateway, ConsentGateway
from kosmos.agents.context import AgentContext
from kosmos.agents.coordinator import Coordinator
from kosmos.agents.mailbox.file_mailbox import FileMailbox
from kosmos.agents.mailbox.messages import AgentMessage
from kosmos.agents.plan import CoordinatorPlan, PlanStep
from kosmos.agents.worker import Worker

__all__ = [
    "AgentContext",
    "AgentMessage",
    "AlwaysGrantConsentGateway",
    "ConsentGateway",
    "Coordinator",
    "CoordinatorPlan",
    "FileMailbox",
    "PlanStep",
    "Worker",
]
