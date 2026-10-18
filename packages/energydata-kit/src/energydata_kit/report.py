"""Reproducible quality reports.

A report is a pure function of the input data, the parameters and the package
version. It contains no wall-clock time, host name or random state, so the same
input yields byte-identical JSON.
"""

from __future__ import annotations

import hashlib
import json
import operator
from collections.abc import Collection, Iterable, Sized
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from energydata_kit import __version__
from energydata_kit.flags import FLAG_COLUMN, QualityFlag, flag_series
from energydata_kit.intervals import (
    Gap,
    _gaps,
    expected_grid,
    find_duplicate_timestamps,
    to_step,
)
from energydata_kit.metadata import IntervalLabel, MeasurementMetadata, _grid_from_metadata
from energydata_kit.semantics import MetadataIssue, check_metadata_consistency, local_day_completeness
from energydata_kit.timestamps import infer_resolution, on_index, utc_ns

__all__ = ["REPORT_SCHEMA_VERSION", "QualityReport", "assess_quality", "fingerprint_series"]

REPORT_SCHEMA_VERSION = "1"


def _iso(ts: pd.Timestamp | None) -> str | None:
    return None if ts is None else ts.isoformat()


def _iso_duration(td: pd.Timedelta | None) -> str | None:
    return None if td is None else td.isoformat()


def _freq_label(freq: str | pd.Timedelta | None) -> str | None:
    # Calendar steps have no ISO 8601 duration; report the pandas frequency.
    return None if freq is None else str(freq)


def _outages(
    known_outages: Iterable[tuple[pd.Timestamp | str, pd.Timestamp | str]],
) -> list[tuple[int, int]]:
    """Validate ``known_outages`` as UTC nanosecond ``(start, end)`` pairs, both ends included."""
    given: object = known_outages  # a single string would otherwise be split into characters
    if isinstance(given, str | bytes) or not isinstance(given, Iterable):
        raise TypeError("known_outages must be a list of (start, end) pairs")
    result = []
    for item in known_outages:
        pair: object = item
        if isinstance(pair, str | bytes) or not isinstance(pair, Sized) or len(item) != 2:
            raise ValueError(f"each known outage must be a (start, end) pair, got {item!r}")
        start, end = (_outage_end(ts) for ts in item)
        if start > end:
            raise ValueError(f"known outage starts after it ends: {start.isoformat()} > {end.isoformat()}")
        result.append((start.value, end.value))
    return result


def _outage_end(value: pd.Timestamp | str) -> pd.Timestamp:
    """One end of a known outage as a timezone-aware timestamp that fits in nanoseconds."""
    try:
        ts = pd.Timestamp(value)
    except (TypeError, ValueError) as exc:  # pandas' parse errors are ValueErrors
        raise ValueError(f"known outage: cannot read {value!r} as a timestamp ({exc})") from None
    if pd.isna(ts):
        raise ValueError(f"known outage must be a timestamp, got {value!r}")
    if ts.tz is None:
        raise ValueError(f"known outage must be timezone-aware, got {value!r}")
    try:
        return ts.as_unit("ns")
    except pd.errors.OutOfBoundsDatetime:
        raise ValueError(
            f"known outage {ts.isoformat()} is outside the timestamps pandas can hold "
            f"({pd.Timestamp.min.date()} to {pd.Timestamp.max.date()})"
        ) from None


def _iso_ns(value: int) -> str:
    return pd.Timestamp(value, unit="ns", tz="UTC").isoformat()


def _plain(value: Any) -> Any:
    """A numpy scalar (e.g. ``np.float64`` from ``series.quantile``) as a Python one, for JSON."""
    return value.item() if isinstance(value, np.generic) else value


def fingerprint_series(series: pd.Series) -> str:
    """SHA-256 over UTC timestamps (ns), numeric values and the series name.

    Stable across pandas versions and datetime resolutions. Non-numeric
    values contribute their ``repr``.
    """
    index = series.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ValueError("series must have a timezone-aware DatetimeIndex; use normalize_timestamps()")
    h = hashlib.sha256()
    h.update(repr(series.name).encode())
    h.update(np.asarray(utc_ns(index), dtype="<i8").tobytes())
    numeric = pd.to_numeric(series, errors="coerce").astype("float64").to_numpy()
    canonical = np.where(np.isnan(numeric), np.nan, numeric)  # one NaN bit pattern
    h.update(np.asarray(canonical, dtype="<f8").tobytes())
    non_numeric = series.notna().to_numpy() & np.isnan(numeric)
    for pos in np.flatnonzero(non_numeric):
        h.update(f"{pos}:{series.iloc[pos]!r}".encode())
    return h.hexdigest()


@dataclass(frozen=True)
class QualityReport:
    """Summary of the quality checks run on one series."""

    series_name: str | None
    fingerprint: str
    n_rows: int
    first_timestamp: str | None
    last_timestamp: str | None
    expected_resolution: str | None
    inferred_resolution: str | None
    n_expected_intervals: int | None
    completeness: float | None
    flag_counts: dict[str, int]
    gaps: list[Gap]
    n_gaps: int
    n_missing_intervals: int
    duplicate_timestamps: list[str]
    n_duplicate_timestamps: int
    parameters: dict[str, Any]
    metadata: dict[str, Any] | None = None
    package_version: str = __version__
    schema_version: str = REPORT_SCHEMA_VERSION
    truncated: dict[str, bool] = field(default_factory=dict)
    metadata_issues: list[MetadataIssue] = field(default_factory=list)
    local_days: dict[str, Any] | None = None
    n_missing_explained: int | None = None
    completeness_excluding_outages: float | None = None

    @property
    def n_flagged_rows(self) -> int:
        """Rows with at least one flag set (``flag_counts["ANY"]``)."""
        return self.flag_counts.get("ANY", 0)

    def to_dict(self) -> dict[str, Any]:
        """The report as plain JSON-compatible data (what ``to_json`` writes)."""
        return {
            "schema_version": self.schema_version,
            "package_version": self.package_version,
            "series_name": self.series_name,
            "fingerprint": self.fingerprint,
            "metadata": self.metadata,
            "parameters": self.parameters,
            "n_rows": self.n_rows,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "expected_resolution": self.expected_resolution,
            "inferred_resolution": self.inferred_resolution,
            "n_expected_intervals": self.n_expected_intervals,
            "completeness": self.completeness,
            "flag_counts": self.flag_counts,
            "gaps": [
                {"start": _iso(g.start), "end": _iso(g.end), "missing_count": g.missing_count}
                for g in self.gaps
            ],
            "n_gaps": self.n_gaps,
            "n_missing_intervals": self.n_missing_intervals,
            "n_missing_explained": self.n_missing_explained,
            "completeness_excluding_outages": self.completeness_excluding_outages,
            "duplicate_timestamps": self.duplicate_timestamps,
            "n_duplicate_timestamps": self.n_duplicate_timestamps,
            "truncated": self.truncated,
            "metadata_issues": [{"code": i.code, "message": i.message} for i in self.metadata_issues],
            "local_days": self.local_days,
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Deterministic JSON (sorted keys, fixed separators)."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=True)


def assess_quality(
    series: pd.Series,
    *,
    metadata: MeasurementMetadata | None = None,
    freq: str | pd.Timedelta | None = None,
    bounds: tuple[float | None, float | None] | None = None,
    stale_min_run: int | None = None,
    stale_atol: float = 0.0,
    stale_exclude: Collection[float] = (),
    cumulative: bool = False,
    counter_tolerance: float = 0.0,
    jump_max_delta: float | None = None,
    origin: pd.Timestamp | None = None,
    tz: str | None = None,
    known_outages: Iterable[tuple[pd.Timestamp | str, pd.Timestamp | str]] = (),
    max_listed: int = 100,
) -> QualityReport:
    """Run all checks on ``series`` and return a :class:`QualityReport`.

    The expected step is taken from ``freq``, else ``metadata.resolution``.
    If neither is given, grid-based checks (gaps, off-grid, completeness) are
    skipped and only the inferred resolution is reported; the step is never
    guessed silently. A metadata resolution with no fixed length (``"MS"``,
    ``"W-MON"``) is a local-calendar step in ``metadata.timezone``, as if
    ``tz`` were given; ``"D"`` stays the 24-hour step (pass ``tz`` for local
    days, which are 23 or 25 hours long across DST).

    ``completeness`` is the share of expected grid timestamps that are
    present, whatever their values: a row with a missing value still counts
    and is flagged ``MISSING_VALUE`` instead. It is ``None`` without a step,
    for an empty series, or when no grid point falls inside the data's time
    span (possible with ``origin``, or with a calendar step longer than the
    data, such as ``"MS"`` on two weeks of data).

    ``origin`` anchors the grid and ``tz`` makes ``freq`` a local-calendar
    step (see :func:`energydata_kit.expected_grid`). The per-local-day
    section (``local_days``, in ``metadata.timezone``, else UTC) is produced
    only for a fixed step without ``tz``; it is ``None`` on a calendar grid
    and without a step.

    ``known_outages`` lists periods in which data is known to be missing
    (maintenance, a meter swap), as timezone-aware ``(start, end)`` pairs,
    both ends included. Missing grid timestamps inside them are counted in
    ``n_missing_explained``; ``completeness_excluding_outages`` leaves the
    grid timestamps inside them out entirely (``None`` when no outages are
    given, or when they cover the whole grid). Gaps, ``n_missing_intervals``,
    ``completeness`` and flags are unchanged: an outage explains a gap, it
    does not hide it.

    ``stale_min_run``, ``cumulative`` and ``jump_max_delta`` enable the opt-in
    stale-value, counter-decrease and jump checks; ``stale_atol``,
    ``stale_exclude`` and ``counter_tolerance`` tune them (see
    :func:`energydata_kit.flag_series`).

    Options may be numpy scalars (e.g. bounds from ``series.quantile()``);
    the report stores them as plain Python numbers.

    ``series`` must have a timezone-aware ``DatetimeIndex`` without ``NaT``
    and is not modified.
    """
    if isinstance(max_listed, bool | np.bool_):
        raise TypeError(f"max_listed must be an integer, got {max_listed!r}")
    max_listed = operator.index(max_listed)  # TypeError for 1.5; accepts numpy integers
    outages = _outages(known_outages)
    if not isinstance(stale_exclude, str | bytes):
        stale_exclude = tuple(stale_exclude)  # read once: applied and recorded alike
    if max_listed < 0:
        raise ValueError("max_listed must be >= 0")
    freq, tz = _grid_from_metadata(freq, tz, metadata)
    # Fixed steps are validated up front; calendar steps (tz given) stay as
    # pandas frequency strings.
    step = None if freq is None or tz is not None else to_step(freq)
    grid_freq = step if step is not None else freq

    flagged = flag_series(
        series,
        freq=grid_freq,
        bounds=bounds,
        stale_min_run=stale_min_run,
        stale_atol=stale_atol,
        stale_exclude=stale_exclude,
        cumulative=cumulative,
        counter_tolerance=counter_tolerance,
        jump_max_delta=jump_max_delta,
        origin=origin,
        tz=tz,
    )
    index = flagged.index
    assert isinstance(index, pd.DatetimeIndex)
    flags = flagged[FLAG_COLUMN].to_numpy()

    counts = {
        m.name: int(np.count_nonzero(flags & m.value))
        for m in QualityFlag
        if m.value and m is not QualityFlag.MISSING_INTERVAL and m.name is not None
    }
    counts["ANY"] = int(np.count_nonzero(flags))

    gaps: list[Gap] = []
    n_expected = None
    completeness = None
    n_missing_explained = None
    completeness_excluding_outages = None
    if grid_freq is not None and len(index):
        # One grid and one presence test serve gaps, completeness and known outages.
        grid = expected_grid(index, grid_freq, origin=origin, tz=tz)
        on_grid = on_index(grid, index)
        gaps = _gaps(grid, on_grid)
        n_expected = len(grid)
        present = int(np.count_nonzero(on_grid))
        # No grid point inside the data's time span (possible with origin=): undefined.
        completeness = round(present / n_expected, 6) if n_expected else None
        n_missing_explained = 0
        if outages:
            grid_ns = utc_ns(grid)
            inside = np.zeros(len(grid), dtype=bool)
            for lo, hi in outages:
                inside |= (grid_ns >= lo) & (grid_ns <= hi)
            missing = ~on_grid
            n_missing_explained = int(np.count_nonzero(missing & inside))
            outside = int(np.count_nonzero(~inside))
            if outside:
                present_outside = int(np.count_nonzero(~missing & ~inside))
                completeness_excluding_outages = round(present_outside / outside, 6)

    local_days = None
    if step is not None and len(index):
        day_tz = "UTC" if metadata is None else metadata.timezone
        label = IntervalLabel.START if metadata is None else metadata.interval_label
        days = local_day_completeness(index, step, day_tz, interval_label=label, origin=origin)
        local_days = _summarize_local_days(days, day_tz, max_listed)

    dups = find_duplicate_timestamps(index)
    truncated = {
        "gaps": len(gaps) > max_listed,
        "duplicate_timestamps": len(dups) > max_listed,
        "incomplete_local_days": bool(local_days and local_days["n_incomplete_days"] > max_listed),
    }

    return QualityReport(
        series_name=None if series.name is None else str(series.name),
        fingerprint=fingerprint_series(series),
        n_rows=len(series),
        first_timestamp=_iso(index.min()) if len(index) else None,
        last_timestamp=_iso(index.max()) if len(index) else None,
        expected_resolution=_iso_duration(step) if tz is None else _freq_label(freq),
        inferred_resolution=_iso_duration(infer_resolution(index)),
        n_expected_intervals=n_expected,
        completeness=completeness,
        flag_counts=counts,
        gaps=gaps[:max_listed],
        n_gaps=len(gaps),
        n_missing_intervals=sum(g.missing_count for g in gaps),
        duplicate_timestamps=[ts.isoformat() for ts in dups[:max_listed]],
        n_duplicate_timestamps=len(dups),
        parameters={
            "freq": _iso_duration(step) if tz is None else _freq_label(freq),
            "origin": None if origin is None else pd.Timestamp(origin).isoformat(),
            "tz": tz,
            "bounds": None if bounds is None else [_plain(b) for b in bounds],
            "max_listed": max_listed,
            "stale_min_run": _plain(stale_min_run),
            "stale_atol": _plain(stale_atol),
            "stale_exclude": [float(x) for x in stale_exclude],
            "cumulative": _plain(cumulative),
            "counter_tolerance": _plain(counter_tolerance),
            "jump_max_delta": _plain(jump_max_delta),
            "known_outages": [[_iso_ns(lo), _iso_ns(hi)] for lo, hi in outages],
        },
        metadata=None if metadata is None else metadata.to_dict(),
        truncated=truncated,
        metadata_issues=[] if metadata is None else check_metadata_consistency(metadata),
        local_days=local_days,
        n_missing_explained=n_missing_explained,
        completeness_excluding_outages=completeness_excluding_outages,
    )


def _summarize_local_days(days: pd.DataFrame, tz: str, max_listed: int) -> dict[str, Any]:
    incomplete = days[days["missing"] > 0]
    return {
        "timezone": tz,
        "n_days": len(days),
        "n_complete_days": len(days) - len(incomplete),
        "n_incomplete_days": len(incomplete),
        # Days shorter than one step expect nothing and have no completeness.
        "min_completeness": None if days["completeness"].isna().all() else float(days["completeness"].min()),
        "incomplete_days": [
            {"date": str(d), "expected": int(e), "present": int(p)}
            for d, e, p in zip(
                incomplete.index[:max_listed],
                incomplete["expected"].iloc[:max_listed],
                incomplete["present"].iloc[:max_listed],
                strict=True,
            )
        ],
    }
