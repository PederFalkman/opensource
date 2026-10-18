import numpy as np
import pandas as pd
import pytest

from energydata_kit import (
    FLAG_COLUMN,
    QualityFlag,
    assess_frame,
    assess_quality,
    counter_decrease_mask,
    flag_series,
    jump_mask,
    make_synthetic_series,
    stale_mask,
)

STALE = int(QualityFlag.STALE_VALUE)
DECREASE = int(QualityFlag.COUNTER_DECREASE)
JUMP = int(QualityFlag.JUMP)


def test_stale_runs():
    v = [1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 4.0]
    assert stale_mask(v, 3).tolist() == [False, True, True, True, False, False, False]
    assert stale_mask(v, 2).tolist() == [False, True, True, True, True, True, False]


def test_stale_missing_and_non_finite_break_runs():
    v = [5.0, 5.0, np.nan, 5.0, 5.0, np.inf, np.inf, np.inf]
    assert stale_mask(v, 3).tolist() == [False] * 8
    assert stale_mask(v, 2).tolist() == [True, True, False, True, True, False, False, False]


def test_stale_tolerance_and_exclude():
    v = [1.0, 1.0005, 0.9998, 2.0, 0.0, 0.0, 0.0]
    assert stale_mask(v, 3).tolist() == [False, False, False, False, True, True, True]
    assert stale_mask(v, 3, atol=1e-3).tolist() == [True, True, True, False, True, True, True]
    assert stale_mask(v, 3, exclude=[0.0]).tolist() == [False] * 7
    # With atol, a near-zero run is excluded whole; only exact zeros were, flagging every other row.
    assert stale_mask([0.0, 0.005, 0.0, 0.005], 3, atol=0.01, exclude=[0.0]).tolist() == [False] * 4
    assert stale_mask([0.0, 0.0, 0.0, 5.0, 5.0, 5.0], 3, exclude=[0.0]).tolist() == [False] * 3 + [True] * 3


def test_stale_edge_cases():
    assert stale_mask([], 2).size == 0
    assert stale_mask([7.0, 7.0], 2).tolist() == [True, True]
    with pytest.raises(ValueError):
        stale_mask([1.0], 1)
    with pytest.raises(ValueError):
        stale_mask([1.0], 2, atol=-1)


def test_counter_decrease_flags_only_the_drop():
    v = [10.0, 11.0, 11.0, 3.0, 4.0, 5.0]  # reset at index 3
    assert counter_decrease_mask(v).tolist() == [False, False, False, True, False, False]


def test_counter_decrease_skips_missing_values():
    v = [10.0, np.nan, 9.0, np.inf, 9.5, 8.0]
    assert counter_decrease_mask(v).tolist() == [False, False, True, False, False, True]


def test_counter_decrease_tolerance():
    v = [100.0, 99.95, 100.1, 99.0]
    assert counter_decrease_mask(v).tolist() == [False, True, False, True]
    assert counter_decrease_mask(v, tolerance=0.1).tolist() == [False, False, False, True]
    with pytest.raises(ValueError):
        counter_decrease_mask(v, tolerance=-1)


def test_flag_series_opt_in():
    s = make_synthetic_series(periods=6)
    s.iloc[1:5] = 50.0
    assert not (flag_series(s)[FLAG_COLUMN] & STALE).any()
    flags = flag_series(s, stale_min_run=4)[FLAG_COLUMN].tolist()
    assert flags == [0, STALE, STALE, STALE, STALE, 0]


def test_flag_series_cumulative():
    idx = pd.date_range("2024-01-01", periods=5, freq="1h", tz="UTC")
    register = pd.Series([100.0, 101.5, 103.0, 0.5, 2.0], index=idx)
    before = register.copy()
    flags = flag_series(register, cumulative=True)[FLAG_COLUMN].tolist()
    assert flags == [0, 0, 0, DECREASE, 0]
    pd.testing.assert_series_equal(register, before)


def test_consecutive_checks_require_sorted_index():
    s = make_synthetic_series(periods=4).iloc[::-1]
    for kwargs in ({"stale_min_run": 2}, {"cumulative": True}):
        with pytest.raises(ValueError, match="sorted"):
            flag_series(s, **kwargs)


def test_report_counts_and_parameters():
    idx = pd.date_range("2024-01-01", periods=6, freq="1h", tz="UTC")
    register = pd.Series([5.0, 5.0, 5.0, 6.0, 1.0, 2.0], index=idx, name="register")
    data = assess_quality(register, freq="1h", stale_min_run=3, cumulative=True).to_dict()
    assert data["flag_counts"]["STALE_VALUE"] == 3
    assert data["flag_counts"]["COUNTER_DECREASE"] == 1
    assert data["flag_counts"]["ANY"] == 4
    assert data["parameters"]["stale_min_run"] == 3 and data["parameters"]["cumulative"] is True


def test_report_defaults_leave_new_checks_off():
    data = assess_quality(make_synthetic_series(), freq="15min").to_dict()
    assert data["flag_counts"]["STALE_VALUE"] == 0 and data["flag_counts"]["COUNTER_DECREASE"] == 0
    assert data["parameters"]["stale_min_run"] is None and data["parameters"]["cumulative"] is False


def test_jump_flags_the_row_where_the_change_lands():
    v = [10.0, 11.0, 30.0, 31.0, 12.0, 12.5]
    assert jump_mask(v, 5.0).tolist() == [False, False, True, False, True, False]
    # Exactly max_delta is not a jump; the comparison is strict.
    assert jump_mask([0.0, 5.0, 0.0], 5.0).tolist() == [False, False, False]


def test_jump_single_outlier_flags_itself_and_the_next_row():
    assert jump_mask([1.0, 1.0, 50.0, 1.0, 1.0], 10.0).tolist() == [False, False, True, True, False]


def test_jump_skips_missing_and_non_finite_values():
    v = [10.0, np.nan, 10.5, np.inf, 30.0, -np.inf, 29.0]
    assert jump_mask(v, 5.0).tolist() == [False, False, False, False, True, False, False]


def test_jump_invalid_limits():
    assert jump_mask([], 1.0).size == 0
    for bad in (0.0, -1.0, np.nan, np.inf):
        with pytest.raises(ValueError):
            jump_mask([1.0, 2.0], bad)


def test_non_finite_options_are_rejected():
    # NaN or inf options were accepted and written into the report as NaN or
    # Infinity, which is not valid JSON.
    s = make_synthetic_series(periods=6)
    for options in (
        {"bounds": (np.nan, 5.0)},
        {"bounds": (-np.inf, None)},
        {"stale_min_run": 3, "stale_atol": np.nan},
        {"stale_min_run": 3, "stale_exclude": [np.inf]},
        {"cumulative": True, "counter_tolerance": np.inf},
    ):
        with pytest.raises(ValueError, match="finite"):
            assess_quality(s, freq="15min", **options)


@pytest.mark.parametrize(
    ("options", "error"),
    [
        # Booleans and non-boolean flags were recorded as-is, so the report failed its JSON Schema.
        ({"max_listed": True}, TypeError),
        ({"cumulative": "yes"}, TypeError),
        ({"cumulative": 1}, TypeError),
        ({"cumulative": True, "counter_tolerance": True}, TypeError),
        ({"jump_max_delta": True}, TypeError),
        ({"bounds": (False, True)}, TypeError),
        ({"stale_min_run": 3, "stale_atol": True}, TypeError),
        ({"stale_min_run": 3, "stale_exclude": [True]}, ValueError),
        # Text failed inside numpy instead of naming the option.
        ({"stale_min_run": "3"}, TypeError),
        ({"jump_max_delta": "5"}, TypeError),
        ({"bounds": ("0", "5")}, TypeError),
        ({"bounds": (0, 1, 2)}, ValueError),  # was "too many values to unpack"
        ({"freq": "D", "tz": "Mars/Phobos"}, ValueError),  # was a KeyError from zoneinfo
    ],
)
def test_option_types_are_checked(options, error):
    with pytest.raises(error, match=r"must be|must contain|pair|unknown time zone|interpreted as an integer"):
        assess_quality(make_synthetic_series(periods=6), **options)


def test_stale_exclude_iterators_are_read_once():
    # A generator was used up by the first column of a frame, and the report recorded [].
    index = pd.date_range("2024-01-01", periods=4, freq="h", tz="UTC")
    frame = pd.DataFrame({"a": 0.0, "b": 0.0}, index=index)
    report = assess_frame(frame, stale_min_run=3, stale_exclude=(x for x in [0.0]))
    assert [r.flag_counts["STALE_VALUE"] for r in report.columns.values()] == [0, 0]
    single = assess_quality(frame["a"], stale_min_run=3, stale_exclude=(x for x in [0.0]))
    assert single.parameters["stale_exclude"] == [0.0]


def test_numpy_options_are_accepted():
    s = make_synthetic_series(periods=6)
    report = assess_quality(
        s,
        freq="15min",
        bounds=np.array([0.0, 50.0]),
        stale_min_run=np.int64(3),
        cumulative=np.bool_(False),
        jump_max_delta=np.float32(5.0),
        max_listed=np.int64(2),
    )
    assert report.parameters["stale_min_run"] == 3 and report.parameters["max_listed"] == 2


def test_stale_exclude_accepts_arrays_and_is_checked_on_empty_input():
    s = make_synthetic_series(periods=6)
    # A numpy array of two or more values raised "truth value ... is ambiguous".
    report = assess_quality(s, freq="15min", stale_min_run=3, stale_exclude=np.array([0.0, 1.0]))
    assert report.parameters["stale_exclude"] == [0.0, 1.0]
    with pytest.raises(ValueError, match="only numbers"):  # was accepted when there were no values
        stale_mask([], 3, exclude=["x"])
    with pytest.raises(TypeError, match="not a string"):
        stale_mask([1.0], 3, exclude="0")


def test_flag_series_jump_opt_in_and_report():
    s = make_synthetic_series(periods=6)
    s.iloc[3] = s.iloc[2] + 1000.0
    assert not (flag_series(s)[FLAG_COLUMN] & JUMP).any()
    flags = flag_series(s, jump_max_delta=500.0)[FLAG_COLUMN].tolist()
    assert flags == [0, 0, 0, JUMP, JUMP, 0]
    report = assess_quality(s, jump_max_delta=500.0)
    assert report.flag_counts["JUMP"] == 2
    assert report.parameters["jump_max_delta"] == 500.0


def test_flag_series_jump_requires_sorted_index():
    s = make_synthetic_series(periods=4).iloc[::-1]
    with pytest.raises(ValueError, match="sorted"):
        flag_series(s, jump_max_delta=1.0)


def test_flag_series_stale_and_counter_tuning():
    idx = pd.date_range("2024-01-01", periods=6, freq="1h", tz="UTC")
    s = pd.Series([0.0, 0.0, 0.0, 5.0, 5.001, 4.9995], index=idx)
    plain = flag_series(s, stale_min_run=3)[FLAG_COLUMN].tolist()
    assert plain == [STALE, STALE, STALE, 0, 0, 0]
    tuned = flag_series(s, stale_min_run=3, stale_atol=0.01, stale_exclude=[0.0])[FLAG_COLUMN].tolist()
    assert tuned == [0, 0, 0, STALE, STALE, STALE]

    register = pd.Series([10.0, 9.99, 12.0, 3.0], index=idx[:4])
    assert flag_series(register, cumulative=True)[FLAG_COLUMN].tolist() == [0, DECREASE, 0, DECREASE]
    tolerant = flag_series(register, cumulative=True, counter_tolerance=0.05)[FLAG_COLUMN].tolist()
    assert tolerant == [0, 0, 0, DECREASE]


def test_tuning_options_recorded_in_report():
    s = make_synthetic_series(periods=8)
    report = assess_quality(s, stale_min_run=3, stale_atol=0.5, stale_exclude=[0], cumulative=True)
    assert report.parameters["stale_atol"] == 0.5
    assert report.parameters["stale_exclude"] == [0.0]
    assert report.parameters["counter_tolerance"] == 0.0


@pytest.mark.parametrize(
    "options",
    [{"stale_atol": 0.1}, {"stale_exclude": [0.0]}, {"counter_tolerance": 0.1}],
)
def test_tuning_options_require_their_check(options):
    s = make_synthetic_series(periods=4)
    with pytest.raises(ValueError, match="require"):
        flag_series(s, **options)
    with pytest.raises(ValueError, match="require"):
        assess_quality(s, **options)
