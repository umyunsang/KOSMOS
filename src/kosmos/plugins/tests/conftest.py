# SPDX-License-Identifier: Apache-2.0
"""Pytest configuration for kosmos.plugins tests.

Enforces Constitution §IV (no live network calls in CI) by autouse-blocking
all outbound socket connections during tests in this package. Tests that
legitimately need network access must opt out via the
``@pytest.mark.allow_network`` marker (rare; live API tests live elsewhere
under ``@pytest.mark.live``).
"""

from __future__ import annotations

import socket
from collections.abc import Iterator

import pytest

_REAL_SOCKET = socket.socket


class _NetworkBlockedError(RuntimeError):
    """Raised when a test attempts an outbound socket connection.

    Constitution §IV: never call live data.go.kr or external APIs from CI.
    """


def _blocked_socket(*_args: object, **_kwargs: object) -> socket.socket:
    raise _NetworkBlockedError(
        "Outbound network access is disabled in kosmos.plugins tests "
        "(Constitution §IV). Use recorded fixtures or "
        "@pytest.mark.allow_network for the rare opt-out case."
    )


@pytest.fixture(autouse=True)
def _block_network(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[None]:
    """Block all outbound socket creation for the duration of each test.

    Tests carrying the ``allow_network`` marker bypass the block.
    """
    if request.node.get_closest_marker("allow_network") is not None:
        yield
        return
    monkeypatch.setattr(socket, "socket", _blocked_socket)
    yield


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "allow_network: opt out of the autouse network block "
        "(use sparingly; prefer recorded fixtures)",
    )
