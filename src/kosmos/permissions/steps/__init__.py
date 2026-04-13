# SPDX-License-Identifier: Apache-2.0
"""Permission pipeline step implementations."""

from kosmos.permissions.steps.refusal_circuit_breaker import (
    CONSECUTIVE_DENIAL_THRESHOLD,
    get_denial_count,
    record_denial,
    record_success,
)
from kosmos.permissions.steps.refusal_circuit_breaker import (
    reset_all as reset_circuit_breaker,
)
from kosmos.permissions.steps.step2_intent import check_intent, reset_call_tracking
from kosmos.permissions.steps.step3_params import PII_ACCEPTING_PARAMS, check_params
from kosmos.permissions.steps.step4_authn import (
    AUTH_LEVEL_ANONYMOUS,
    AUTH_LEVEL_BASIC,
    AUTH_LEVEL_VERIFIED,
    check_authn,
)
from kosmos.permissions.steps.step5_terms import (
    check_terms,
    clear_all_consent,
    grant_consent,
    revoke_consent,
)

__all__ = [
    # Step 2
    "check_intent",
    "reset_call_tracking",
    # Step 3
    "check_params",
    "PII_ACCEPTING_PARAMS",
    # Step 4
    "check_authn",
    "AUTH_LEVEL_ANONYMOUS",
    "AUTH_LEVEL_BASIC",
    "AUTH_LEVEL_VERIFIED",
    # Step 5
    "check_terms",
    "grant_consent",
    "revoke_consent",
    "clear_all_consent",
    # Circuit breaker
    "record_denial",
    "record_success",
    "get_denial_count",
    "reset_circuit_breaker",
    "CONSECUTIVE_DENIAL_THRESHOLD",
]
