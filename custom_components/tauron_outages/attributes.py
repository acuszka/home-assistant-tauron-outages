"""Attribute formatting helpers for Tauron outage entities."""

from __future__ import annotations

from typing import Any

from .api import OutagePeriod


def period_attributes(period: OutagePeriod | None) -> dict[str, Any]:
    """Return Home Assistant attributes for one outage period."""

    if period is None:
        return {}

    return {
        "start": period.start.isoformat() if period.start else None,
        "end": period.end.isoformat() if period.end else None,
        "type": period.outage_type,
        "message": period.message,
        "raw_outage_type": period.raw_outage_type,
    }


def periods_attributes(periods: tuple[OutagePeriod, ...]) -> list[dict[str, Any]]:
    """Return Home Assistant attributes for multiple outage periods."""

    return [period_attributes(period) for period in periods]

