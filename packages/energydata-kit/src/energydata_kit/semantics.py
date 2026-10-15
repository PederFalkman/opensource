"""Interval semantics: label conversion, metadata consistency, local-day completeness.

A timestamp on interval data names one edge of an interval. With
``IntervalLabel.START`` the value at 00:00 covers 00:00-00:15; with
``IntervalLabel.END`` the same interval is stamped 00:15. Nothing in this
module shifts timestamps implicitly: conversion happens only through
:func:`relabel_intervals`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from energydata_kit.intervals import to_step
from energydata_kit.metadata import Aggregation, IntervalLabel, MeasurementMetadata, get_unit_registry
from energydata_kit.timestamps import utc_ns

__all__ = [
    "MetadataIssue",
    "check_metadata_consistency",
    "interval_bounds",
    "local_day_completeness",
    "relabel_intervals",
]


def _require_aware(index: pd.DatetimeIndex) -> None:
    if not isinstance(index, pd.DatetimeIndex):
        raise TypeError(f"expected a DatetimeIndex, got {type(index).__name__}")
    if index.tz is None:
        raise ValueError("timestamps must be timezone-aware; use normalize_timestamps() first")


def relabel_intervals(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    from_label: IntervalLabel | str,
    to_label: IntervalLabel | str,
) -> pd.DatetimeIndex:
    """Return a new index with interval timestamps moved from one edge to the other.

    ``END -> START`` subtracts one step, ``START -> END`` adds one; equal
    labels return a copy. Order and duplicates are preserved.
    """
    _require_aware(index)
    step = to_step(freq)
    src, dst = IntervalLabel(from_label), IntervalLabel(to_label)
    if src == dst:
        return index.copy()
    return index + step if dst is IntervalLabel.END else index - step


def interval_bounds(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    label: IntervalLabel | str,
) -> tuple[pd.DatetimeIndex, pd.DatetimeIndex]:
    """``(starts, ends)`` of the intervals that ``index`` labels."""
    starts = relabel_intervals(index, freq, label, IntervalLabel.START)
    return starts, starts + to_step(freq)


@dataclass(frozen=True)
class MetadataIssue:
    """A likely inconsistency in :class:`MeasurementMetadata`. Advisory, not an error."""

    code: str
    message: str


_AVERAGING = {Aggregation.MEAN, Aggregation.MIN, Aggregation.MAX}


def check_metadata_consistency(metadata: MeasurementMetadata) -> list[MetadataIssue]:
    """Return advisory issues where unit, aggregation and labels disagree.

    Rules (stable codes):

    - ``SUM_OF_POWER``: ``sum`` of a power-dimensioned unit (W, var, VA).
      Interval sums of power are rarely meaningful; energy (Wh) was likely meant.
    - ``AVERAGED_ENERGY``: ``mean``/``min``/``max`` of an energy-dimensioned
      unit. Energy per interval is normally a ``sum``; average power was likely
      meant. (Instantaneous energy, such as a meter register reading, is fine.)
    - ``MISSING_RESOLUTION``: an interval aggregation without a ``resolution``,
      so the interval length is undefined.
    - ``LABEL_ON_INSTANTANEOUS``: ``interval_label="end"`` on instantaneous
      samples, which have no interval.
    """
    ureg = get_unit_registry()
    dims = ureg.Unit(metadata.unit).dimensionality
    agg = metadata.aggregation
    issues = []
    if agg is Aggregation.SUM and dims == ureg.watt.dimensionality:
        issues.append(
            MetadataIssue(
                "SUM_OF_POWER",
                f"aggregation 'sum' with power unit {metadata.unit!r}; an energy unit was likely meant",
            )
        )
    if agg in _AVERAGING and dims == ureg.joule.dimensionality:
        issues.append(
            MetadataIssue(
                "AVERAGED_ENERGY",
                f"aggregation {agg.value!r} with energy unit {metadata.unit!r}; "
                "energy per interval is normally a 'sum'",
            )
        )
    if agg is not Aggregation.INSTANTANEOUS and metadata.resolution is None:
        issues.append(
            MetadataIssue(
                "MISSING_RESOLUTION",
                f"aggregation {agg.value!r} describes an interval, but no resolution is set",
            )
        )
    if agg is Aggregation.INSTANTANEOUS and metadata.interval_label is IntervalLabel.END:
        issues.append(
            MetadataIssue(
                "LABEL_ON_INSTANTANEOUS",
                "interval_label 'end' has no meaning for instantaneous samples",
            )
        )
    return issues


def local_day_completeness(
    index: pd.DatetimeIndex,
    freq: str | pd.Timedelta,
    tz: str,
    interval_label: IntervalLabel | str = IntervalLabel.START,
) -> pd.DataFrame:
    """Expected vs. present intervals for each local calendar day.

    Each interval is assigned to the local day in which it *starts* (after
    converting ``interval_label`` to start). The expected count follows the
    local day length, e.g. 92 / 96 / 100 intervals at 15 minutes on DST
    spring-forward / normal / fall-back days. Only unique timestamps aligned to
    the grid from local midnight count as present.

    Returns a frame indexed by ``local_date`` (``datetime.date``) with columns
    ``expected``, ``present``, ``missing`` and ``completeness``. The first and
    last day are included even if the data covers them only partly.
    """
    _require_aware(index)
    step = to_step(freq)
    columns = ["expected", "present", "missing", "completeness"]
    if len(index) == 0:
        return pd.DataFrame(columns=columns, index=pd.Index([], name="local_date"))

    starts = relabel_intervals(index.unique(), step, interval_label, IntervalLabel.START).sort_values()
    local = starts.tz_convert(tz)
    days = pd.date_range(local[0].date(), local[-1].date() + pd.Timedelta(days=1), freq="D")
    # Midnight can be skipped (shift to the first valid time) or repeated
    # (take the first occurrence) in a few zones.
    boundaries = days.tz_localize(
        tz, ambiguous=np.ones(len(days), dtype=bool), nonexistent="shift_forward"
    ).tz_convert("UTC")
    bounds_ns = utc_ns(boundaries)
    starts_ns = utc_ns(starts)
    step_ns = step.value

    expected = (np.diff(bounds_ns) // step_ns).astype(np.int64)
    day_idx = np.searchsorted(bounds_ns, starts_ns, side="right") - 1
    on_grid = (starts_ns - bounds_ns[day_idx]) % step_ns == 0
    present = np.minimum(np.bincount(day_idx[on_grid], minlength=len(expected)), expected)

    return pd.DataFrame(
        {
            "expected": expected,
            "present": present.astype(np.int64),
            "missing": (expected - present).astype(np.int64),
            "completeness": np.round(present / expected, 6),
        },
        index=pd.Index([d.date() for d in days[:-1]], name="local_date"),
    )
