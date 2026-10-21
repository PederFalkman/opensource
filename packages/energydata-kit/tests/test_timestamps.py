import datetime as dt

import pandas as pd
import pytest

from energydata_kit import TimestampError, infer_resolution, normalize_timestamps, summarize_timestamps


def test_naive_requires_assume_tz():
    with pytest.raises(TimestampError, match="naive"):
        normalize_timestamps(["2024-01-01 00:00", "2024-01-01 01:00"])


def test_dates_without_time_are_naive():
    # "2024-01-02" ends in "-02", which was read as a UTC offset: dates came out
    # as UTC midnights and assume_tz was refused as "already timezone-aware".
    with pytest.raises(TimestampError, match="naive"):
        normalize_timestamps(["2024-01-01", "2024-01-02"])
    idx = normalize_timestamps(["2024-01-01", "2024-01-02"], assume_tz="Europe/Stockholm")
    assert list(idx) == [pd.Timestamp("2023-12-31T23:00Z"), pd.Timestamp("2024-01-01T23:00Z")]
    # Offsets after a time of day are still recognised, in every ISO form.
    for text in (
        "2024-01-01T01:00+01:00",
        "2024-01-01 01:00:00.0 +01:00",
        "20240101T0100+0100",
        "2024-01-01T01+01",
    ):
        assert list(normalize_timestamps([text])) == [pd.Timestamp("2024-01-01T00:00Z")], text


def test_naive_localized_and_converted_to_utc():
    idx = normalize_timestamps(["2024-01-01 01:00", "2024-01-01 02:00"], assume_tz="Europe/Stockholm")
    assert str(idx.tz) == "UTC"
    assert idx.unit == "ns"
    assert list(idx) == [pd.Timestamp("2024-01-01T00:00Z"), pd.Timestamp("2024-01-01T01:00Z")]


def test_mixed_offsets_across_dst_are_accepted():
    # Spring-forward in Europe/Stockholm: 01:45+01:00 is followed by 03:00+02:00.
    idx = normalize_timestamps(["2024-03-31T01:45:00+01:00", "2024-03-31T03:00:00+02:00"])
    assert idx[1] - idx[0] == pd.Timedelta("15min")


def test_offset_strings_take_the_fast_path_with_the_same_result():
    # OSS-136 (P-16): strict "+HH:MM"/"Z" strings are split and parsed on pandas' naive
    # path; other forms fall back to the general parser. Both give the same instants.
    strict = [
        "2024-03-31T01:30:00+01:00",
        "2024-03-31 03:30:00.250+02:00",
        "2024-03-31T01:45Z",
        "2024-03-30T21:15-05:30",
    ]
    expected = pd.DatetimeIndex(pd.to_datetime(strict, utc=True, format="ISO8601")).as_unit("ns")
    assert normalize_timestamps(strict).equals(expected)
    for odd in ("2024-03-31T01:30:00+0100", "2024-03-31T01:30:00+01"):
        assert normalize_timestamps([odd])[0] == pd.Timestamp("2024-03-31T00:30:00Z")
    # Errors still come from the general path, with its message (a lowercase "z" was
    # never accepted).
    for bad in ("2024-13-01T00:00:00+01:00", "2024-03-31T00:30:00z"):
        with pytest.raises(TimestampError, match="could not parse"):
            normalize_timestamps([bad])


def test_offset_fast_path_falls_back_at_the_edge_of_the_range():
    # Near the end of the nanosecond range, applying the offset overflows; the fast path
    # must hand over to the general parser rather than raise a different error.
    edge = ["2262-04-11T10:00:00-12:00"]
    try:
        expected = pd.DatetimeIndex(pd.to_datetime(edge, utc=True, format="ISO8601")).as_unit("ns")
    except (ValueError, OverflowError):
        with pytest.raises((TimestampError, ValueError, OverflowError)):
            normalize_timestamps(edge)
    else:
        assert normalize_timestamps(edge).equals(expected)


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


@pytest.mark.parametrize("assume_tz", [None, "Europe/Stockholm"])
def test_empty_input(assume_tz):
    idx = normalize_timestamps([], assume_tz=assume_tz)
    assert len(idx) == 0 and str(idx.tz) == "UTC"


def test_single_string_is_rejected():
    with pytest.raises(TypeError, match="single string"):
        normalize_timestamps("2024-01-01T00:00Z")
