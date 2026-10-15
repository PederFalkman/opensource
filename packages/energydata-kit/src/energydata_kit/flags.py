"""Explicit, non-destructive quality flags.

Flags are stored as an integer bitmask alongside the original values. No
check in this module modifies, drops, fills or reorders input values.
"""

from __future__ import annotations

from collections.abc import Collection
from enum import IntFlag

import numpy as np
import pandas as pd

from energydata_kit.intervals import duplicate_mask, missing_timestamps, off_grid_mask

__all__ = [
    "FLAG_COLUMN",
    "VALUE_COLUMN",
    "QualityFlag",
    "counter_decrease_mask",
    "decode_flags",
    "flag_series",
    "missing_value_mask",
    "non_finite_mask",
    "non_numeric_mask",
    "out_of_bounds_mask",
    "stale_mask",
]

VALUE_COLUMN = "value"
FLAG_COLUMN = "quality_flag"


class QualityFlag(IntFlag):
    """Bitmask of quality issues. Values are part of the public, stable API."""

    OK = 0
    MISSING_VALUE = 1  # NaN / None / NA at an existing timestamp
    NON_FINITE = 2  # +inf or -inf
    NON_NUMERIC = 4  # value cannot be interpreted as a number
    DUPLICATE_TIMESTAMP = 8  # timestamp occurs more than once (all occurrences)
    OFF_GRID_TIMESTAMP = 16  # timestamp not aligned to the expected step
    OUT_OF_BOUNDS = 32  # finite value outside caller-supplied bounds
    MISSING_INTERVAL = 64  # row inserted for an absent grid timestamp
    STALE_VALUE = 128  # part of a run of repeated values (opt-in)
    COUNTER_DECREASE = 256  # cumulative counter went down (opt-in)


def decode_flags(value: int) -> list[str]:
    """Names of the flags set in ``value``, in bit order; ``["OK"]`` for 0."""
    flag = QualityFlag(int(value))
    if flag == QualityFlag.OK:
        return ["OK"]
    return [m.name for m in QualityFlag if m.value and flag & m and m.name is not None]


def _as_series(values: pd.Series | np.ndarray | list[object]) -> pd.Series:
    return values if isinstance(values, pd.Series) else pd.Series(values, dtype=object)


def _numeric(values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").astype("float64")


def missing_value_mask(values: pd.Series | np.ndarray | list[object]) -> np.ndarray:
    """True where the value is NaN, None or pandas NA."""
    return np.asarray(_as_series(values).isna(), dtype=bool)


def non_numeric_mask(values: pd.Series | np.ndarray | list[object]) -> np.ndarray:
    """True where a non-missing value cannot be converted to a number."""
    s = _as_series(values)
    return np.asarray(s.notna() & _numeric(s).isna(), dtype=bool)


def non_finite_mask(values: pd.Series | np.ndarray | list[object]) -> np.ndarray:
    """True where the value is ``+inf`` or ``-inf``."""
    return np.asarray(np.isinf(_numeric(_as_series(values)).to_numpy()), dtype=bool)


def out_of_bounds_mask(
    values: pd.Series | np.ndarray | list[object],
    lower: float | None = None,
    upper: float | None = None,
) -> np.ndarray:
    """True where a finite value lies outside the inclusive range ``[lower, upper]``.

    Bounds are supplied by the caller; the package ships no domain limits.
    """
    if lower is not None and upper is not None and lower > upper:
        raise ValueError(f"lower bound {lower} exceeds upper bound {upper}")
    v = _numeric(_as_series(values)).to_numpy()
    finite = np.isfinite(v)
    mask = np.zeros(v.shape, dtype=bool)
    if lower is not None:
        mask |= finite & (v < lower)
    if upper is not None:
        mask |= finite & (v > upper)
    return mask


def stale_mask(
    values: pd.Series | np.ndarray | list[object],
    min_run: int,
    *,
    atol: float = 0.0,
    exclude: Collection[float] = (),
) -> np.ndarray:
    """True for every value in a run of at least ``min_run`` consecutive repeated values.

    Values are compared in row order: a run continues while each finite value
    differs from the previous one by at most ``atol``. Missing or non-finite
    values end a run and are never flagged. Runs whose values are in
    ``exclude`` (e.g. ``0.0`` for generation at night) are not flagged. Time
    gaps between rows are not considered; check gaps separately.
    """
    if min_run < 2:
        raise ValueError("min_run must be >= 2")
    if atol < 0:
        raise ValueError("atol must be >= 0")
    v = _numeric(_as_series(values)).to_numpy()
    if v.size == 0:
        return np.zeros(0, dtype=bool)
    finite = np.isfinite(v)
    filled = np.where(finite, v, 0.0)  # avoid inf - inf; non-finite never joins a run
    same = finite[1:] & finite[:-1] & (np.abs(np.diff(filled)) <= atol)
    run_start = np.ones(v.size, dtype=bool)
    run_start[1:] = ~same
    run_id = np.cumsum(run_start) - 1
    mask = (np.bincount(run_id)[run_id] >= min_run) & finite
    if exclude:
        mask &= ~np.isin(v, np.asarray(list(exclude), dtype="float64"))
    return np.asarray(mask, dtype=bool)


def counter_decrease_mask(
    values: pd.Series | np.ndarray | list[object],
    *,
    tolerance: float = 0.0,
) -> np.ndarray:
    """True where a cumulative counter falls below the previous finite value.

    Meant for monotonically non-decreasing registers (e.g. energy meter
    readings). Each value is compared with the last finite value before it,
    so only the row where the drop happens is flagged. Resets and rollovers
    both show up as decreases; this function does not guess which one it is.
    Drops of at most ``tolerance`` are ignored.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")
    v = _numeric(_as_series(values))
    finite = pd.Series(np.isfinite(v.to_numpy()), index=v.index)
    previous = v.where(finite).ffill().shift(1)
    return np.asarray(finite & previous.notna() & (v < previous - tolerance), dtype=bool)


def flag_series(
    series: pd.Series,
    *,
    freq: str | pd.Timedelta | None = None,
    bounds: tuple[float | None, float | None] | None = None,
    insert_missing: bool = False,
    stale_min_run: int | None = None,
    cumulative: bool = False,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
) -> pd.DataFrame:
    """Return a new frame with the original values and a ``quality_flag`` bitmask.

    Parameters
    ----------
    series:
        Values indexed by a timezone-aware ``DatetimeIndex``. Not modified.
    freq:
        Expected step. Enables ``OFF_GRID_TIMESTAMP`` and, with
        ``insert_missing``, ``MISSING_INTERVAL``. A fixed step unless ``tz``
        is given.
    bounds:
        Optional ``(lower, upper)`` plausibility range; either may be ``None``.
    insert_missing:
        If true, add one row (value ``NaN``) per absent grid timestamp,
        flagged ``MISSING_INTERVAL | MISSING_VALUE``. Original rows are kept
        unchanged and in their original relative order.
    stale_min_run:
        If set, flag ``STALE_VALUE`` on runs of at least this many repeated
        values (see :func:`stale_mask`). Off by default: a sensible run length
        depends on the signal.
    cumulative:
        If true, treat the series as a cumulative counter and flag
        ``COUNTER_DECREASE`` (see :func:`counter_decrease_mask`).
    origin:
        Timezone-aware timestamp the grid runs through (default: the first
        timestamp). See :func:`energydata_kit.expected_grid`.
    tz:
        Treat ``freq`` as a local-calendar step in this zone, e.g. ``"D"`` in
        ``"Europe/Stockholm"`` (23/25-hour DST days) or ``"MS"``.
    """
    index = series.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ValueError("series must have a timezone-aware DatetimeIndex; use normalize_timestamps()")
    if insert_missing and freq is None:
        raise ValueError("insert_missing requires freq")
    if insert_missing and not index.is_monotonic_increasing:
        raise ValueError("insert_missing requires a sorted index so original row order is kept")
    if (stale_min_run is not None or cumulative) and not index.is_monotonic_increasing:
        raise ValueError("stale and counter checks compare consecutive rows and require a sorted index")

    flags = np.zeros(len(series), dtype=np.uint16)
    flags[missing_value_mask(series)] |= np.uint16(QualityFlag.MISSING_VALUE)
    flags[non_finite_mask(series)] |= np.uint16(QualityFlag.NON_FINITE)
    flags[non_numeric_mask(series)] |= np.uint16(QualityFlag.NON_NUMERIC)
    flags[duplicate_mask(index)] |= np.uint16(QualityFlag.DUPLICATE_TIMESTAMP)
    if freq is not None:
        flags[off_grid_mask(index, freq, origin, tz=tz)] |= np.uint16(QualityFlag.OFF_GRID_TIMESTAMP)
    if bounds is not None:
        flags[out_of_bounds_mask(series, *bounds)] |= np.uint16(QualityFlag.OUT_OF_BOUNDS)
    if stale_min_run is not None:
        flags[stale_mask(series, stale_min_run)] |= np.uint16(QualityFlag.STALE_VALUE)
    if cumulative:
        flags[counter_decrease_mask(series)] |= np.uint16(QualityFlag.COUNTER_DECREASE)

    frame = pd.DataFrame(
        {VALUE_COLUMN: series.to_numpy(copy=True), FLAG_COLUMN: flags},
        index=index.copy(),
    )

    if insert_missing and freq is not None:
        missing = missing_timestamps(index, freq, origin=origin, tz=tz)
        if len(missing):
            filler = pd.DataFrame(
                {
                    VALUE_COLUMN: np.full(len(missing), np.nan),
                    FLAG_COLUMN: np.full(
                        len(missing),
                        QualityFlag.MISSING_INTERVAL | QualityFlag.MISSING_VALUE,
                        dtype=np.uint16,
                    ),
                },
                index=missing.tz_convert(index.tz).as_unit(index.unit),
            )
            frame = pd.concat([frame, filler]).sort_index(kind="stable")
            frame[FLAG_COLUMN] = frame[FLAG_COLUMN].astype(np.uint16)

    frame.index.name = index.name
    return frame
