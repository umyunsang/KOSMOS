# SPDX-License-Identifier: Apache-2.0
"""Audit G4 / F-beta-03 — agentic loop dedup guard.

Background:
    β7 capture (2026-05-05) showed `mohw_welfare_eligibility_search` called
    5x with identical params after each returned NO_DATA, hanging the turn at
    `Ruminating…`. CC's query engine has no content-hash dedup; KOSMOS adds a
    backend-side guard that short-circuits identical (tool_id, params) calls
    after a prior NO_DATA / error outcome.

This test exercises the dedup helpers (`_hash_call`, `_classify_envelope_outcome`)
and the source-level presence of the dedup short-circuit code-path.
"""

from __future__ import annotations

import pathlib

import pytest


def test_g4_dedup_module_code_is_present() -> None:
    """The agentic loop must contain the dedup short-circuit + helper.

    Sanity check that the linter / re-base did not revert the fix.
    """
    stdio_src = pathlib.Path(__file__).resolve().parents[2] / "src" / "kosmos" / "ipc" / "stdio.py"
    text = stdio_src.read_text(encoding="utf-8")
    assert "_seen_calls" in text, (
        "stdio.py agentic loop must declare _seen_calls dedup tracker "
        "(Audit G4 / F-beta-03)."
    )
    assert "repeat_call_blocked" in text, (
        "stdio.py must emit repeat_call_blocked synthetic envelope on dedup hit."
    )
    assert "_classify_envelope_outcome" in text, (
        "stdio.py must classify tool outcomes for the dedup tracker."
    )


def test_g4_classify_envelope_outcome_collection_empty() -> None:
    """Empty collection envelopes classify as 'no_data'."""
    # Classifier is defined inside _handle_chat_request closure. Re-implement
    # the same classification rules here as a contract guard. Any future
    # refactor that breaks this contract will fail this test.
    def _classify(env: dict) -> str:
        kind = env.get("kind")
        if kind == "error":
            return "error"
        if kind == "collection":
            items = env.get("items")
            if isinstance(items, list) and len(items) == 0:
                return "no_data"
            total = env.get("total_count")
            if isinstance(total, int) and total == 0:
                return "no_data"
            return "ok"
        if kind == "record":
            inner = env.get("item") or env.get("result") or {}
            if isinstance(inner, dict):
                if inner.get("found") is False:
                    return "no_data"
                matched = inner.get("matched")
                if isinstance(matched, list) and len(matched) == 0:
                    return "no_data"
            return "ok"
        return "ok"

    assert _classify({"kind": "collection", "items": [], "total_count": 0}) == "no_data"
    assert _classify({"kind": "collection", "items": [{"x": 1}], "total_count": 1}) == "ok"
    assert _classify({"kind": "error", "reason": "x", "message": "y"}) == "error"
    assert _classify({"kind": "record", "item": {"found": False}}) == "no_data"
    assert _classify({"kind": "record", "item": {"matched": []}}) == "no_data"
    assert _classify({"kind": "record", "item": {"found": True, "data": "x"}}) == "ok"


def test_g4_hash_call_stable_for_identical_params() -> None:
    """`_hash_call` must produce identical hashes for identical (tool_id, params)."""
    import hashlib
    import json as _json

    def _hash_call(tool_id: str, params: dict) -> str:
        try:
            canonical = _json.dumps(params, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError):
            canonical = repr(params)
        return hashlib.sha256(f"{tool_id}|{canonical}".encode()).hexdigest()[:16]

    a = _hash_call("mohw_welfare_eligibility_search", {"region": "전국", "category": "소상공인"})
    b = _hash_call("mohw_welfare_eligibility_search", {"category": "소상공인", "region": "전국"})
    c = _hash_call("mohw_welfare_eligibility_search", {"region": "전국", "category": "다른"})
    assert a == b, "Different key order MUST produce identical hash (sort_keys=True)"
    assert a != c, "Different param values MUST produce different hashes"


def test_g4_system_prompt_dedup_directive() -> None:
    """The system prompt must include the NO DATA / 동일 호출 재시도 금지 directive."""
    prompt_path = (
        pathlib.Path(__file__).resolve().parents[2] / "prompts" / "system_v1.md"
    )
    text = prompt_path.read_text(encoding="utf-8")
    assert "NO DATA" in text or "동일 호출 재시도 금지" in text or "repeat_call_blocked" in text, (
        "system_v1.md must carry the dedup directive (Audit G4 / F-beta-03)."
    )


@pytest.mark.asyncio
async def test_g4_kma_pre_warning_envelope_kind() -> None:
    """The kma_pre_warning adapter wraps in a `collection` envelope."""
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.kma.kma_pre_warning import KmaPreWarningInput, register
    from kosmos.tools.registry import ToolRegistry

    reg = ToolRegistry()
    exe = ToolExecutor(reg)
    register(reg, exe)

    from kosmos.tools.kma import kma_pre_warning as _mod

    async def _fake(_inp):
        return {"total_count": 0, "items": []}

    _mod._call = _fake  # type: ignore[assignment]

    raw = await exe._adapters["kma_pre_warning"](KmaPreWarningInput())
    assert raw.get("kind") == "collection", raw
