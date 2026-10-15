"""Reproducible quality reports.

A report is a pure function of the input data, the parameters and the package
version. It contains no wall-clock time, host name or random state, so the same
input yields byte-identical JSON.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from energydata_kit import __version__
from energydata_kit.flags import FLAG_COLUMN, QualityFlag, flag_series
from energydata_kit.intervals import (
    Gap,
    expected_grid,
    find_duplicate_timestamps,
    find_missing_intervals,
    to_step,
)
from energydata_kit.metadata import MeasurementMetadata
from energydata_kit.timestamps import infer_resolution, utc_ns

__all__ = ["REPORT_SCHEMA_VERSION", "QualityReport", "assess_quality", "fingerprint_series"]

REPORT_SCHEMA_VERSION = "1"


def _iso(ts: pd.Timestamp | None) -> str | None:
    return None if ts is None else ts.isoformat()


def _iso_duration(td: pd.Timedelta | None) -> str | None:
    return None if td is None else td.isoformat()


def fingerprint_series(series: pd.Series) -> str:
    """SHA-256 over UTC timestamps (ns), numeric values and the series name.

    Stable across pandas versions and datetime resolutions. Non-numeric
    values contribute their ``repr``.
    """
    index = series.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise ValueError("series must have a timezone-aware DatetimeIndex")
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

    @property
    def n_flagged_rows(self) -> int:
        return self.flag_counts.get("ANY", 0)

    def to_dict(self) -> dict[str, Any]:
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
            "duplicate_timestamps": self.duplicate_timestamps,
            "n_duplicate_timestamps": self.n_duplicate_timestamps,
            "truncated": self.truncated,
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
    max_listed: int = 100,
) -> QualityReport:
    """Run all checks on ``series`` and return a :class:`QualityReport`.

    The expected step is taken from ``freq``, else ``metadata.resolution``.
    If neither is given, grid-based checks (gaps, off-grid, completeness) are
    skipped and only the inferred resolution is reported; the step is never
    guessed silently.

    ``series`` must have a timezone-aware ``DatetimeIndex`` and is not modified.
    """
    if max_listed < 0:
        raise ValueError("max_listed must be >= 0")
    if freq is None and metadata is not None:
        freq = metadata.resolution
    step = None if freq is None else to_step(freq)

    flagged = flag_series(series, freq=step, bounds=bounds)
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
    if step is not None and len(index):
        gaps = find_missing_intervals(index, step)
        grid = expected_grid(index, step)
        n_expected = len(grid)
        present = int(grid.isin(index.as_unit("ns")).sum())
        completeness = round(present / n_expected, 6)

    dups = find_duplicate_timestamps(index)
    truncated = {"gaps": len(gaps) > max_listed, "duplicate_timestamps": len(dups) > max_listed}

    return QualityReport(
        series_name=None if series.name is None else str(series.name),
        fingerprint=fingerprint_series(series),
        n_rows=len(series),
        first_timestamp=_iso(index.min()) if len(index) else None,
        last_timestamp=_iso(index.max()) if len(index) else None,
        expected_resolution=_iso_duration(step),
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
            "freq": _iso_duration(step),
            "bounds": None if bounds is None else list(bounds),
            "max_listed": max_listed,
        },
        metadata=None if metadata is None else metadata.to_dict(),
        truncated=truncated,
    )
