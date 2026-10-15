"""Missing-interval, duplicate and grid-alignment detection.

These functions work on a fixed-step grid (e.g. 15 minutes, 1 hour). Normalize
timestamps to UTC first (see :func:`energydata_kit.normalize_timestamps`), so
that DST transitions do not appear as gaps or duplicates.

Calendar steps whose length varies (months, local calendar days) are out of
scope for this version.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from energydata_kit.timestamps import utc_ns

__all__ = [
    "Gap",
    "duplicate_mask",
    "expected_grid",
    "find_duplicate_timestamps",
    "find_missing_intervals",
    "off_grid_mask",
    "to_step",
]


@dataclass(frozen=True)
class Gap:
    """A run of consecutive expected timestamps that are absent.

    ``start`` and ``end`` are the first and last *missing* timestamps
    (inclusive), so a single missing interval has ``start == end``.
    """

    start: pd.Timestamp
    end: pd.Timestamp
    missing_count: int


def to_step(freq: str | pd.Timedelta) -> pd.Timedelta:
    """Convert a fixed frequency (``"15min"``, ``"1h"``, ``Timedelta``) to a ``Timedelta``.

    Raises ``ValueError`` for non-positive or variable-length steps such as
    ``"MS"`` (month start).
    """
    if isinstance(freq, pd.Timedelta):
        step = freq
    else:
        try:
            step = pd.Timedelta(pd.tseries.frequencies.to_offset(freq).nanos, unit="ns")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{freq!r} is not a fixed-length step") from exc
    if step <= pd.Timedelta(0):
        raise ValueError(f"step must be positive, got {step}")
    return step


def _require_aware(index: pd.DatetimeIndex) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"expected a DatetimeIndex, got {type(index).__name__}")
    if index.tz is None:
        raise ValueError("timestamps must be timezone-aware; use normalize_timestamps() first")


def duplicate_mask(index: pd.DatetimeIndex) -> np.ndarray:
    """Boolean mask marking *every* occurrence of a repeated timestamp."""
    return np.asarray(index.duplicated(keep=False), dtype=bool)


def find_duplicate_timestamps(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Sorted unique timestamps that occur more than once."""
    return pd.DatetimeIndex(index[index.duplicated(keep="first")].unique()).sort_values()


def off_grid_mask(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    origin: pd.Timestamp | None = None,
) -> np.ndarray:
    """Mask of timestamps not aligned to ``origin + k * step``.

    ``origin`` defaults to the earliest timestamp.
    """
    _require_aware(index)
    if len(index) == 0:
        return np.zeros(0, dtype=bool)
    step = to_step(freq).value
    anchor = (index.min() if origin is None else pd.Timestamp(origin)).as_unit("ns").value
    offsets = utc_ns(index) - anchor
    return np.asarray(offsets % step != 0, dtype=bool)


def expected_grid(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> pd.DatetimeIndex:
    """The regular grid from ``start`` (default: first timestamp) to ``end`` (default: last)."""
    _require_aware(index)
    if len(index) == 0 and (start is None or end is None):
        return pd.DatetimeIndex([], tz=index.tz).as_unit("ns")
    lo = index.min() if start is None else pd.Timestamp(start)
    hi = index.max() if end is None else pd.Timestamp(end)
    return pd.date_range(lo, hi, freq=to_step(freq)).as_unit("ns")


def find_missing_intervals(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> list[Gap]:
    """Return runs of grid timestamps that are absent from ``index``.

    Duplicates and off-grid timestamps neither fill nor create gaps; detect
    them separately with :func:`duplicate_mask` and :func:`off_grid_mask`.
    """
    grid = expected_grid(index, freq, start, end)
    if len(grid) == 0:
        return []
    present = grid.isin(index.as_unit("ns"))
    missing_pos = np.flatnonzero(~present)
    if missing_pos.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(missing_pos) > 1) + 1
    gaps = []
    for run in np.split(missing_pos, breaks):
        gaps.append(Gap(start=grid[run[0]], end=grid[run[-1]], missing_count=int(run.size)))
    return gaps
