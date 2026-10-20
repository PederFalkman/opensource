"""Explicit, non-destructive quality flags.

Flags are stored as an integer bitmask alongside the original values. No
check in this module modifies, drops, fills or reorders input values.
"""

from __future__ import annotations

import functools
import numbers
import operator
from collections.abc import Collection
from enum import IntFlag
from typing import Any

import numpy as np
import pandas as pd

from energydata_kit.intervals import duplicate_mask, missing_timestamps, off_grid_mask
from energydata_kit.timestamps import utc_ns

__all__ = [
    "FLAG_COLUMN",
    "VALUE_COLUMN",
    "QualityFlag",
    "counter_decrease_mask",
    "counter_rollover_mask",
    "decode_flags",
    "flag_series",
    "jump_mask",
    "jump_rate_mask",
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
    COUNTER_ROLLOVER = 1024  # cumulative counter wrapped past its modulus (opt-in; report schema 2)


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


def _number(value: object, name: str) -> float:
    """``value`` as a float, if it is a real number (numpy ones included) but not a bool."""
    if isinstance(value, bool | np.bool_) or not isinstance(value, numbers.Real):
        raise TypeError(f"{name} must be a number, got {value!r}")
    return float(value)


def _bounds(bounds: object) -> tuple[Any, Any]:
    """``bounds`` checked as a ``(lower, upper)`` pair of numbers or ``None``, returned unchanged."""
    pair: Any = bounds
    if isinstance(pair, str | bytes) or not hasattr(pair, "__len__") or len(pair) != 2:
        raise ValueError(f"bounds must be a (lower, upper) pair, got {bounds!r}")
    lower, upper = pair
    for name, bound in (("lower bound", lower), ("upper bound", upper)):
        if bound is not None:
            _number(bound, name)
    return lower, upper


def _duration(value: object, name: str) -> pd.Timedelta:
    """``value`` as a positive ``Timedelta``; a bare number is refused (no unit)."""
    if isinstance(value, bool | np.bool_ | numbers.Number):
        raise TypeError(f"{name} must be a duration such as '1h' or a Timedelta, got {value!r}")
    try:
        td = pd.Timedelta(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a duration such as '1h', got {value!r}") from exc
    if pd.isna(td) or td <= pd.Timedelta(0):
        raise ValueError(f"{name} must be a positive duration, got {value!r}")
    return td


def _max_gap(max_gap: object) -> pd.Timedelta | None:
    """``max_gap`` as a positive ``Timedelta``, or ``None``."""
    return None if max_gap is None else _duration(max_gap, "max_gap")


def _max_rate(max_rate: object) -> tuple[float, pd.Timedelta] | None:
    """``jump_max_rate`` as ``(delta, period)``, or ``None``."""
    return None if max_rate is None else _rate(max_rate)


def _rate(max_rate: object) -> tuple[float, pd.Timedelta]:
    """``max_rate`` as ``(delta, period)``: a finite ``delta > 0`` per a positive duration."""
    if not isinstance(max_rate, tuple | list) or len(max_rate) != 2:
        raise TypeError(f"max_rate must be a pair (delta, period) such as (50.0, '1h'), got {max_rate!r}")
    delta, period = max_rate
    if not np.isfinite(_number(delta, "max_rate delta")) or delta <= 0:
        raise ValueError(f"max_rate delta must be a finite number > 0, got {delta!r}")
    return float(delta), _duration(period, "max_rate period")


def _times_ns(values: object, n: int) -> np.ndarray:
    """Nanosecond timestamps of ``values``' index; ``max_gap`` needs to know when each value is."""
    index = getattr(values, "index", None)
    if not isinstance(index, pd.DatetimeIndex) or len(index) != n:
        raise TypeError("max_gap needs values as a Series with a DatetimeIndex")
    return utc_ns(index)


def _with_index(values: object, numeric: pd.Series) -> pd.Series:
    """``numeric`` carrying the original index when ``values`` had one (for ``max_gap``)."""
    index = getattr(values, "index", None)
    if isinstance(index, pd.Index) and len(index) == len(numeric):
        return pd.Series(numeric.to_numpy(), index=index)
    return numeric


def _near_previous_finite(values: pd.Series, finite: pd.Series, gap: pd.Timedelta | None) -> np.ndarray:
    """True where the last finite value before a row is at most ``gap`` earlier (all True without a gap)."""
    if gap is None or len(values) == 0:
        return np.ones(len(values), dtype=bool)
    times = pd.Series(_times_ns(values, len(values)), dtype="float64")
    previous = times.where(np.asarray(finite, dtype=bool)).ffill().shift(1)
    return np.asarray((times - previous) <= gap.value, dtype=bool)


def out_of_bounds_mask(
    values: pd.Series | np.ndarray | list[object],
    *,
    lower: float | None = None,
    upper: float | None = None,
) -> np.ndarray:
    """True where a finite value lies outside the inclusive range ``[lower, upper]``.

    Bounds are supplied by the caller; the package ships no domain limits.
    """
    for name, bound in (("lower", lower), ("upper", upper)):
        if bound is not None and not np.isfinite(
            _number(bound, f"{name} bound")
        ):  # NaN or inf would make the report invalid JSON
            raise ValueError(f"{name} bound must be a finite number or None, got {bound!r}")
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
    max_gap: str | pd.Timedelta | None = None,
) -> np.ndarray:
    """True for every value in a run of at least ``min_run`` consecutive repeated values.

    Values are compared in row order: a run continues while each finite value
    differs from the previous one by at most ``atol``. Missing or non-finite
    values end a run and are never flagged. Runs whose values all lie within
    ``atol`` of a value in ``exclude`` (e.g. ``0.0`` for generation at night)
    are not flagged.

    Time gaps between rows are not considered unless ``max_gap`` is given
    (e.g. ``"1h"``): then a run also ends where two consecutive rows are more
    than ``max_gap`` apart, so a flat line before and after an outage counts
    as two runs. ``max_gap`` needs ``values`` as a Series with a
    ``DatetimeIndex``.
    """
    if isinstance(min_run, bool | np.bool_):
        raise TypeError(f"min_run must be an integer, got {min_run!r}")
    min_run = operator.index(min_run)  # TypeError for 3.5 or "3"; accepts numpy integers
    if min_run < 2:
        raise ValueError("min_run must be >= 2")
    if not np.isfinite(_number(atol, "atol")) or atol < 0:
        raise ValueError("atol must be a finite number >= 0")
    excluded = _excluded_values(exclude)
    gap = _max_gap(max_gap)
    v = _numeric(_as_series(values)).to_numpy()
    if v.size == 0:
        return np.zeros(0, dtype=bool)
    finite = np.isfinite(v)
    filled = np.where(finite, v, 0.0)  # avoid inf - inf; non-finite never joins a run
    same = finite[1:] & finite[:-1] & (np.abs(np.diff(filled)) <= atol)
    if gap is not None:
        same &= np.diff(_times_ns(values, v.size)) <= gap.value
    run_start = np.ones(v.size, dtype=bool)
    run_start[1:] = ~same
    run_id = np.cumsum(run_start) - 1
    mask = (np.bincount(run_id)[run_id] >= min_run) & finite
    if excluded.size:
        # A run is left out when every value in it is within atol of an excluded value,
        # so a near-zero run with atol > 0 is excluded whole, not row by row.
        near = np.zeros(v.size, dtype=bool)
        near[finite] = (np.abs(v[finite, None] - excluded[None, :]) <= atol).any(axis=1)
        far_in_run = np.bincount(run_id, weights=(~near).astype(np.float64))
        mask &= far_in_run[run_id] > 0
    return np.asarray(mask, dtype=bool)


def _excluded_values(exclude: Collection[float]) -> np.ndarray:
    """``exclude`` as finite floats; checked before any data is read, so empty input checks it too."""
    given: object = exclude
    if isinstance(given, str | bytes):
        raise TypeError("exclude must be a collection of numbers, not a string")
    values = list(exclude)
    if any(isinstance(x, bool | np.bool_) for x in values):
        raise ValueError(f"exclude must contain only numbers, got {values!r}")
    try:
        excluded = np.asarray(values, dtype="float64")
    except (TypeError, ValueError):
        raise ValueError(f"exclude must contain only numbers, got {values!r}") from None
    if not np.isfinite(excluded).all():
        # Non-finite values never form a run, and NaN or inf would make the report invalid JSON.
        raise ValueError(f"exclude must contain finite numbers, got {excluded.tolist()!r}")
    return excluded


def counter_decrease_mask(
    values: pd.Series | np.ndarray | list[object],
    *,
    tolerance: float = 0.0,
    max_gap: str | pd.Timedelta | None = None,
) -> np.ndarray:
    """True where a cumulative counter falls below the previous finite value.

    Meant for monotonically non-decreasing registers (e.g. energy meter
    readings). Each value is compared with the last finite value before it,
    so only the row where the drop happens is flagged. Resets and rollovers
    both show up as decreases; this function does not guess which one it is
    (:func:`counter_rollover_mask` tells them apart given the modulus).
    Drops of at most ``tolerance`` are ignored. With ``max_gap``, a value is
    not compared with a previous finite value more than ``max_gap`` earlier
    (``values`` must then be a Series with a ``DatetimeIndex``).
    """
    if not np.isfinite(_number(tolerance, "tolerance")) or tolerance < 0:
        raise ValueError("tolerance must be a finite number >= 0")
    gap = _max_gap(max_gap)
    v = _numeric(_as_series(values))
    finite = pd.Series(np.isfinite(v.to_numpy()), index=v.index)
    previous = v.where(finite).ffill().shift(1)
    near = _near_previous_finite(_with_index(values, v), finite, gap)
    return np.asarray(finite & previous.notna() & (v < previous - tolerance) & near, dtype=bool)


def _modulus(modulus: object, name: str) -> float:
    """A register modulus: a finite number > 0, supplied by the caller and never guessed."""
    value = _number(modulus, name)
    if not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a finite number > 0, got {modulus!r}")
    return value


def counter_rollover_mask(
    values: pd.Series | np.ndarray | list[object],
    modulus: float,
    *,
    tolerance: float = 0.0,
    max_gap: str | pd.Timedelta | None = None,
) -> np.ndarray:
    """True where a counter decrease is consistent with a register wrapping past ``modulus``.

    Only rows :func:`counter_decrease_mask` flags (with the same
    ``tolerance`` and ``max_gap``) are candidates. A drop from the previous
    finite value ``prev`` to ``cur`` is a rollover when the increase implied
    by wrapping, ``cur + modulus - prev``, is at least ``-tolerance`` and
    less than ``modulus / 2``; any other drop stays a plain decrease (a reset,
    or a drop too large to be a wrap). With ``modulus=1e6``, 999 990 → 10 is
    a rollover (implied +20) and 500 000 → 0 is not. The modulus is the
    register size, supplied by the caller; the package never guesses one.
    """
    m = _modulus(modulus, "modulus")
    decrease = counter_decrease_mask(values, tolerance=tolerance, max_gap=max_gap)
    v = _numeric(_as_series(values)).to_numpy()
    previous = pd.Series(np.where(np.isfinite(v), v, np.nan)).ffill().shift(1).to_numpy()
    implied = v + m - previous  # NaN where there is no previous value; those are not decreases
    return np.asarray(decrease & (implied >= -tolerance) & (implied < m / 2), dtype=bool)


def jump_mask(
    values: pd.Series | np.ndarray | list[object],
    max_delta: float,
    *,
    max_gap: str | pd.Timedelta | None = None,
) -> np.ndarray:
    """True where a value differs from the previous finite value by more than ``max_delta``.

    Each finite value is compared with the last finite value before it, so
    missing and non-finite values are skipped, never flagged. Only the row
    where the change lands is flagged: a single outlier therefore flags
    itself and the row after it (the jump away and the jump back). The limit
    is supplied by the caller; the package ships no domain limits. Time gaps
    between rows are not considered unless ``max_gap`` is given: then a value
    is not compared with a previous finite value more than ``max_gap``
    earlier (``values`` must be a Series with a ``DatetimeIndex``).
    """
    if not np.isfinite(_number(max_delta, "max_delta")) or max_delta <= 0:
        raise ValueError("max_delta must be a finite number > 0")
    gap = _max_gap(max_gap)
    v = _numeric(_as_series(values))
    finite = pd.Series(np.isfinite(v.to_numpy()), index=v.index)
    previous = v.where(finite).ffill().shift(1)
    near = _near_previous_finite(_with_index(values, v), finite, gap)
    return np.asarray(finite & previous.notna() & ((v - previous).abs() > max_delta) & near, dtype=bool)


def jump_rate_mask(
    values: pd.Series,
    max_rate: tuple[float, str | pd.Timedelta],
    *,
    max_gap: str | pd.Timedelta | None = None,
) -> np.ndarray:
    """True where a value changes faster than ``max_rate`` since the previous finite value.

    ``max_rate`` is ``(delta, period)``, e.g. ``(50.0, "1h")`` for 50 per
    hour: a row is flagged when ``|change| > delta * elapsed / period``,
    where ``elapsed`` is the time since the last finite value before it.
    Unlike :func:`jump_mask`, the limit grows with the time between rows, so
    a normal ramp across a gap is not a jump and one limit fits any
    resolution. Missing and non-finite values are skipped, never flagged;
    rows with the same timestamp as that value (duplicates) are not compared.
    With ``max_gap``, a value is not compared with one more than ``max_gap``
    earlier. The rate is supplied by the caller in the data's own unit; the
    package ships no domain limits. ``values`` must be a Series with a
    ``DatetimeIndex``.
    """
    delta, period = _rate(max_rate)
    gap = _max_gap(max_gap)
    v = _numeric(_as_series(values)).to_numpy()
    if v.size == 0:
        return np.zeros(0, dtype=bool)
    times = _times_ns(values, v.size)
    finite = np.isfinite(v)
    filled = np.where(finite, v, 0.0)  # avoid inf - inf
    # Position of the last finite value before each row (-1: none). Integer
    # nanoseconds keep the elapsed time exact.
    positions = np.where(finite, np.arange(v.size), -1)
    previous = np.full(v.size, -1)
    previous[1:] = np.maximum.accumulate(positions)[:-1]
    compared = finite & (previous >= 0)
    p = np.where(compared, previous, 0)
    elapsed = times - times[p]
    mask = compared & (elapsed > 0) & (np.abs(filled - filled[p]) > delta * (elapsed / period.value))
    if gap is not None:
        mask &= elapsed <= gap.value
    return np.asarray(mask, dtype=bool)


def _check_options(
    stale_min_run: int | None,
    stale_atol: float,
    stale_exclude: Collection[float],
    cumulative: bool,
    counter_tolerance: float,
    jump_max_delta: float | None = None,
    max_gap: object = None,
    jump_max_rate: object = None,
    counter_rollover: object = None,
) -> None:
    """Reject a non-boolean ``cumulative`` and fine-tuning options given without the check they tune."""
    if not isinstance(cumulative, bool | np.bool_):
        raise TypeError(f"cumulative must be True or False, got {cumulative!r}")
    if stale_min_run is None and (stale_atol or len(stale_exclude)):
        raise ValueError("stale_atol and stale_exclude require stale_min_run")
    if not cumulative and counter_tolerance:
        raise ValueError("counter_tolerance requires cumulative=True")
    if counter_rollover is not None:
        _modulus(counter_rollover, "counter_rollover")
        if not cumulative:
            raise ValueError("counter_rollover requires cumulative=True")
    _max_rate(jump_max_rate)
    jumps = jump_max_delta is not None or jump_max_rate is not None
    if _max_gap(max_gap) is not None and stale_min_run is None and not cumulative and not jumps:
        raise ValueError("max_gap requires stale_min_run, cumulative=True, jump_max_delta or jump_max_rate")


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
    counter_rollover: float | None = None,
    jump_max_delta: float | None = None,
    jump_max_rate: tuple[float, str | pd.Timedelta] | None = None,
    max_gap: str | pd.Timedelta | None = None,
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
    counter_rollover:
        The counter's register modulus (e.g. ``1e6``), if known. A decrease
        consistent with wrapping past it is flagged ``COUNTER_ROLLOVER``
        instead of ``COUNTER_DECREASE`` (see :func:`counter_rollover_mask`).
        Requires ``cumulative``; never guessed.
    jump_max_delta:
        If set, flag ``JUMP`` where a value differs from the previous finite
        value by more than this (see :func:`jump_mask`). Off by default.
    jump_max_rate:
        If set, ``(delta, period)``, e.g. ``(50.0, "1h")``: flag ``JUMP``
        where a value changes faster than ``delta`` per ``period`` since the
        previous finite value (see :func:`jump_rate_mask`). Off by default;
        may be combined with ``jump_max_delta``.
    max_gap:
        Optional duration (e.g. ``"1h"``): the stale, counter and jump checks
        do not compare rows further apart than this, so an outage neither
        joins two flat stretches into one run nor makes the first value after
        it a jump or a counter decrease. Requires one of those checks.
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
    _check_options(
        stale_min_run,
        stale_atol,
        stale_exclude,
        cumulative,
        counter_tolerance,
        jump_max_delta,
        max_gap,
        jump_max_rate,
        counter_rollover,
    )
    jumps = jump_max_delta is not None or jump_max_rate is not None
    consecutive = stale_min_run is not None or cumulative or jumps
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
        lower, upper = _bounds(bounds)
        flags[out_of_bounds_mask(series, lower=lower, upper=upper)] |= np.uint16(QualityFlag.OUT_OF_BOUNDS)
    if stale_min_run is not None:
        stale = stale_mask(series, stale_min_run, atol=stale_atol, exclude=stale_exclude, max_gap=max_gap)
        flags[stale] |= np.uint16(QualityFlag.STALE_VALUE)
    if cumulative:
        decrease = counter_decrease_mask(series, tolerance=counter_tolerance, max_gap=max_gap)
        if counter_rollover is not None:
            rollover = counter_rollover_mask(
                series, counter_rollover, tolerance=counter_tolerance, max_gap=max_gap
            )
            flags[rollover] |= np.uint16(QualityFlag.COUNTER_ROLLOVER)
            decrease = decrease & ~rollover
        flags[decrease] |= np.uint16(QualityFlag.COUNTER_DECREASE)
    if jump_max_delta is not None:
        flags[jump_mask(series, jump_max_delta, max_gap=max_gap)] |= np.uint16(QualityFlag.JUMP)
    if jump_max_rate is not None:
        flags[jump_rate_mask(series, jump_max_rate, max_gap=max_gap)] |= np.uint16(QualityFlag.JUMP)

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
