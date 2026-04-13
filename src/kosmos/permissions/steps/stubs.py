# SPDX-License-Identifier: Apache-2.0
"""Steps 2-5: Re-exports from active step implementations.

This module previously contained pass-through stubs.  All four functions are
now backed by full implementations; this shim preserves the import path used
by pipeline.py and any external callers while the pipeline is updated to
import directly from the step modules.
"""

from __future__ import annotations

from kosmos.permissions.steps.step2_intent import check_intent as check_intent
from kosmos.permissions.steps.step3_params import check_params as check_params
from kosmos.permissions.steps.step4_authn import check_authn as check_authn
from kosmos.permissions.steps.step5_terms import check_terms as check_terms

__all__ = ["check_authn", "check_intent", "check_params", "check_terms"]
