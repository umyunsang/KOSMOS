# SPDX-License-Identifier: Apache-2.0
"""Pytest fixtures — Constitution §IV: no live network calls in CI.

Only IPv4 / IPv6 socket creation is blocked; AF_UNIX socketpairs used
by the asyncio event loop continue to work (otherwise pytest-asyncio
would fail to set up).
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from typing import Any

import pytest

_REAL_SOCKET = socket.socket


@pytest.fixture(autouse=True)
def block_network(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    if request.node.get_closest_marker("allow_network") is not None:
        yield
        return

    def _maybe_block(*args: Any, **kwargs: Any) -> socket.socket:
        family = (
            kwargs.get("family")
            if "family" in kwargs
            else (args[0] if args else socket.AF_INET)
        )
        if family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError(
                "Outbound network access is blocked in plugin tests "
                "(Constitution §IV). Use a recorded fixture or "
                "@pytest.mark.allow_network for the rare opt-out."
            )
        return _REAL_SOCKET(*args, **kwargs)

    monkeypatch.setattr(socket, "socket", _maybe_block)
    yield


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "allow_network: opt out of the autouse network block",
    )
