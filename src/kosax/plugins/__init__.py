# SPDX-License-Identifier: Apache-2.0
"""KOSAX plugin DX module.

External developer contribution surface for KOSAX tool adapters.
Migration tree § L1-B B8 + Epic #1636.

Public re-exports kept intentionally minimal so the import surface
is a stable contract:

- ``PluginManifest`` — top-level Pydantic v2 manifest contract.
- ``PIPATrusteeAcknowledgment`` — nested PIPA §26 trustee block.
- ``CANONICAL_ACKNOWLEDGMENT_SHA256`` — derived constant; computed
  at import time from ``docs/plugins/security-review.md`` markers.
- Exception types from :mod:`kosax.plugins.exceptions`.
"""

from __future__ import annotations

from kosax.plugins.canonical_acknowledgment import (
    CANONICAL_ACKNOWLEDGMENT_SHA256,
    CANONICAL_ACKNOWLEDGMENT_TEXT,
)
from kosax.plugins.exceptions import (
    AcknowledgmentMismatchError,
    ManifestValidationError,
    PluginRegistrationError,
)
from kosax.plugins.manifest_schema import (
    AdapterRealDomainPolicy,
    PIPATrusteeAcknowledgment,
    PluginManifest,
)

__all__ = [
    "CANONICAL_ACKNOWLEDGMENT_SHA256",
    "CANONICAL_ACKNOWLEDGMENT_TEXT",
    "AdapterRealDomainPolicy",
    "AcknowledgmentMismatchError",
    "ManifestValidationError",
    "PIPATrusteeAcknowledgment",
    "PluginManifest",
    "PluginRegistrationError",
]
