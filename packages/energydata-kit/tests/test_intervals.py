import pandas as pd
import pytest

from energydata_kit import (
    duplicate_mask,
    expected_grid,
    find_duplicate_timestamps,
    find_missing_intervals,
    make_synthetic_series,
    normalize_timestamps,
    off_grid_mask,
)
from energydata_kit.intervals import to_step


def test_no_gaps_in_clean_series():
    s = make_synthetic_series()
    assert find_missing_intervals(s.index, "15min") == []


def test_gap_runs_are_grouped():
    s = make_synthetic_series(drop=[5, 6, 7, 40])
    gaps = find_missing_intervals(s.index, "15min")
    assert [(g.start, g.end, g.missing_count) for g in gaps] == [
        (pd.Timestamp("2024-01-01T01:15Z"), pd.Timestamp("2024-01-01T01:45Z"), 3),
        (pd.Timestamp("2024-01-01T10:00Z"), pd.Timestamp("2024-01-01T10:00Z"), 1),
    ]


def test_explicit_window_detects_leading_and_trailing_gaps():
    s = make_synthetic_series(periods=4)
    gaps = find_missing_intervals(
        s.index, "15min", start=pd.Timestamp("2023-12-31T23:30Z"), end=pd.Timestamp("2024-01-01T01:15Z")
    )
    assert [g.missing_count for g in gaps] == [2, 2]


def test_duplicates_do_not_fill_or_create_gaps():
    s = make_synthetic_series(duplicate=[3, 3, 10])
    assert find_missing_intervals(s.index, "15min") == []
    assert list(find_duplicate_timestamps(s.index)) == [s.index[3], s.index[11]]
    assert duplicate_mask(s.index).sum() == 4


@pytest.mark.parametrize(("day", "expected"), [("2024-03-31", 92), ("2024-10-27", 100), ("2024-06-01", 96)])
def test_local_dst_days_are_complete_on_utc_grid(day, expected):
    local = pd.date_range(day, periods=expected, freq="15min", tz="Europe/Stockholm")
    idx = normalize_timestamps(local)
    assert find_missing_intervals(idx, "15min") == []
    assert idx.is_unique
    assert local[-1].date() == local[0].date()  # all intervals belong to the same local day


def test_off_grid():
    idx = pd.DatetimeIndex(
        ["2024-01-01T00:00Z", "2024-01-01T00:15Z", "2024-01-01T00:22Z", "2024-01-01T00:30Z"]
    )
    assert off_grid_mask(idx, "15min").tolist() == [False, False, True, False]
    origin = pd.Timestamp("2024-01-01T00:07Z")
    assert off_grid_mask(idx, "15min", origin=origin).tolist() == [True, True, False, True]
    assert off_grid_mask(idx[:0], "15min").size == 0


def test_naive_index_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        find_missing_intervals(pd.date_range("2024-01-01", periods=3, freq="h"), "1h")


def test_empty_index():
    empty = pd.DatetimeIndex([], tz="UTC")
    assert find_missing_intervals(empty, "1h") == []
    assert len(expected_grid(empty, "1h")) == 0


def test_to_step():
    assert to_step("15min") == pd.Timedelta(minutes=15)
    assert to_step("h") == pd.Timedelta(hours=1)
    for bad in ("MS", "0min", "-1h", "not-a-freq"):  # "nonsense" warns on pandas 2.2/2.3
        with pytest.raises(ValueError):
            to_step(bad)
