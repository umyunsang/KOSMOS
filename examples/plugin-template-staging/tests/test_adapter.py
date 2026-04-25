# SPDX-License-Identifier: Apache-2.0
"""Adapter happy-path + error-path tests for my_plugin.

The scaffolded test passes out of the box because the adapter stub
echoes the input deterministically. Replace these assertions with real
ones once the adapter calls the upstream public API.
"""

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


def test_input_validation_rejects_empty_query() -> None:
    with pytest.raises(Exception):
        LookupInput(query="")
