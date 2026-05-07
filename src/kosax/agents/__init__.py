# SPDX-License-Identifier: Apache-2.0
"""kosax.agents — Agent Swarm Core public API.

Spec: specs/027-agent-swarm-core/spec.md
Epic: #13
"""

from kosax.agents.consent import AlwaysGrantConsentGateway, ConsentGateway
from kosax.agents.context import AgentContext
from kosax.agents.coordinator import Coordinator
from kosax.agents.mailbox.file_mailbox import FileMailbox
from kosax.agents.mailbox.messages import AgentMessage
from kosax.agents.plan import CoordinatorPlan, PlanStep
from kosax.agents.worker import Worker

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
