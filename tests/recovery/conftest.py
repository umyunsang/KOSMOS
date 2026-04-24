# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for the recovery package tests."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

import httpx
import pytest
from pydantic import BaseModel

from kosmos.tools.models import GovAPITool


class _DummyInput(BaseModel):
    """Minimal input schema for test fixtures."""

    query: str


class _DummyOutput(BaseModel):
    """Minimal output schema for test fixtures."""

    result: str


# ---------------------------------------------------------------------------
# Adapter factory fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def make_success_adapter() -> Callable[[], Callable[[object], Awaitable[dict[str, object]]]]:
    """Return a factory that creates an async adapter returning ``{"result": "ok"}``."""

    def _factory() -> Callable[[object], Awaitable[dict[str, object]]]:
        async def _adapter(args: object) -> dict[str, object]:
            return {"result": "ok"}

        return _adapter

    return _factory


@pytest.fixture()
def make_failure_adapter() -> Callable[
    [int, str, str | None], Callable[[object], Awaitable[dict[str, object]]]
]:
    """Return a factory that creates an async adapter raising ``httpx.HTTPStatusError``."""

    def _factory(
        status_code: int,
        body: str = "",
        content_type: str | None = None,
    ) -> Callable[[object], Awaitable[dict[str, object]]]:
        headers = {}
        if content_type is not None:
            headers["content-type"] = content_type

        request = httpx.Request("GET", "https://api.example.com/test")
        response = httpx.Response(status_code, text=body, headers=headers, request=request)
        exc = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=request,
            response=response,
        )

        async def _adapter(args: object) -> dict[str, object]:
            raise exc

        return _adapter

    return _factory


@pytest.fixture()
def make_timeout_adapter() -> Callable[[], Callable[[object], Awaitable[dict[str, object]]]]:
    """Return a factory that creates an async adapter raising ``httpx.ReadTimeout``."""

    def _factory() -> Callable[[object], Awaitable[dict[str, object]]]:
        async def _adapter(args: object) -> dict[str, object]:
            raise httpx.ReadTimeout("read timed out")

        return _adapter

    return _factory


# ---------------------------------------------------------------------------
# Response body helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_xml_gateway_response() -> Callable[[int | str, str], str]:
    """Return a helper that builds a data.go.kr XML gateway response body."""

    def _make(code: int | str, message: str = "") -> str:
        return (
            "<OpenAPI_ServiceResponse>"
            "<cmmMsgHeader>"
            f"<returnReasonCode>{code}</returnReasonCode>"
            f"<returnAuthMsg>{message}</returnAuthMsg>"
            "</cmmMsgHeader>"
            "</OpenAPI_ServiceResponse>"
        )

    return _make


@pytest.fixture()
def sample_json_error_response() -> Callable[[int | str, str], str]:
    """Return a helper that builds a data.go.kr JSON error response body."""

    def _make(code: int | str, message: str = "") -> str:
        return json.dumps({"resultCode": code, "resultMsg": message})

    return _make


# ---------------------------------------------------------------------------
# Tool fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_gov_api_tool() -> GovAPITool:
    """Return a ``GovAPITool`` with test values for use in recovery tests."""
    return GovAPITool(
        id="test_tool",
        name_ko="테스트 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="https://api.example.com/test",
        auth_type="api_key",
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="test 테스트 tool adapter",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_concurrency_safe=True,
        is_personal_data=False,
        cache_ttl_seconds=3600,
        rate_limit_per_minute=60,
    )


@pytest.fixture()
def sample_tool() -> GovAPITool:
    """Return a minimal GovAPITool for use in recovery tests."""
    return GovAPITool(
        id="test_tool",
        name_ko="테스트 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="https://api.example.com/test",
        auth_type="api_key",
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="test 테스트",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_concurrency_safe=True,
        is_personal_data=False,
        cache_ttl_seconds=60,
        rate_limit_per_minute=100,
    )


@pytest.fixture()
def no_cache_tool() -> GovAPITool:
    """Return a GovAPITool with cache_ttl_seconds=0 (no caching)."""
    return GovAPITool(
        id="no_cache_tool",
        name_ko="캐시 없는 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="https://api.example.com/no-cache",
        auth_type="api_key",
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="no cache 캐시없음",
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
