# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin adapter for my_plugin.

Layer 1 (green) — read-only public data.
"""

from __future__ import annotations

from typing import Any

from .schema import LookupInput, LookupOutput


def _build_tool() -> Any:
    from kosmos.tools.models import GovAPITool

    return GovAPITool(
        id="plugin.my_plugin.lookup",
        name_ko="my_plugin 조회",
        ministry="OTHER",
        category=["my_plugin"],
        endpoint="https://example.com/my_plugin",
        auth_type="api_key",
        input_schema=LookupInput,
        output_schema=LookupOutput,
        search_hint="my_plugin 조회 lookup",
        auth_level="AAL1",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        is_personal_data=False,
        primitive="lookup",
        published_tier_minimum="digital_onepass_level1_aal1",
        nist_aal_hint="AAL1",
    )


TOOL = _build_tool()


async def adapter(payload: LookupInput) -> dict[str, Any]:
    """Replace this stub with a real httpx call against the upstream API."""
    return {"echo": payload.query, "source": "my_plugin-stub"}
