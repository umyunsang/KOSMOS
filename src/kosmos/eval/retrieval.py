# SPDX-License-Identifier: Apache-2.0
"""BM25 retrieval quality evaluation harness — T039.

CLI entry point::

    python -m kosmos.eval.retrieval eval/retrieval_queries.yaml

Loads the seed adapter registry, runs each query through lookup(mode="search"),
computes recall@1 and recall@5, and writes a JSON report to
.eval-artifacts/retrieval.json.

Exit codes:
    0 — pass  (recall@5 >= 0.80)
    1 — warn  (0.60 <= recall@5 < 0.80)
    2 — fail  (recall@5 < 0.60)

NOTE: As of Stage 2a, only ``koroad_accident_hazard_search`` is registered.
The other 3 seed adapters (kma_forecast_fetch, hira_hospital_search,
nmc_emergency_search) land in Stage 3.  When fewer than 4 adapters are
registered, recall@5 will be artificially high for queries targeting KOROAD
and zero for the others — the JSON report emits a WARN in that case.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report schema (Pydantic-free to avoid import overhead in a CLI entrypoint)
# ---------------------------------------------------------------------------

# The minimum number of distinct seed adapters we expect.
_EXPECTED_ADAPTER_COUNT = 4

# The adapter IDs that should be registered for a complete eval run.
_SEED_ADAPTER_IDS: frozenset[str] = frozenset(
    {
        "koroad_accident_hazard_search",
        "kma_forecast_fetch",
        "hira_hospital_search",
        "nmc_emergency_search",
    }
)


def _load_queries(yaml_path: Path) -> list[dict[str, Any]]:
    """Load and validate the queries YAML file.

    Args:
        yaml_path: Path to the retrieval_queries.yaml file.

    Returns:
        List of query dicts, each with 'id', 'query', 'expected_tool_id'.

    Raises:
        SystemExit: If the file is missing or malformed.
    """
    if not yaml_path.exists():
        logger.error("Queries file not found: %s", yaml_path)
        sys.exit(2)

    with yaml_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict) or "queries" not in data:
        logger.error("Invalid YAML structure in %s — expected top-level 'queries' key", yaml_path)
        sys.exit(2)

    queries: list[dict[str, Any]] = data["queries"]
    for entry in queries:
        if "query" not in entry or "expected_tool_id" not in entry:
            logger.error("Query entry missing required fields: %r", entry)
            sys.exit(2)

    return queries


def _build_registry() -> tuple[object, object]:
    """Build and populate the tool registry with the 4 seed adapters.

    Registers each seed adapter individually so the eval harness is resilient
    to partial registration (e.g., if one adapter module has import errors).
    This avoids calling ``register_all_tools()`` which may fail if geocoding
    or composite modules are not yet implemented.

    The 4 seed adapters are:
        - koroad_accident_hazard_search  (always available)
        - kma_forecast_fetch             (Stage 3)
        - hira_hospital_search           (Stage 3)
        - nmc_emergency_search           (Stage 2a stub)

    Returns:
        (registry, executor) tuple ready for search.
    """
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.registry import ToolRegistry

    registry = ToolRegistry()
    executor = ToolExecutor(registry)

    # Attempt to register each seed adapter; log warnings on failure.
    _try_register_adapter(
        "kosmos.tools.koroad.accident_hazard_search",
        "register",
        registry,
        executor,
        requires_executor=True,
    )
    _try_register_adapter(
        "kosmos.tools.kma.forecast_fetch",
        "register",
        registry,
        executor,
        requires_executor=False,
    )
    _try_register_adapter(
        "kosmos.tools.hira.hospital_search",
        "register",
        registry,
        executor,
        requires_executor=True,
    )
    _try_register_adapter(
        "kosmos.tools.nmc.emergency_search",
        "register",
        registry,
        executor,
        requires_executor=True,
    )

    return registry, executor


def _try_register_adapter(
    module_path: str,
    fn_name: str,
    registry: object,
    executor: object,
    requires_executor: bool,
) -> None:
    """Attempt to import and call a register function, logging on failure.

    Args:
        module_path: Dotted module path to import.
        fn_name: Name of the registration function in the module.
        registry: ToolRegistry instance.
        executor: ToolExecutor instance.
        requires_executor: If True, call register(registry, executor),
                           else call register(registry).
    """
    import importlib

    try:
        module = importlib.import_module(module_path)
        fn = getattr(module, fn_name)
        if requires_executor:
            fn(registry, executor)
        else:
            fn(registry)
        logger.info("Registered adapter from %s", module_path)
    except Exception as exc:
        logger.warning("Failed to register adapter from %s: %s", module_path, exc)


async def _run_query(
    query: str,
    registry: object,
    top_k: int = 5,
) -> list[str]:
    """Run a single BM25 search query and return ordered tool_id list.

    Args:
        query: Natural-language query string.
        registry: Populated ToolRegistry.
        top_k: Maximum number of results to fetch.

    Returns:
        Ordered list of tool_id strings (rank 1 first).
    """
    from kosmos.tools.lookup import lookup
    from kosmos.tools.models import LookupSearchInput

    inp = LookupSearchInput(mode="search", query=query, top_k=top_k)
    result = await lookup(inp, registry=registry)

    # lookup returns LookupSearchResult on search mode
    if hasattr(result, "candidates"):
        return [c.tool_id for c in result.candidates]
    return []


def _compute_recall(
    ranked: list[str],
    expected: str,
    at_k: int,
) -> int:
    """Return 1 if expected appears in the top-at_k of ranked, else 0."""
    return 1 if expected in ranked[:at_k] else 0


def _build_warnings(
    registry: object,
    missing_adapters: list[str],
) -> list[str]:
    """Build the warnings list for the JSON report.

    Args:
        registry: The populated ToolRegistry.
        missing_adapters: Seed adapter IDs that were not found in the registry.

    Returns:
        List of warning strings.
    """
    warnings: list[str] = []
    registry_size = len(registry)  # type: ignore[arg-type]

    if registry_size < _EXPECTED_ADAPTER_COUNT:
        warnings.append(
            f"Registry has {registry_size} adapter(s); expected {_EXPECTED_ADAPTER_COUNT}. "
            "recall@5 is artificially inflated for registered adapters and zero for "
            f"missing adapters: {missing_adapters}. "
            "Stage 3 will register the remaining adapters."
        )

    return warnings


async def _evaluate(
    queries: list[dict[str, Any]],
    registry: object,
) -> dict[str, Any]:
    """Run the full eval loop and return the report dict.

    Args:
        queries: Loaded query entries from the YAML file.
        registry: Populated ToolRegistry.

    Returns:
        Report dict matching the documented JSON schema.
    """
    total = len(queries)
    hits_at_1 = 0
    hits_at_5 = 0

    # Per-adapter tracking: {tool_id: {"total": int, "hits_at_1": int, "hits_at_5": int}}
    per_adapter: dict[str, dict[str, int]] = {}

    for entry in queries:
        query_str: str = entry["query"]
        expected_tool_id: str = entry["expected_tool_id"]

        ranked = await _run_query(query_str, registry, top_k=5)

        hit1 = _compute_recall(ranked, expected_tool_id, at_k=1)
        hit5 = _compute_recall(ranked, expected_tool_id, at_k=5)

        hits_at_1 += hit1
        hits_at_5 += hit5

        if expected_tool_id not in per_adapter:
            per_adapter[expected_tool_id] = {"total": 0, "hits_at_1": 0, "hits_at_5": 0}
        per_adapter[expected_tool_id]["total"] += 1
        per_adapter[expected_tool_id]["hits_at_1"] += hit1
        per_adapter[expected_tool_id]["hits_at_5"] += hit5

        query_id = entry.get("id", "?")
        logger.debug(
            "Query %s (%r): expected=%s ranked=%s hit@1=%d hit@5=%d",
            query_id,
            query_str[:40],
            expected_tool_id,
            ranked[:5],
            hit1,
            hit5,
        )

    recall_at_1 = hits_at_1 / total if total > 0 else 0.0
    recall_at_5 = hits_at_5 / total if total > 0 else 0.0

    # Check which seed adapters are missing from the registry
    registered_ids: set[str] = {t.id for t in registry.all_tools()}  # type: ignore[attr-defined]
    missing_adapters = sorted(_SEED_ADAPTER_IDS - registered_ids)

    # Compute per-adapter recall metrics
    per_adapter_report: dict[str, dict[str, object]] = {}
    for tool_id, counts in per_adapter.items():
        t = counts["total"]
        per_adapter_report[tool_id] = {
            "total_queries": t,
            "hits_at_1": counts["hits_at_1"],
            "hits_at_5": counts["hits_at_5"],
            "recall_at_1": counts["hits_at_1"] / t if t > 0 else 0.0,
            "recall_at_5": counts["hits_at_5"] / t if t > 0 else 0.0,
        }

    return {
        "total_queries": total,
        "recall_at_1": round(recall_at_1, 4),
        "recall_at_5": round(recall_at_5, 4),
        "per_adapter": per_adapter_report,
        "registry_size": len(registry),  # type: ignore[arg-type]
        "warnings": _build_warnings(registry, missing_adapters),
        "timestamp": datetime.now(UTC).isoformat(),
    }


def _write_report(report: dict[str, Any], output_path: Path) -> None:
    """Write the JSON report to output_path, creating parent dirs as needed."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    logger.info("Report written to %s", output_path)


def _exit_code(recall_at_5: float) -> int:
    """Compute exit code from recall@5 value.

    Returns:
        0 — pass  (>= 0.80)
        1 — warn  ([0.60, 0.80))
        2 — fail  (< 0.60)
    """
    if recall_at_5 >= 0.80:
        return 0
    if recall_at_5 >= 0.60:
        return 1
    return 2


def main(argv: list[str] | None = None) -> None:
    """CLI entry point for retrieval evaluation.

    Usage::

        python -m kosmos.eval.retrieval eval/retrieval_queries.yaml

    Args:
        argv: Argument list (default: sys.argv[1:]).
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    args = argv if argv is not None else sys.argv[1:]

    if not args:
        logger.error("Usage: python -m kosmos.eval.retrieval <queries.yaml>")
        sys.exit(2)

    queries_path = Path(args[0])
    output_path = Path(".eval-artifacts/retrieval.json")

    logger.info("Loading queries from %s", queries_path)
    queries = _load_queries(queries_path)
    logger.info("Loaded %d queries", len(queries))

    logger.info("Building tool registry...")
    registry, _ = _build_registry()
    logger.info("Registry size: %d adapters", len(registry))  # type: ignore[arg-type]

    logger.info("Running BM25 retrieval evaluation...")
    report = asyncio.run(_evaluate(queries, registry))

    _write_report(report, output_path)

    recall5 = report["recall_at_5"]
    recall1 = report["recall_at_1"]

    if report["warnings"]:
        for w in report["warnings"]:
            logger.warning("WARN: %s", w)

    code = _exit_code(float(recall5))
    status = {0: "PASS", 1: "WARN", 2: "FAIL"}[code]

    # Single-line stdout summary (only print() allowed per spec)
    print(  # noqa: T201
        f"[{status}] recall@5={recall5:.2%} recall@1={recall1:.2%} "
        f"total={report['total_queries']} registry={report['registry_size']}"
    )

    sys.exit(code)


if __name__ == "__main__":
    main()
