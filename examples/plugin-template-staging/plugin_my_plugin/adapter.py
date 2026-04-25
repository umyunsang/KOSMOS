# SPDX-License-Identifier: Apache-2.0
"""KOSMOS plugin adapter for my_plugin.

Layer 1 (green) — read-only public data.
"""

from __future__ import annotations

from typing import Any

from .schema import LookupInput, LookupOutput


def _build_tool() -> Any:
    """Construct the GovAPITool registry entry on first access.

    Imported lazily so the scaffold's tests (which do not require the
    KOSMOS host) can run without ``kosmos`` installed. The host triggers
    construction at install time when reading the module-level ``TOOL``
    attribute via PEP 562.
    """
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


_TOOL_CACHE: Any = None


def __getattr__(name: str) -> Any:
    """PEP 562: provide lazy module-level ``TOOL`` so this file imports
    without ``kosmos`` being available (e.g. scaffold tests)."""
    global _TOOL_CACHE
    if name == "TOOL":
        if _TOOL_CACHE is None:
            _TOOL_CACHE = _build_tool()
        return _TOOL_CACHE
    raise AttributeError(name)


async def adapter(payload: LookupInput) -> dict[str, Any]:
    """Replace this stub with a real httpx call against the upstream API."""
    return {"echo": payload.query, "source": "my_plugin-stub"}
