# SPDX-License-Identifier: Apache-2.0
"""Pytest fixtures — Constitution §IV: no live network calls in CI."""

from __future__ import annotations

import socket
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def block_network(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> Iterator[None]:
    if request.node.get_closest_marker("allow_network") is not None:
        yield
        return

    def _blocked(*_a: object, **_k: object) -> socket.socket:
        raise RuntimeError(
            "Outbound network access is blocked in plugin tests "
            "(Constitution §IV)."
        )

    monkeypatch.setattr(socket, "socket", _blocked)
    yield


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "allow_network: opt out of the autouse network block",
    )
