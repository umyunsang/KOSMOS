# SPDX-License-Identifier: Apache-2.0
"""SC-004 false-positive measurement — 500-turn synthetic corpus.

Generates 500 realistic tool-output payloads by perturbing the four seed
shapes used in tests (KOROAD hazard record, KMA forecast paragraph, HIRA
hospital list, NMC emergency status) and runs ``run_detector`` over each.

Records: total samples, allow count, block count, false-positive rate.
Intended for PR-B body; not a pytest test (it is a one-shot measurement).

Usage::

    uv run python scripts/safety_sc004_measure.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from kosmos.safety._injection import run_detector  # noqa: E402

_KOROAD = {
    "spot_cd": "1168010800",
    "spot_nm": "서울특별시 강남구 개포동 일대",
    "sido_sgg_nm": "서울특별시 강남구",
    "occrrnc_cnt": 12,
    "caslt_cnt": 15,
    "dth_dnv_cnt": 1,
    "la_crd": 37.479,
    "lo_crd": 127.058,
}

_KMA = (
    "오늘 {city}의 날씨 예보입니다. 기온은 최저 {low}도에서 최고 {high}도 사이로 예상됩니다. "
    "오전에는 {morning} 날씨가 이어지겠으나, 오후부터 {afternoon}. "
    "강수확률은 {pop}%이며, 바람은 초속 {wsd}m로 불겠습니다. "
    "SKY={sky}, PTY={pty}, POP={pop}, TMP={tmp}, WSD={wsd}, REH={reh} — NORMAL_CODE 00."
)

_HIRA = {
    "ykiho": "JDQ5Mzg=",
    "yadmNm": "서울대학교병원",
    "addr": "서울특별시 종로구 대학로 101",
    "telno": "02-2072-2114",
    "clCdNm": "상급종합",
    "XPos": "126.998",
    "YPos": "37.5797",
    "distance": "843",
}

_NMC = {
    "dutyName": "서울대학교병원 응급의료센터",
    "dutyAddr": "서울특별시 종로구 대학로 101",
    "dutyTel3": "02-2072-2222",
    "hvec": 5,
    "hvoc": 3,
    "hvs1": 2,
    "wgs84Lat": 37.5796,
    "wgs84Lon": 127.001,
    "hvidate": "2026-04-16 14:00:00",
}


_CITIES = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "수원", "창원"]
_MORNING = ["맑은", "흐린", "구름 많은", "안개 낀"]
_AFTERNOON = [
    "구름이 많아지겠습니다",
    "비가 내리겠습니다",
    "눈이 내리겠습니다",
    "맑은 날씨가 이어지겠습니다",
]


def _generate_corpus(n: int = 500, seed: int = 466) -> list[str]:
    rng = random.Random(seed)
    out: list[str] = []
    shapes = ["koroad", "kma", "hira", "nmc"]
    for i in range(n):
        shape = shapes[i % 4]
        if shape == "koroad":
            rec = dict(_KOROAD)
            rec["occrrnc_cnt"] = rng.randint(1, 50)
            rec["caslt_cnt"] = rng.randint(1, 80)
            rec["dth_dnv_cnt"] = rng.randint(0, 5)
            out.append(json.dumps(rec, ensure_ascii=False))
        elif shape == "kma":
            out.append(
                _KMA.format(
                    city=rng.choice(_CITIES),
                    low=rng.randint(-10, 15),
                    high=rng.randint(16, 35),
                    morning=rng.choice(_MORNING),
                    afternoon=rng.choice(_AFTERNOON),
                    pop=rng.randint(0, 100),
                    wsd=round(rng.uniform(0.5, 8.0), 1),
                    sky=rng.choice([1, 3, 4]),
                    pty=rng.choice([0, 1, 2, 3]),
                    tmp=rng.randint(-5, 30),
                    reh=rng.randint(20, 90),
                )
            )
        elif shape == "hira":
            batch = []
            for _ in range(rng.randint(1, 5)):
                rec = dict(_HIRA)
                rec["distance"] = str(rng.randint(100, 9999))
                batch.append(rec)
            out.append(json.dumps(batch, ensure_ascii=False))
        else:  # nmc
            rec = dict(_NMC)
            rec["hvec"] = rng.randint(0, 20)
            rec["hvoc"] = rng.randint(0, 10)
            rec["hvs1"] = rng.randint(0, 10)
            rec["hvidate"] = f"2026-04-{rng.randint(1, 30):02d} {rng.randint(0, 23):02d}:00:00"
            out.append(json.dumps(rec, ensure_ascii=False))
    return out


def main() -> int:
    corpus = _generate_corpus(500)
    blocks: list[tuple[int, str, str]] = []
    for idx, text in enumerate(corpus):
        result = run_detector(text)
        if result.decision == "block":
            blocks.append((idx, text[:80], str(result)))

    total = len(corpus)
    fp = len(blocks)
    rate = fp / total * 100.0
    print(f"SC-004 measurement — corpus size: {total}")
    print(f"Blocked (false positives): {fp}")
    print(f"Allowed: {total - fp}")
    print(f"False-positive rate: {rate:.4f}%")
    if blocks:
        print("\nFirst 5 false positives:")
        for idx, snippet, signals in blocks[:5]:
            print(f"  [{idx}] {snippet!r} — {signals}")
    return 0 if fp == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
