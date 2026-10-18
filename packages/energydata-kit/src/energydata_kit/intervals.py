"""Missing-interval, duplicate and grid-alignment detection.

Two kinds of grid are supported:

- **Fixed steps** (``"15min"``, ``"1h"``): a regular grid in UTC. Normalize
  timestamps to UTC first (see :func:`energydata_kit.normalize_timestamps`), so
  that DST transitions do not appear as gaps or duplicates.
- **Local-calendar steps** (pass ``tz=``): any pandas frequency, e.g. ``"D"``,
  ``"W-MON"`` or ``"MS"``, laid out in local wall-clock time and converted to
  UTC. A daily grid in ``Europe/Stockholm`` then has a 23-hour step on the
  spring DST day. Calendar steps are never assumed: without ``tz`` only fixed
  steps are accepted.

By default the grid is anchored at the first timestamp. Pass ``origin`` (a
timezone-aware timestamp) to anchor it elsewhere, so that a leading off-grid
timestamp does not shift the whole grid.
"""

from __future__ import annotations

import datetime as dt
import zoneinfo
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from energydata_kit.timestamps import on_index, utc_ns

__all__ = [
    "Gap",
    "duplicate_mask",
    "expected_grid",
    "find_duplicate_timestamps",
    "find_missing_intervals",
    "missing_timestamps",
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
    ``"MS"`` (month start); grid functions accept those with ``tz=``.
    """
    if isinstance(freq, pd.Timedelta):
        step = freq
    else:
        try:
            step = pd.Timedelta(pd.tseries.frequencies.to_offset(freq).nanos, unit="ns")
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"{freq!r} is not a fixed-length step; pass tz= to use it as a local-calendar step"
            ) from exc
    if step <= pd.Timedelta(0):
        raise ValueError(f"step must be positive, got {step}")
    return step


def _require_aware(index: pd.DatetimeIndex) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"expected a DatetimeIndex, got {type(index).__name__}")
    if index.tz is None:
        raise ValueError("timestamps must be timezone-aware; use normalize_timestamps() first")
    if index.hasnans:
        raise ValueError("timestamps must not contain NaT")


def _aware(ts: pd.Timestamp | str, what: str) -> pd.Timestamp:
    out = pd.Timestamp(ts)
    if out.tz is None:
        raise ValueError(f"{what} must be timezone-aware, got {ts!r}")
    return out


def duplicate_mask(index: pd.DatetimeIndex) -> np.ndarray:
    """Boolean mask marking *every* occurrence of a repeated timestamp."""
    return np.asarray(index.duplicated(keep=False), dtype=bool)


def find_duplicate_timestamps(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Sorted unique timestamps that occur more than once."""
    return pd.DatetimeIndex(index[index.duplicated(keep="first")].unique()).sort_values()


def _check_tz(tz: str | None) -> None:
    """Reject an unknown ``tz`` with ``ValueError`` (zoneinfo raises a ``KeyError`` subclass)."""
    if tz is None or isinstance(tz, dt.tzinfo):
        return
    try:
        zoneinfo.ZoneInfo(tz)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError(f"unknown time zone {tz!r}") from exc


def off_grid_mask(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    *,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
) -> np.ndarray:
    """Mask of timestamps that do not lie on the grid.

    Fixed steps: not aligned to ``origin + k * step``. Calendar steps
    (``tz`` given): not a point of the local-calendar grid. ``origin``
    defaults to the earliest timestamp.
    """
    _require_aware(index)
    _check_tz(tz)
    if len(index) == 0:
        return np.zeros(0, dtype=bool)
    if tz is not None:
        grid = expected_grid(index, freq, origin=origin, tz=tz)
        return ~on_index(index, grid)
    step = to_step(freq).value
    anchor = index.min() if origin is None else _aware(origin, "origin")
    offsets = utc_ns(index) - anchor.as_unit("ns").value
    return np.asarray(offsets % step != 0, dtype=bool)


_DST_WORDS = ("dst", "ambiguous", "nonexistent", "non-existent")


def _local_range(freq: str | pd.Timedelta, **bounds: Any) -> pd.DatetimeIndex:
    """``pd.date_range`` in local time, with a clear error for DST wall-time clashes."""
    try:
        return pd.date_range(freq=freq, **bounds)
    except Exception as exc:  # pandas < 3 raises pytz errors, which are not ValueErrors
        text = f"{type(exc).__name__} {exc}".lower()  # pytz: AmbiguousTimeError, NonExistentTimeError
        if not any(word in text for word in _DST_WORDS):
            raise
        raise ValueError(
            f"the local-calendar grid ({freq!r}) hits a wall-clock time that a DST change skips "
            f"or repeats ({exc}); anchor it at a time of day that occurs once on every day, "
            "e.g. origin= at midnight"
        ) from exc


def expected_grid(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    *,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
) -> pd.DatetimeIndex:
    """Grid timestamps (UTC) between ``start`` and ``end``, inclusive.

    ``start``/``end`` default to the first/last timestamp. With ``origin``,
    the grid runs through ``origin`` and only grid points inside the window
    are returned. With ``tz``, ``freq`` is a local-calendar frequency and
    calendar offsets such as ``"MS"`` snap to their own anchor points.
    """
    _require_aware(index)
    _check_tz(tz)
    if len(index) == 0 and (start is None or end is None):
        return pd.DatetimeIndex([], tz="UTC").as_unit("ns")
    lo = index.min() if start is None else _aware(start, "start")
    hi = index.max() if end is None else _aware(end, "end")
    anchor = None if origin is None else _aware(origin, "origin")

    if tz is not None:
        local_lo, local_hi = lo.tz_convert(tz), hi.tz_convert(tz)
        first = local_lo if anchor is None else anchor.tz_convert(tz)
        grid = _local_range(start=first, end=local_hi, freq=freq) if first <= local_hi else None
        if first > local_lo:
            # The grid also runs back from the origin: extend it until it covers local_lo.
            periods = 2
            back = _local_range(end=first, periods=periods, freq=freq)
            while back[0] > local_lo:
                periods *= 2
                back = _local_range(end=first, periods=periods, freq=freq)
            grid = back if grid is None else back.union(grid)
        if grid is None:
            return pd.DatetimeIndex([], tz="UTC").as_unit("ns")
        grid = grid[(grid >= local_lo) & (grid <= local_hi)]
        return grid.tz_convert("UTC").as_unit("ns")

    step = to_step(freq)
    if anchor is not None:
        step_ns, o = step.value, anchor.as_unit("ns").value
        lo_ns = o - ((o - lo.as_unit("ns").value) // step_ns) * step_ns  # first grid point >= lo
        hi_ns = o + ((hi.as_unit("ns").value - o) // step_ns) * step_ns  # last grid point <= hi
        if lo_ns > hi_ns:
            return pd.DatetimeIndex([], tz="UTC").as_unit("ns")
        lo, hi = pd.Timestamp(lo_ns, unit="ns", tz="UTC"), pd.Timestamp(hi_ns, unit="ns", tz="UTC")
    return pd.date_range(lo, hi, freq=step).tz_convert("UTC").as_unit("ns")


def find_missing_intervals(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    *,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
) -> list[Gap]:
    """Return runs of grid timestamps that are absent from ``index``.

    Duplicates and off-grid timestamps neither fill nor create gaps; detect
    them separately with :func:`duplicate_mask` and :func:`off_grid_mask`.
    """
    grid = expected_grid(index, freq, start=start, end=end, origin=origin, tz=tz)
    if len(grid) == 0:
        return []
    return _gaps(grid, on_index(grid, index))


def _gaps(grid: pd.DatetimeIndex, present: np.ndarray) -> list[Gap]:
    """Runs of grid timestamps where ``present`` (aligned with ``grid``) is false."""
    missing_pos = np.flatnonzero(~present)
    if missing_pos.size == 0:
        return []
    breaks = np.flatnonzero(np.diff(missing_pos) > 1) + 1
    return [
        Gap(start=grid[run[0]], end=grid[run[-1]], missing_count=int(run.size))
        for run in np.split(missing_pos, breaks)
    ]


def missing_timestamps(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    *,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
) -> pd.DatetimeIndex:
    """Every absent grid timestamp (UTC), in order."""
    grid = expected_grid(index, freq, start=start, end=end, origin=origin, tz=tz)
    return grid[~on_index(grid, index)]
