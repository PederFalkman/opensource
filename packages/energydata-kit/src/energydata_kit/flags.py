"""Explicit, non-destructive quality flags.

Flags are stored as an integer bitmask alongside the original values. No
check in this module modifies, drops, fills or reorders input values.
"""

from __future__ import annotations

from enum import IntFlag

import numpy as np
import pandas as pd

from energydata_kit.intervals import duplicate_mask, find_missing_intervals, off_grid_mask

__all__ = [
    "FLAG_COLUMN",
    "VALUE_COLUMN",
    "QualityFlag",
    "decode_flags",
    "flag_series",
    "missing_value_mask",
    "non_finite_mask",
    "non_numeric_mask",
    "out_of_bounds_mask",
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


def flag_series(
    series: pd.Series,
    *,
    freq: str | pd.Timedelta | None = None,
    bounds: tuple[float | None, float | None] | None = None,
    insert_missing: bool = False,
) -> pd.DataFrame:
    """Return a new frame with the original values and a ``quality_flag`` bitmask.

    Parameters
    ----------
    series:
        Values indexed by a timezone-aware ``DatetimeIndex``. Not modified.
    freq:
        Expected fixed step. Enables ``OFF_GRID_TIMESTAMP`` and, with
        ``insert_missing``, ``MISSING_INTERVAL``.
    bounds:
        Optional ``(lower, upper)`` plausibility range; either may be ``None``.
    insert_missing:
        If true, add one row (value ``NaN``) per absent grid timestamp,
        flagged ``MISSING_INTERVAL | MISSING_VALUE``. Original rows are kept
        unchanged and in their original relative order.
    """
    index = series.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ValueError("series must have a timezone-aware DatetimeIndex; use normalize_timestamps()")
    if insert_missing and freq is None:
        raise ValueError("insert_missing requires freq")
    if insert_missing and not index.is_monotonic_increasing:
        raise ValueError("insert_missing requires a sorted index so original row order is kept")

    flags = np.zeros(len(series), dtype=np.uint16)
    flags[missing_value_mask(series)] |= np.uint16(QualityFlag.MISSING_VALUE)
    flags[non_finite_mask(series)] |= np.uint16(QualityFlag.NON_FINITE)
    flags[non_numeric_mask(series)] |= np.uint16(QualityFlag.NON_NUMERIC)
    flags[duplicate_mask(index)] |= np.uint16(QualityFlag.DUPLICATE_TIMESTAMP)
    if freq is not None:
        flags[off_grid_mask(index, freq)] |= np.uint16(QualityFlag.OFF_GRID_TIMESTAMP)
    if bounds is not None:
        flags[out_of_bounds_mask(series, *bounds)] |= np.uint16(QualityFlag.OUT_OF_BOUNDS)

    frame = pd.DataFrame(
        {VALUE_COLUMN: series.to_numpy(copy=True), FLAG_COLUMN: flags},
        index=index.copy(),
    )

    if insert_missing and freq is not None:
        missing = [
            ts
            for gap in find_missing_intervals(index, freq)
            for ts in pd.date_range(gap.start, gap.end, freq=freq)
        ]
        if missing:
            filler = pd.DataFrame(
                {
                    VALUE_COLUMN: np.full(len(missing), np.nan),
                    FLAG_COLUMN: np.full(
                        len(missing),
                        QualityFlag.MISSING_INTERVAL | QualityFlag.MISSING_VALUE,
                        dtype=np.uint16,
                    ),
                },
                index=pd.DatetimeIndex(missing).as_unit(index.unit),
            )
            frame = pd.concat([frame, filler]).sort_index(kind="stable")
            frame[FLAG_COLUMN] = frame[FLAG_COLUMN].astype(np.uint16)

    frame.index.name = index.name
    return frame
