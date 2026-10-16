"""Quality reports for several measurement columns that share one timestamp index.

Each column gets exactly the report :func:`energydata_kit.assess_quality`
gives for that column alone, so per-column reports stay comparable with
single-series reports. The timestamp sections (gaps, duplicates, off-grid
counts) are therefore repeated per column; they come from the shared index
and are identical.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from energydata_kit import __version__
from energydata_kit.flags import FLAG_COLUMN, VALUE_COLUMN, flag_series
from energydata_kit.metadata import MeasurementMetadata
from energydata_kit.report import REPORT_SCHEMA_VERSION, QualityReport, assess_quality

__all__ = [
    "COLUMN_OPTIONS",
    "FLAG_OPTIONS",
    "FrameQualityReport",
    "assess_frame",
    "flag_column",
    "flag_frame",
]

#: Options that may differ per column in :func:`assess_frame`.
COLUMN_OPTIONS = frozenset(
    {
        "metadata",
        "bounds",
        "stale_min_run",
        "stale_atol",
        "stale_exclude",
        "cumulative",
        "counter_tolerance",
        "jump_max_delta",
    }
)


@dataclass(frozen=True)
class FrameQualityReport:
    """Per-column quality reports for a frame, plus a combined fingerprint."""

    columns: dict[str, QualityReport]
    fingerprint: str
    package_version: str = __version__
    schema_version: str = REPORT_SCHEMA_VERSION
    summary: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def n_flagged_rows(self) -> int:
        """Rows flagged in at least one column's report, summed over columns."""
        return sum(r.n_flagged_rows for r in self.columns.values())

    @property
    def n_missing_intervals(self) -> int:
        """Missing grid intervals of the shared index (the same for every column)."""
        return max((r.n_missing_intervals for r in self.columns.values()), default=0)

    def to_dict(self) -> dict[str, Any]:
        """The report as plain JSON-compatible data (what ``to_json`` writes)."""
        return {
            "schema_version": self.schema_version,
            "package_version": self.package_version,
            "fingerprint": self.fingerprint,
            "column_order": list(self.columns),
            "summary": self.summary,
            "columns": {name: report.to_dict() for name, report in self.columns.items()},
        }

    def to_json(self, indent: int | None = 2) -> str:
        """Deterministic JSON (sorted keys, fixed separators)."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True, ensure_ascii=True)


def _validate(
    frame: pd.DataFrame,
    columns: Sequence[str] | None,
    metadata: Mapping[str, MeasurementMetadata] | None,
    per_column: Mapping[str, Mapping[str, Any]] | None,
    allowed: frozenset[str],
) -> tuple[list[str], dict[str, MeasurementMetadata], dict[str, dict[str, Any]]]:
    """Check column selection and per-column arguments; return them normalised."""
    names = list(frame.columns) if columns is None else list(columns)
    if not names:
        raise ValueError("no columns to assess")
    if not all(isinstance(n, str) for n in names):
        raise ValueError("column names must be strings")
    if len(set(names)) != len(names) or frame.columns.has_duplicates:
        raise ValueError("column names must be unique")
    unknown = [n for n in names if n not in frame.columns]
    if unknown:
        raise ValueError(f"columns not in frame: {unknown}")
    metas: dict[str, MeasurementMetadata] = dict(metadata or {})
    overrides_by_column: dict[str, dict[str, Any]] = {k: dict(v) for k, v in (per_column or {}).items()}
    for kind, keys in (("metadata", metas), ("per_column", overrides_by_column)):
        stray = sorted(set(keys) - set(names))
        if stray:
            raise ValueError(f"{kind} names columns that are not assessed: {stray}")
    for name, meta in metas.items():
        if meta.name != name:
            raise ValueError(f"metadata for column {name!r} is named {meta.name!r}")
    for name, overrides in overrides_by_column.items():
        bad = sorted(set(overrides) - allowed)
        if bad:
            raise ValueError(f"per_column[{name!r}]: unsupported options {bad}")
    return names, metas, overrides_by_column


def assess_frame(
    frame: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
    metadata: Mapping[str, MeasurementMetadata] | None = None,
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
    per_column: Mapping[str, Mapping[str, Any]] | None = None,
    max_listed: int = 100,
) -> FrameQualityReport:
    """Run :func:`energydata_kit.assess_quality` on each column of ``frame``.

    Parameters
    ----------
    frame:
        Columns of values indexed by one timezone-aware ``DatetimeIndex``.
        Not modified.
    columns:
        Columns to assess, in report order (default: all, in frame order).
        Column names must be strings.
    metadata:
        ``MeasurementMetadata`` per column name; each entry's ``name`` must
        equal its key. Columns without an entry get no metadata.
    freq, origin, tz, max_listed:
        Shared by all columns, as in :func:`energydata_kit.assess_quality`.
        Without ``freq``, each column uses its own ``metadata.resolution``.
    bounds, stale_min_run, stale_atol, stale_exclude, cumulative, counter_tolerance, jump_max_delta:
        Check options applied to every column. Columns usually differ in
        unit and meaning, so set them per column with ``per_column`` unless
        they really apply to all.
    per_column:
        Option overrides per column name, e.g.
        ``{"export_kwh": {"cumulative": True}, "power_kw": {"bounds": (0, 50)}}``.
        Allowed keys: :data:`COLUMN_OPTIONS`.
    """
    names, metas, overrides_by_column = _validate(frame, columns, metadata, per_column, COLUMN_OPTIONS)

    shared: dict[str, Any] = {
        "metadata": None,
        "bounds": bounds,
        "stale_min_run": stale_min_run,
        "stale_atol": stale_atol,
        "stale_exclude": stale_exclude,
        "cumulative": cumulative,
        "counter_tolerance": counter_tolerance,
        "jump_max_delta": jump_max_delta,
    }
    reports: dict[str, QualityReport] = {}
    for name in names:
        options = {**shared, "metadata": metas.get(name), **overrides_by_column.get(name, {})}
        series = frame[name].rename(name)
        reports[name] = assess_quality(
            series, freq=freq, origin=origin, tz=tz, max_listed=max_listed, **options
        )

    digest = hashlib.sha256()
    for name, report in reports.items():
        digest.update(f"{name}\0{report.fingerprint}\n".encode())
    summary = {
        name: {
            "n_flagged_rows": r.n_flagged_rows,
            "completeness": r.completeness,
            "n_missing_intervals": r.n_missing_intervals,
            "n_metadata_issues": len(r.metadata_issues),
        }
        for name, r in reports.items()
    }
    return FrameQualityReport(columns=reports, fingerprint=digest.hexdigest(), summary=summary)


#: Options that may differ per column in :func:`flag_frame`.
FLAG_OPTIONS = COLUMN_OPTIONS - {"metadata"}


def flag_column(name: str) -> str:
    """Name of the flag column for value column ``name`` in :func:`flag_frame` output."""
    return f"{FLAG_COLUMN}_{name}"


def flag_frame(
    frame: pd.DataFrame,
    *,
    columns: Sequence[str] | None = None,
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
    per_column: Mapping[str, Mapping[str, Any]] | None = None,
) -> pd.DataFrame:
    """Run :func:`energydata_kit.flag_series` on each column of ``frame``.

    Returns a new frame with, for each assessed column in order, the original
    values and a ``quality_flag_<column>`` bitmask (see :func:`flag_column`).
    Each flag column is exactly what ``flag_series`` gives for that column.
    With ``insert_missing``, rows for absent grid timestamps are added once
    and flagged ``MISSING_INTERVAL | MISSING_VALUE`` in every flag column.
    ``frame`` is not modified.

    Shared options and ``per_column`` overrides work as in :func:`assess_frame`
    (allowed override keys: :data:`FLAG_OPTIONS`).
    """
    names, _, overrides_by_column = _validate(frame, columns, None, per_column, FLAG_OPTIONS)
    clashes = sorted(flag_column(n) for n in names if flag_column(n) in frame.columns)
    if clashes:
        raise ValueError(f"flag column names already used by value columns: {clashes}")
    shared: dict[str, Any] = {
        "bounds": bounds,
        "stale_min_run": stale_min_run,
        "stale_atol": stale_atol,
        "stale_exclude": stale_exclude,
        "cumulative": cumulative,
        "counter_tolerance": counter_tolerance,
        "jump_max_delta": jump_max_delta,
    }
    parts: dict[str, pd.Series] = {}
    index: pd.Index | None = None
    for name in names:
        options = {**shared, **overrides_by_column.get(name, {})}
        flagged = flag_series(
            frame[name], freq=freq, insert_missing=insert_missing, origin=origin, tz=tz, **options
        )
        if index is None:
            index = flagged.index
        elif not flagged.index.equals(index):  # pragma: no cover - same index in, same rows out
            raise AssertionError("flag_series produced different rows for columns of one frame")
        parts[name] = flagged[VALUE_COLUMN].rename(name)
        parts[flag_column(name)] = flagged[FLAG_COLUMN].rename(flag_column(name))
    result = pd.concat(list(parts.values()), axis=1)
    result.index.name = frame.index.name
    return result
