# SPDX-License-Identifier: Apache-2.0
"""Tests for ResponseCache and build_degradation_message."""

from __future__ import annotations

import pytest

from kosmos.recovery.cache import CacheEntry, ResponseCache
from kosmos.recovery.classifier import ClassifiedError, ErrorClass
from kosmos.recovery.messages import build_degradation_message
from kosmos.tools.models import GovAPITool

# ---------------------------------------------------------------------------
# ResponseCache
# ---------------------------------------------------------------------------


class TestResponseCache:
    def test_put_and_get_hit(self) -> None:
        cache = ResponseCache()
        h = cache.compute_hash({"q": "test"})
        cache.put("tool_a", h, {"result": "ok"}, ttl_seconds=60)
        result = cache.get("tool_a", h)
        assert result == {"result": "ok"}

    def test_get_miss_returns_none(self) -> None:
        cache = ResponseCache()
        h = cache.compute_hash({"q": "test"})
        result = cache.get("tool_a", h)
        assert result is None

    def test_ttl_zero_not_stored(self) -> None:
        cache = ResponseCache()
        h = cache.compute_hash({"q": "test"})
        cache.put("tool_a", h, {"result": "ok"}, ttl_seconds=0)
        result = cache.get("tool_a", h)
        assert result is None

    def test_expired_entry_returns_none(self) -> None:
        cache = ResponseCache()
        h = cache.compute_hash({"q": "test"})
        cache.put("tool_a", h, {"result": "ok"}, ttl_seconds=1)
        # Manually age the entry
        old_entry = cache._store[f"tool_a:{h}"]  # noqa: SLF001
        aged_entry = CacheEntry(
            tool_id=old_entry.tool_id,
            arguments_hash=old_entry.arguments_hash,
            data=old_entry.data,
            cached_at=old_entry.cached_at - 2,  # 2 seconds in the past
            ttl_seconds=1,
        )
        cache._store[f"tool_a:{h}"] = aged_entry  # noqa: SLF001
        result = cache.get("tool_a", h)
        assert result is None

    def test_lru_eviction(self) -> None:
        cache = ResponseCache(max_entries=3)
        for i in range(3):
            h = cache.compute_hash({"i": i})
            cache.put(f"tool_{i}", h, {"n": i}, ttl_seconds=60)

        # Access tool_0 to make it most-recently used
        h0 = cache.compute_hash({"i": 0})
        cache.get("tool_0", h0)

        # Add a 4th entry — should evict LRU (tool_1, the oldest untouched)
        h3 = cache.compute_hash({"i": 3})
        cache.put("tool_3", h3, {"n": 3}, ttl_seconds=60)

        assert len(cache._store) == 3  # noqa: SLF001
        # tool_1 should have been evicted (least recently used)
        h1 = cache.compute_hash({"i": 1})
        assert cache.get("tool_1", h1) is None

    def test_hash_deterministic(self) -> None:
        cache = ResponseCache()
        h1 = cache.compute_hash({"b": 2, "a": 1})
        h2 = cache.compute_hash({"a": 1, "b": 2})
        assert h1 == h2

    def test_hash_different_values(self) -> None:
        cache = ResponseCache()
        h1 = cache.compute_hash({"q": "foo"})
        h2 = cache.compute_hash({"q": "bar"})
        assert h1 != h2

    def test_get_returns_copy(self) -> None:
        """Returned dict should be a copy to prevent mutation of cached data."""
        cache = ResponseCache()
        h = cache.compute_hash({"q": "test"})
        cache.put("tool_a", h, {"result": "ok"}, ttl_seconds=60)
        result = cache.get("tool_a", h)
        assert result is not None
        result["result"] = "mutated"
        # Second get should return original
        result2 = cache.get("tool_a", h)
        assert result2 == {"result": "ok"}


# ---------------------------------------------------------------------------
# build_degradation_message
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_tool() -> GovAPITool:
    from pydantic import BaseModel

    class _In(BaseModel):
        q: str

    class _Out(BaseModel):
        r: str

    return GovAPITool(
        id="test_tool",
        name_ko="테스트 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="https://api.example.com/",
        auth_type="public",
        input_schema=_In,
        output_schema=_Out,
        search_hint="test 테스트",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_concurrency_safe=False,
        is_personal_data=False,
        cache_ttl_seconds=0,
        rate_limit_per_minute=10,
    )


class TestBuildDegradationMessage:
    def _make_error(
        self,
        error_class: ErrorClass,
        source: str = "json_body",
    ) -> ClassifiedError:
        return ClassifiedError(
            error_class=error_class,
            is_retryable=False,
            raw_code=None,
            raw_message="test error",
            source=source,
        )

    def test_general_error_message(self, sample_tool: GovAPITool) -> None:
        err = self._make_error(ErrorClass.TRANSIENT)
        msg = build_degradation_message(sample_tool, err)
        assert "테스트 도구" in msg
        assert "잠시 후 다시 시도해주세요" in msg

    def test_circuit_open_message(self, sample_tool: GovAPITool) -> None:
        err = self._make_error(ErrorClass.APP_ERROR, source="circuit_open")
        msg = build_degradation_message(sample_tool, err)
        assert "테스트 도구" in msg
        assert "점검 중" in msg or "일시적으로 중단" in msg

    def test_deprecated_message(self, sample_tool: GovAPITool) -> None:
        err = self._make_error(ErrorClass.DEPRECATED)
        msg = build_degradation_message(sample_tool, err)
        assert "테스트 도구" in msg
        assert "종료" in msg or "변경" in msg

    def test_auth_expired_message(self, sample_tool: GovAPITool) -> None:
        err = self._make_error(ErrorClass.AUTH_FAILURE)
        msg = build_degradation_message(sample_tool, err)
        assert "테스트 도구" in msg
        assert "인증이 만료" in msg

    def test_name_ko_included_in_all_messages(self, sample_tool: GovAPITool) -> None:
        for ec in [ErrorClass.TRANSIENT, ErrorClass.RATE_LIMIT, ErrorClass.TIMEOUT]:
            err = self._make_error(ec)
            msg = build_degradation_message(sample_tool, err)
            assert sample_tool.name_ko in msg

    def test_message_is_korean(self, sample_tool: GovAPITool) -> None:
        """Messages contain Korean characters (verify they're not pure ASCII)."""
        err = self._make_error(ErrorClass.TRANSIENT)
        msg = build_degradation_message(sample_tool, err)
        has_korean = any("\uac00" <= ch <= "\ud7a3" for ch in msg)
        assert has_korean, f"Expected Korean text in: {msg!r}"
