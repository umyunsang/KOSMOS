# SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for live API validation tests.

Provides pre-configured httpx clients, API keys from environment variables,
and credential validation helpers.  All fixtures fail immediately if required
environment variables are missing — no silent skips.
"""

from __future__ import annotations

import os

import httpx
import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# Required environment variables — tests hard-fail if any are missing
# ---------------------------------------------------------------------------

_LIVE_ENV_VARS = {
    "KOSMOS_FRIENDLI_TOKEN": "FriendliAI Serverless API token",
    "KOSMOS_DATA_GO_KR_API_KEY": "data.go.kr public data portal key",
    "KOSMOS_KOROAD_API_KEY": "KOROAD open data portal key",
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
    """Return the KOROAD API key from the environment."""
    return _require_env("KOSMOS_KOROAD_API_KEY")


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------


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
