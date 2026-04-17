# SPDX-License-Identifier: Apache-2.0
"""Unit tests for GovAPITool and ToolResult validation in kosmos.tools.models."""

import pytest
from pydantic import BaseModel, ValidationError

from kosmos.tools.models import GovAPITool, ToolResult

# ---------------------------------------------------------------------------
# Helper: minimal valid GovAPITool kwargs (without factory fixture)
# ---------------------------------------------------------------------------


class _MinimalInput(BaseModel):
    q: str


class _MinimalOutput(BaseModel):
    result: str


_MINIMAL_KWARGS = {
    "id": "test_tool",
    "name_ko": "테스트도구",
    "provider": "테스트기관",
    "category": ["test"],
    "endpoint": "https://apis.data.go.kr/test",
    # V6: auth_type='public' is consistent with auth_level='public'.
    # (api_key requires AAL1+; use 'public' for a no-auth test stub.)
    "auth_type": "public",
    "input_schema": _MinimalInput,
    "output_schema": _MinimalOutput,
    "search_hint": "test 테스트 sample",
    "auth_level": "public",
    "pipa_class": "non_personal",
    "is_irreversible": False,
    "dpa_reference": None,
    # Spec-024 V5 biconditional: auth_level='public' ⇔ requires_auth==False.
    "requires_auth": False,
    # FR-038: pipa_class='non_personal' ⇒ no PII → is_personal_data=False.
    "is_personal_data": False,
}


def _make(**overrides) -> GovAPITool:
    """Build a GovAPITool from _MINIMAL_KWARGS with optional field overrides."""
    return GovAPITool(**{**_MINIMAL_KWARGS, **overrides})


# ===========================================================================
# GovAPITool — fail-closed defaults
# ===========================================================================


class TestFailClosedDefaults:
    def test_fail_closed_defaults(self, sample_tool_factory):
        """All boolean security fields must default to the restrictive value.

        Under Spec-024 V5 the factory's public defaults are auto-aligned to
        requires_auth=False / is_personal_data=False (public tools cannot
        require auth). To exercise the *model-level* fail-closed defaults we
        request an AAL1 PII-class tool so the True/True model defaults apply.
        """
        tool = sample_tool_factory(
            auth_level="AAL1",
            pipa_class="personal",
            dpa_reference="dpa-mock-fail-closed",
        )

        assert tool.requires_auth is True
        assert tool.is_personal_data is True
        assert tool.is_concurrency_safe is False
        assert tool.cache_ttl_seconds == 0
        assert tool.rate_limit_per_minute == 10
        assert tool.is_core is False

    def test_explicit_overrides(self, sample_tool_factory):
        """Caller-supplied values must override every security default."""
        # V6: auth_type='public' permits auth_level='public' + requires_auth=False.
        tool = sample_tool_factory(
            auth_type="public",
            auth_level="public",
            requires_auth=False,
            is_personal_data=False,
            is_concurrency_safe=True,
            cache_ttl_seconds=300,
            rate_limit_per_minute=60,
            is_core=True,
        )

        assert tool.requires_auth is False
        assert tool.is_personal_data is False
        assert tool.is_concurrency_safe is True
        assert tool.cache_ttl_seconds == 300
        assert tool.rate_limit_per_minute == 60
        assert tool.is_core is True


# ===========================================================================
# GovAPITool — id validation
# ===========================================================================


class TestIdValidation:
    @pytest.mark.parametrize(
        "valid_id",
        [
            "kma_weather",
            "a",
            "abc123",
            "koroad_accident_search",
        ],
    )
    def test_valid_id_patterns(self, valid_id):
        """IDs that match ^[a-z][a-z0-9_]*$ must be accepted without error."""
        tool = _make(id=valid_id)
        assert tool.id == valid_id

    def test_invalid_id_uppercase(self):
        """IDs containing uppercase letters must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make(id="KMA_Weather")

    def test_invalid_id_starts_with_number(self):
        """IDs that start with a digit must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make(id="123abc")

    def test_invalid_id_special_chars(self):
        """IDs with hyphens or special chars must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make(id="kma-weather")

    def test_invalid_id_empty(self):
        """An empty string must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make(id="")


# ===========================================================================
# GovAPITool — category validation
# ===========================================================================


class TestCategoryValidation:
    def test_empty_category_raises(self):
        """An empty category list must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make(category=[])


# ===========================================================================
# GovAPITool — other field validations
# ===========================================================================


class TestOtherValidations:
    def test_invalid_rate_limit_zero(self):
        """rate_limit_per_minute=0 must raise ValidationError (must be > 0)."""
        with pytest.raises(ValidationError):
            _make(rate_limit_per_minute=0)

    def test_invalid_cache_ttl_negative(self):
        """cache_ttl_seconds=-1 must raise ValidationError (must be >= 0)."""
        with pytest.raises(ValidationError):
            _make(cache_ttl_seconds=-1)

    def test_empty_search_hint_raises(self):
        """An empty search_hint string must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make(search_hint="")

    def test_whitespace_only_search_hint_raises(self):
        """A whitespace-only search_hint must raise ValidationError."""
        with pytest.raises(ValidationError):
            _make(search_hint="   ")


# ===========================================================================
# GovAPITool — to_openai_tool
# ===========================================================================


class TestToOpenAITool:
    def test_to_openai_tool_format(self, sample_tool_factory):
        """to_openai_tool() must return a well-formed OpenAI function definition."""
        tool = sample_tool_factory()
        result = tool.to_openai_tool()

        assert result["type"] == "function"
        func = result["function"]
        assert func["name"] == tool.id
        assert func["description"] == tool.name_ko
        assert "properties" in func["parameters"]

    def test_to_openai_tool_name_matches_id(self):
        """to_openai_tool() 'name' must equal the tool's id field exactly."""
        tool = _make(id="hira_hospital_info")
        result = tool.to_openai_tool()

        assert result["function"]["name"] == "hira_hospital_info"

    def test_to_openai_tool_description_matches_name_ko(self):
        """to_openai_tool() 'description' must equal name_ko verbatim."""
        tool = _make(name_ko="병원정보조회")
        result = tool.to_openai_tool()

        assert result["function"]["description"] == "병원정보조회"

    def test_to_openai_tool_parameters_is_json_schema(self):
        """'parameters' must be the JSON Schema dict produced by input_schema."""
        tool = _make()
        result = tool.to_openai_tool()
        parameters = result["function"]["parameters"]

        # Must be a dict with at least the JSON Schema 'properties' key
        assert isinstance(parameters, dict)
        assert "properties" in parameters


# ===========================================================================
# ToolResult
# ===========================================================================


class TestToolResult:
    def test_tool_result_success(self):
        """A successful ToolResult must carry data and have no error fields set."""
        result = ToolResult(
            tool_id="kma_weather_forecast",
            success=True,
            data={"temperature": 22.5, "condition": "맑음", "humidity": 45},
        )

        assert result.tool_id == "kma_weather_forecast"
        assert result.success is True
        assert result.data == {"temperature": 22.5, "condition": "맑음", "humidity": 45}
        assert result.error is None
        assert result.error_type is None

    def test_tool_result_failure(self):
        """A failed ToolResult must carry error and error_type with no data."""
        result = ToolResult(
            tool_id="kma_weather_forecast",
            success=False,
            error="Upstream API returned 503",
            error_type="execution",
        )

        assert result.tool_id == "kma_weather_forecast"
        assert result.success is False
        assert result.data is None
        assert result.error == "Upstream API returned 503"
        assert result.error_type == "execution"

    def test_tool_result_all_error_types_accepted(self):
        """All documented error_type literals must be accepted by ToolResult."""
        valid_error_types = [
            "validation",
            "rate_limit",
            "not_found",
            "execution",
            "schema_mismatch",
        ]
        for error_type in valid_error_types:
            result = ToolResult(
                tool_id="test_tool",
                success=False,
                error="some error",
                error_type=error_type,
            )
            assert result.error_type == error_type

    def test_tool_result_unknown_error_type_raises(self):
        """An unrecognised error_type literal must raise ValidationError."""
        with pytest.raises(ValidationError):
            ToolResult(
                tool_id="test_tool",
                success=False,
                error="some error",
                error_type="unknown_type",
            )
