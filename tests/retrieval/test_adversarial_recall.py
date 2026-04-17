# SPDX-License-Identifier: Apache-2.0
"""SC-002 adversarial recall gate (spec 026, T024).

Gated by ``@pytest.mark.live_embedder`` — skipped in CI because it
downloads / uses locally-cached HuggingFace model weights.

Operators run this locally::

    uv run pytest tests/retrieval/test_adversarial_recall.py -m live_embedder -v

Asserts:
    backend=hybrid recall@5 >= 0.80  (SC-002 pass threshold)
    backend=bm25   recall@5 <  0.50  (documents the lexical gap that
                                       motivates the dense addition)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_ADVERSARIAL_YAML = _REPO_ROOT / "eval" / "retrieval_queries_adversarial.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_adversarial_queries() -> list[dict]:
    """Load and return all adversarial query entries from the YAML file."""
    with _ADVERSARIAL_YAML.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data["queries"]


def _build_registry_with_backend(backend: str, monkeypatch: pytest.MonkeyPatch) -> object:
    """Build a fresh ToolRegistry with the given KOSMOS_RETRIEVAL_BACKEND."""
    monkeypatch.setenv("KOSMOS_RETRIEVAL_BACKEND", backend)

    # Import here (after env var is set) so the factory reads the new value.
    # We must rebuild the registry from scratch since the backend is baked in.
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.registry import ToolRegistry

    registry = ToolRegistry()
    executor = ToolExecutor(registry)

    # Register seed adapters.
    import importlib

    _adapters = [
        ("kosmos.tools.koroad.accident_hazard_search", "register", True),
        ("kosmos.tools.kma.forecast_fetch", "register", False),
        ("kosmos.tools.hira.hospital_search", "register", True),
        ("kosmos.tools.nmc.emergency_search", "register", True),
    ]
    for module_path, fn_name, requires_executor in _adapters:
        module = importlib.import_module(module_path)
        fn = getattr(module, fn_name)
        if requires_executor:
            fn(registry, executor)
        else:
            fn(registry)

    return registry


async def _run_queries(
    queries: list[dict],
    registry: object,
    top_k: int = 5,
) -> float:
    """Run all queries through the search path and compute recall@5."""
    from kosmos.tools.lookup import lookup
    from kosmos.tools.models import LookupSearchInput

    hits = 0
    for entry in queries:
        inp = LookupSearchInput(mode="search", query=entry["query"], top_k=top_k)
        result = await lookup(inp, registry=registry)

        ranked_ids = [c.tool_id for c in result.candidates] if hasattr(result, "candidates") else []

        if entry["expected_tool_id"] in ranked_ids[:top_k]:
            hits += 1

    return hits / len(queries) if queries else 0.0


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


@pytest.mark.live_embedder
class TestAdversarialRecall:
    """SC-002 gate: hybrid recall@5 >= 0.80, bm25 recall@5 < 0.50."""

    def test_hybrid_recall_at_5_meets_threshold(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Hybrid backend must achieve recall@5 >= 0.80 on the adversarial set."""
        queries = _load_adversarial_queries()
        registry = _build_registry_with_backend("hybrid", monkeypatch)

        recall = asyncio.run(_run_queries(queries, registry, top_k=5))

        assert recall >= 0.80, (
            f"hybrid recall@5={recall:.3f} is below the SC-002 threshold of 0.80.\n"
            f"Adversarial set size: {len(queries)}"
        )

    def test_bm25_recall_at_5_below_threshold(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """BM25 backend must have recall@5 < 0.50 on the adversarial set.

        This documents the lexical gap that motivates the dense addition.
        If BM25 suddenly passes most adversarial queries, it likely means
        the query set has been compromised by accidental token overlap.
        """
        queries = _load_adversarial_queries()
        registry = _build_registry_with_backend("bm25", monkeypatch)

        recall = asyncio.run(_run_queries(queries, registry, top_k=5))

        assert recall < 0.50, (
            f"bm25 recall@5={recall:.3f} is unexpectedly high (>= 0.50).\n"
            "This may indicate the adversarial queries accidentally share "
            "tokens with adapter search_hints. Run test_adversarial_overlap.py "
            "to diagnose overlap.\n"
            f"Adversarial set size: {len(queries)}"
        )
