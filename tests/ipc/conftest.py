# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures for IPC tests (Spec 032 WS1).

Provides:
- ``fake_clock``: injectable fake ``datetime`` for deterministic time tests.
- ``make_uuid7``: factory returning deterministic UUIDv7 strings.
- ``ndjson_buffer``: capture buffer that accumulates NDJSON lines emitted
  during a test and exposes them as a list of dicts.
- ``ipc_env_overrides``: monkeypatched env vars for KOSMOS_IPC_* knobs.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest

# ---------------------------------------------------------------------------
# Fake clock
# ---------------------------------------------------------------------------


class FakeClock:
    """Controllable monotonic clock for unit tests."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 4, 19, 12, 0, 0, tzinfo=UTC)

    @property
    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self._now = self._now + timedelta(seconds=seconds)

    def utcnow_str(self) -> str:
        return self._now.isoformat()


@pytest.fixture
def fake_clock() -> FakeClock:
    """Return a FakeClock initialised to 2026-04-19T12:00:00+00:00."""
    return FakeClock()


# ---------------------------------------------------------------------------
# UUIDv7 factory
# ---------------------------------------------------------------------------


class UUIDv7Factory:
    """Deterministic UUIDv7 factory that increments a counter per call."""

    def __init__(self) -> None:
        self._counter = 0

    def __call__(self) -> str:
        self._counter += 1
        # Build a UUIDv7-shaped string using timestamp + counter for test
        # determinism.  uuid.uuid7() is Python 3.13+; we use uuid4 random bits
        # and overwrite the timestamp prefix (same approach as envelope.ts).
        now_ms = int(time.time() * 1000)
        ts_hex = f"{now_ms:012x}"  # 48-bit timestamp as 12 hex chars
        counter_hex = f"{self._counter:012x}"
        # UUIDv7 layout: xxxxxxxx-xxxx-7xxx-yxxx-xxxxxxxxxxxx
        # Positions 0-7 and 9-12 are the 48-bit timestamp prefix.
        raw = uuid.uuid4().hex  # 32 hex chars, no hyphens
        # Replace first 12 hex chars (48 bits) with timestamp, version nibble,
        # and last 12 with counter for determinism.
        deterministic_hex = ts_hex + "7" + raw[13:20] + counter_hex
        return str(uuid.UUID(deterministic_hex))

    @property
    def counter(self) -> int:
        return self._counter


@pytest.fixture
def make_uuid7() -> UUIDv7Factory:
    """Return a UUIDv7 factory with a fresh counter per test."""
    return UUIDv7Factory()


# ---------------------------------------------------------------------------
# NDJSON capture buffer
# ---------------------------------------------------------------------------


class NDJSONBuffer:
    """In-memory NDJSON capture buffer for testing emit helpers."""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def write(self, line: str) -> None:
        """Accept a line (with or without trailing newline)."""
        stripped = line.rstrip("\n")
        if stripped:
            self._lines.append(stripped)

    def as_dicts(self) -> list[dict[str, object]]:
        """Parse all captured lines as JSON objects."""
        return [json.loads(ln) for ln in self._lines]

    def as_raw_lines(self) -> list[str]:
        return list(self._lines)

    def clear(self) -> None:
        self._lines.clear()

    def __len__(self) -> int:
        return len(self._lines)


@pytest.fixture
def ndjson_buffer() -> NDJSONBuffer:
    """Return a fresh NDJSON capture buffer."""
    return NDJSONBuffer()


# ---------------------------------------------------------------------------
# Environment overrides for KOSMOS_IPC_* knobs
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=False)
def ipc_env_overrides(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Set small KOSMOS_IPC_* defaults suitable for fast unit tests.

    Opt-in per test/module by requesting this fixture.
    Values are restored after each test.
    """
    overrides = {
        "KOSMOS_IPC_RING_SIZE": "16",
        "KOSMOS_IPC_TX_CACHE_CAPACITY": "8",
        "KOSMOS_IPC_HEARTBEAT_INTERVAL_MS": "500",
        "KOSMOS_IPC_HEARTBEAT_DEAD_MS": "1500",
    }
    for k, v in overrides.items():
        monkeypatch.setenv(k, v)
    yield
