# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for live API validation tests.

Provides pre-configured httpx clients, API keys from environment variables,
and credential validation helpers.  All fixtures fail immediately if required
environment variables are missing — no silent skips.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any

import httpx
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Required environment variables — tests hard-fail if any are missing
# ---------------------------------------------------------------------------

_LIVE_ENV_VARS = {
    "KOSMOS_FRIENDLI_TOKEN": "FriendliAI Serverless API token",
    "KOSMOS_DATA_GO_KR_API_KEY": "data.go.kr public data portal key (shared by KMA + KOROAD)",
}


def _require_env(var_name: str) -> str:
    """Return the value of *var_name* or raise immediately."""
    value = os.environ.get(var_name, "").strip()
    if not value:
        pytest.fail(
            f"Required environment variable {var_name} is not set. "
            f"Live tests require real API credentials.",
        )
    return value


# ---------------------------------------------------------------------------
# Credential fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def friendli_token() -> str:
    """Return the FriendliAI API token from the environment."""
    return _require_env("KOSMOS_FRIENDLI_TOKEN")


@pytest.fixture(scope="session")
def data_go_kr_api_key() -> str:
    """Return the data.go.kr API key from the environment."""
    return _require_env("KOSMOS_DATA_GO_KR_API_KEY")


@pytest.fixture(scope="session")
def koroad_api_key() -> str:
    """Return the KOROAD API key (same as data.go.kr key) from the environment."""
    return _require_env("KOSMOS_DATA_GO_KR_API_KEY")


@pytest.fixture(scope="session")
def kakao_api_key() -> str:
    """Return the Kakao REST API key from the environment.

    Reads ``KOSMOS_KAKAO_API_KEY``.  Hard-fails with an exact message required
    by FR-004 / Story 1 AS-8 if the variable is unset or empty.

    Prerequisite: The Kakao Developers app must have the Local API activated
    (앱 설정 → 제품 설정 → 카카오맵 → 사용 설정 → 상태 ON).
    """
    value = os.environ.get("KOSMOS_KAKAO_API_KEY", "").strip()
    if not value:
        pytest.fail("set KOSMOS_KAKAO_API_KEY to run live geocoding tests")
    return value


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _live_rate_limit_pause() -> AsyncIterator[None]:
    """Pause after each live test to avoid FriendliAI 429 rate limiting.

    FriendliAI Serverless has aggressive per-minute rate limits.
    A 10-second cooling period between tests prevents cascading 429 errors.
    """
    yield
    await asyncio.sleep(10)


# Minimum inter-call delay for the Kakao Local API free-tier quota (100k/day).
# 200 ms × ~20 calls per test run is well within the daily budget.
_KAKAO_MIN_INTER_CALL_DELAY_S = 0.2


@pytest_asyncio.fixture
async def kakao_rate_limit_delay() -> AsyncIterator[Callable[[], Coroutine[Any, Any, None]]]:
    """Yield an async delay callable for use between consecutive Kakao API calls.

    The Kakao Local API has a free-tier daily quota of 100,000 requests.
    Inserting a 200 ms pause between calls within a single test keeps burst
    rate low and prevents exhausting the quota during a full ``-m live`` run.

    This fixture is NOT autouse — the global ``_live_rate_limit_pause`` already
    adds a 10-second post-test cooldown.  Use this fixture explicitly inside
    geocoding tests that make more than one Kakao call within a single test
    body.

    Usage::

        async def test_foo(kakao_rate_limit_delay):
            result1 = await search_address("query1")
            await kakao_rate_limit_delay()
            result2 = await search_address("query2")
    """

    async def _delay() -> None:
        await asyncio.sleep(_KAKAO_MIN_INTER_CALL_DELAY_S)

    yield _delay


@pytest_asyncio.fixture
async def live_http_client() -> httpx.AsyncClient:
    """Provide a plain httpx.AsyncClient for direct API calls."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
        yield client


@pytest_asyncio.fixture
async def friendli_http_client(friendli_token: str) -> httpx.AsyncClient:
    """Provide an httpx.AsyncClient pre-configured for FriendliAI."""
    async with httpx.AsyncClient(
        base_url="https://api.friendli.ai/serverless/v1",
        headers={"Authorization": f"Bearer {friendli_token}"},
        timeout=httpx.Timeout(60.0),
    ) as client:
        yield client
