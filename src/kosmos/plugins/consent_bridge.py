# SPDX-License-Identifier: Apache-2.0
"""IPCConsentBridge — wraps the citizen consent IPC round-trip.

This module replaces ``installer.py:_default_consent_prompt`` (the
"deny by default" stub) at runtime. The bridge:

1. Accepts the same synchronous callable signature as
   :class:`kosmos.plugins.installer.ConsentPrompt` so :func:`install_plugin`
   keeps working unchanged.
2. Internally builds a :class:`~kosmos.ipc.frame_schema.PermissionRequestFrame`
   carrying the manifest's ``permission_layer`` + (when ``processes_pii``)
   the trustee org name + canonical PIPA SHA-256.
3. Awaits the citizen's :class:`~kosmos.ipc.frame_schema.PermissionResponseFrame`
   via :func:`asyncio.wait_for` with a 60-second budget.
4. Returns ``True`` on ``allow_once`` / ``allow_session`` / ``granted``,
   ``False`` on ``deny`` / ``denied`` / timeout.

Per Constitution §II — Fail-Closed Security: the timeout default is
denial; an in-flight install where the citizen walks away from the
prompt completes with ``exit_code=5`` rather than auto-granting.

Per Spec 1978 + Spec 033, ``_pending_perms`` is the existing global
correlation map at ``stdio.py:521``. The bridge writes the request
frame, registers a future against ``request_id``, awaits the future,
and pops it — regardless of outcome — so the map never leaks.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from kosmos.ipc.frame_schema import IPCFrame, PermissionRequestFrame

logger = logging.getLogger(__name__)


WriteFrameFn = Callable[[IPCFrame], Awaitable[None]]


# Default timeout: 60 s. Matches Spec 1978 _pending_perms wait_for budget
# at stdio.py:814 so citizens see uniform timeout semantics across in-tree
# adapter consents and plugin install consents.
DEFAULT_CONSENT_TIMEOUT_S: float = 60.0


def _utcnow_iso() -> str:
    return (
        datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.")
        + f"{datetime.now(tz=UTC).microsecond // 1000:03d}Z"
    )


class IPCConsentBridge:
    """Bridges installer.ConsentPrompt sync interface to async IPC round-trip.

    The class is callable; its ``__call__`` matches the
    :class:`kosmos.plugins.installer.ConsentPrompt` signature exactly:

        Callable[[CatalogEntry, CatalogVersion, PluginManifest], bool]

    Internal flow per ``__call__``:
      1. Generate a fresh ``request_id`` (UUIDv4 hex).
      2. Build a :class:`PermissionRequestFrame` with the manifest metadata.
      3. Create a future in ``_pending_perms`` keyed by ``request_id``.
      4. Schedule the frame write via ``asyncio.run_coroutine_threadsafe``
         (the bridge is invoked from a synchronous context — installer
         runs in an executor thread, see plugin_op_dispatcher.handle_install).
      5. ``concurrent.futures.Future.result(timeout=DEFAULT_CONSENT_TIMEOUT_S)``
         blocks until the matching :class:`PermissionResponseFrame` resolves
         the asyncio future.
      6. Map response decision to bool: granted/allow_once/allow_session →
         True; deny/denied/anything else → False.
      7. Pop the request_id from ``_pending_perms`` regardless of outcome.

    Constructor injection keeps the bridge testable: unit tests inject a
    mock ``write_frame`` and pre-populate ``pending_perms`` to drive the
    decision branches.
    """

    def __init__(
        self,
        *,
        write_frame: WriteFrameFn,
        pending_perms: dict[str, asyncio.Future[Any]],
        session_id: str,
        timeout_seconds: float = DEFAULT_CONSENT_TIMEOUT_S,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._write_frame = write_frame
        self._pending_perms = pending_perms
        self._session_id = session_id
        self._timeout_seconds = timeout_seconds
        # Cache the running loop at construction time so the sync __call__
        # path can dispatch coroutines back to the event loop without
        # re-resolving it from a different thread.
        try:
            self._loop = loop or asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

    def __call__(  # noqa: C901 — branch count reflects PIPA + layer + emit + await fan-out; splitting hurts readability
        self,
        entry: object,
        version: object,
        manifest: object,
    ) -> bool:
        """Synchronous consent prompt — emits IPC + awaits citizen reply.

        The ``entry`` / ``version`` / ``manifest`` parameters are typed
        loosely (``object``) to avoid an import-time cycle with
        ``installer.py``; the runtime objects are
        :class:`kosmos.plugins.installer.CatalogEntry` /
        :class:`CatalogVersion` and
        :class:`kosmos.plugins.manifest_schema.PluginManifest` respectively.
        """
        if self._loop is None:
            logger.warning(
                "IPCConsentBridge invoked without an event loop bound; "
                "denying consent for safety (this should never happen at "
                "runtime — check dispatcher boot wiring)."
            )
            return False

        plugin_id = getattr(manifest, "plugin_id", "unknown")
        version_str = getattr(version, "version", "0.0.0")
        permission_layer = int(getattr(manifest, "permission_layer", 1))
        processes_pii = bool(getattr(manifest, "processes_pii", False))

        # PIPA §26 metadata extraction — only attached when processes_pii is True
        # per FR-012. Inactive PII flag means the modal omits trustee fields.
        trustee_org_name: str | None = None
        ack_sha256: str | None = None
        if processes_pii:
            ack = getattr(manifest, "pipa_trustee_acknowledgment", None)
            if ack is not None:
                trustee_org_name = getattr(ack, "trustee_org_name", None)
                ack_sha256 = getattr(ack, "acknowledgment_sha256", None)

        request_id = str(uuid.uuid4())

        # Korean-primary description with English fallback; the modal
        # surfaces both per UI-C.1 + bilingual guideline.
        risk_level: str
        if permission_layer == 1:
            risk_level = "low"
        elif permission_layer == 2:
            risk_level = "medium"
        else:
            risk_level = "high"

        description_ko = (
            f"플러그인 설치 동의: {plugin_id} v{version_str}"
            f" · Layer {permission_layer}"
            + (f" · 수탁 기관: {trustee_org_name}" if trustee_org_name else "")
            + (f" · PIPA §26 ack-sha256: {ack_sha256[:16]}…" if ack_sha256 else "")
        )
        description_en = (
            f"Plugin install consent: {plugin_id} v{version_str}"
            f" · Layer {permission_layer}"
            + (f" · Trustee: {trustee_org_name}" if trustee_org_name else "")
            + (f" · PIPA §26 ack-sha256: {ack_sha256[:16]}…" if ack_sha256 else "")
        )

        request_frame = PermissionRequestFrame(
            session_id=self._session_id,
            correlation_id=request_id,
            role="backend",
            ts=_utcnow_iso(),
            kind="permission_request",
            request_id=request_id,
            worker_id="plugin_install_dispatcher",
            primitive_kind="submit",  # plugin install treated as submit-class
            description_ko=description_ko,
            description_en=description_en,
            risk_level=risk_level,  # type: ignore[arg-type]
        )

        # Register the asyncio future that will be resolved when the matching
        # permission_response arrives. The future creation MUST happen on
        # the event loop thread to avoid cross-thread future violations.
        async def _emit_and_await() -> bool:
            future: asyncio.Future[Any] = self._loop.create_future()  # type: ignore[union-attr]
            self._pending_perms[request_id] = future
            try:
                await self._write_frame(request_frame)
                response = await asyncio.wait_for(
                    future, timeout=self._timeout_seconds
                )
            except TimeoutError:
                logger.warning(
                    "IPCConsentBridge: 60s timeout awaiting permission_response "
                    "for plugin %s (request_id=%s) — denying",
                    plugin_id,
                    request_id,
                )
                return False
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "IPCConsentBridge: error awaiting permission_response: %s", exc
                )
                return False
            finally:
                self._pending_perms.pop(request_id, None)

            decision = getattr(response, "decision", None)
            return decision in ("granted", "allow_once", "allow_session")

        # Bridge sync → async. Schedule the coroutine on the cached loop and
        # block synchronously on the resulting concurrent future until it
        # resolves (either with bool or via the inner timeout/error fallback).
        future = asyncio.run_coroutine_threadsafe(_emit_and_await(), self._loop)
        try:
            # Add a small slack on top of the inner wait_for so the caller
            # never sees a TimeoutError leak from the concurrent future
            # itself; the async path has its own timeout that already
            # converted to bool.
            return future.result(timeout=self._timeout_seconds + 5.0)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "IPCConsentBridge: outer concurrent-future failed for plugin %s: %s",
                plugin_id,
                exc,
            )
            return False


__all__ = ["DEFAULT_CONSENT_TIMEOUT_S", "IPCConsentBridge"]
