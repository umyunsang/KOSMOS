# SPDX-License-Identifier: Apache-2.0
"""Quickstart Scenario C probe — upstream 429 throttle emission (Spec 032 T054).

Spec 032 ``quickstart.md § 3.1``::

    uv run python -m kosmos.ipc.demo.upstream_429_probe --retry-after 15

Drives ``BackpressureController.emit_upstream_429`` (FR-014..016) to produce one
``BackpressureSignalFrame`` with ``signal="throttle"`` and ``source="upstream_429"``.
The frame is:

1. Emitted as NDJSON on stdout for pipeline / `jq` inspection.
2. Mirrored to ``/tmp/backpressure-throttle.json`` (overridable via
   ``--fixture-path``) so the TUI ``hud_probe.ts`` companion can load the exact
   same bytes without re-running the backend.

Both sinks receive the identical JSON dict so that the TUI render path is
byte-equivalent to the pipe path (SC-004 invariant: two-hop equality).

This harness is **synthetic** — it does NOT perform a real HTTP request.
It validates the Retry-After parsing + HUD dual-locale copy end-to-end
through the production ``BackpressureController.emit_upstream_429`` code path.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from kosmos.ipc.backpressure import BackpressureController
from kosmos.ipc.envelope import emit_ndjson

logger = logging.getLogger(__name__)

_DEFAULT_FIXTURE_PATH = Path("/tmp/backpressure-throttle.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Spec 032 Scenario C synthetic upstream-429 probe",
    )
    parser.add_argument(
        "--session-id",
        default="s-demo",
        help="Session identifier stamped on the frame (default: s-demo).",
    )
    parser.add_argument(
        "--retry-after",
        type=int,
        default=15,
        help=(
            "Seconds value for the simulated Retry-After header "
            "(default: 15).  Clamped by the controller to [1, 900]."
        ),
    )
    parser.add_argument(
        "--queue-depth",
        type=int,
        default=0,
        help="Queue depth to report for HUD context (default: 0).",
    )
    parser.add_argument(
        "--fixture-path",
        type=Path,
        default=_DEFAULT_FIXTURE_PATH,
        help=(
            "Filesystem path the emitted frame is mirrored to (JSON dict, "
            "pretty-printed).  The TUI hud_probe.ts reads this fixture."
        ),
    )
    parser.add_argument(
        "--no-fixture",
        action="store_true",
        help="Skip the fixture-file mirror and only write NDJSON to stdout.",
    )
    args = parser.parse_args(argv)

    controller = BackpressureController(session_id=args.session_id)
    frame = controller.emit_upstream_429(
        retry_after_header=args.retry_after,
        queue_depth=args.queue_depth,
    )

    sys.stdout.write(emit_ndjson(frame))
    sys.stdout.flush()

    if not args.no_fixture:
        payload = frame.model_dump(mode="json", exclude_none=False)
        args.fixture_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
