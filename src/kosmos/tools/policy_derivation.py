# SPDX-License-Identifier: Apache-2.0
"""Policy-derivation tables for AdapterRealDomainPolicy → Spec 024/025/1636 invariants.

Epic δ #2295 introduced ``AdapterRealDomainPolicy`` as the single permission
representation each adapter cites from agency-published policy. The previous
KOSMOS-invented per-adapter ``auth_level`` / ``pipa_class`` / ``is_irreversible``
fields are removed from adapter declarations.

Spec 024 / 025 / 1636 invariants still need values to enforce. This module is
the canonical bridge: ``citizen_facing_gate`` (5 enum) is mapped to the
infrastructure-level fields that the existing invariants consume.

Mapping table (binding contract — change requires ADR):

    citizen_facing_gate │ derived auth_level │ derived is_irreversible │ derived pipa_class default
    ────────────────────┼────────────────────┼─────────────────────────┼──────────────────────────
    "read-only"         │ "AAL1"             │ False                   │ "non_personal"
    "login"             │ "AAL2"             │ False                   │ "personal"
    "action"            │ "AAL2"             │ False                   │ "personal"
    "sign"              │ "AAL3"             │ True                    │ "personal"
    "submit"            │ "AAL3"             │ True                    │ "personal"

Rationale:
- ``read-only`` ⇒ AAL1 (citizen identity not required; serviceKey auth at infra)
  per NIST SP 800-63-4. Not ``public`` because the Spec 025 V1 invariant
  (``pipa_class != non_personal`` ⇒ ``auth_level != public``) makes ``public``
  unsafe whenever pipa_class is later overridden to something non-trivial.
- ``login`` / ``action`` ⇒ AAL2 (citizen identity verification required).
- ``sign`` / ``submit`` ⇒ AAL3 (digital signature or irreversible submission;
  highest assurance).
- ``is_irreversible=True`` only for ``sign`` and ``submit``. ``login`` and
  ``action`` are reversible by definition (citizen can re-do the action).
- ``pipa_class`` default is conservative: ``read-only`` defaults to
  ``non_personal`` (most read-only public APIs return aggregates / rosters);
  every other gate defaults to ``personal`` since citizen identity is involved.
  Adapters can override this default per their cited policy URL via the
  separate ``GovAPITool.pipa_class_override`` field (introduced for adapters
  whose published policy declares stricter classification).

References:
- ``AdapterRealDomainPolicy`` — ``src/kosmos/tools/models.py``
- Spec 024 ``ToolCallAuditRecord`` invariants — ``src/kosmos/security/audit.py``
- Spec 025 v6 ``compute_permission_tier`` — ``src/kosmos/tools/permissions.py``
- Spec 1636 plugin Q3 — ``src/kosmos/plugins/checks/q3_security.py``
"""

from __future__ import annotations

from typing import Final, Literal

CitizenFacingGate = Literal["read-only", "login", "action", "sign", "submit"]
AALLevel = Literal["public", "AAL1", "AAL2", "AAL3"]
PIPAClass = Literal["non_personal", "personal", "sensitive", "identifier"]


# Canonical lookup table — single source of truth. Update via ADR only.
_GATE_TO_AUTH_LEVEL: Final[dict[CitizenFacingGate, AALLevel]] = {
    "read-only": "AAL1",
    "login": "AAL2",
    "action": "AAL2",
    "sign": "AAL3",
    "submit": "AAL3",
}

_GATE_TO_IS_IRREVERSIBLE: Final[dict[CitizenFacingGate, bool]] = {
    "read-only": False,
    "login": False,
    "action": False,
    "sign": True,
    "submit": True,
}

_GATE_TO_PIPA_CLASS_DEFAULT: Final[dict[CitizenFacingGate, PIPAClass]] = {
    "read-only": "non_personal",
    "login": "personal",
    "action": "personal",
    "sign": "personal",
    "submit": "personal",
}


def derive_min_auth_level(gate: CitizenFacingGate) -> AALLevel:
    """Derive the minimum NIST SP 800-63-4 AAL required for *gate*.

    Args:
        gate: Citizen-facing gate category from AdapterRealDomainPolicy.

    Returns:
        AAL level (``"public"`` / ``"AAL1"`` / ``"AAL2"`` / ``"AAL3"``).

    Raises:
        KeyError: If *gate* is not in the canonical mapping (impossible
            in practice because Pydantic validates the Literal at construction).
    """
    return _GATE_TO_AUTH_LEVEL[gate]


def derive_is_irreversible(gate: CitizenFacingGate) -> bool:
    """Derive the irreversibility flag for *gate*.

    Args:
        gate: Citizen-facing gate category from AdapterRealDomainPolicy.

    Returns:
        ``True`` for ``sign`` and ``submit`` (the citizen cannot undo via a
        second tool call); ``False`` otherwise.
    """
    return _GATE_TO_IS_IRREVERSIBLE[gate]


def derive_pipa_class_default(gate: CitizenFacingGate) -> PIPAClass:
    """Derive the default PIPA classification for *gate*.

    Returns the conservative default. Adapters whose cited agency policy
    declares stricter classification (e.g., 민감 / 고유식별) override via
    the explicit ``GovAPITool.pipa_class_override`` field.

    Args:
        gate: Citizen-facing gate category from AdapterRealDomainPolicy.

    Returns:
        PIPA class (``"non_personal"`` / ``"personal"`` / ``"sensitive"`` /
        ``"identifier"``).
    """
    return _GATE_TO_PIPA_CLASS_DEFAULT[gate]


__all__ = [
    "AALLevel",
    "CitizenFacingGate",
    "PIPAClass",
    "derive_is_irreversible",
    "derive_min_auth_level",
    "derive_pipa_class_default",
]
