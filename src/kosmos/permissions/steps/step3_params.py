# SPDX-License-Identifier: Apache-2.0
"""Step 3: Parameter inspection and Korean PII detection.

Scans all string-typed values in the tool's arguments_json for patterns that
match recognised personally identifiable information (PII) categories relevant
to Korean public-API usage.  If PII is detected in parameters that are *not*
explicitly declared as PII-accepting, the call is denied to prevent accidental
data leakage to government APIs.

Detected PII categories:
- 주민등록번호 (Resident Registration Number, RRN): ``\\d{6}-[1-4]\\d{6}``
- 전화번호 (Korean mobile phone): ``01[016789]-?\\d{3,4}-?\\d{4}``
- 이메일 (Email address)
- 여권번호 (Passport number): ``[A-Z]\\d{8}``
- 신용카드 (Credit card number): 16-digit with optional separators

The scanning is deliberately conservative: it matches patterns inside larger
strings as well as exact-match values (using ``re.search``).  False-positive
risk is low because these patterns are structurally distinctive.

Parameters explicitly listed in ``PII_ACCEPTING_PARAMS`` are excluded from
the scan — this allows tools that legitimately receive a phone number (e.g.,
an identity-verification tool) to pass through step 3.

All exceptions cause a fail-closed deny.
"""

from __future__ import annotations

import json
import logging
import re

from kosmos.permissions.models import (
    PermissionCheckRequest,
    PermissionDecision,
    PermissionStepResult,
)

logger = logging.getLogger(__name__)

_STEP = 3

# ---------------------------------------------------------------------------
# PII regex patterns
# ---------------------------------------------------------------------------

# Mapping of PII type label to compiled pattern.
# Patterns use re.search so they catch PII embedded inside longer strings.
_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "rrn": re.compile(r"\d{6}-[1-4]\d{6}"),
    "phone_kr": re.compile(r"01[016789]-?\d{3,4}-?\d{4}"),
    "email": re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "passport_kr": re.compile(r"[A-Z]\d{8}"),
    "credit_card": re.compile(r"\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}"),
}

# ---------------------------------------------------------------------------
# PII-accepting parameter names
# ---------------------------------------------------------------------------

# Parameter names that are explicitly declared as PII-accepting.  Tools that
# legitimately take these values (e.g., identity-verification endpoints) list
# the parameter names here so step 3 skips the scan for those keys.
# This set is intentionally conservative and kept small.
PII_ACCEPTING_PARAMS: frozenset[str] = frozenset(
    {
        "citizen_id",  # Citizen identifier field in personal-data tools
        "resident_number",  # RRN parameter for identity verification tools
        "phone_number",  # Explicit phone-number input fields
        "passport_number",  # Passport number for travel/identity APIs
    }
)


def _scan_value_for_pii(value: str) -> str | None:
    """Scan a single string value against all PII patterns.

    Returns the PII type label of the first match, or None if clean.
    """
    for pii_type, pattern in _PII_PATTERNS.items():
        if pattern.search(value):
            return pii_type
    return None


def _scan_args(args: dict[str, object]) -> tuple[str, str] | None:
    """Recursively scan all string values in *args* for PII.

    Args:
        args: Parsed JSON object of tool arguments.

    Returns:
        (param_path, pii_type) tuple on first hit, or None if clean.
        param_path is the dot-joined key path (e.g. ``"query"`` or
        ``"filter.value"``).
    """
    return _scan_dict(args, prefix="")


def _scan_dict(obj: dict[str, object], prefix: str) -> tuple[str, str] | None:
    for key, value in obj.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if full_key.split(".")[-1] in PII_ACCEPTING_PARAMS:
            continue
        hit = _scan_node(value, full_key)
        if hit:
            return hit
    return None


def _scan_node(value: object, path: str) -> tuple[str, str] | None:
    if isinstance(value, str):
        pii_type = _scan_value_for_pii(value)
        if pii_type:
            return (path, pii_type)
    elif isinstance(value, dict):
        return _scan_dict(value, path)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            hit = _scan_node(item, f"{path}[{i}]")
            if hit:
                return hit
    return None


# ---------------------------------------------------------------------------
# Main step function
# ---------------------------------------------------------------------------


def check_params(request: PermissionCheckRequest) -> PermissionStepResult:
    """Step 3: Scan tool arguments for PII patterns.

    Args:
        request: The permission check request.

    Returns:
        PermissionStepResult allow if no PII detected, deny otherwise.
    """
    try:
        try:
            args = json.loads(request.arguments_json)
        except json.JSONDecodeError:
            # Invalid JSON — intent step should have caught this, but
            # fail-closed here too.
            logger.warning(
                "Step %d: arguments_json is not valid JSON for tool %s",
                _STEP,
                request.tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="invalid_arguments_json",
            )

        if not isinstance(args, dict):
            # Non-object payloads cannot be scanned — deny to be safe.
            logger.warning(
                "Step %d: arguments_json is not an object for tool %s",
                _STEP,
                request.tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason="arguments_not_object",
            )

        hit = _scan_args(args)
        if hit is not None:
            param_path, pii_type = hit
            logger.warning(
                "Step %d: PII detected in parameter %r (type=%s) for tool %s — denying",
                _STEP,
                param_path,
                pii_type,
                request.tool_id,
            )
            return PermissionStepResult(
                decision=PermissionDecision.deny,
                step=_STEP,
                reason=f"pii_detected:{pii_type}",
            )

        logger.debug("Step %d: parameter scan clean for tool %s", _STEP, request.tool_id)
        return PermissionStepResult(decision=PermissionDecision.allow, step=_STEP)

    except Exception as exc:
        logger.exception(
            "Step %d: unexpected exception during parameter scan for tool %s: %s",
            _STEP,
            request.tool_id,
            exc,
        )
        return PermissionStepResult(
            decision=PermissionDecision.deny,
            step=_STEP,
            reason="internal_error",
        )
