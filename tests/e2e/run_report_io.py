# SPDX-License-Identifier: Apache-2.0
"""Run report I/O helper for spec 030 Scenario 1 E2E.

Provides ``dump_run_report`` — writes a RunReport to disk as JSON under
KOSMOS_E2E_DUMP_DIR when set, returns None otherwise.

Exit code semantics (contracts/scenario-runner-cli.md §2):
  - Non-writable dump_dir raises RuntimeError (exit code 3 semantics).
  - When dump_dir is None, returns None silently — CI default.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from tests.e2e.models import RunReport

logger = logging.getLogger(__name__)


def dump_run_report(report: RunReport, dump_dir: Path | None) -> Path | None:
    """Write a RunReport to disk as ``030-<scenario_id>-<unix_ms>.json``.

    Args:
        report: The fully populated RunReport to serialize.
        dump_dir: Target directory path.  When None, no-op — returns None.
                  When provided but non-writable, raises RuntimeError.

    Returns:
        The Path of the written file, or None when dump_dir is None.

    Raises:
        RuntimeError: When dump_dir is provided but cannot be written to
            (exit code 3 semantics per contracts/scenario-runner-cli.md §2).
    """
    if dump_dir is None:
        return None

    # Validate directory is writable before attempting the write
    if not dump_dir.exists():
        try:
            dump_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RuntimeError(
                f"dump_run_report: cannot create dump_dir {dump_dir!r}: {exc}"
            ) from exc

    if not dump_dir.is_dir():
        raise RuntimeError(
            f"dump_run_report: dump_dir {dump_dir!r} exists but is not a directory"
        )

    # Test write access via a temporary probe
    probe = dump_dir / ".write_probe"
    try:
        probe.touch()
        probe.unlink()
    except OSError as exc:
        raise RuntimeError(
            f"dump_run_report: dump_dir {dump_dir!r} is not writable: {exc}"
        ) from exc

    unix_ms = int(time.time() * 1000)
    filename = f"030-{report.scenario_id}-{unix_ms}.json"
    output_path = dump_dir / filename

    # JSON serialization via RunReport.model_dump_json() only — no bespoke encoders
    json_str = report.model_dump_json(indent=2)
    output_path.write_text(json_str, encoding="utf-8")

    logger.info("dump_run_report: wrote %s (%d bytes)", output_path, len(json_str))
    return output_path
