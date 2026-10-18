import numpy as np
import pandas as pd
import pytest

pa = pytest.importorskip("pandera.pandas")

from energydata_kit import MeasurementMetadata, flag_series, make_synthetic_series  # noqa: E402
from energydata_kit import pandera_checks as pc  # noqa: E402

META = MeasurementMetadata(name="synthetic_power", unit="kW", resolution="15min", aggregation="mean")


def failed_checks(schema, series):
    try:
        schema.validate(series, lazy=True)
    except pa.errors.SchemaErrors as exc:
        return sorted(set(exc.failure_cases["check"]))
    return []


def test_clean_series_passes():
    s = make_synthetic_series()
    out = pc.series_schema(metadata=META).validate(s)
    pd.testing.assert_series_equal(out, s)


def test_all_failures_are_reported_together():
    s = make_synthetic_series(drop=[5], duplicate=[10], inf_at=[20])
    assert failed_checks(pc.series_schema(metadata=META), s) == [
        "duplicate timestamps",
        "missing intervals after these timestamps at 15min resolution",
        "non-finite or non-numeric values",
    ]


def test_missing_values_follow_nullable():
    s = make_synthetic_series(nan_at=[3])
    assert failed_checks(pc.series_schema(metadata=META), s) == []
    assert failed_checks(pc.series_schema(metadata=META, nullable=False), s) != []


def test_grid_checks_need_a_step():
    s = make_synthetic_series(drop=[5])
    assert failed_checks(pc.series_schema(), s) == []
    assert failed_checks(pc.series_schema(freq="15min"), s) == [
        "missing intervals after these timestamps at 15min resolution"
    ]


def test_gap_is_reported_on_the_row_before_it():
    s = make_synthetic_series(drop=[5, 6, 40])
    try:
        pc.series_schema(freq="15min").validate(s, lazy=True)
    except pa.errors.SchemaErrors as exc:
        rows = sorted(exc.failure_cases["index"])
    assert rows == [pd.Timestamp("2024-01-01T01:00Z"), pd.Timestamp("2024-01-01T09:45Z")]


def test_naive_index_fails():
    s = pd.Series([1.0, 2.0], index=pd.date_range("2024-01-01", periods=2, freq="h"))
    assert "timestamps must be timezone-aware; use normalize_timestamps()" in failed_checks(
        pc.series_schema(), s
    )


def test_bounds_stale_and_counter():
    idx = pd.date_range("2024-01-01", periods=6, freq="1h", tz="UTC")
    s = pd.Series([5.0, 5.0, 5.0, 6.0, 1.0, 900.0], index=idx)
    schema = pc.series_schema(freq="1h", bounds=(0, 100), stale_min_run=3, cumulative=True)
    assert failed_checks(schema, s) == [
        "cumulative counter decreased",
        "runs of 3 or more repeated values",
        "values outside [0, 100]",
    ]


def test_stale_check_keeps_nan_as_run_breaker():
    idx = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
    s = pd.Series([5.0, 5.0, np.nan, 5.0, 5.0], index=idx)
    assert failed_checks(pa.SeriesSchema(checks=[pc.stale_check(3)], nullable=True), s) == []


def test_index_checks_work_on_pa_index():
    s = make_synthetic_series(duplicate=[2], drop=[6])
    schema = pa.SeriesSchema(
        index=pa.Index(checks=[pc.no_duplicate_timestamps_check(), pc.on_grid_check("15min")])
    )
    assert failed_checks(schema, s) == ["duplicate timestamps"]
    # On Pandera 0.24 every check in pa.Index raised TypeError (it passes the timestamps
    # with a RangeIndex), and the timezone check reported aware timestamps as naive.
    assert failed_checks(pa.SeriesSchema(index=pa.Index(checks=[pc.timezone_aware_check()])), s) == []


def test_agrees_with_flag_series():
    s = make_synthetic_series(duplicate=[4], inf_at=[7])
    flagged = flag_series(s, freq="15min")
    try:
        pc.series_schema(metadata=META).validate(s, lazy=True)
    except pa.errors.SchemaErrors as exc:
        failing_rows = set(exc.failure_cases["index"].dropna())
    assert failing_rows == set(flagged.index[flagged["quality_flag"] != 0])


def test_invalid_arguments_fail_early():
    with pytest.raises(ValueError):
        pc.stale_check(1)
    with pytest.raises(ValueError):
        pc.counter_check(tolerance=-1)
    with pytest.raises(ValueError):
        pc.jump_check(0)
    # These were accepted, and then every validation failed on the configuration.
    with pytest.raises(ValueError, match="exceeds upper bound"):
        pc.within_bounds_check(lower=5, upper=1)
    with pytest.raises(ValueError, match="only numbers"):
        pc.stale_check(3, exclude=["x"])
    with pytest.raises(ValueError):
        pc.series_schema(bounds=(5, 1))


def test_consecutive_checks_refuse_unsorted_timestamps():
    # In file order 5, 1, 2 looks like a counter decrease; in time order it is 1, 2, 5.
    # flag_series refuses such input, and the Pandera checks now say so too.
    index = pd.DatetimeIndex(["2024-01-01T00:30Z", "2024-01-01T00:00Z", "2024-01-01T00:15Z"])
    series = pd.Series([5.0, 1.0, 2.0], index=index)
    for check in (pc.counter_check(), pc.jump_check(3.0), pc.stale_check(2)):
        with pytest.raises(pa.errors.SchemaErrors) as exc:
            pa.SeriesSchema(checks=[check]).validate(series, lazy=True)
        assert "require a sorted index" in str(exc.value.failure_cases["failure_case"].iloc[0])
    # Without timestamps, the row order is the only order there is.
    assert pa.SeriesSchema(checks=[pc.counter_check()]).validate(pd.Series([1.0, 2.0])).tolist() == [1.0, 2.0]


def test_jump_check():
    idx = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
    s = pd.Series([1.0, np.nan, 1.5, 40.0, 41.0], index=idx)
    assert failed_checks(pc.series_schema(freq="1h", jump_max_delta=10.0), s) == [
        "changes larger than 10.0 between consecutive values"
    ]
    assert failed_checks(pc.series_schema(freq="1h", jump_max_delta=50.0), s) == []


def test_origin_and_calendar_steps():
    idx = pd.date_range("2024-03-29", periods=5, freq="D", tz="Europe/Stockholm").tz_convert("UTC")
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=idx)
    assert failed_checks(pc.series_schema(freq="D", tz="Europe/Stockholm"), s) == []
    gap = s.drop(idx[2])
    with pytest.raises(pa.errors.SchemaErrors) as exc:
        pc.series_schema(freq="D", tz="Europe/Stockholm").validate(gap, lazy=True)
    assert list(exc.value.failure_cases["index"]) == [idx[1]]
    shifted = pd.Series(
        [1.0, 2.0, 3.0],
        index=pd.DatetimeIndex(["2024-01-01T00:07Z", "2024-01-01T00:15Z", "2024-01-01T00:30Z"]),
    )
    origin = pd.Timestamp("2024-01-01T00:00Z")
    assert failed_checks(pa.SeriesSchema(checks=[pc.on_grid_check("15min", origin=origin)]), shifted) == [
        "timestamps not aligned to 15min"
    ]


def test_series_schema_tuning_options():
    idx = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
    night = pd.Series([0.0, 0.0, 0.0, 4.0, 5.0], index=idx)
    assert failed_checks(pc.series_schema(freq="1h", stale_min_run=3), night) == [
        "runs of 3 or more repeated values"
    ]
    assert failed_checks(pc.series_schema(freq="1h", stale_min_run=3, stale_exclude=[0.0]), night) == []
    register = pd.Series([10.0, 9.99, 12.0, 13.0, 14.0], index=idx)
    assert failed_checks(pc.series_schema(freq="1h", cumulative=True), register) == [
        "cumulative counter decreased"
    ]
    assert failed_checks(pc.series_schema(freq="1h", cumulative=True, counter_tolerance=0.05), register) == []
    with pytest.raises(ValueError, match="require"):
        pc.series_schema(counter_tolerance=0.1)


def test_leading_gap_after_off_grid_start_is_reported():
    # The series starts off-grid, so no present grid point precedes the gap at 00:15;
    # assess_quality counts that gap, and the schema must fail too.
    index = pd.DatetimeIndex(["2024-06-01 00:07", "2024-06-01 00:30", "2024-06-01 00:45"], tz="UTC")
    series = pd.Series([1.0, 2.0, 3.0], index=index)
    origin = pd.Timestamp("2024-06-01", tz="UTC")
    schema = pa.SeriesSchema(checks=[pc.no_missing_intervals_check("15min", origin=origin)])
    with pytest.raises(pa.errors.SchemaErrors) as info:
        schema.validate(series, lazy=True)
    assert list(info.value.failure_cases["index"]) == [index[0]]
