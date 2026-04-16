# SPDX-License-Identifier: Apache-2.0
"""Freshness validation for NMC emergency room responses."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_KST = ZoneInfo("Asia/Seoul")


@dataclass(frozen=True, slots=True)
class FreshnessResult:
    """Result of a freshness check against an hvidate timestamp."""

    is_fresh: bool
    data_age_minutes: float
    threshold_minutes: int
    hvidate_raw: str | None


def check_freshness(
    hvidate_str: str | None,
    threshold_minutes: int | None = None,
) -> FreshnessResult:
    """Check whether an NMC hvidate timestamp is within the freshness threshold.

    Args:
        hvidate_str: The hvidate value from the NMC response (YYYY-MM-DD HH:MM:SS KST).
        threshold_minutes: Maximum acceptable age in minutes. When None, reads
            from settings.nmc_freshness_minutes.

    Returns:
        FreshnessResult with is_fresh=True if data age <= threshold, False otherwise.
        Missing/empty/unparseable hvidate always returns is_fresh=False (fail-closed).
    """
    if threshold_minutes is None:
        from kosmos.settings import settings

        threshold_minutes = settings.nmc_freshness_minutes

    if not hvidate_str or not hvidate_str.strip():
        logger.warning("Missing or empty hvidate — treating as stale (fail-closed)")
        return FreshnessResult(
            is_fresh=False,
            data_age_minutes=float("inf"),
            threshold_minutes=threshold_minutes,
            hvidate_raw=hvidate_str,
        )

    try:
        hvidate = datetime.strptime(hvidate_str.strip(), "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=_KST,
        )
    except (ValueError, TypeError):
        logger.warning("Unparseable hvidate %r — treating as stale (fail-closed)", hvidate_str)
        return FreshnessResult(
            is_fresh=False,
            data_age_minutes=float("inf"),
            threshold_minutes=threshold_minutes,
            hvidate_raw=hvidate_str,
        )

    now = datetime.now(tz=_KST)
    age_minutes = (now - hvidate).total_seconds() / 60.0

    return FreshnessResult(
        is_fresh=age_minutes <= threshold_minutes,
        data_age_minutes=round(age_minutes, 2),
        threshold_minutes=threshold_minutes,
        hvidate_raw=hvidate_str,
    )
