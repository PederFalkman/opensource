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


def test_assess_quality_builds_the_grid_once(monkeypatch):
    # Gaps, completeness and known outages share one grid and one presence test (OSS-74).
    import energydata_kit.report as report_module

    calls = {"expected_grid": 0, "on_index": 0}
    for name in calls:
        original = getattr(report_module, name)

        def counted(*args, _original=original, _name=name, **kwargs):
            calls[_name] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(report_module, name, counted)

    index = pd.date_range("2024-03-30", periods=96 * 3, freq="15min", tz="UTC").delete([5, 6, 200])
    series = pd.Series(1.0, index=index)
    outage = [(index[0], index[10])]
    for tz in (None, "Europe/Stockholm"):
        calls.update(expected_grid=0, on_index=0)
        report = ek.assess_quality(series, freq="15min", tz=tz, known_outages=outage)
        assert calls == {"expected_grid": 1, "on_index": 1}
        expected_gaps = ek.find_missing_intervals(index, "15min", tz=tz)
        assert [(g.start.isoformat(), g.end.isoformat(), g.missing_count) for g in expected_gaps] == [
            (g["start"], g["end"], g["missing_count"]) for g in report.to_dict()["gaps"]
        ]
        assert report.n_missing_intervals == 3 and report.n_missing_explained == 2
