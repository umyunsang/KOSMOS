# SPDX-License-Identifier: Apache-2.0
"""Root test configuration — live marker skip logic.

Ensures ``@pytest.mark.live`` tests are skipped by default and only run
when explicitly selected via ``pytest -m live``.
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip live-marked tests unless ``-m live`` is explicitly passed."""
    marker_expr = str(config.getoption("-m", default=""))
    # Require explicit `-m live` or `-m "live and ..."` to run live tests.
    # Reject expressions like `-m "not live"` that merely mention the word.
    explicitly_selected = marker_expr.strip() == "live" or marker_expr.strip().startswith("live ")
    if not explicitly_selected:
        skip_live = pytest.mark.skip(reason="live tests require -m live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)
