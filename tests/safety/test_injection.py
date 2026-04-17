# SPDX-License-Identifier: Apache-2.0
"""Tests for the indirect-prompt-injection detector (US2 / Phase 4).

Validates T021 fixtures and ensures clean tool outputs do not false-positive
(SC-004).  Tests are written before _injection.py exists (T022) so they fail
on first run and become the acceptance gate for T023.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kosmos.safety._injection import run_detector

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "safety"
INJECTION_SAMPLES_PATH = FIXTURES_DIR / "injection_samples.json"


def _load_injection_samples() -> list[dict]:
    return json.loads(INJECTION_SAMPLES_PATH.read_text(encoding="utf-8"))


INJECTION_SAMPLES = _load_injection_samples()


# ---------------------------------------------------------------------------
# Block fixtures — all 10 must produce decision == "block"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sample", INJECTION_SAMPLES, ids=[s["id"] for s in INJECTION_SAMPLES])
def test_block_fixtures(sample: dict) -> None:
    """Every injection fixture must be blocked by the detector."""
    result = run_detector(sample["input_text"])
    assert result.decision == "block", (
        f"[{sample['id']}] expected 'block' but got '{result.decision}'. "
        f"structural={result.structural_score:.3f}, "
        f"entropy={result.entropy_score:.3f}, "
        f"length_deviation={result.length_deviation:.3f}"
    )
    assert result.structural_score >= 0.0
    assert result.entropy_score >= 0.0
    assert result.length_deviation >= 0.0


# ---------------------------------------------------------------------------
# Allow fixtures — 4 clean real-world tool output shapes must NOT be blocked
# ---------------------------------------------------------------------------

_KOROAD_HAZARD_RECORD = (
    '{"spot_cd": "1168010800", "spot_nm": "서울특별시 강남구 개포동 일대", '
    '"sido_sgg_nm": "서울특별시 강남구", "occrrnc_cnt": 12, "caslt_cnt": 15, '
    '"dth_dnv_cnt": 1, "la_crd": 37.479, "lo_crd": 127.058}'
)

_KMA_FORECAST_PARAGRAPH = (
    "오늘 서울의 날씨 예보입니다. 기온은 최저 9도에서 최고 19도 사이로 예상됩니다. "
    "오전에는 맑은 날씨가 이어지겠으나, 오후부터 구름이 많아지겠습니다. "
    "강수확률은 10%로 매우 낮으며, 바람은 초속 2.5m로 약하게 불겠습니다. "
    "SKY=1, PTY=0, POP=10, TMP=14, WSD=2.5, REH=55 — NORMAL_CODE 00."
)

_HIRA_HOSPITAL_LIST = (
    '[{"ykiho": "JDQ5Mzg=", "yadmNm": "서울대학교병원", '
    '"addr": "서울특별시 종로구 대학로 101", "telno": "02-2072-2114", '
    '"clCdNm": "상급종합", "XPos": "126.998", "YPos": "37.5797", "distance": "843"}, '
    '{"ykiho": "JDQ1NjE=", "yadmNm": "서울특별시보라매병원", '
    '"addr": "서울특별시 동작구 보라매로5길 20", "telno": "02-840-2114", '
    '"clCdNm": "상급종합", "XPos": "126.924", "YPos": "37.4946", "distance": "1254"}]'
)

_NMC_EMERGENCY_STATUS = (
    '{"dutyName": "서울대학교병원 응급의료센터", '
    '"dutyAddr": "서울특별시 종로구 대학로 101", "dutyTel3": "02-2072-2222", '
    '"hvec": 5, "hvoc": 3, "hvs1": 2, '
    '"wgs84Lat": 37.5796, "wgs84Lon": 127.001, "hvidate": "2026-04-16 14:00:00"}'
)

_ALLOW_CASES = [
    ("koroad_hazard_record", _KOROAD_HAZARD_RECORD),
    ("kma_forecast_paragraph", _KMA_FORECAST_PARAGRAPH),
    ("hira_hospital_list_korean", _HIRA_HOSPITAL_LIST),
    ("nmc_emergency_room_hvidate", _NMC_EMERGENCY_STATUS),
]


@pytest.mark.parametrize("label,text", _ALLOW_CASES, ids=[c[0] for c in _ALLOW_CASES])
def test_allow_clean_outputs(label: str, text: str) -> None:
    """Clean tool outputs must NOT be blocked (SC-004 false-positive guard)."""
    result = run_detector(text)
    assert result.decision == "allow", (
        f"[{label}] False positive — clean output was blocked. "
        f"structural={result.structural_score:.3f}, "
        f"entropy={result.entropy_score:.3f}, "
        f"length_deviation={result.length_deviation:.3f}"
    )
