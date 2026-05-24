# SPDX-License-Identifier: Apache-2.0
"""Regression tests for MCP server environment bootstrap."""

from __future__ import annotations

import asyncio
from typing import Any

from ummaya.ipc import mcp_server


def test_mcp_server_main_loads_repo_dotenv(monkeypatch: Any) -> None:
    """Direct ``python -m ummaya.ipc.mcp_server`` loads repo ``.env`` first."""
    calls: list[str] = []

    def fake_load_repo_dotenv() -> None:
        calls.append("dotenv")

    def fake_register_all_tools(*_args: Any, **_kwargs: Any) -> object:
        calls.append("register")

        class FakeRoutingIndex:
            by_primitive: dict[str, list[str]] = {}

        return FakeRoutingIndex()

    def fake_emit_manifest(*_args: Any, **_kwargs: Any) -> None:
        calls.append("manifest")

    async def fake_run_loop(_server: mcp_server.MCPServer) -> None:
        calls.append("loop")

    monkeypatch.setattr(mcp_server, "load_repo_dotenv", fake_load_repo_dotenv, raising=False)
    monkeypatch.setattr(mcp_server, "register_all_tools", fake_register_all_tools)
    monkeypatch.setattr(mcp_server, "emit_manifest", fake_emit_manifest)
    monkeypatch.setattr(mcp_server, "_run_loop", fake_run_loop)

    asyncio.run(mcp_server.main())

    assert calls == ["dotenv", "register", "manifest", "loop"]
