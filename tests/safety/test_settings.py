# SPDX-License-Identifier: Apache-2.0
"""Settings tests — default instantiation, aggregate nesting, and fail-closed coverage.

T013: Default-path assertion (two tests below).
T029: Fail-closed moderation-key coverage (three tests added below).
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from kosmos.safety._settings import SafetySettings
from kosmos.settings import KosmosSettings
from kosmos.tools.errors import ConfigurationError


def test_safety_settings_defaults() -> None:
    s = SafetySettings()
    assert s.redact_tool_output is True
    assert s.injection_detector_enabled is True
    assert s.moderation_enabled is False
    assert s.openai_moderation_api_key is None


def test_kosmos_settings_nests_safety() -> None:
    top = KosmosSettings()
    assert isinstance(top.safety, SafetySettings)
    assert top.safety.redact_tool_output is True


# ---------------------------------------------------------------------------
# T029 — Fail-closed moderation key coverage
# ---------------------------------------------------------------------------


def test_moderation_enabled_without_key_raises_configuration_error() -> None:
    """SafetySettings(moderation_enabled=True) with no key → ConfigurationError."""
    with pytest.raises(ConfigurationError) as exc_info:
        SafetySettings(moderation_enabled=True)  # type: ignore[call-arg]
    err = exc_info.value
    assert err.var_name == "KOSMOS_OPENAI_MODERATION_API_KEY"


def test_moderation_enabled_with_key_constructs() -> None:
    """SafetySettings(moderation_enabled=True, key=...) succeeds; key round-trips."""
    s = SafetySettings(  # type: ignore[call-arg]
        moderation_enabled=True,
        **{"KOSMOS_OPENAI_MODERATION_API_KEY": "sk-test"},
    )
    assert s.moderation_enabled is True
    assert s.openai_moderation_api_key is not None
    assert s.openai_moderation_api_key.get_secret_value() == "sk-test"


def test_api_key_type_is_secretstr() -> None:
    """openai_moderation_api_key is always None or SecretStr, never a plain str."""
    s_default = SafetySettings()
    assert s_default.openai_moderation_api_key is None

    s_with_key = SafetySettings(  # type: ignore[call-arg]
        moderation_enabled=True,
        **{"KOSMOS_OPENAI_MODERATION_API_KEY": "sk-test"},
    )
    assert isinstance(s_with_key.openai_moderation_api_key, SecretStr)
    # Must never be a bare str
    assert not isinstance(s_with_key.openai_moderation_api_key, str)
