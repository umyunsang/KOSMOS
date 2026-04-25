# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 input + output schemas for the lookup primitive."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LookupInput(BaseModel):
    """Input model — REPLACE with real fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = Field(min_length=1, description="Search query text.")


class LookupOutput(BaseModel):
    """Output model — REPLACE with real fields matching the upstream response."""

    model_config = ConfigDict(frozen=True, extra="allow")

    echo: str = Field(description="Echo of the input query (placeholder).")
    source: str = Field(description="Source identifier (placeholder).")
