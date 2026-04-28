# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.tools.kma.kma_current_observation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import ValidationError

from kosmos.tools.errors import ConfigurationError, ToolExecutionError
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.kma.kma_current_observation import (
    KMA_CURRENT_OBSERVATION_TOOL,
    KmaCurrentObservationInput,
    KmaCurrentObservationOutput,
    _call,
    _parse_response,
    _pivot_rows_to_output,
    register,
)
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text())


def _make_mock_client(fixture_data: dict) -> httpx.AsyncClient:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = fixture_data
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# TestKmaCurrentObservationInput
# ---------------------------------------------------------------------------


class TestKmaCurrentObservationInput:
    def test_valid_construction(self):
        params = KmaCurrentObservationInput(
            base_date="20260413",
            base_time="0600",
            nx=61,
            ny=126,
        )
        assert params.base_date == "20260413"
        assert params.base_time == "0600"
        assert params.nx == 61
        assert params.ny == 126
        assert params.num_of_rows == 10
        assert params.page_no == 1
        assert params.data_type == "JSON"

    def test_base_time_rounds_down(self):
        """Minutes are stripped; '0610' must become '0600'."""
        params = KmaCurrentObservationInput(
            base_date="20260413",
            base_time="0610",
            nx=61,
            ny=126,
        )
        assert params.base_time == "0600"

    def test_base_time_already_rounded(self):
        """'0600' is already on the hour and must be preserved as-is."""
        params = KmaCurrentObservationInput(
            base_date="20260413",
            base_time="0600",
            nx=61,
            ny=126,
        )
        assert params.base_time == "0600"

    def test_invalid_base_date_format(self):
        """A date with dashes must raise ValidationError."""
        with pytest.raises(ValidationError):
            KmaCurrentObservationInput(
                base_date="2026-04-13",
                base_time="0600",
                nx=61,
                ny=126,
            )

    def test_grid_bounds_nx_min(self):
        """nx=1 is the minimum valid value."""
        params = KmaCurrentObservationInput(base_date="20260413", base_time="0600", nx=1, ny=1)
        assert params.nx == 1

    def test_grid_bounds_nx_max(self):
        """nx=149 is the maximum valid value."""
        params = KmaCurrentObservationInput(base_date="20260413", base_time="0600", nx=149, ny=253)
        assert params.nx == 149

    def test_grid_bounds_nx_too_large(self):
        """nx=150 must raise ValidationError."""
        with pytest.raises(ValidationError):
            KmaCurrentObservationInput(base_date="20260413", base_time="0600", nx=150, ny=126)

    def test_grid_bounds_ny_too_large(self):
        """ny=254 must raise ValidationError."""
        with pytest.raises(ValidationError):
            KmaCurrentObservationInput(base_date="20260413", base_time="0600", nx=61, ny=254)


# ---------------------------------------------------------------------------
# TestRn1Normalization
# ---------------------------------------------------------------------------


class TestRn1Normalization:
    """KmaCurrentObservationOutput.rn1 field_validator normalises null forms."""

    def test_dash_normalized_to_zero(self):
        out = KmaCurrentObservationOutput(
            base_date="20260413", base_time="0600", nx=61, ny=126, rn1="-"
        )
        assert out.rn1 == 0.0

    def test_none_normalized_to_zero(self):
        out = KmaCurrentObservationOutput(
            base_date="20260413", base_time="0600", nx=61, ny=126, rn1=None
        )
        assert out.rn1 == 0.0

    def test_empty_string_normalized_to_zero(self):
        out = KmaCurrentObservationOutput(
            base_date="20260413", base_time="0600", nx=61, ny=126, rn1=""
        )
        assert out.rn1 == 0.0

    def test_numeric_string_preserved(self):
        out = KmaCurrentObservationOutput(
            base_date="20260413", base_time="0600", nx=61, ny=126, rn1="5.5"
        )
        assert out.rn1 == 5.5

    def test_zero_string(self):
        out = KmaCurrentObservationOutput(
            base_date="20260413", base_time="0600", nx=61, ny=126, rn1="0"
        )
        assert out.rn1 == 0.0


# ---------------------------------------------------------------------------
# TestPivotRowsToOutput
# ---------------------------------------------------------------------------


class TestPivotRowsToOutput:
    """_pivot_rows_to_output converts row format to flat model."""

    _BASE = {
        "baseDate": "20260413",
        "baseTime": "0600",
        "nx": 61,
        "ny": 126,
    }

    def _make_rows(self, overrides: dict | None = None) -> list[dict]:
        base = [
            {**self._BASE, "category": "T1H", "obsrValue": "12.3"},
            {**self._BASE, "category": "RN1", "obsrValue": "0"},
            {**self._BASE, "category": "UUU", "obsrValue": "-1.2"},
            {**self._BASE, "category": "VVV", "obsrValue": "2.5"},
            {**self._BASE, "category": "WSD", "obsrValue": "3.1"},
            {**self._BASE, "category": "REH", "obsrValue": "65"},
            {**self._BASE, "category": "PTY", "obsrValue": "0"},
            {**self._BASE, "category": "VEC", "obsrValue": "220"},
        ]
        if overrides:
            for row in base:
                if row["category"] in overrides:
                    row["obsrValue"] = overrides[row["category"]]
        return base

    def test_full_observation(self):
        """All 8 categories present produce a fully populated output model."""
        rows = self._make_rows()
        out = _pivot_rows_to_output(rows)
        assert out.base_date == "20260413"
        assert out.base_time == "0600"
        assert out.nx == 61
        assert out.ny == 126
        assert out.t1h == 12.3
        assert out.rn1 == 0.0
        assert out.uuu == -1.2
        assert out.vvv == 2.5
        assert out.wsd == 3.1
        assert out.reh == 65.0
        assert out.pty == 0
        assert out.vec == 220.0

    def test_rn1_dash_handling(self):
        """RN1='-' sentinel is normalised to 0.0 by the field_validator."""
        rows = self._make_rows({"RN1": "-"})
        out = _pivot_rows_to_output(rows)
        assert out.rn1 == 0.0


# ---------------------------------------------------------------------------
# TestParseResponse
# ---------------------------------------------------------------------------


class TestParseResponse:
    def test_success(self):
        """Load the success fixture and assert all output fields."""
        data = _load_fixture("kma_obs_success.json")
        out = _parse_response(data)
        assert out.base_date == "20260413"
        assert out.base_time == "0600"
        assert out.nx == 61
        assert out.ny == 126
        assert out.t1h == 12.3
        assert out.rn1 == 0.0
        assert out.pty == 0
        assert out.vec == 220.0

    def test_error_raises(self):
        """An error response fixture raises ToolExecutionError."""
        data = _load_fixture("kma_obs_error.json")
        with pytest.raises(ToolExecutionError) as exc_info:
            _parse_response(data)
        assert "03" in str(exc_info.value)

    def test_rn1_dash_fixture(self):
        """Load the RN1-dash fixture and confirm rn1==0.0."""
        data = _load_fixture("kma_obs_rn1_dash.json")
        out = _parse_response(data)
        assert out.rn1 == 0.0


# ---------------------------------------------------------------------------
# TestCall
# ---------------------------------------------------------------------------


class TestCall:
    @pytest.mark.asyncio
    async def test_success_flow(self, monkeypatch):
        """_call with a mocked httpx client returns a dict matching output schema."""
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-abc")
        fixture_data = _load_fixture("kma_obs_success.json")
        mock_client = _make_mock_client(fixture_data)

        params = KmaCurrentObservationInput(base_date="20260413", base_time="0600", nx=61, ny=126)
        result = await _call(params, client=mock_client)

        assert isinstance(result, dict)
        assert result["base_date"] == "20260413"
        assert result["t1h"] == 12.3
        assert result["rn1"] == 0.0
        assert result["pty"] == 0

    @pytest.mark.asyncio
    async def test_missing_api_key(self, monkeypatch):
        """Absent KOSMOS_DATA_GO_KR_API_KEY raises ConfigurationError."""
        monkeypatch.delenv("KOSMOS_DATA_GO_KR_API_KEY", raising=False)

        params = KmaCurrentObservationInput(base_date="20260413", base_time="0600", nx=61, ny=126)
        with pytest.raises(ConfigurationError):
            await _call(params)


# ---------------------------------------------------------------------------
# TestToolDefinition
# ---------------------------------------------------------------------------


class TestToolDefinition:
    def test_tool_id(self):
        assert KMA_CURRENT_OBSERVATION_TOOL.id == "kma_current_observation"

    def test_is_core_true(self):
        assert KMA_CURRENT_OBSERVATION_TOOL.is_core is True

    def test_provider(self):
        assert KMA_CURRENT_OBSERVATION_TOOL.ministry == "KMA"

    def test_cache_ttl(self):
        assert KMA_CURRENT_OBSERVATION_TOOL.cache_ttl_seconds == 600

    # test_not_personal_data removed in Epic δ #2295 — is_personal_data field deleted
    # from GovAPITool as Spec 033 KOSMOS-invented residue (Constitution § II).


# ---------------------------------------------------------------------------
# TestRegister
# ---------------------------------------------------------------------------


class TestRegister:
    def test_register_adds_to_registry_and_executor(self):
        """register() wires the tool into both registry and executor."""
        registry = ToolRegistry()
        executor = ToolExecutor(registry)

        register(registry, executor)

        assert "kma_current_observation" in registry
        assert registry.lookup("kma_current_observation") is KMA_CURRENT_OBSERVATION_TOOL
        assert "kma_current_observation" in executor._adapters
