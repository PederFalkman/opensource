"""energydata-kit checks as Pandera checks (optional extra).

Install with ``pip install "energydata-kit[pandera]"``. Each factory returns a
``pandera`` ``Check`` built on the same masks as :func:`energydata_kit.flag_series`,
so a schema validation and a flagging run agree. Pandera reports failures;
it does not flag or change data.

Index-based checks read the timestamps of whatever they receive, so they work
both in ``pa.Index(checks=[...])`` and directly on a ``SeriesSchema``.
:func:`series_schema` attaches every check to the series: Pandera's lazy
validation drops index-check failures when a value check also fails, and
series-level checks avoid that.
"""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

import pandas as pd

try:
    import pandera.pandas as pa
except ImportError as exc:  # pragma: no cover - exercised only without the extra
    raise ImportError(
        'energydata_kit.pandera_checks needs Pandera: pip install "energydata-kit[pandera]"'
    ) from exc

from energydata_kit.flags import (
    counter_decrease_mask,
    jump_mask,
    non_finite_mask,
    non_numeric_mask,
    out_of_bounds_mask,
    stale_mask,
)
from energydata_kit.intervals import duplicate_mask, expected_grid, off_grid_mask
from energydata_kit.metadata import MeasurementMetadata

__all__ = [
    "counter_check",
    "finite_check",
    "jump_check",
    "no_duplicate_timestamps_check",
    "no_missing_intervals_check",
    "on_grid_check",
    "series_schema",
    "stale_check",
    "timezone_aware_check",
    "within_bounds_check",
]

_PREFIX = "energydata_kit."


def _index(obj: Any) -> pd.DatetimeIndex:
    # Pandera hands index checks the index as a Series (``index.to_series()``),
    # whose own index is the original DatetimeIndex.
    index = obj if isinstance(obj, pd.Index) else obj.index
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"expected a DatetimeIndex, got {type(index).__name__}")
    return index


def _rows(obj: Any, ok: Any) -> pd.Series:
    # Always answer per row. Whole-object (scalar) results have no row index,
    # and with pandas < 3 Pandera then fails to combine them with row-level
    # failures from other checks.
    index = obj if isinstance(obj, pd.Index) else obj.index
    return pd.Series(ok, index=index, dtype=bool)


def _is_aware(obj: Any) -> pd.Series:
    index = obj if isinstance(obj, pd.Index) else obj.index
    return _rows(obj, isinstance(index, pd.DatetimeIndex) and index.tz is not None)


def _no_gap_after(
    obj: Any, freq: str | pd.Timedelta, origin: pd.Timestamp | None, tz: str | None
) -> pd.Series:
    index = _index(obj)
    grid = expected_grid(index, freq, origin=origin, tz=tz)
    present = grid.isin(index.as_unit("ns"))
    # A gap starts where a present grid point is followed by an absent one.
    before_gap = grid[:-1][present[:-1] & ~present[1:]]
    return _rows(obj, ~index.as_unit("ns").isin(before_gap))


def timezone_aware_check() -> pa.Check:
    """Index timestamps must be timezone-aware (reported on every row if not)."""
    return pa.Check(
        _is_aware,
        name=_PREFIX + "timezone_aware",
        error="timestamps must be timezone-aware; use normalize_timestamps()",
        ignore_na=False,
    )


def no_duplicate_timestamps_check() -> pa.Check:
    """Every timestamp occurs once. Failure cases list each duplicated row."""
    return pa.Check(
        lambda idx: _rows(idx, ~duplicate_mask(_index(idx))),
        name=_PREFIX + "no_duplicate_timestamps",
        error="duplicate timestamps",
        ignore_na=False,
    )


def on_grid_check(
    freq: str | pd.Timedelta, *, origin: pd.Timestamp | None = None, tz: str | None = None
) -> pa.Check:
    """Every timestamp lies on the grid (see :func:`energydata_kit.off_grid_mask`)."""
    return pa.Check(
        lambda idx: _rows(idx, ~off_grid_mask(_index(idx), freq, origin=origin, tz=tz)),
        name=_PREFIX + "on_grid",
        error=f"timestamps not aligned to {freq}",
        ignore_na=False,
    )


def no_missing_intervals_check(
    freq: str | pd.Timedelta, *, origin: pd.Timestamp | None = None, tz: str | None = None
) -> pa.Check:
    """No grid timestamp between the first and last is absent.

    Each gap is reported on the last present row before it.
    """
    return pa.Check(
        lambda idx: _no_gap_after(idx, freq, origin, tz),
        name=_PREFIX + "no_missing_intervals",
        error=f"missing intervals after these timestamps at {freq} resolution",
        ignore_na=False,
    )


def finite_check() -> pa.Check:
    """Present values are numeric and finite (missing values are left to ``nullable``)."""
    return pa.Check(
        lambda s: pd.Series(~(non_finite_mask(s) | non_numeric_mask(s)), index=s.index),
        name=_PREFIX + "finite",
        error="non-finite or non-numeric values",
    )


def within_bounds_check(*, lower: float | None = None, upper: float | None = None) -> pa.Check:
    """Finite values lie within the inclusive ``[lower, upper]`` range."""
    return pa.Check(
        lambda s: pd.Series(~out_of_bounds_mask(s, lower=lower, upper=upper), index=s.index),
        name=_PREFIX + "within_bounds",
        error=f"values outside [{lower}, {upper}]",
    )


def stale_check(min_run: int, *, atol: float = 0.0, exclude: Collection[float] = ()) -> pa.Check:
    """No run of ``min_run`` or more repeated values (see :func:`energydata_kit.stale_mask`).

    Runs ``ignore_na=False`` so that missing values still break runs.
    """
    stale_mask([], min_run, atol=atol)  # validate arguments now, not at validation time
    return pa.Check(
        lambda s: pd.Series(~stale_mask(s, min_run, atol=atol, exclude=exclude), index=s.index),
        name=_PREFIX + "no_stale_values",
        error=f"runs of {min_run} or more repeated values",
        ignore_na=False,
    )


def counter_check(*, tolerance: float = 0.0) -> pa.Check:
    """A cumulative counter never decreases (see :func:`energydata_kit.counter_decrease_mask`)."""
    counter_decrease_mask([], tolerance=tolerance)
    return pa.Check(
        lambda s: pd.Series(~counter_decrease_mask(s, tolerance=tolerance), index=s.index),
        name=_PREFIX + "counter_not_decreasing",
        error="cumulative counter decreased",
        ignore_na=False,
    )


def jump_check(max_delta: float) -> pa.Check:
    """No change larger than ``max_delta`` from the previous finite value.

    See :func:`energydata_kit.jump_mask`: missing and non-finite values pass and are
    skipped, so each value is compared with the last finite value before it.
    """
    jump_mask([], max_delta)
    return pa.Check(
        lambda s: pd.Series(~jump_mask(s, max_delta), index=s.index),
        name=_PREFIX + "no_jumps",
        error=f"changes larger than {max_delta} between consecutive values",
        ignore_na=False,
    )


def series_schema(
    *,
    metadata: MeasurementMetadata | None = None,
    freq: str | pd.Timedelta | None = None,
    bounds: tuple[float | None, float | None] | None = None,
    stale_min_run: int | None = None,
    cumulative: bool = False,
    jump_max_delta: float | None = None,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
    nullable: bool = True,
) -> pa.SeriesSchema:
    """A ``SeriesSchema`` running the same checks as :func:`energydata_kit.assess_quality`.

    The step comes from ``freq``, else ``metadata.resolution``; without one,
    grid checks are left out. The schema name is ``metadata.name`` if given.
    """
    if freq is None and metadata is not None:
        freq = metadata.resolution
    index_checks = [timezone_aware_check(), no_duplicate_timestamps_check()]
    if freq is not None:
        index_checks += [
            on_grid_check(freq, origin=origin, tz=tz),
            no_missing_intervals_check(freq, origin=origin, tz=tz),
        ]
    value_checks = [finite_check()]
    if bounds is not None:
        value_checks.append(within_bounds_check(lower=bounds[0], upper=bounds[1]))
    if stale_min_run is not None:
        value_checks.append(stale_check(stale_min_run))
    if cumulative:
        value_checks.append(counter_check())
    if jump_max_delta is not None:
        value_checks.append(jump_check(jump_max_delta))
    return pa.SeriesSchema(
        checks=index_checks + value_checks,
        nullable=nullable,
        name=None if metadata is None else metadata.name,
    )
