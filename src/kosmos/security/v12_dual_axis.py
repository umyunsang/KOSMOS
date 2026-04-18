# SPDX-License-Identifier: Apache-2.0
"""v1.2 GA dual-axis auth backstop (T012).

Spec 031 § 6 layers the 18-label Korea-published tier (primary axis) over the
NIST AAL1/2/3 advisory hint (secondary axis). During the pre-v1.2 compatibility
window (FR-028), ``AdapterRegistration`` accepts ``published_tier_minimum=None``
and ``nist_aal_hint=None`` so the existing Spec 022 adapters (lookup /
resolve_location) keep registering unchanged.

When v1.2 GA ships, flipping :data:`V12_GA_ACTIVE` to ``True`` enables
:func:`enforce`: it raises ``RegistrationError`` at registry.register() time for
any adapter that still ships either field as ``None`` (FR-030).

This module is intentionally side-effect free; the toggle lives in code so that
v1.2 GA is a one-line review-gated change, not an env-var flip.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from kosmos.tools.errors import RegistrationError

if TYPE_CHECKING:
    from kosmos.tools.registry import AdapterRegistration


V12_GA_ACTIVE: bool = False
"""Master toggle for the v1.2 GA dual-axis backstop.

Stays ``False`` throughout the pre-v1.2 compatibility window. When the v1.2
cutover PR lands, this flips to ``True`` and :func:`enforce` begins rejecting
adapters that omit either axis of the dual-axis auth contract.
"""


def enforce(registration: AdapterRegistration) -> None:
    """Reject registrations that violate the v1.2 GA dual-axis invariant.

    No-op while :data:`V12_GA_ACTIVE` is ``False``. When the toggle flips,
    both ``published_tier_minimum`` and ``nist_aal_hint`` MUST be non-None per
    FR-030.

    Args:
        registration: The adapter registration about to be accepted.

    Raises:
        RegistrationError: If the v1.2 GA toggle is active and either axis of
            the dual-axis auth contract is still ``None``.
    """
    if not V12_GA_ACTIVE:
        return

    missing: list[str] = []
    if registration.published_tier_minimum is None:
        missing.append("published_tier_minimum")
    if registration.nist_aal_hint is None:
        missing.append("nist_aal_hint")

    if missing:
        raise RegistrationError(
            registration.tool_id,
            (
                "v1.2 GA dual-axis violation (FR-030): "
                f"required field(s) missing: {', '.join(missing)}. "
                "Both axes become mandatory once V12_GA_ACTIVE=True."
            ),
        )


__all__ = ["V12_GA_ACTIVE", "enforce"]
