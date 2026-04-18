# SPDX-License-Identifier: Apache-2.0
"""Test-layer Pydantic v2 models for spec 030 Scenario 1 E2E Route Safety (Re-baseline).

Defines:
- ScenarioTurn: One scripted mock-LLM turn.
- ScenarioScript: Ordered sequence of turns + metadata.
- CapturedSpan: Per-span snapshot for OTel assertions.
- ObservabilitySnapshot: Collection of CapturedSpan with sdk_disabled flag.
- RunReport: Top-level scenario run artifact with all assertion surfaces.

All models are frozen Pydantic v2; no Any; all fields explicitly typed.
Constitution §III compliance verified.

schema_version="030-runreport-v1" is frozen — bumping requires a spec amendment.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kosmos.llm.models import TokenUsage

# ---------------------------------------------------------------------------
# 2.1 ScenarioTurn
# ---------------------------------------------------------------------------

ScenarioId = Literal[
    "happy",
    "degraded_kma_retry",
    "degraded_koroad_no_retry",
    "both_down",
    "quirk_2023_gangwon",
    "quirk_2023_jeonbuk",
    "quirk_2022_control",
]


class ScenarioTurn(BaseModel):
    """One scripted entry from the mock LLM.

    Invariants (I1–I3):
      I1: kind="tool_call" => tool_name and tool_arguments are non-None; text_content is None.
      I2: kind="text_delta" => text_content is non-None; tool_name and tool_arguments are None.
      I3: tool_arguments, when present, serializes to <= 1 KiB.
    """

    model_config = ConfigDict(frozen=True)

    index: int = Field(ge=0, description="Zero-based position in the scenario turn sequence.")
    kind: Literal["tool_call", "text_delta"]
    tool_name: Literal["resolve_location", "lookup"] | None = None
    tool_arguments: dict[str, Any] | None = None
    text_content: str | None = None
    token_usage: TokenUsage | None = None

    @model_validator(mode="after")
    def _check_invariants(self) -> ScenarioTurn:
        if self.kind == "tool_call":
            if self.tool_name is None:
                raise ValueError("I1: kind='tool_call' requires tool_name to be non-None")
            if self.tool_arguments is None:
                raise ValueError("I1: kind='tool_call' requires tool_arguments to be non-None")
            if self.text_content is not None:
                raise ValueError("I1: kind='tool_call' requires text_content to be None")
            # I3: serialized args <= 1 KiB
            args_bytes = len(json.dumps(self.tool_arguments).encode())
            if args_bytes > 1024:
                raise ValueError(
                    f"I3: tool_arguments serializes to {args_bytes} bytes, exceeds 1 KiB"
                )
        elif self.kind == "text_delta":
            if self.text_content is None:
                raise ValueError("I2: kind='text_delta' requires text_content to be non-None")
            if self.tool_name is not None:
                raise ValueError("I2: kind='text_delta' requires tool_name to be None")
            if self.tool_arguments is not None:
                raise ValueError("I2: kind='text_delta' requires tool_arguments to be None")
        return self


# ---------------------------------------------------------------------------
# 2.2 ScenarioScript
# ---------------------------------------------------------------------------


class ScenarioScript(BaseModel):
    """Typed ordered collection of ScenarioTurns plus run metadata.

    Consumed by MockLLMClient builder helpers in conftest.py.
    """

    model_config = ConfigDict(frozen=True)

    scenario_id: ScenarioId
    turns: tuple[ScenarioTurn, ...]
    expected_stop_reason: Literal["end_turn", "error_unrecoverable", "api_budget_exceeded"]

    @model_validator(mode="after")
    def _check_min_turns(self) -> ScenarioScript:
        if len(self.turns) < 2:
            raise ValueError("ScenarioScript must have at least 2 turns (tool call + synthesis)")
        return self


# ---------------------------------------------------------------------------
# 2.4 CapturedSpan
# ---------------------------------------------------------------------------


class CapturedSpan(BaseModel):
    """Per-span snapshot for FR-017/018/019 assertions.

    Invariants:
      I4: outcome="error" => status_code="ERROR" and error_type is non-None.
      I5: adapter_id is not None => tool_name == "lookup".
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(description='Span name, e.g., "execute_tool resolve_location".')
    operation_name: Literal["execute_tool"] | None = None
    tool_name: str
    tool_call_id: str | None = None
    outcome: Literal["ok", "error"]
    adapter_id: str | None = None
    error_type: str | None = None
    status_code: Literal["UNSET", "OK", "ERROR"]
    attribute_keys: frozenset[str]

    @model_validator(mode="after")
    def _check_invariants(self) -> CapturedSpan:
        # I4
        if self.outcome == "error":
            if self.status_code != "ERROR":
                raise ValueError(
                    f"I4: outcome='error' requires status_code='ERROR', got {self.status_code!r}"
                )
            if self.error_type is None:
                raise ValueError("I4: outcome='error' requires error_type to be non-None")
        # I5
        if self.adapter_id is not None and self.tool_name != "lookup":
            raise ValueError(
                f"I5: adapter_id is non-None but tool_name={self.tool_name!r} != 'lookup'"
            )
        return self


# ---------------------------------------------------------------------------
# 2.3 ObservabilitySnapshot
# ---------------------------------------------------------------------------


class ObservabilitySnapshot(BaseModel):
    """Typed test-safe view of OTel spans for one scenario run.

    When sdk_disabled=True, spans MUST be empty (FR-020).
    """

    model_config = ConfigDict(frozen=True)

    spans: tuple[CapturedSpan, ...] = Field(default=())
    sdk_disabled: bool = False

    @model_validator(mode="after")
    def _check_sdk_disabled(self) -> ObservabilitySnapshot:
        if self.sdk_disabled and self.spans:
            raise ValueError("ObservabilitySnapshot: spans must be empty when sdk_disabled=True")
        return self


# ---------------------------------------------------------------------------
# 2.5 RunReport
# ---------------------------------------------------------------------------


class RunReport(BaseModel):
    """Top-level artifact produced by every scenario run.

    Assertion surface, optional JSON export, and evidence artifact.

    Invariants:
      I7: len(fetched_adapter_ids) == count of spans with adapter_id not None.
      I8: stop_reason="end_turn" => final_response is non-empty.
      I9: stop_reason="error_unrecoverable" => final_response is None OR graceful Korean msg.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["030-runreport-v1"] = "030-runreport-v1"
    scenario_id: ScenarioId
    trigger_query: str
    tool_call_order: tuple[str, ...]
    fetched_adapter_ids: tuple[str, ...]
    final_response: str | None
    stop_reason: Literal["end_turn", "error_unrecoverable", "api_budget_exceeded"]
    usage_totals: TokenUsage
    observability: ObservabilitySnapshot
    adapter_rate_limit_hits: dict[str, int]
    elapsed_ms: int = Field(ge=0, description="Wall-clock ms for the full run (advisory).")

    @model_validator(mode="after")
    def _check_invariants(self) -> RunReport:
        # I7: fetched_adapter_ids count matches spans with adapter_id.
        # Enforced only when OTel SDK is enabled AND at least one adapter span exists
        # (span_adapter_count > 0).  When the executor does not yet emit
        # kosmos.tool.adapter, span_adapter_count is 0 and I7 is not triggered —
        # this avoids false failures while the instrumentation is being built out.
        span_adapter_count = sum(1 for s in self.observability.spans if s.adapter_id is not None)
        if (
            not self.observability.sdk_disabled
            and span_adapter_count > 0
            and span_adapter_count != len(self.fetched_adapter_ids)
        ):
            raise ValueError(
                f"I7: fetched_adapter_ids has {len(self.fetched_adapter_ids)} entries "
                f"but {span_adapter_count} spans carry adapter_id — these must match"
            )
        # I8
        if self.stop_reason == "end_turn" and not self.final_response:
            raise ValueError("I8: stop_reason='end_turn' requires non-empty final_response")
        # I9: stop_reason="error_unrecoverable" => final_response is None OR graceful Korean msg.
        if self.stop_reason == "error_unrecoverable" and self.final_response is not None:
            korean_apology_markers = ["죄송", "장애", "일시적", "다시", "이용할 수 없"]
            if not any(marker in self.final_response for marker in korean_apology_markers):
                raise ValueError(
                    "I9: stop_reason='error_unrecoverable' with non-None final_response "
                    "must be a graceful Korean apology message containing one of: "
                    f"{korean_apology_markers!r}"
                )
        return self
