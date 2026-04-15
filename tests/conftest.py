# SPDX-License-Identifier: Apache-2.0
"""Root test configuration — live marker skip logic and .env loading.

Ensures ``@pytest.mark.live`` tests are skipped by default and only run
when explicitly selected via ``pytest -m live``. Also loads ``.env`` from
the repository root into ``os.environ`` so tool adapters that read env
vars via ``os.environ.get()`` (e.g. Kakao, data.go.kr) see the same
configuration the CLI entry point sees.
"""

from __future__ import annotations

import pytest

from kosmos._dotenv import load_repo_dotenv

load_repo_dotenv()


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
