import datetime as dt

import pandas as pd
import pytest

from energydata_kit import (
    IntervalLabel,
    MeasurementMetadata,
    assess_quality,
    check_metadata_consistency,
    interval_bounds,
    local_day_completeness,
    make_synthetic_series,
    relabel_intervals,
)

IDX = pd.DatetimeIndex(["2024-01-01T00:15Z", "2024-01-01T00:30Z", "2024-01-01T00:30Z"])


def test_relabel_round_trip_preserves_order_and_duplicates():
    starts = relabel_intervals(IDX, "15min", "end", "start")
    assert list(starts) == [
        pd.Timestamp(t) for t in ("2024-01-01T00:00Z", "2024-01-01T00:15Z", "2024-01-01T00:15Z")
    ]
    assert relabel_intervals(starts, "15min", IntervalLabel.START, IntervalLabel.END).equals(IDX)


def test_relabel_same_label_is_a_copy():
    out = relabel_intervals(IDX, "15min", "start", "start")
    assert out.equals(IDX) and out is not IDX


def test_relabel_rejects_bad_input():
    with pytest.raises(ValueError):
        relabel_intervals(IDX, "15min", "end", "middle")
    with pytest.raises(ValueError, match="timezone-aware"):
        relabel_intervals(pd.DatetimeIndex(["2024-01-01"]), "15min", "end", "start")


def test_interval_bounds():
    starts, ends = interval_bounds(IDX[:1], "15min", "end")
    assert starts[0] == pd.Timestamp("2024-01-01T00:00Z")
    assert ends[0] == pd.Timestamp("2024-01-01T00:15Z")


def codes(**kwargs):
    return [i.code for i in check_metadata_consistency(MeasurementMetadata(name="x", **kwargs))]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"unit": "kW", "resolution": "15min", "aggregation": "mean"}, []),
        ({"unit": "kWh", "resolution": "15min", "aggregation": "sum", "interval_label": "end"}, []),
        ({"unit": "kWh"}, []),  # instantaneous register reading
        ({"unit": "kW", "resolution": "15min", "aggregation": "sum"}, ["SUM_OF_POWER"]),
        ({"unit": "kvar", "resolution": "1h", "aggregation": "sum"}, ["SUM_OF_POWER"]),
        ({"unit": "MWh", "resolution": "1h", "aggregation": "mean"}, ["AVERAGED_ENERGY"]),
        ({"unit": "kWh", "resolution": "1h", "aggregation": "max"}, ["AVERAGED_ENERGY"]),
        ({"unit": "kW", "aggregation": "mean"}, ["MISSING_RESOLUTION"]),
        ({"unit": "kW", "aggregation": "sum"}, ["SUM_OF_POWER", "MISSING_RESOLUTION"]),
        ({"unit": "V", "interval_label": "end"}, ["LABEL_ON_INSTANTANEOUS"]),
    ],
)
def test_metadata_consistency(kwargs, expected):
    assert codes(**kwargs) == expected


@pytest.mark.parametrize(
    ("day", "expected"),
    [("2024-03-31", 92), ("2024-10-27", 100), ("2024-06-01", 96)],
)
def test_local_day_expected_counts_follow_dst(day, expected):
    local = pd.date_range(day, periods=expected, freq="15min", tz="Europe/Stockholm")
    out = local_day_completeness(local.tz_convert("UTC"), "15min", "Europe/Stockholm")
    assert out.index.tolist() == [dt.date.fromisoformat(day)]
    assert out.iloc[0].to_dict() == {
        "expected": expected,
        "present": expected,
        "missing": 0,
        "completeness": 1.0,
    }


def test_local_day_end_labels_assign_midnight_to_previous_day():
    # End-labelled: 00:15..24:00 local covers exactly one day.
    ends = pd.date_range("2024-06-01 00:15", periods=96, freq="15min", tz="Europe/Stockholm")
    out = local_day_completeness(ends, "15min", "Europe/Stockholm", interval_label="end")
    assert out.index.tolist() == [dt.date(2024, 6, 1)]
    assert out["present"].tolist() == [96]
    # The same timestamps read as start labels spill into the next day.
    assert local_day_completeness(ends, "15min", "Europe/Stockholm").index.size == 2


def test_local_day_missing_duplicates_and_off_grid():
    idx = pd.date_range("2024-06-01", periods=96, freq="15min", tz="Europe/Stockholm").tz_convert("UTC")
    idx = idx.delete([10, 11]).append(idx[[5]]).append(pd.DatetimeIndex([idx[20] + pd.Timedelta("7min")]))
    out = local_day_completeness(idx, "15min", "Europe/Stockholm")
    assert out.iloc[0][["expected", "present", "missing"]].tolist() == [96, 94, 2]


def test_local_day_partial_edges_and_empty():
    idx = pd.date_range("2024-06-01 23:00", periods=8, freq="15min", tz="UTC")
    out = local_day_completeness(idx, "15min", "UTC")
    assert out["present"].tolist() == [4, 4] and out["expected"].tolist() == [96, 96]
    empty = local_day_completeness(pd.DatetimeIndex([], tz="UTC"), "15min", "UTC")
    assert empty.empty and list(empty.columns) == ["expected", "present", "missing", "completeness"]


def test_report_sections():
    s = make_synthetic_series(drop=[5, 6])
    meta = MeasurementMetadata(name="p", unit="kW", resolution="15min", aggregation="sum")
    data = assess_quality(s, metadata=meta).to_dict()
    assert data["metadata_issues"] == [
        {
            "code": "SUM_OF_POWER",
            "message": "aggregation 'sum' with power unit 'kW'; an energy unit was likely meant",
        }
    ]
    assert data["local_days"] == {
        "timezone": "UTC",
        "n_days": 1,
        "n_complete_days": 0,
        "n_incomplete_days": 1,
        "min_completeness": round(94 / 96, 6),
        "incomplete_days": [{"date": "2024-01-01", "expected": 96, "present": 94}],
    }


def test_report_without_step_has_no_local_days():
    data = assess_quality(make_synthetic_series()).to_dict()
    assert data["local_days"] is None and data["metadata_issues"] == []


def test_day_shorter_than_step_has_no_completeness():
    # 24-hour step: the 23-hour spring DST day expects no interval.
    idx = pd.date_range("2024-03-30T23:00Z", periods=4, freq="24h")
    days = local_day_completeness(idx, "24h", "Europe/Stockholm")
    spring = days.loc[dt.date(2024, 3, 31)]
    assert spring["expected"] == 0 and spring["missing"] == 0
    assert pd.isna(spring["completeness"])
    assert days["completeness"].drop(dt.date(2024, 3, 31)).notna().all()


def test_report_with_step_longer_than_a_day_is_valid_json():
    s = pd.Series(1.0, index=pd.date_range("2024-01-01", periods=5, freq="2D", tz="UTC"))
    report = assess_quality(s, freq="2D")
    assert report.local_days is not None and report.local_days["min_completeness"] is None
    assert "NaN" not in report.to_json()


def test_nat_in_index_is_rejected():
    idx = pd.DatetimeIndex([pd.Timestamp("2024-01-01T00:00Z"), pd.NaT])
    with pytest.raises(ValueError, match="NaT"):
        local_day_completeness(idx, "15min", "UTC")
