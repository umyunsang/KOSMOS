# SPDX-License-Identifier: Apache-2.0
"""Adapter happy-path + error-path tests for my_plugin."""

from __future__ import annotations

import pytest

from plugin_my_plugin.adapter import adapter
from plugin_my_plugin.schema import LookupInput, LookupOutput


@pytest.mark.asyncio
async def test_adapter_happy_path() -> None:
    payload = LookupInput(query="hello")
    result = await adapter(payload)
    LookupOutput.model_validate(result)
    assert result["echo"] == "hello"


@pytest.mark.asyncio
async def test_adapter_error_path() -> None:
    with pytest.raises(Exception):
        LookupInput(query="")
