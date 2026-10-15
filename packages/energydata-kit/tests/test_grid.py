"""Grid origin and local-calendar steps (OSS-05)."""

import pandas as pd
import pytest

from energydata_kit import (
    FLAG_COLUMN,
    QualityFlag,
    assess_quality,
    expected_grid,
    find_missing_intervals,
    flag_series,
    missing_timestamps,
    normalize_timestamps,
    off_grid_mask,
)

UTC_MIDNIGHT = pd.Timestamp("2024-01-01T00:00Z")
TZ = "Europe/Stockholm"


def ts(*values):
    return pd.DatetimeIndex([pd.Timestamp(v) for v in values])


# --- origin -------------------------------------------------------------------


def test_origin_stops_a_leading_off_grid_timestamp_shifting_the_grid():
    idx = ts("2024-01-01T00:07Z", "2024-01-01T00:15Z", "2024-01-01T00:30Z", "2024-01-01T00:45Z")
    # Default anchor is the first timestamp, so every later row looks off-grid.
    assert off_grid_mask(idx, "15min").tolist() == [False, True, True, True]
    assert off_grid_mask(idx, "15min", origin=UTC_MIDNIGHT).tolist() == [True, False, False, False]
    assert list(expected_grid(idx, "15min", origin=UTC_MIDNIGHT)) == list(idx[1:])
    assert find_missing_intervals(idx, "15min", origin=UTC_MIDNIGHT) == []


def test_origin_snaps_window_to_grid():
    idx = ts("2024-01-01T00:20Z", "2024-01-01T01:10Z")
    grid = expected_grid(idx, "15min", origin=UTC_MIDNIGHT)
    assert [t.strftime("%H:%M") for t in grid] == ["00:30", "00:45", "01:00"]
    assert len(missing_timestamps(idx, "15min", origin=UTC_MIDNIGHT)) == 3
    # Origin after the data and window narrower than a step both work.
    late = pd.Timestamp("2030-01-01T00:00Z")
    assert len(expected_grid(idx, "15min", origin=late)) == 3
    assert len(expected_grid(ts("2024-01-01T00:20Z", "2024-01-01T00:25Z"), "15min", origin=UTC_MIDNIGHT)) == 0


def test_origin_must_be_timezone_aware():
    idx = ts("2024-01-01T00:00Z")
    with pytest.raises(ValueError, match="origin must be timezone-aware"):
        off_grid_mask(idx, "15min", origin=pd.Timestamp("2024-01-01"))


# --- local-calendar steps -----------------------------------------------------


def local_midnights(start, days, freq="D"):
    return normalize_timestamps(pd.date_range(start, periods=days, freq=freq, tz=TZ))


def test_daily_local_data_across_dst_is_regular_only_on_a_calendar_grid():
    idx = local_midnights("2024-03-29", 5)  # includes the 23-hour day of 2024-03-31
    assert not off_grid_mask(idx, "D", tz=TZ).any()
    assert find_missing_intervals(idx, "D", tz=TZ) == []
    # A fixed 24-hour UTC grid misreads the DST day: that is the old limitation.
    assert off_grid_mask(idx, "1D").tolist() == [False, False, False, True, True]


def test_daily_gap_is_reported_at_local_midnight():
    idx = local_midnights("2024-10-25", 5).delete(2)  # drop 2024-10-27 (25-hour day)
    gaps = find_missing_intervals(idx, "D", tz=TZ)
    assert [(g.start, g.missing_count) for g in gaps] == [(pd.Timestamp("2024-10-26T22:00Z"), 1)]


def test_monthly_steps_and_explicit_tz_requirement():
    idx = local_midnights("2024-01-01", 6, freq="MS").delete(3)  # drop April (DST already on)
    assert [g.start for g in find_missing_intervals(idx, "MS", tz=TZ)] == [pd.Timestamp("2024-03-31T22:00Z")]
    with pytest.raises(ValueError, match="pass tz="):
        find_missing_intervals(idx, "MS")


def test_calendar_origin_sets_wall_clock_time():
    # Daily readings at 06:00 local, one taken at 07:00 by mistake.
    idx = normalize_timestamps(["2024-03-30 06:00", "2024-03-31 07:00", "2024-04-01 06:00"], assume_tz=TZ)
    origin = pd.Timestamp("2024-01-01 06:00", tz=TZ)
    assert off_grid_mask(idx, "D", origin=origin, tz=TZ).tolist() == [False, True, False]
    assert [g.start for g in find_missing_intervals(idx, "D", origin=origin, tz=TZ)] == [
        pd.Timestamp("2024-03-31T04:00Z")
    ]


# --- flag_series and report ---------------------------------------------------


def test_flag_series_inserts_missing_local_day():
    idx = local_midnights("2024-03-29", 5).delete(2)
    s = pd.Series([1.0, 2.0, 4.0, 5.0], index=idx)
    out = flag_series(s, freq="D", tz=TZ, insert_missing=True)
    assert len(out) == 5
    inserted = out[(out[FLAG_COLUMN] & int(QualityFlag.MISSING_INTERVAL)) != 0]
    assert list(inserted.index) == [pd.Timestamp("2024-03-30T23:00Z")]
    assert str(out.index.tz) == "UTC"


def test_report_with_calendar_step():
    idx = local_midnights("2024-03-29", 5).delete(2)
    data = assess_quality(pd.Series([1.0, 2.0, 4.0, 5.0], index=idx, name="daily"), freq="D", tz=TZ).to_dict()
    assert data["expected_resolution"] == "D"
    assert data["n_expected_intervals"] == 5 and data["n_missing_intervals"] == 1
    assert data["completeness"] == 0.8
    assert data["local_days"] is None
    assert data["parameters"]["tz"] == TZ and data["parameters"]["freq"] == "D"


def test_report_with_origin():
    idx = ts("2024-01-01T00:07Z", "2024-01-01T00:15Z", "2024-01-01T00:30Z")
    data = assess_quality(pd.Series([1.0, 2.0, 3.0], index=idx), freq="15min", origin=UTC_MIDNIGHT).to_dict()
    assert data["flag_counts"]["OFF_GRID_TIMESTAMP"] == 1
    assert data["n_gaps"] == 0
    assert data["parameters"]["origin"] == "2024-01-01T00:00:00+00:00"
