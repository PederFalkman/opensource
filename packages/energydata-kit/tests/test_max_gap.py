"""``max_gap`` (P-8): stale, counter and jump checks do not compare rows across a larger gap."""

import io
import json

import numpy as np
import pandas as pd
import pytest

from energydata_kit import (
    FLAG_COLUMN,
    QualityFlag,
    assess_frame,
    assess_quality,
    counter_decrease_mask,
    flag_frame,
    flag_series,
    jump_mask,
    stale_mask,
)
from energydata_kit.cli import main

# Hourly rows with a six-hour outage between 02:00 and 08:00.
INDEX = pd.DatetimeIndex(
    ["2024-01-01T00:00Z", "2024-01-01T01:00Z", "2024-01-01T02:00Z", "2024-01-01T08:00Z", "2024-01-01T09:00Z"]
)


def test_stale_run_ends_at_a_larger_gap():
    s = pd.Series([5.0, 5.0, 5.0, 5.0, 5.0], index=INDEX)
    assert stale_mask(s, 4).all()
    assert not stale_mask(s, 4, max_gap="1h").any()  # runs of 3 and 2
    assert stale_mask(s, 3, max_gap="1h").tolist() == [True, True, True, False, False]
    assert stale_mask(s, 4, max_gap=pd.Timedelta("6h")).all()  # exactly max_gap apart still compares


def test_counter_and_jump_not_compared_across_a_larger_gap():
    s = pd.Series([10.0, 11.0, 12.0, 3.0, 50.0], index=INDEX)
    assert counter_decrease_mask(s).tolist() == [False, False, False, True, False]
    assert not counter_decrease_mask(s, max_gap="1h").any()
    assert jump_mask(s, 5).tolist() == [False, False, False, True, True]
    assert jump_mask(s, 5, max_gap="1h").tolist() == [False, False, False, False, True]


def test_gap_is_measured_to_the_last_finite_value():
    # 01:00 is missing, so 02:00 is compared with 00:00, two hours earlier.
    s = pd.Series([1.0, np.nan, 100.0, 100.0, 1.0], index=INDEX)
    assert jump_mask(s, 10, max_gap="1h").tolist() == [False, False, False, False, True]
    assert jump_mask(s, 10, max_gap="2h").tolist() == [False, False, True, False, True]


def test_duplicate_timestamps_are_zero_apart():
    index = pd.DatetimeIndex(["2024-01-01T00:00Z", "2024-01-01T00:00Z", "2024-01-01T05:00Z"])
    s = pd.Series([1.0, 50.0, 0.0], index=index)
    assert jump_mask(s, 10, max_gap="1h").tolist() == [False, True, False]


def test_empty_input_and_validation():
    for mask in (
        jump_mask([], 10, max_gap="1h"),
        counter_decrease_mask([], max_gap="1h"),
        stale_mask([], 2, max_gap="1h"),
    ):
        assert mask.tolist() == []
    for bad in (0, 1.5, True):
        with pytest.raises(TypeError, match="max_gap must be a duration"):
            jump_mask([], 10, max_gap=bad)
    for bad in ("soon", "0s", "-1h"):
        with pytest.raises(ValueError, match="max_gap must be"):
            jump_mask([], 10, max_gap=bad)
    with pytest.raises(TypeError, match="DatetimeIndex"):
        jump_mask([1.0, 2.0], 10, max_gap="1h")  # no timestamps to measure the gap with


def test_flag_series_and_report():
    s = pd.Series([10.0, 11.0, 12.0, 3.0, 50.0], index=INDEX, name="kwh")
    flags = flag_series(s, cumulative=True, jump_max_delta=5, max_gap="1h")[FLAG_COLUMN]
    assert flags.tolist() == [0, 0, 0, 0, int(QualityFlag.JUMP)]
    with pytest.raises(ValueError, match="max_gap requires"):
        flag_series(s, max_gap="1h")
    report = assess_quality(s, cumulative=True, jump_max_delta=5, max_gap="90min").to_dict()
    assert report["parameters"]["max_gap"] == "P0DT1H30M0S"
    assert report["flag_counts"]["COUNTER_DECREASE"] == 0 and report["flag_counts"]["JUMP"] == 1
    assert assess_quality(s, jump_max_delta=5).to_dict()["parameters"]["max_gap"] is None


def test_frames_take_max_gap_shared_and_per_column():
    frame = pd.DataFrame({"a": [5.0] * 5, "b": [5.0] * 5}, index=INDEX)
    report = assess_frame(frame, stale_min_run=4, per_column={"b": {"max_gap": "1h"}}).to_dict()
    counts = {name: col["flag_counts"]["STALE_VALUE"] for name, col in report["columns"].items()}
    assert counts == {"a": 5, "b": 0}
    assert [col["parameters"]["max_gap"] for col in report["columns"].values()] == [None, "P0DT1H0M0S"]
    flagged = flag_frame(frame, stale_min_run=4, max_gap="1h")
    assert not flagged.filter(like="quality_flag_").any().any()


def test_cli_max_gap(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("timestamp,kwh\n" + "".join(f"{t.isoformat()},5\n" for t in INDEX))

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        return main(list(argv), stdin=io.StringIO(), stdout=out, stderr=err), out.getvalue(), err.getvalue()

    code, out, _ = run("report", str(path), "--stale-min-run", "4", "--max-gap", "1h")
    data = json.loads(out)
    assert (
        code == 0
        and data["flag_counts"]["STALE_VALUE"] == 0
        and data["parameters"]["max_gap"] == "P0DT1H0M0S"
    )
    assert json.loads(run("report", str(path), "--stale-min-run", "4")[1])["flag_counts"]["STALE_VALUE"] == 5
    code, out, err = run("report", str(path), "--stale-min-run", "4", "--max-gap", "soon")
    assert code == 2 and out == "" and "max_gap must be" in err
    code, out, err = run("report", str(path), "--max-gap", "1h")
    assert code == 2 and "max_gap requires" in err


def test_pandera_checks_take_max_gap():
    pa = pytest.importorskip("pandera.pandas")
    from energydata_kit import pandera_checks as pc

    s = pd.Series([10.0, 11.0, 12.0, 3.0, 3.0], index=INDEX)  # drop and jump across the gap
    flat = pd.Series([1.0, 2.0, 7.0, 7.0, 7.0], index=INDEX)  # a run of three across the gap
    cases = [
        (s, pc.counter_check(max_gap="1h"), pc.counter_check()),
        (s, pc.jump_check(5, max_gap="1h"), pc.jump_check(5)),
        (flat, pc.stale_check(3, max_gap="1h"), pc.stale_check(3)),
    ]
    for data, gapped, plain in cases:
        pa.SeriesSchema(checks=[gapped]).validate(data)
        with pytest.raises(pa.errors.SchemaError):
            pa.SeriesSchema(checks=[plain]).validate(data)
    pc.series_schema(cumulative=True, max_gap="1h").validate(s)
    with pytest.raises(ValueError, match="max_gap requires"):
        pc.series_schema(max_gap="1h")
    with pytest.raises(ValueError, match="max_gap must be"):
        pc.stale_check(3, max_gap="soon")
