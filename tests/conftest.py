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
    """Skip live-marked tests unless the corresponding marker is explicitly selected.

    Skips:
    - ``@pytest.mark.live``: requires explicit ``-m live``.
    - ``@pytest.mark.live_embedder``: requires explicit ``-m live_embedder``
      (downloads/uses HF model weights — NFR-NoNetAtRuntime, spec 026 T024).
    """
    marker_expr = str(config.getoption("-m", default=""))

    # ``live`` family
    live_selected = (
        marker_expr.strip() == "live"
        or marker_expr.strip().startswith("live ")
    )
    if not live_selected:
        skip_live = pytest.mark.skip(reason="live tests require -m live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)

    # ``live_embedder`` family (spec 026, NFR-NoNetAtRuntime)
    live_embedder_selected = (
        marker_expr.strip() == "live_embedder"
        or marker_expr.strip().startswith("live_embedder ")
    )
    if not live_embedder_selected:
        skip_embedder = pytest.mark.skip(
            reason="live_embedder tests require -m live_embedder (downloads HF weights)"
        )
        for item in items:
            if "live_embedder" in item.keywords:
                item.add_marker(skip_embedder)
