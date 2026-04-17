# SPDX-License-Identifier: Apache-2.0
"""Fail-open degradation test — T026 (spec 026, US2 P1, SC-005, FR-002).

When ``KOSMOS_RETRIEVAL_BACKEND=dense`` but the SentenceTransformer model
fails to load, the registry MUST:

1. Fall back to ``BM25Backend`` silently from the caller's perspective.
2. Emit exactly ONE structured WARN log with
       event             = "retrieval.degraded"
       requested_backend = "dense"
       effective_backend = "bm25"
3. NOT emit a second WARN on subsequent ``search()`` / ``score()`` calls
   (one-shot latch — FR-002 / DegradationRecord contract).

This test is written first (tests-first mandate, spec 026 Appendix B gate).
It WILL FAIL until T027 lands because ``build_retriever_from_env`` currently
raises ``NotImplementedError`` for ``backend=dense`` (T006 placeholder).
Expected initial failure mode:

    ImportError (dense_backend module not yet created by US1/T021)

After US1 lands (T021-T023), the failures will shift to assertion failures
(DegradationRecord not yet wired into factory) until T027 is implemented.
"""

from __future__ import annotations

import importlib
import logging

import pytest

from kosmos.tools.retrieval.bm25_backend import BM25Backend


def _patch_sentence_transformer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch SentenceTransformer to raise RuntimeError on construction.

    Patches both the canonical sentence_transformers top-level path and
    the dense_backend module path (if the module exists — it's created by
    US1/T021). Using ``raising=False`` for each so tests survive when
    dense_backend.py hasn't landed yet.

    When the dense_backend module does not exist the
    sentence_transformers.SentenceTransformer patch is sufficient to
    intercept any attempted import-and-use during registry construction.
    """
    _sentinel_error = RuntimeError("simulated load failure")

    def _raise_on_construct(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise _sentinel_error

    # Patch top-level sentence_transformers.SentenceTransformer.
    monkeypatch.setattr(
        "sentence_transformers.SentenceTransformer",
        _raise_on_construct,
        raising=False,
    )

    # If dense_backend module exists (after US1/T021 lands), patch its
    # local SentenceTransformer reference too.
    if importlib.util.find_spec("kosmos.tools.retrieval.dense_backend") is not None:
        # Ensure the module is imported so setattr can target it.
        import kosmos.tools.retrieval.dense_backend  # noqa: F401

        monkeypatch.setattr(
            "kosmos.tools.retrieval.dense_backend.SentenceTransformer",
            _raise_on_construct,
            raising=False,
        )


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_dense_load_failure_degrades_to_bm25(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """With backend=dense and a simulated load failure, registry uses BM25Backend.

    Checks:
    - registry._retriever is BM25Backend
    - exactly one WARN record has event="retrieval.degraded",
      requested_backend="dense", effective_backend="bm25"
    """
    monkeypatch.setenv("KOSMOS_RETRIEVAL_BACKEND", "dense")
    _patch_sentence_transformer(monkeypatch)

    with caplog.at_level(logging.WARNING, logger="kosmos"):
        from kosmos.eval.retrieval import _build_registry

        registry, _ = _build_registry()

    # Assertion 1: effective retriever is BM25Backend (fail-open contract)
    assert isinstance(registry._retriever, BM25Backend), (
        f"Expected BM25Backend after dense load failure, got {type(registry._retriever).__name__}"
    )

    # Assertion 2: exactly one WARN log with required structured fields
    degraded_records = [
        r
        for r in caplog.records
        if r.levelname == "WARNING" and getattr(r, "event", None) == "retrieval.degraded"
    ]
    all_warn = [
        (r.message, getattr(r, "event", None)) for r in caplog.records if r.levelname == "WARNING"
    ]
    assert len(degraded_records) == 1, (
        f"Expected exactly 1 WARN with event='retrieval.degraded', "
        f"got {len(degraded_records)}. All WARN records: {all_warn}"
    )

    warn_record = degraded_records[0]
    assert getattr(warn_record, "requested_backend", None) == "dense", (
        f"Expected requested_backend='dense', "
        f"got {getattr(warn_record, 'requested_backend', None)!r}"
    )
    assert getattr(warn_record, "effective_backend", None) == "bm25", (
        f"Expected effective_backend='bm25', "
        f"got {getattr(warn_record, 'effective_backend', None)!r}"
    )


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_second_search_call_emits_no_additional_warn(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """After degradation, the one-shot latch prevents a second WARN.

    The FR-002 invariant: exactly one WARN per degraded registry instance,
    regardless of how many times ``score()``/``search()`` is called.
    """
    monkeypatch.setenv("KOSMOS_RETRIEVAL_BACKEND", "dense")
    _patch_sentence_transformer(monkeypatch)

    with caplog.at_level(logging.WARNING, logger="kosmos"):
        from kosmos.eval.retrieval import _build_registry

        registry, _ = _build_registry()

        # Count WARN records after registry construction
        warn_count_after_build = sum(
            1
            for r in caplog.records
            if r.levelname == "WARNING" and getattr(r, "event", None) == "retrieval.degraded"
        )

        # Second search call — must NOT emit a second WARN (one-shot latch)
        registry.search("교통사고 다발구간")

    # Total degraded WARNs must still be exactly 1
    total_degraded_warns = sum(
        1
        for r in caplog.records
        if r.levelname == "WARNING" and getattr(r, "event", None) == "retrieval.degraded"
    )
    assert total_degraded_warns == 1, (
        f"One-shot latch violated: expected 1 total degradation WARN, "
        f"got {total_degraded_warns} after second search() call."
    )
    assert warn_count_after_build == 1, (
        "First WARN must fire at build time (registry construction), not deferred to search."
    )
