# SPDX-License-Identifier: Apache-2.0
"""Per-adapter retry policy registry.

Allows different tool adapters to be configured with independent retry
behaviour (e.g. a slow government API can tolerate more retries with longer
delays than a fast in-process cache lookup).
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class RetryPolicy(BaseModel):
    """Per-adapter retry configuration.

    Mirrors the shape of ``ToolRetryPolicy`` but is intentionally a separate
    type so that the registry can store a ``RetryPolicy`` without coupling to
    the retry loop implementation.
    """

    model_config = ConfigDict(frozen=True)

    max_retries: int = 3
    """Maximum number of retry attempts (not counting the initial attempt)."""

    base_delay: float = 1.0
    """Initial back-off delay in seconds before the first retry."""

    max_delay: float = 30.0
    """Upper bound on back-off delay in seconds."""

    exponential_base: float = 2.0
    """Multiplier applied on each successive retry (exponential back-off)."""

    retryable_status_codes: frozenset[int] = frozenset({429, 500, 502, 503, 504})
    """HTTP status codes that should be retried."""

    retry_on_timeout: bool = True
    """Whether network/service timeouts should be retried."""


class RetryPolicyRegistry:
    """Registry of per-adapter retry policies.

    Falls back to a default ``RetryPolicy`` when no tool-specific policy has
    been registered.  Policies are looked up by ``tool_id`` (the stable
    snake_case identifier on ``GovAPITool``).

    Usage::

        registry = RetryPolicyRegistry()
        registry.register("koroad_accident_search", RetryPolicy(max_retries=5))
        policy = registry.get("koroad_accident_search")
    """

    def __init__(self, default: RetryPolicy | None = None) -> None:
        self._policies: dict[str, RetryPolicy] = {}
        self._default = default or RetryPolicy()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, tool_id: str, policy: RetryPolicy) -> None:
        """Register a retry policy for *tool_id*.

        Registering a second policy for the same ``tool_id`` overwrites the
        previous entry.

        Args:
            tool_id: Stable snake_case tool identifier.
            policy: The ``RetryPolicy`` to apply when this tool is called.
        """
        self._policies[tool_id] = policy
        logger.debug("Registered retry policy for tool %s: %r", tool_id, policy)

    def get(self, tool_id: str) -> RetryPolicy:
        """Return the retry policy for *tool_id*.

        Returns the tool-specific policy if one has been registered, otherwise
        the default policy supplied at construction time.

        Args:
            tool_id: Stable snake_case tool identifier.

        Returns:
            The ``RetryPolicy`` to use for this tool.
        """
        policy = self._policies.get(tool_id, self._default)
        if tool_id not in self._policies:
            logger.debug("No policy for tool %s — using default", tool_id)
        return policy

    @property
    def default(self) -> RetryPolicy:
        """The default ``RetryPolicy`` used when no per-tool policy is registered."""
        return self._default
