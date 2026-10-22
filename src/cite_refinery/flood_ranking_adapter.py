"""Offline, conservative adapter for source-pinned flood-station rankings.

NOT a flood forecasting, risk-calibration or public alert delivery system.
The adapter rejects invalid telemetry with explicit diagnostics; it never emits
public warnings, hides rejected readings, or modifies original upstream code.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class RankedStation:
    station: Any
    relative_level: float


@dataclass(frozen=True)
class RejectedStation:
    station_id: str
    reason: str


@dataclass(frozen=True)
class StationRanking:
    candidates: tuple[RankedStation, ...]
    rejected: tuple[RejectedStation, ...]
    degraded_input: bool


def _finite(value: object) -> float | None:
    # No bool, string, arbitrary float-coercion or unbounded integer overflow.
    if type(value) not in (float, int):
        return None
    try:
        result = float(value)
    except (OverflowError, ValueError):
        return None
    return result if isfinite(result) else None


def inspect_stations(stations: object) -> StationRanking:
    """Sample each station's inputs once; sort deterministically by ID on ties.

    Rejects malformed input rather than producing a misleading ranking. A caller
    MUST consider 'degraded_input' and cannot treat candidates as a public alert.
    """
    if not isinstance(stations, (list, tuple)):
        raise TypeError("Expected finite-length list/tuple of upstream station objects")
    accepted: list[RankedStation] = []
    rejected: list[RejectedStation] = []
    seen: set[str] = set()
    for station in stations:
        sid = getattr(station, "station_id", None)
        if not isinstance(sid, str) or not sid.strip():
            rejected.append(RejectedStation("<unknown>", "invalid_station_id"))
            continue
        if sid in seen:
            raise ValueError("Repeated station ID in same snapshot: " + sid)
        seen.add(sid)
        level = _finite(getattr(station, "latest_level", None))
        if level is None:
            rejected.append(RejectedStation(sid, "invalid_or_nonfinite_water_level"))
            continue
        rng = getattr(station, "typical_range", None)
        if not isinstance(rng, tuple) or len(rng) != 2:
            rejected.append(RejectedStation(sid, "invalid_typical_range"))
            continue
        low, high = _finite(rng[0]), _finite(rng[1])
        if low is None or high is None or high <= low:
            rejected.append(RejectedStation(sid, "invalid_typical_range"))
            continue
        width = high - low
        delta = level - low
        if not isfinite(width) or width <= 0 or not isfinite(delta):
            rejected.append(RejectedStation(sid, "overflowed_relative_range"))
            continue
        ratio = delta / width
        if not isfinite(ratio):
            rejected.append(RejectedStation(sid, "overflowed_relative_level"))
            continue
        accepted.append(RankedStation(station, ratio))
    # No input-order dependence for equal scores across distinct station IDs.
    accepted.sort(key=lambda c: (-c.relative_level, c.station.station_id))
    rejected.sort(key=lambda c: (c.station_id, c.reason))
    return StationRanking(tuple(accepted), tuple(rejected), bool(rejected))


def highest_station_candidates(stations: object, count: int) -> StationRanking:
    if type(count) is not int or count < 0:
        raise ValueError("Top-N count must be a nonnegative integer")
    result = inspect_stations(stations)
    return StationRanking(result.candidates[:count], result.rejected,
                          result.degraded_input)


def stations_above_threshold(stations: object, tolerance: float) -> StationRanking:
    threshold = _finite(tolerance)
    if threshold is None:
        raise ValueError("Threshold must be finite numeric")
    result = inspect_stations(stations)
    return StationRanking(tuple(x for x in result.candidates if x.relative_level > threshold),
                          result.rejected, result.degraded_input)
