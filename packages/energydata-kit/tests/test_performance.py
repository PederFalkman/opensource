"""Coarse guard against accidental quadratic behaviour on long series.

The budgets are ~20x the times measured on a laptop-class CI runner (see
docs/architecture/PERFORMANCE.md), so they only fail on a real regression,
not on a slow machine. Run ``python benchmarks/run.py`` for actual numbers.
"""

import time

import numpy as np
import pandas as pd

import energydata_kit as ek


def year_of_minutes() -> pd.Series:
    rng = np.random.default_rng(0)
    n = 525_600
    index = pd.date_range("2023-01-01", periods=n, freq="1min", tz="UTC")
    series = pd.Series(rng.normal(100.0, 5.0, n), index=index, name="power")
    return series.drop(series.index[rng.choice(n, n // 1000, replace=False)])


def test_assess_quality_on_a_year_of_minute_data_is_fast():
    series = year_of_minutes()
    start = time.perf_counter()
    report = ek.assess_quality(series, freq="1min", bounds=(0, 200), stale_min_run=5, jump_max_delta=50)
    elapsed = time.perf_counter() - start
    assert report.n_missing_intervals == 525
    assert elapsed < 10.0, f"assess_quality took {elapsed:.1f} s on 525k rows"
