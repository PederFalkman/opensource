"""Small deterministic synthetic datasets for tests and examples.

The generated signal is a generic daily sinusoid plus seeded Gaussian noise.
It is not derived from, and does not represent, any real site, customer or
asset.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from energydata_kit.timestamps import utc_ns

__all__ = ["make_synthetic_series"]


def make_synthetic_series(
    *,
    start: str = "2024-01-01T00:00:00Z",
    periods: int = 96,
    freq: str = "15min",
    seed: int = 0,
    base: float = 100.0,
    amplitude: float = 20.0,
    noise: float = 1.0,
    name: str = "synthetic_power",
    drop: Sequence[int] = (),
    duplicate: Sequence[int] = (),
    nan_at: Sequence[int] = (),
    inf_at: Sequence[int] = (),
) -> pd.Series:
    """Return a regular UTC series with optional, explicitly placed defects.

    Defect positions refer to the clean series before any rows are dropped:

    - ``drop``: rows removed, creating missing intervals.
    - ``duplicate``: rows repeated once (same timestamp and value).
    - ``nan_at`` / ``inf_at``: values replaced by ``NaN`` / ``+inf``.

    The same arguments always return identical data.
    """
    if periods < 0:
        raise ValueError("periods must be >= 0")
    index = pd.date_range(pd.Timestamp(start), periods=periods, freq=freq, name="timestamp").as_unit("ns")
    if index.tz is None:
        raise ValueError("start must include a UTC offset, e.g. '...Z'")
    index = index.tz_convert("UTC")

    rng = np.random.default_rng(seed)
    day_fraction = (utc_ns(index) % 86_400_000_000_000) / 86_400_000_000_000
    values = base + amplitude * np.sin(2 * np.pi * day_fraction) + noise * rng.standard_normal(periods)

    defects = {"drop": drop, "duplicate": duplicate, "nan_at": nan_at, "inf_at": inf_at}
    for label, positions in defects.items():
        for pos in positions:
            if not 0 <= pos < periods:
                raise IndexError(f"{label} position {pos} out of range for {periods} periods")

    values[list(nan_at)] = np.nan
    values[list(inf_at)] = np.inf

    series = pd.Series(values, index=index, name=name)
    if duplicate:
        repeats = series.iloc[np.array(sorted(set(duplicate)), dtype=np.intp)]
        series = pd.concat([series, repeats]).sort_index(kind="stable")
    if drop:
        series = series[~series.index.isin(index[list(drop)])]
    return series
