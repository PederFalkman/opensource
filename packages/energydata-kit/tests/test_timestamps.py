import datetime as dt

import pandas as pd
import pytest

from energydata_kit import TimestampError, infer_resolution, normalize_timestamps, summarize_timestamps


def test_naive_requires_assume_tz():
    with pytest.raises(TimestampError, match="naive"):
        normalize_timestamps(["2024-01-01 00:00", "2024-01-01 01:00"])


def test_naive_localized_and_converted_to_utc():
    idx = normalize_timestamps(["2024-01-01 01:00", "2024-01-01 02:00"], assume_tz="Europe/Stockholm")
    assert str(idx.tz) == "UTC"
    assert idx.unit == "ns"
    assert list(idx) == [pd.Timestamp("2024-01-01T00:00Z"), pd.Timestamp("2024-01-01T01:00Z")]


def test_mixed_offsets_across_dst_are_accepted():
    # Spring-forward in Europe/Stockholm: 01:45+01:00 is followed by 03:00+02:00.
    idx = normalize_timestamps(["2024-03-31T01:45:00+01:00", "2024-03-31T03:00:00+02:00"])
    assert idx[1] - idx[0] == pd.Timedelta("15min")


def test_mixed_aware_and_naive_rejected():
    with pytest.raises(TimestampError, match="mix of timezone-aware"):
        normalize_timestamps(["2024-01-01T00:00Z", "2024-01-01T01:00"])


def test_unparseable_value_named_instead_of_reported_as_naive():
    # "not-a-date" has no offset suffix; it must not be counted as naive.
    expected = r"could not parse 1 timestamp\(s\) as ISO 8601 \(position 0: 'not-a-date'\)"
    with pytest.raises(TimestampError, match=expected):
        normalize_timestamps(["not-a-date", "2024-01-01T01:00Z"])
    with pytest.raises(TimestampError, match="position 1: '2024-13-01T00:00Z'"):
        normalize_timestamps(["2024-01-01T00:00Z", "2024-13-01T00:00Z"])


def test_assume_tz_with_aware_input_rejected():
    with pytest.raises(TimestampError, match="already timezone-aware"):
        normalize_timestamps(["2024-01-01T00:00Z"], assume_tz="UTC")


def test_missing_and_unparseable_rejected():
    with pytest.raises(TimestampError, match="missing"):
        normalize_timestamps(["2024-01-01T00:00Z", None])
    with pytest.raises(TimestampError, match="parse"):
        normalize_timestamps(["2024-01-01T00:00Z", "not a dateZ"])


def test_ambiguous_fall_back_hour():
    # 02:00-02:45 local occurs twice on 2024-10-27 in Europe/Stockholm.
    local = pd.date_range("2024-10-27 01:00", "2024-10-27 03:45", freq="15min").tolist()
    repeated = local[:8] + local[4:8] + local[8:]
    with pytest.raises(TimestampError, match="localize"):
        normalize_timestamps(repeated, assume_tz="Europe/Stockholm")
    idx = normalize_timestamps(repeated, assume_tz="Europe/Stockholm", ambiguous="infer")
    assert idx.is_unique and idx.is_monotonic_increasing
    assert infer_resolution(idx) == pd.Timedelta("15min")
    assert len(idx) == 16


def test_nonexistent_spring_forward_policy():
    with pytest.raises(TimestampError):
        normalize_timestamps(["2024-03-31 02:30"], assume_tz="Europe/Stockholm")
    idx = normalize_timestamps(
        ["2024-03-31 02:30"], assume_tz="Europe/Stockholm", nonexistent="shift_forward"
    )
    assert idx[0] == pd.Timestamp("2024-03-31T01:00Z")


def test_order_and_duplicates_preserved():
    values = ["2024-01-01T02:00Z", "2024-01-01T01:00Z", "2024-01-01T01:00Z"]
    idx = normalize_timestamps(values)
    assert list(idx.strftime("%H")) == ["02", "01", "01"]


def test_datetime_objects_and_index_input():
    aware = [dt.datetime(2024, 1, 1, tzinfo=dt.UTC), dt.datetime(2024, 1, 1, 1, tzinfo=dt.UTC)]
    assert len(normalize_timestamps(aware)) == 2
    idx = pd.date_range("2024-01-01", periods=3, freq="h", tz="Europe/Berlin")
    assert str(normalize_timestamps(idx).tz) == "UTC"


def test_unsupported_type_rejected():
    with pytest.raises(TimestampError, match="unsupported"):
        normalize_timestamps([1.5])


def test_infer_resolution_mode_and_ties():
    idx = pd.DatetimeIndex(
        ["2024-01-01T00:00Z", "2024-01-01T00:15Z", "2024-01-01T00:30Z", "2024-01-01T01:30Z"]
    )
    assert infer_resolution(idx) == pd.Timedelta("15min")
    tie = pd.DatetimeIndex(["2024-01-01T00:00Z", "2024-01-01T01:00Z", "2024-01-01T01:30Z"])
    assert infer_resolution(tie) == pd.Timedelta("30min")
    assert infer_resolution(pd.DatetimeIndex(["2024-01-01T00:00Z"])) is None


def test_summarize():
    idx = pd.DatetimeIndex(["2024-01-01T01:00Z", "2024-01-01T00:00Z", "2024-01-01T00:00Z"])
    s = summarize_timestamps(idx)
    assert s.n_timestamps == 3 and s.n_unique == 2
    assert s.is_timezone_aware and s.timezone == "UTC"
    assert not s.is_monotonic_increasing
    assert s.inferred_resolution == pd.Timedelta("1h")
