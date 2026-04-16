# SPDX-License-Identifier: Apache-2.0
"""Envelope normalizer for ``lookup(mode='fetch')`` responses.

Every adapter handler output MUST pass through ``normalize()`` before being
returned to the model.  ``normalize()`` validates the output against the
frozen 5-variant ``LookupOutput`` discriminated union, injects the ``meta``
block, and raises EnvelopeNormalizationError on discriminator mismatches.

FR-014: Inject ``meta.source``, ``meta.fetched_at``, ``meta.request_id``,
        ``meta.elapsed_ms`` on every envelope.
FR-015: Reject discriminator mismatches with ``EnvelopeNormalizationError``.
FR-017: Catch handler exceptions and convert to ``LookupError`` — implemented
        in ``ToolExecutor.invoke()``, not here.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

from kosmos.tools.errors import EnvelopeNormalizationError, LookupErrorReason
from kosmos.tools.models import (
    LookupError as LookupErrorModel,
)
from kosmos.tools.models import (
    LookupMeta,
    LookupOutput,
)

if TYPE_CHECKING:
    from kosmos.tools.models import GovAPITool

logger = logging.getLogger(__name__)

# TypeAdapter for validating arbitrary dicts against LookupOutput.
_LOOKUP_OUTPUT_ADAPTER: TypeAdapter[object] = TypeAdapter(LookupOutput)


def normalize(
    output: object,
    tool: GovAPITool,
    request_id: str,
    elapsed_ms: int,
) -> object:
    """Validate and enrich a handler output into the LookupOutput envelope.

    Args:
        output: The raw return value from an adapter handler.  Expected to be
                a dict or a Pydantic model instance that matches one of the
                five LookupOutput variants.
        tool: The GovAPITool definition for the adapter that produced *output*.
        request_id: UUID string for this request (injected into meta).
        elapsed_ms: Elapsed time in milliseconds since the fetch started.

    Returns:
        A validated LookupOutput instance (one of the five variants).

    Raises:
        EnvelopeNormalizationError: When *output* does not match any variant of
            the frozen discriminated union (FR-015).
    """
    meta = LookupMeta(
        source=tool.id,
        fetched_at=datetime.now(tz=UTC),
        request_id=request_id,
        elapsed_ms=max(0, elapsed_ms),
    )

    # Convert Pydantic model → dict so TypeAdapter can work uniformly.
    if hasattr(output, "model_dump"):
        raw = output.model_dump()
    elif isinstance(output, dict):
        raw = output
    else:
        raise EnvelopeNormalizationError(
            tool.id,
            f"handler returned unexpected type {type(output).__name__!r}; "
            "expected dict or BaseModel",
        )

    # Always overwrite meta so that adapters cannot return stale or forged
    # meta values.
    if isinstance(raw, dict):
        raw = {**raw, "meta": meta.model_dump(mode="json")}

    try:
        validated = _LOOKUP_OUTPUT_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        raise EnvelopeNormalizationError(
            tool.id,
            f"LookupOutput validation failed: {exc}",
        ) from exc

    return validated


def make_error_envelope(
    tool_id: str,
    reason: LookupErrorReason,
    message: str,
    request_id: str,
    elapsed_ms: int,
    *,
    retryable: bool = False,
    upstream_code: str | None = None,
    upstream_message: str | None = None,
) -> LookupErrorModel:
    """Construct a ``LookupError`` envelope with a fully populated ``meta`` block.

    Used by the executor when a handler raises an exception (FR-017) or when
    the Layer 3 gate short-circuits before the handler is invoked (FR-025).
    """
    meta = LookupMeta(
        source=tool_id,
        fetched_at=datetime.now(tz=UTC),
        request_id=request_id,
        elapsed_ms=max(0, elapsed_ms),
    )
    return LookupErrorModel(
        kind="error",
        reason=reason,
        message=message,
        retryable=retryable,
        upstream_code=upstream_code,
        upstream_message=upstream_message,
        meta=meta,
    )
