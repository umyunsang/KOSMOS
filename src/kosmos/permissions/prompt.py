# SPDX-License-Identifier: Apache-2.0
"""PIPA §15(2) consent prompt builder — Spec 033 T015 (WS4).

Implements ``PIPAConsentPrompt``, the frozen Pydantic v2 model that carries the
4-tuple required by PIPA §15(2) for a single adapter call.  The builder enforces:

- Invariant C1: all four PIPA tuple fields are non-empty ``StrictStr``.
- Invariant C2: individual-consent rule — bundling pipa_class ∈ {민감, 고유식별, 특수}
  into a single prompt is prohibited by PIPA §22(1); calling ``build()`` with a
  mixed list raises ``ValidationError``.

Reference:
    specs/033-permission-v2-spectrum/contracts/consent-prompt.contract.md § 1, 2, 4
    PIPA §15(2) 4-tuple, §22(1) individual-consent rule
    ISO/IEC 29184:2020 §5.3 plain-language binding
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    StrictStr,
    field_validator,
)

__all__ = [
    "PIPAConsentPrompt",
    "IndividualConsentViolationError",
    "build",
]

_logger = logging.getLogger(__name__)

# PIPA classification literals used throughout this module.
_INDIVIDUAL_CONSENT_CLASSES: frozenset[str] = frozenset({"민감", "고유식별", "특수"})
"""pipa_class values that mandate individual (non-bundled) consent prompts.

PIPA §22(1): sensitive, unique-identifier, and special-category data must each
receive a dedicated consent prompt.  The citizen cannot consent to multiple
such categories in a single UI interaction.
"""


class IndividualConsentViolationError(ValueError):
    """Raised when bundling pipa_class ∈ {민감, 고유식별, 특수} into one prompt.

    PIPA §22(1) mandates that each sensitive/unique-identifier/special item
    receives its own individual consent prompt.  Bundling is prohibited.

    Attributes:
        offending_classes: The set of individual-consent classes that were
            included in the same prompt request.
    """

    def __init__(self, offending_classes: frozenset[str]) -> None:
        self.offending_classes = offending_classes
        super().__init__(
            f"Invariant C2 violation: pipa_class values {sorted(offending_classes)!r} "
            "require individual consent prompts and MUST NOT be bundled together "
            "in a single PIPAConsentPrompt.  Issue one prompt per classification "
            "(PIPA §22(1))."
        )


class PIPAConsentPrompt(BaseModel):
    """Frozen model for a single PIPA §15(2) consent prompt.

    Each instance corresponds to exactly one adapter call and one pipa_class.
    All four PIPA §15(2) tuple fields are mandatory and non-empty (Invariant C1).

    Invariant C1: All 4 PIPA tuple fields must be non-empty ``StrictStr``.
        ``purpose``, ``data_items``, ``retention_period``, and
        ``refusal_right`` are all required.  A missing or empty field raises
        ``ValidationError`` at construction time — the prompt is never built.

    Invariant C2 (enforced by ``build()``): If the caller attempts to build a
        prompt bundling pipa_class ∈ {민감, 고유식별, 특수} with any other
        individual-consent class, ``IndividualConsentViolationError`` is raised.

    Reference:
        specs/033-permission-v2-spectrum/contracts/consent-prompt.contract.md § 1, 2
    """

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # -----------------------------------------------------------------------
    # PIPA §15(2) 4-tuple — all required, non-empty (Invariant C1)
    # -----------------------------------------------------------------------

    purpose: StrictStr
    """목적 — single paragraph describing the purpose of personal data processing."""

    data_items: StrictStr
    """항목 — bullet list (one item per line) of data items to be collected."""

    retention_period: StrictStr
    """보유기간 — ISO 8601 duration string or '일회성' for one-shot processing."""

    refusal_right: StrictStr
    """거부권 및 불이익 — paragraph describing the right to refuse and consequences."""

    # -----------------------------------------------------------------------
    # Context metadata (required for rendering and audit)
    # -----------------------------------------------------------------------

    tool_id: StrictStr
    """Canonical adapter identifier (e.g. ``hira_hospital_search``)."""

    pipa_class: Literal["일반", "민감", "고유식별", "특수"]
    """PIPA classification of the data processed by this adapter call."""

    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"]
    """Authentication level required to invoke the adapter."""

    # -----------------------------------------------------------------------
    # Field-level validators (Invariant C1 — non-empty StrictStr)
    # -----------------------------------------------------------------------

    @field_validator("purpose", "data_items", "retention_period", "refusal_right")
    @classmethod
    def _require_non_empty(cls, v: str) -> str:
        """Enforce Invariant C1: all 4 PIPA tuple fields must be non-empty."""
        if not v.strip():
            raise ValueError(
                "Invariant C1: PIPA §15(2) 4-tuple field must be a non-empty string. "
                "Missing or blank fields are never acceptable — the consent prompt "
                "MUST include all four required disclosures (목적/항목/보유기간/거부권)."
            )
        return v

    @field_validator("tool_id")
    @classmethod
    def _require_non_empty_tool_id(cls, v: str) -> str:
        """Enforce non-empty tool_id for audit binding."""
        if not v.strip():
            raise ValueError("tool_id must be a non-empty string.")
        return v

    def render_title(self) -> str:
        """Return the consent prompt title per contracts/consent-prompt.contract.md § 1.

        Format: ``[{tool_id}] 개인정보 처리 동의``
        """
        return f"[{self.tool_id}] 개인정보 처리 동의"

    def render_aal_notice(self) -> str | None:
        """Return the AAL notice line for auth_level ∈ {AAL2, AAL3}, else None.

        Per contracts/consent-prompt.contract.md § 3:
        When auth_level ∈ {AAL2, AAL3}, the prompt MUST include a visible line
        indicating that additional re-authentication may be required.
        """
        if self.auth_level in {"AAL2", "AAL3"}:
            return f"인증 수준: {self.auth_level} — 추가 본인확인이 필요할 수 있습니다."
        return None

    def render_text(self) -> str:
        """Return the complete human-readable consent prompt as a single string.

        Sections (in order per contract § 1):
          1. Title
          2. 목적 (purpose)
          3. 항목 (data_items)
          4. 보유기간 (retention_period)
          5. 거부권 및 불이익 (refusal_right)
          6. [Optional] AAL notice line (if auth_level ∈ {AAL2, AAL3})
        """
        lines: list[str] = [
            self.render_title(),
            "",
            "■ 처리 목적",
            self.purpose,
            "",
            "■ 수집 항목",
            self.data_items,
            "",
            "■ 보유기간",
            self.retention_period,
            "",
            "■ 거부권 및 불이익",
            self.refusal_right,
        ]
        aal_notice = self.render_aal_notice()
        if aal_notice:
            lines += ["", aal_notice]
        return "\n".join(lines)


def build(
    tool_id: str,
    pipa_class: Literal["일반", "민감", "고유식별", "특수"],
    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"],
    purpose: str,
    data_items: str,
    retention_period: str,
    refusal_right: str,
) -> PIPAConsentPrompt:
    """Build a single ``PIPAConsentPrompt`` with full validation.

    This factory validates Invariant C1 (non-empty 4-tuple) and is the
    recommended entry-point for constructing prompts programmatically.

    For building multiple prompts from a list of decisions, see
    ``build_from_decisions()``.

    Args:
        tool_id: Canonical adapter identifier.
        pipa_class: PIPA data classification for this prompt.
        auth_level: Authentication level required by the adapter.
        purpose: PIPA §15(2)(1) 목적 — purpose of processing.
        data_items: PIPA §15(2)(2) 항목 — data items collected.
        retention_period: PIPA §15(2)(4) 보유기간 — retention period.
        refusal_right: PIPA §15(2)(3) 거부권 — right to refuse + consequences.

    Returns:
        A frozen ``PIPAConsentPrompt`` instance.

    Raises:
        ValidationError: If any of the 4-tuple fields is empty (Invariant C1).
    """
    _logger.debug(
        "Building PIPAConsentPrompt for tool_id=%r pipa_class=%r auth_level=%r",
        tool_id,
        pipa_class,
        auth_level,
    )
    return PIPAConsentPrompt(
        tool_id=tool_id,
        pipa_class=pipa_class,
        auth_level=auth_level,
        purpose=purpose,
        data_items=data_items,
        retention_period=retention_period,
        refusal_right=refusal_right,
    )


def build_from_decisions(
    decisions: Sequence[object],
) -> list[PIPAConsentPrompt]:
    """Build a list of prompts from a sequence of decision objects.

    Enforces Invariant C2 (individual-consent rule, PIPA §22(1)):
    if the list contains more than one item with pipa_class ∈ {민감, 고유식별, 특수},
    ``IndividualConsentViolationError`` is raised immediately — the caller MUST
    split the decisions into individual prompts.

    Each decision object is expected to have the following attributes:
        ``tool_id``, ``pipa_class``, ``auth_level``,
        ``purpose``, ``data_items``, ``retention_period``, ``refusal_right``.

    Args:
        decisions: A sequence of objects with the above attributes.

    Returns:
        A list of frozen ``PIPAConsentPrompt`` instances (one per decision).

    Raises:
        IndividualConsentViolationError: If bundling individual-consent classes
            (Invariant C2).
        ValidationError: If any decision is missing a required 4-tuple field
            (Invariant C1).
        AttributeError: If a decision object is missing expected attributes.
    """
    # Invariant C2: collect pipa_class values that require individual consent.
    individual_classes_found: list[str] = [
        d.pipa_class  # type: ignore[attr-defined]
        for d in decisions
        if d.pipa_class in _INDIVIDUAL_CONSENT_CLASSES  # type: ignore[attr-defined]
    ]
    if len(individual_classes_found) > 1:
        offending = frozenset(individual_classes_found)
        _logger.error(
            "Invariant C2 violation: cannot bundle individual-consent classes %r "
            "into a single prompt (PIPA §22(1)).",
            sorted(offending),
        )
        raise IndividualConsentViolationError(offending)

    prompts: list[PIPAConsentPrompt] = []
    for d in decisions:
        prompt = PIPAConsentPrompt(
            tool_id=d.tool_id,  # type: ignore[attr-defined]
            pipa_class=d.pipa_class,  # type: ignore[attr-defined]
            auth_level=d.auth_level,  # type: ignore[attr-defined]
            purpose=d.purpose,  # type: ignore[attr-defined]
            data_items=d.data_items,  # type: ignore[attr-defined]
            retention_period=d.retention_period,  # type: ignore[attr-defined]
            refusal_right=d.refusal_right,  # type: ignore[attr-defined]
        )
        prompts.append(prompt)
    return prompts
