# SPDX-License-Identifier: Apache-2.0
"""Degradation latch for fail-open dense → BM25 fallback (spec 026, FR-002).

FR-002 contract:
    When ``KOSMOS_RETRIEVAL_BACKEND`` is ``dense`` or ``hybrid`` and
    model load fails, the registry MUST degrade to pure BM25 and emit
    exactly one structured WARN log per degraded registry instance.

This module is a mutable latch, not a Pydantic model — zero
serialisation surface, zero public getters beyond
``has_emitted``/``record`` for test inspection.
"""

from __future__ import annotations

import logging


class DegradationRecord:
    """One-shot WARN latch per registry instance.

    The latch is private to a single ``ToolRegistry`` — it MUST NOT be
    shared across registries. Subsequent ``emit_if_needed`` calls are
    no-ops after the first emission so per-query spam is impossible.
    """

    __slots__ = ("_emitted", "_requested_backend", "_effective_backend", "_reason")

    def __init__(self) -> None:
        self._emitted: bool = False
        self._requested_backend: str | None = None
        self._effective_backend: str | None = None
        self._reason: str | None = None

    @property
    def has_emitted(self) -> bool:
        """Whether a degradation WARN has already been logged."""
        return self._emitted

    @property
    def record(self) -> tuple[str, str, str] | None:
        """Snapshot of the first degradation, for test inspection.

        Returns ``(requested_backend, effective_backend, reason)`` once
        ``emit_if_needed`` has fired, else ``None``.
        """
        if not self._emitted:
            return None
        assert self._requested_backend is not None
        assert self._effective_backend is not None
        assert self._reason is not None
        return (self._requested_backend, self._effective_backend, self._reason)

    def emit_if_needed(
        self,
        logger: logging.Logger,
        *,
        requested_backend: str,
        effective_backend: str,
        reason: str,
    ) -> None:
        """Emit the FR-002 WARN line exactly once per instance.

        Args:
            logger: Caller-owned ``logging.Logger``. Stdlib logging only
                per AGENTS.md hard rule.
            requested_backend: ``dense`` or ``hybrid`` — whatever the
                operator asked for via ``KOSMOS_RETRIEVAL_BACKEND``.
            effective_backend: Always ``bm25`` per FR-002 (pure BM25 is
                the regression safety net).
            reason: One-line machine-friendly cause (e.g.,
                ``"dense load failed: OSError"``).
        """
        if self._emitted:
            return

        self._emitted = True
        self._requested_backend = requested_backend
        self._effective_backend = effective_backend
        self._reason = reason

        logger.warning(
            "retrieval backend degraded: %s -> %s (%s)",
            requested_backend,
            effective_backend,
            reason,
            extra={
                "event": "retrieval.degraded",
                "requested_backend": requested_backend,
                "effective_backend": effective_backend,
                "reason": reason,
            },
        )
