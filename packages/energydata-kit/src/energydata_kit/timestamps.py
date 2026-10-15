"""Timestamp normalization and validation.

All downstream checks in energydata-kit operate on timezone-aware UTC
timestamps. Converting to UTC first means daylight-saving transitions do not
create artificial gaps or duplicates: a local day with 23 or 25 hours is still
a regular grid in UTC.
"""

from __future__ import annotations

import datetime as _dt
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

__all__ = [
    "TimestampError",
    "TimestampSummary",
    "infer_resolution",
    "normalize_timestamps",
    "summarize_timestamps",
    "utc_ns",
]

_OFFSET_SUFFIX = re.compile(r"(Z|[+-]\d{2}(:?\d{2})?)$", re.IGNORECASE)

AmbiguousPolicy = Literal["raise", "infer"]
NonexistentPolicy = Literal["raise", "shift_forward", "shift_backward"]


class TimestampError(ValueError):
    """Raised when timestamps cannot be normalized unambiguously."""


def _is_aware(value: object) -> bool:
    if isinstance(value, str):
        return bool(_OFFSET_SUFFIX.search(value.strip()))
    if isinstance(value, _dt.datetime):  # includes pd.Timestamp
        return value.tzinfo is not None and value.utcoffset() is not None
    if isinstance(value, np.datetime64):
        return False
    raise TimestampError(f"unsupported timestamp value {value!r} of type {type(value).__name__}")


def _to_datetime_index(values: Iterable[object] | pd.Index | pd.Series) -> pd.DatetimeIndex:
    if isinstance(values, pd.DatetimeIndex):
        return values
    if isinstance(values, pd.Series) and pd.api.types.is_datetime64_any_dtype(values.dtype):
        return pd.DatetimeIndex(values)

    items = pd.Series(list(values), dtype=object)
    if items.isna().any():
        raise TimestampError(f"{int(items.isna().sum())} missing timestamp value(s)")
    aware = items.map(_is_aware)
    try:
        if bool(aware.all()):
            # Mixed UTC offsets (e.g. across a DST change) are only
            # representable after conversion to a common zone.
            return pd.DatetimeIndex(pd.to_datetime(items, utc=True, format="ISO8601"))
        if not bool(aware.any()):
            return pd.DatetimeIndex(pd.to_datetime(items, format="ISO8601"))
    except (ValueError, TypeError) as exc:
        raise TimestampError(f"could not parse timestamps: {exc}") from exc
    raise TimestampError(
        f"mix of timezone-aware ({int(aware.sum())}) and naive "
        f"({int((~aware).sum())}) timestamps; refusing to guess"
    )


def normalize_timestamps(
    values: Iterable[object] | pd.Index | pd.Series,
    *,
    assume_tz: str | None = None,
    ambiguous: AmbiguousPolicy = "raise",
    nonexistent: NonexistentPolicy = "raise",
) -> pd.DatetimeIndex:
    """Return timestamps as a timezone-aware UTC ``DatetimeIndex`` (ns resolution).

    Parameters
    ----------
    values:
        Timestamps as a ``DatetimeIndex``, datetime-like ``Series``, or an
        iterable of ISO 8601 strings / ``datetime`` objects.
    assume_tz:
        IANA time zone used to localize *naive* timestamps, e.g.
        ``"Europe/Stockholm"``. Required when the input is naive; ignored
        (must be ``None``) for timezone-aware input to avoid silent
        reinterpretation.
    ambiguous:
        How to resolve repeated local wall-clock times at the end of DST.
        ``"infer"`` uses the order of the timestamps; ``"raise"`` refuses.
    nonexistent:
        How to handle local times skipped at the start of DST.

    Order and duplicates are preserved; this function never drops or
    reorders rows.
    """
    idx = _to_datetime_index(values)
    if idx.hasnans:
        raise TimestampError(f"{int(np.count_nonzero(idx.isna()))} missing timestamp value(s)")

    if idx.tz is None:
        if assume_tz is None:
            raise TimestampError("timestamps are naive; pass assume_tz to state their time zone")
        try:
            idx = idx.tz_localize(assume_tz, ambiguous=ambiguous, nonexistent=nonexistent)
        except Exception as exc:  # pandas < 3 raises pytz errors, which are not ValueErrors
            raise TimestampError(f"could not localize to {assume_tz}: {exc}") from exc
    elif assume_tz is not None:
        raise TimestampError("assume_tz was given but timestamps are already timezone-aware")

    return idx.tz_convert("UTC").as_unit("ns")


def utc_ns(index: pd.DatetimeIndex) -> np.ndarray:
    """Timestamps as int64 nanoseconds since the Unix epoch (UTC)."""
    return np.asarray(index.as_unit("ns").to_numpy(dtype="datetime64[ns]")).view("i8")


def infer_resolution(index: pd.DatetimeIndex) -> pd.Timedelta | None:
    """Return the most common positive step between sorted unique timestamps.

    Ties are broken towards the smallest step. Returns ``None`` when fewer
    than two distinct timestamps exist.
    """
    unique = index.unique().sort_values()
    if len(unique) < 2:
        return None
    steps = pd.Series(np.diff(utc_ns(unique)))
    counts = steps.value_counts()
    best = int(counts[counts == counts.max()].index.min())
    return pd.Timedelta(best, unit="ns")


@dataclass(frozen=True)
class TimestampSummary:
    """Structural facts about a timestamp index."""

    n_timestamps: int
    n_unique: int
    is_timezone_aware: bool
    timezone: str | None
    is_monotonic_increasing: bool
    first: pd.Timestamp | None
    last: pd.Timestamp | None
    inferred_resolution: pd.Timedelta | None


def summarize_timestamps(index: pd.DatetimeIndex) -> TimestampSummary:
    """Describe an index without modifying it."""
    return TimestampSummary(
        n_timestamps=len(index),
        n_unique=int(index.nunique()),
        is_timezone_aware=index.tz is not None,
        timezone=None if index.tz is None else str(index.tz),
        is_monotonic_increasing=bool(index.is_monotonic_increasing),
        first=index.min() if len(index) else None,
        last=index.max() if len(index) else None,
        inferred_resolution=infer_resolution(index),
    )
