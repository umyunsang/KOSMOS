# SPDX-License-Identifier: Apache-2.0
"""Shadow-eval battery for Epic #467 (spec 026-cicd-prompt-registry).

Implements FR-D01..FR-D06:
- FR-D01: CLI entry point via ``python -m tests.shadow_eval.battery``.
- FR-D02: Module-level ``_tracer`` attribute for monkeypatching in tests.
- FR-D03: Spans stamped with ``deployment.environment`` + ``kosmos.eval.input_id``.
- FR-D04: Twin-run principle — identical battery inputs across both environments.
- FR-D05: Network isolation — only the injected ``httpx.MockTransport`` is used.
- FR-D06: JSON artifact written to ``--out`` path with ``spans`` key.
"""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys
from typing import Any

import httpx
from opentelemetry import trace

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level tracer — tests monkeypatch this attribute.
# All span creation MUST go through this reference (not a closure-captured local).
# ---------------------------------------------------------------------------

_tracer = trace.get_tracer(__name__)

# ---------------------------------------------------------------------------
# Fixed battery inputs (FR-D03, FR-D04).
# The id set MUST be identical across both environment runs.
# ---------------------------------------------------------------------------

_BATTERY_INPUTS: tuple[dict[str, str], ...] = (
    {"id": "case-001", "prompt": "What is the nearest emergency room?"},
    {"id": "case-002", "prompt": "Show me accident hazard zones near Gangnam."},
)

# ---------------------------------------------------------------------------
# Public API
#
# ``run(...)`` is the synchronous primary entry point — it performs no awaitable
# work and returns a plain ``dict``.  ``run_async(...)`` is a thin coroutine
# wrapper for callers inside ``async def`` tests; it invokes ``run`` and returns
# the same dict.  Keeping the two APIs explicit avoids the earlier
# ``_AwaitableDict`` hack that conflated sync and async contracts.
# ---------------------------------------------------------------------------


def run(
    *,
    environment: str,
    transport: httpx.MockTransport | None = None,
    out: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Run the shadow-eval battery for *environment* and return the result dict.

    Parameters
    ----------
    environment:
        Either ``"main"`` (merge-base run) or ``"shadow"`` (PR-head run).
    transport:
        **Required.** An ``httpx.MockTransport`` used for every outbound HTTP
        request.  Passing ``None`` raises ``TypeError`` (FR-D05 fail-closed).
    out:
        Optional path to write the JSON artifact (FR-D06).

    Returns
    -------
    dict[str, Any]
        ``{"environment": ..., "spans": [...], "results": [...]}``.
    """
    if transport is None:
        raise TypeError(
            "transport is required — the shadow-eval battery must never use a live "
            "httpx client.  Pass an httpx.MockTransport to run()."
        )
    if environment not in ("main", "shadow"):
        raise ValueError(f"environment must be 'main' or 'shadow', got {environment!r}")

    span_records: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    for case in _BATTERY_INPUTS:
        with _tracer.start_as_current_span("battery.case") as span:
            span.set_attribute("deployment.environment", environment)
            span.set_attribute("kosmos.eval.input_id", case["id"])

            # All HTTP MUST go through the injected transport (FR-D05).
            with httpx.Client(transport=transport) as client:
                resp = client.post(
                    "https://mock.local/v1/chat/completions",
                    json={
                        "model": "kosmos-eval",
                        "messages": [{"role": "user", "content": case["prompt"]}],
                    },
                )

            status = resp.status_code
            results.append({"id": case["id"], "status": status})

            # Record span attributes for the JSON artifact (FR-D06).
            span_records.append(
                {
                    "name": "battery.case",
                    "attributes": {
                        "deployment.environment": environment,
                        "kosmos.eval.input_id": case["id"],
                    },
                }
            )

        logger.debug("battery case %s: status=%d env=%s", case["id"], status, environment)

    artifact: dict[str, Any] = {
        "environment": environment,
        "spans": span_records,
        "results": results,
    }

    if out is not None:
        out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug("battery artifact written to %s", out)

    return artifact


async def run_async(
    *,
    environment: str,
    transport: httpx.MockTransport | None = None,
    out: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Async wrapper around :func:`run` for ``async def`` test callers.

    The battery itself performs no I/O beyond the injected ``httpx.MockTransport``
    and therefore does not need to be genuinely asynchronous; this coroutine
    exists so ``await`` sites remain ergonomic without forcing sync callers to
    manage an event loop.
    """
    return run(environment=environment, transport=transport, out=out)


# ---------------------------------------------------------------------------
# CLI entry point (FR-D01)
# ---------------------------------------------------------------------------


def _main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m tests.shadow_eval.battery",
        description="Run the shadow-eval prompt battery for one deployment environment.",
    )
    parser.add_argument(
        "--environment",
        choices=["main", "shadow"],
        required=True,
        help="Deployment environment to tag spans with.",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        required=True,
        help="Path to write the JSON artifact.",
    )
    args = parser.parse_args(argv)

    # In CLI mode, fabricate a local mock transport so CI can invoke the module
    # without external injection.  No live network calls are made (FR-D05).
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "cli-mock",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    transport = httpx.MockTransport(_handler)
    result = run(environment=args.environment, transport=transport, out=args.out)
    logger.info(
        "battery complete: environment=%s cases=%d",
        args.environment,
        len(result.get("results", [])),
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
