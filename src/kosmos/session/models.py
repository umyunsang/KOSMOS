# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 models for KOSMOS session persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SessionMetadata(BaseModel):
    """Metadata for a persisted session.

    Stored as the first line of each session JSONL file so that
    :func:`list_sessions` can cheaply enumerate sessions without loading
    the full message history.
    """

    model_config = ConfigDict(frozen=True)

    session_id: str
    """UUID string that uniquely identifies this session."""

    created_at: datetime
    """Wall-clock timestamp when the session was first created."""

    updated_at: datetime
    """Wall-clock timestamp of the most recent entry written."""

    title: str | None = None
    """Auto-generated from the first user message (first 50 chars)."""

    message_count: int = 0
    """Number of message entries recorded (user + assistant pairs)."""

    total_tokens_used: int = 0
    """Running total of all tokens consumed across the session."""

    parent_session_id: str | None = None
    """UUID of the parent session when this session was branched."""


class SessionEntry(BaseModel):
    """A single entry appended to the session JSONL file.

    Each line in the ``.jsonl`` file deserializes to one ``SessionEntry``.
    The ``entry_type`` field discriminates the shape of ``data``:

    - ``"metadata"``    — :class:`SessionMetadata` dict (first line only).
    - ``"message"``     — :class:`~kosmos.llm.models.ChatMessage` dict.
    - ``"tool_call"``   — tool call dict with ``id``, ``name``, ``arguments``.
    - ``"tool_result"`` — tool result dict with ``tool_id``, ``success``, ``data``.
    """

    model_config = ConfigDict(frozen=True)

    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """UTC timestamp of when this entry was appended."""

    entry_type: str
    """Discriminator: ``"metadata"``, ``"message"``, ``"tool_call"``, or ``"tool_result"``."""

    data: dict[str, Any]
    """Serialized payload whose schema depends on ``entry_type``."""

    parent_id: str | None = None
    """UUID chain link for session branching; ``None`` on the main timeline."""
