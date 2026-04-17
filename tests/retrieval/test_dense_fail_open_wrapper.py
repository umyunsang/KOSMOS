# SPDX-License-Identifier: Apache-2.0
"""_DenseFailOpenWrapper lazy-path fail-open tests (spec 026, Codex round 5).

Guards the regression that motivated Codex P1 on #837:
when ``KOSMOS_RETRIEVAL_BACKEND=dense`` and cold-start is ``lazy`` (default),
a model-load failure at the first ``.score()`` call must degrade to the
BM25 companion — not silently return ``[]`` forever.

Contract:
1. First ``.score()`` after a lazy-load failure returns the BM25 ranking
   (never empty when the BM25 corpus is non-empty and the query matches).
2. Exactly one structured WARN with
       event             = "retrieval.degraded"
       requested_backend = "dense"
       effective_backend = "bm25"
   fires across the wrapper's lifetime (one-shot latch via
   ``DegradationRecord``).
3. After degradation, subsequent ``.score()`` calls short-circuit to
   BM25 without re-invoking the dense backend.

These tests DO NOT exercise the eager-mode path — that is covered by
``tests/retrieval/test_fail_open.py`` which verifies registry-level
fail-open before the wrapper's lazy latch can fire.
"""

from __future__ import annotations

import logging

import pytest

from kosmos.tools.bm25_index import BM25Index
from kosmos.tools.retrieval.backend import _DenseFailOpenWrapper
from kosmos.tools.retrieval.bm25_backend import BM25Backend
from kosmos.tools.retrieval.degrade import DegradationRecord
from kosmos.tools.retrieval.dense_backend import DenseBackend

_FAKE_SHA256 = "a" * 64
_CORPUS = {
    "koroad_accident_hazard_search": (
        "교통사고 위험지점 사고다발구역 accident hazard spot dangerous zone"
    ),
    "kma_forecast_fetch": (
        "단기예보 날씨예보 기온 강수 short-term forecast weather temperature"
    ),
    "nmc_emergency_search": (
        "응급실 실시간 병상 emergency room bed availability"
    ),
}


def _patch_dense_load_to_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make SentenceTransformer construction raise on the lazy load path."""

    def _failing_transformer(model_id, *, device=None):  # type: ignore[no-untyped-def]  # noqa: ARG001
        raise RuntimeError("simulated encoder failure")

    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer",
        _failing_transformer,
        raising=False,
    )
    monkeypatch.setattr(
        "kosmos.tools.retrieval.dense_backend.SentenceTransformer",
        _failing_transformer,
        raising=False,
    )
    # Defensive: prevent disk / hash work on the failure path.
    monkeypatch.setattr(
        "kosmos.tools.retrieval.dense_backend.DenseBackend._find_weight_file",
        staticmethod(lambda model_id: "/fake/path/model.safetensors"),  # noqa: ARG005
    )
    monkeypatch.setattr(
        "kosmos.tools.retrieval.dense_backend.DenseBackend._sha256_file",
        staticmethod(lambda path: _FAKE_SHA256),  # noqa: ARG005
    )


def _make_wrapper() -> tuple[_DenseFailOpenWrapper, DegradationRecord]:
    degradation_record = DegradationRecord()
    dense = DenseBackend(model_id="intfloat/multilingual-e5-small", cold_start="lazy")
    bm25 = BM25Backend(BM25Index({}))
    wrapper = _DenseFailOpenWrapper(
        dense=dense,
        bm25=bm25,
        degradation_record=degradation_record,
    )
    return wrapper, degradation_record


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_lazy_load_failure_serves_bm25_and_emits_single_warn(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """First lazy-load failure degrades to BM25 and fires exactly one WARN."""
    _patch_dense_load_to_fail(monkeypatch)

    wrapper, _ = _make_wrapper()
    wrapper.rebuild(_CORPUS)  # buffers dense corpus + builds BM25 companion

    with caplog.at_level(logging.WARNING, logger="kosmos"):
        # First score: dense lazy load fails → wrapper swaps in BM25.
        result = wrapper.score("교통사고 위험지점")

    # BM25 matches the KOROAD corpus document — non-empty, positive top score.
    assert result, "BM25 companion must return a non-empty ranking on degraded query"
    tool_ids = {tid for tid, _ in result}
    assert "koroad_accident_hazard_search" in tool_ids
    assert all(s >= 0.0 for _, s in result)

    # Exactly one structured WARN with the required fields.
    degraded_records = [
        r
        for r in caplog.records
        if r.levelname == "WARNING" and getattr(r, "event", None) == "retrieval.degraded"
    ]
    assert len(degraded_records) == 1, (
        f"Expected exactly 1 'retrieval.degraded' WARN, got {len(degraded_records)}. "
        f"All WARN messages: {[r.message for r in caplog.records if r.levelname == 'WARNING']}"
    )
    warn_record = degraded_records[0]
    assert getattr(warn_record, "requested_backend", None) == "dense"
    assert getattr(warn_record, "effective_backend", None) == "bm25"


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_second_score_after_degradation_emits_no_additional_warn(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Once degraded, the wrapper short-circuits to BM25 without re-warning."""
    _patch_dense_load_to_fail(monkeypatch)

    wrapper, _ = _make_wrapper()
    wrapper.rebuild(_CORPUS)

    with caplog.at_level(logging.WARNING, logger="kosmos"):
        wrapper.score("교통사고 위험지점")  # degrades
        wrapper.score("날씨 기온")  # must NOT re-warn
        wrapper.score("응급실 병상")  # must NOT re-warn

    degraded_count = sum(
        1
        for r in caplog.records
        if r.levelname == "WARNING" and getattr(r, "event", None) == "retrieval.degraded"
    )
    assert degraded_count == 1, (
        f"One-shot latch violated: expected 1 'retrieval.degraded' WARN across "
        f"three queries, got {degraded_count}."
    )


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_degraded_wrapper_does_not_reinvoke_dense(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After degradation, subsequent score() must not call dense.score()."""
    _patch_dense_load_to_fail(monkeypatch)

    wrapper, _ = _make_wrapper()
    wrapper.rebuild(_CORPUS)

    # Trigger degradation.
    wrapper.score("교통사고")
    assert wrapper._degraded is True

    # Instrument the dense backend to raise loudly if called again.
    call_count = {"n": 0}
    original_score = wrapper._dense.score

    def _counting_score(query: str) -> list[tuple[str, float]]:
        call_count["n"] += 1
        return original_score(query)

    wrapper._dense.score = _counting_score  # type: ignore[method-assign]

    # Subsequent queries must bypass dense entirely.
    wrapper.score("날씨")
    wrapper.score("응급실")
    assert call_count["n"] == 0, (
        f"Degraded wrapper re-invoked dense.score() {call_count['n']} times — "
        "should short-circuit to BM25 companion."
    )


def test_wrapper_satisfies_retriever_protocol() -> None:
    """_DenseFailOpenWrapper must satisfy the runtime_checkable Retriever protocol."""
    from kosmos.tools.retrieval.backend import Retriever

    dense = DenseBackend(model_id="intfloat/multilingual-e5-small", cold_start="lazy")
    bm25 = BM25Backend(BM25Index({}))
    wrapper = _DenseFailOpenWrapper(dense=dense, bm25=bm25, degradation_record=None)
    assert isinstance(wrapper, Retriever), (
        "_DenseFailOpenWrapper must structurally satisfy Retriever"
    )
