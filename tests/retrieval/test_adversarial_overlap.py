# SPDX-License-Identifier: Apache-2.0
"""Adversarial overlap CI check (spec 026, T019).

Loads eval/retrieval_queries_adversarial.yaml (created by T020) and asserts
that every query has zero kiwipiepy-token overlap with its target adapter's
search_hint. This is an author-time guard — it fails the build the moment
anyone adds a paraphrase query that accidentally shares a morpheme with the
target adapter's search_hint.

Uses the same kiwipiepy POS configuration (NNG/NNP/VV/VA/SL) as
src/kosmos/tools/tokenizer.py (via kosmos.tools.tokenizer.tokenize).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent.parent
_ADVERSARIAL_YAML = _REPO_ROOT / "eval" / "retrieval_queries_adversarial.yaml"


# ---------------------------------------------------------------------------
# Adapter search_hint lookup (read-only; no adapter body edits)
# ---------------------------------------------------------------------------


def _load_adapter_search_hints() -> dict[str, str]:
    """Return a dict mapping tool_id → search_hint for the 4 seed adapters.

    This deliberately imports the adapter modules and reads the GovAPITool
    instances rather than hard-coding the strings, so any future search_hint
    change automatically propagates to this check.
    """
    hints: dict[str, str] = {}

    try:
        from kosmos.tools.koroad.accident_hazard_search import KOROAD_ACCIDENT_HAZARD_SEARCH_TOOL

        hints[KOROAD_ACCIDENT_HAZARD_SEARCH_TOOL.id] = (
            KOROAD_ACCIDENT_HAZARD_SEARCH_TOOL.search_hint
        )
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"Failed to load koroad search_hint: {exc}")

    try:
        from kosmos.tools.kma.forecast_fetch import KMA_FORECAST_FETCH_TOOL

        hints[KMA_FORECAST_FETCH_TOOL.id] = KMA_FORECAST_FETCH_TOOL.search_hint
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"Failed to load kma search_hint: {exc}")

    try:
        from kosmos.tools.hira.hospital_search import HIRA_HOSPITAL_SEARCH_TOOL

        hints[HIRA_HOSPITAL_SEARCH_TOOL.id] = HIRA_HOSPITAL_SEARCH_TOOL.search_hint
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"Failed to load hira search_hint: {exc}")

    try:
        from kosmos.tools.nmc.emergency_search import NMC_EMERGENCY_SEARCH_TOOL

        hints[NMC_EMERGENCY_SEARCH_TOOL.id] = NMC_EMERGENCY_SEARCH_TOOL.search_hint
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"Failed to load nmc search_hint: {exc}")

    return hints


def _tokenize(text: str) -> frozenset[str]:
    """Tokenize text using the same kiwipiepy configuration as bm25_index.py."""
    from kosmos.tools.tokenizer import tokenize

    return frozenset(tokenize(text))


def _jaccard_overlap(set_a: frozenset[str], set_b: frozenset[str]) -> float:
    """Return |A ∩ B| / |A ∪ B|, or 0.0 when both sets are empty."""
    union = set_a | set_b
    if not union:
        return 0.0
    intersection = set_a & set_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestAdversarialOverlap:
    """Validate that every adversarial query has zero lexical overlap with its target adapter."""

    def test_adversarial_yaml_exists(self) -> None:
        """The adversarial YAML file must exist (created by T020)."""
        assert _ADVERSARIAL_YAML.exists(), (
            f"eval/retrieval_queries_adversarial.yaml not found at {_ADVERSARIAL_YAML}. "
            "T020 must create this file before T019 can pass."
        )

    def test_adversarial_yaml_has_minimum_queries(self) -> None:
        """The YAML must contain at least 20 queries (FR-012)."""
        if not _ADVERSARIAL_YAML.exists():
            pytest.skip("adversarial YAML not yet created (T020 pending)")

        with _ADVERSARIAL_YAML.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        queries = data.get("queries", [])
        assert len(queries) >= 20, (
            f"Expected >= 20 adversarial queries, got {len(queries)}. "
            "Add more entries to eval/retrieval_queries_adversarial.yaml."
        )

    @pytest.mark.parametrize(
        "entry",
        # Collect all entries at import time; skip parametrize if file absent.
        (
            yaml.safe_load(_ADVERSARIAL_YAML.read_text(encoding="utf-8"))["queries"]
            if _ADVERSARIAL_YAML.exists()
            else []
        ),
        ids=(
            [
                f"q{i}_{e.get('expected_tool_id', 'unknown')}"
                for i, e in enumerate(
                    yaml.safe_load(_ADVERSARIAL_YAML.read_text(encoding="utf-8"))["queries"]
                )
            ]
            if _ADVERSARIAL_YAML.exists()
            else []
        ),
    )
    def test_zero_token_overlap(self, entry: dict) -> None:
        """Each adversarial query must share no kiwipiepy tokens with its target search_hint."""
        query = entry["query"]
        expected_tool_id = entry["expected_tool_id"]

        adapter_hints = _load_adapter_search_hints()
        assert expected_tool_id in adapter_hints, (
            f"expected_tool_id={expected_tool_id!r} not found among "
            f"registered seed adapters: {sorted(adapter_hints.keys())}"
        )

        search_hint = adapter_hints[expected_tool_id]
        query_tokens = _tokenize(query)
        hint_tokens = _tokenize(search_hint)

        overlap = len(query_tokens & hint_tokens)
        assert overlap == 0, (
            f"Adversarial query {query!r} shares {overlap} token(s) "
            f"with search_hint of {expected_tool_id!r}.\n"
            f"  Query tokens : {sorted(query_tokens)}\n"
            f"  Hint tokens  : {sorted(hint_tokens)}\n"
            f"  Shared       : {sorted(query_tokens & hint_tokens)}\n"
            "Remove shared tokens from either the query or the search_hint."
        )

    def test_lexical_overlap_score_field_is_zero(self) -> None:
        """The lexical_overlap_score field in the YAML must be 0.0 for all entries."""
        if not _ADVERSARIAL_YAML.exists():
            pytest.skip("adversarial YAML not yet created (T020 pending)")

        with _ADVERSARIAL_YAML.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        for i, entry in enumerate(data.get("queries", [])):
            score = entry.get("lexical_overlap_score", None)
            assert score == 0.0, (
                f"Query entry {i} has lexical_overlap_score={score!r}; expected 0.0.\n"
                f"Entry: {entry}"
            )
