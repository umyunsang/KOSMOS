# SPDX-License-Identifier: Apache-2.0
"""KFTC OpenGiro secret redaction checks."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ummaya.settings import UmmayaSettings
from ummaya.tools.mock.kftc.opengiro import build_setup_readiness

_ROOT = Path(__file__).resolve().parents[2]
_SCANNED_PATHS = (
    _ROOT / "src/ummaya/tools/mock/kftc/opengiro.py",
    _ROOT / "src/ummaya/settings.py",
    _ROOT / "docs/api/submit/kftc_opengiro.md",
    _ROOT / "specs/2799-kftc-opengiro-send",
    _ROOT / "tests/unit/tools/test_mock_kftc_opengiro.py",
    _ROOT / "tests/integration/test_kftc_opengiro_discovery.py",
)

_FORBIDDEN_VALUE_PATTERNS = (
    re.compile(r"(?i)bearer\s+[a-z0-9._-]{12,}"),
    re.compile(r"(?i)(?<![a-z0-9_])client_secret\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)(?<![a-z0-9_])access_token\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"(?i)authorization:\s*[a-z0-9._-]{12,}"),
)


def _iter_text_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return [
        child
        for child in path.rglob("*")
        if child.is_file()
        and child.suffix in {".md", ".py", ".json"}
        and "__pycache__" not in child.parts
    ]


@pytest.mark.parametrize("pattern", _FORBIDDEN_VALUE_PATTERNS)
def test_kftc_artifacts_do_not_contain_secret_value_patterns(pattern: re.Pattern[str]) -> None:
    offenders: list[str] = []
    for base in _SCANNED_PATHS:
        if not base.exists():
            continue
        for path in _iter_text_files(base):
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                offenders.append(str(path.relative_to(_ROOT)))

    assert offenders == [], f"KFTC secret-like value pattern found in: {offenders}"


def test_readiness_model_does_not_serialize_operator_secret_values() -> None:
    cfg = UmmayaSettings(
        _env_file=None,
        kftc_opengiro_service_enabled=True,
        kftc_opengiro_callback_url="https://operator.example/auth/kftc/opengiro/callback",
        kftc_opengiro_api_key_registered=True,
        kftc_opengiro_client_id="portal-client-id",
        kftc_opengiro_client_secret="redacted-portal-credential",
        kftc_opengiro_access_token="redacted-portal-token",
        kftc_opengiro_documents_accessible=True,
        kftc_opengiro_live_probe_enabled=True,
    )
    payload = build_setup_readiness(cfg).model_dump_json()

    assert "portal-client-id" not in payload
    assert "redacted-portal-credential" not in payload
    assert "redacted-portal-token" not in payload
