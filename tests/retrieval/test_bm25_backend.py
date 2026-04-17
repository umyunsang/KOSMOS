# SPDX-License-Identifier: Apache-2.0
"""BM25Backend parity test — spec 026, FR-009, SC-004.

Guards the contract that ``BM25Backend.score()`` is a verbatim delegation to
the wrapped ``BM25Index.score()``: both objects are constructed from the same
corpus dict (4 seed adapters), and every query in the committed 30-query set
must produce byte-identical ``list[tuple[str, float]]`` output.

Adapter sourcing: delegates to ``kosmos.eval.retrieval._build_registry()``,
which registers each seed adapter individually (resilient to partial imports)
and returns a populated ``ToolRegistry``.  The corpus is extracted as
``{tool_id: search_hint}`` for the 4 canonical seed IDs.

Index ownership: two independent ``BM25Index`` instances share no state.
``BM25Backend`` wraps its own instance.  Equality is therefore semantic
(deterministic computation), not object-identity.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_QUERIES_PATH = Path(__file__).parent.parent.parent / "eval" / "retrieval_queries.yaml"

_SEED_TOOL_IDS: frozenset[str] = frozenset(
    {
        "koroad_accident_hazard_search",
        "kma_forecast_fetch",
        "hira_hospital_search",
        "nmc_emergency_search",
    }
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _load_queries() -> list[dict[str, Any]]:
    """Load the committed 30-query set from eval/retrieval_queries.yaml."""
    assert _QUERIES_PATH.exists(), f"Missing query file: {_QUERIES_PATH}"
    with _QUERIES_PATH.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    assert isinstance(data, dict) and "queries" in data, (
        f"Malformed YAML in {_QUERIES_PATH}: expected top-level 'queries' key"
    )
    return data["queries"]


def _build_seed_corpus() -> dict[str, str]:
    """Build {tool_id: search_hint} for the 4 canonical seed adapters.

    Delegates registry construction to the eval harness builder so adapter
    sourcing logic is DRY and resilient to import errors in one module.
    """
    from kosmos.eval.retrieval import _build_registry
    from kosmos.tools.registry import ToolRegistry

    registry, _ = _build_registry()
    assert isinstance(registry, ToolRegistry)

    corpus: dict[str, str] = {}
    for tool in registry.all_tools():
        if tool.id in _SEED_TOOL_IDS:
            corpus[tool.id] = tool.search_hint

    assert len(corpus) == len(_SEED_TOOL_IDS), (
        f"Expected {len(_SEED_TOOL_IDS)} seed adapters in corpus, "
        f"got {len(corpus)}: {sorted(corpus)} "
        f"(missing: {sorted(_SEED_TOOL_IDS - corpus.keys())})"
    )
    return corpus


# ---------------------------------------------------------------------------
# Parametrize over the 30-query set
# ---------------------------------------------------------------------------

_QUERIES = _load_queries()

# Build parametrize IDs from query text truncated to 40 chars for readability.
_QUERY_IDS = [f"{entry['id']}-{entry['query'][:40].replace(' ', '_')}" for entry in _QUERIES]


# ---------------------------------------------------------------------------
# Parity test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", _QUERIES, ids=_QUERY_IDS)
def test_bm25_backend_score_parity(entry: dict[str, Any]) -> None:
    """Assert BM25Backend.score() == BM25Index.score() for every query.

    Two independent BM25Index instances are built from the same corpus so the
    comparison is semantic equality (deterministic computation) rather than
    object identity. This is the stricter test: even if the wrapper were
    replaced by a non-delegating copy, numeric drift would surface here.
    """
    from kosmos.tools.bm25_index import BM25Index
    from kosmos.tools.retrieval.bm25_backend import BM25Backend

    corpus = _build_seed_corpus()
    query: str = entry["query"]

    # Two independent BM25Index instances — same corpus, no shared state.
    raw_index = BM25Index(corpus)
    wrapper = BM25Backend(BM25Index(corpus))

    raw_result: list[tuple[str, float]] = raw_index.score(query)
    wrapper_result: list[tuple[str, float]] = wrapper.score(query)

    assert raw_result == wrapper_result, (
        f"Score mismatch for query {entry['id']!r} ({query!r}):\n"
        f"  raw_index : {raw_result}\n"
        f"  bm25_backend: {wrapper_result}"
    )
