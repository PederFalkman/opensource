"""Explicit, non-destructive quality flags.

Flags are stored as an integer bitmask alongside the original values. No
check in this module modifies, drops, fills or reorders input values.
"""

from __future__ import annotations

import functools
import operator
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
    "jump_mask",
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
    JUMP = 512  # change from the previous finite value exceeds a limit (opt-in)


_ALL_BITS = functools.reduce(operator.or_, (m.value for m in QualityFlag), 0)


def decode_flags(value: int) -> list[str]:
    """Names of the flags set in ``value``, in bit order; ``["OK"]`` for 0.

    Raises ``ValueError`` for a negative value or one with bits no flag uses.
    """
    number = int(value)
    if number != value or number < 0 or number & ~_ALL_BITS:
        raise ValueError(f"{value!r} is not a combination of QualityFlag values")
    flag = QualityFlag(number)
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
    *,
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


def jump_mask(
    values: pd.Series | np.ndarray | list[object],
    max_delta: float,
) -> np.ndarray:
    """True where a value differs from the previous finite value by more than ``max_delta``.

    Each finite value is compared with the last finite value before it, so
    missing and non-finite values are skipped, never flagged. Only the row
    where the change lands is flagged: a single outlier therefore flags
    itself and the row after it (the jump away and the jump back). The limit
    is supplied by the caller; the package ships no domain limits. Time gaps
    between rows are not considered; check gaps separately.
    """
    if not np.isfinite(max_delta) or max_delta <= 0:
        raise ValueError("max_delta must be a finite number > 0")
    v = _numeric(_as_series(values))
    finite = pd.Series(np.isfinite(v.to_numpy()), index=v.index)
    previous = v.where(finite).ffill().shift(1)
    return np.asarray(finite & previous.notna() & ((v - previous).abs() > max_delta), dtype=bool)


def _check_options(
    stale_min_run: int | None,
    stale_atol: float,
    stale_exclude: Collection[float],
    cumulative: bool,
    counter_tolerance: float,
) -> None:
    """Reject fine-tuning options given without the check they tune."""
    if stale_min_run is None and (stale_atol or len(stale_exclude)):
        raise ValueError("stale_atol and stale_exclude require stale_min_run")
    if not cumulative and counter_tolerance:
        raise ValueError("counter_tolerance requires cumulative=True")


def flag_series(
    series: pd.Series,
    *,
    freq: str | pd.Timedelta | None = None,
    bounds: tuple[float | None, float | None] | None = None,
    insert_missing: bool = False,
    stale_min_run: int | None = None,
    stale_atol: float = 0.0,
    stale_exclude: Collection[float] = (),
    cumulative: bool = False,
    counter_tolerance: float = 0.0,
    jump_max_delta: float | None = None,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
) -> pd.DataFrame:
    """Return a new frame with the original values and a ``quality_flag`` bitmask.

    Parameters
    ----------
    series:
        Values indexed by a timezone-aware ``DatetimeIndex`` without ``NaT``.
        Not modified.
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
    stale_atol, stale_exclude:
        Passed to :func:`stale_mask` as ``atol`` and ``exclude``. Require
        ``stale_min_run``.
    cumulative:
        If true, treat the series as a cumulative counter and flag
        ``COUNTER_DECREASE`` (see :func:`counter_decrease_mask`).
    counter_tolerance:
        Passed to :func:`counter_decrease_mask` as ``tolerance``. Requires
        ``cumulative``.
    jump_max_delta:
        If set, flag ``JUMP`` where a value differs from the previous finite
        value by more than this (see :func:`jump_mask`). Off by default.
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
    if index.hasnans:
        raise ValueError("series index must not contain NaT")
    if insert_missing and freq is None:
        raise ValueError("insert_missing requires freq")
    if insert_missing and not index.is_monotonic_increasing:
        raise ValueError("insert_missing requires a sorted index so original row order is kept")
    _check_options(stale_min_run, stale_atol, stale_exclude, cumulative, counter_tolerance)
    consecutive = stale_min_run is not None or cumulative or jump_max_delta is not None
    if consecutive and not index.is_monotonic_increasing:
        raise ValueError("stale, counter and jump checks compare consecutive rows and require a sorted index")

    flags = np.zeros(len(series), dtype=np.uint16)
    flags[missing_value_mask(series)] |= np.uint16(QualityFlag.MISSING_VALUE)
    flags[non_finite_mask(series)] |= np.uint16(QualityFlag.NON_FINITE)
    flags[non_numeric_mask(series)] |= np.uint16(QualityFlag.NON_NUMERIC)
    flags[duplicate_mask(index)] |= np.uint16(QualityFlag.DUPLICATE_TIMESTAMP)
    if freq is not None:
        flags[off_grid_mask(index, freq, origin=origin, tz=tz)] |= np.uint16(QualityFlag.OFF_GRID_TIMESTAMP)
    if bounds is not None:
        lower, upper = bounds
        flags[out_of_bounds_mask(series, lower=lower, upper=upper)] |= np.uint16(QualityFlag.OUT_OF_BOUNDS)
    if stale_min_run is not None:
        stale = stale_mask(series, stale_min_run, atol=stale_atol, exclude=stale_exclude)
        flags[stale] |= np.uint16(QualityFlag.STALE_VALUE)
    if cumulative:
        decrease = counter_decrease_mask(series, tolerance=counter_tolerance)
        flags[decrease] |= np.uint16(QualityFlag.COUNTER_DECREASE)
    if jump_max_delta is not None:
        flags[jump_mask(series, jump_max_delta)] |= np.uint16(QualityFlag.JUMP)

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
