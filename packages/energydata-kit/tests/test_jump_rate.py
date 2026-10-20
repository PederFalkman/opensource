"""``jump_max_rate`` (P-7): a jump limit per unit of time, scaled by the time between rows."""

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
    flag_frame,
    flag_series,
    jump_mask,
    jump_rate_mask,
)
from energydata_kit.cli import main


def at(*times: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex([f"2024-01-01T{t}Z" for t in times])


# 15-minute rows, then a 2h45 gap, then 15-minute rows again.
INDEX = at("00:00", "00:15", "00:30", "03:15", "03:30")


def test_limit_scales_with_elapsed_time():
    # 50 per hour: 12.5 per 15 minutes, 137.5 over the 2h45 gap.
    s = pd.Series([0.0, 12.5, 25.0, 160.0, 174.0], index=INDEX)
    assert jump_rate_mask(s, (50, "1h")).tolist() == [False, False, False, False, True]
    assert jump_rate_mask(s, (50.0, pd.Timedelta("1h"))).tolist() == [False, False, False, False, True]
    # The same ramp with an absolute limit flags the row after the gap too.
    assert jump_mask(s, 12.5).tolist() == [False, False, False, True, True]
    # A decrease counts as a change too.
    assert jump_rate_mask(-s, (50, "1h")).tolist() == [False, False, False, False, True]


def test_one_rate_fits_any_resolution():
    hourly = pd.Series([0.0, 50.0, 100.0], index=at("00:00", "01:00", "02:00"))
    quarterly = pd.Series([0.0, 12.5, 25.0], index=at("00:00", "00:15", "00:30"))
    for s in (hourly, quarterly):
        assert not jump_rate_mask(s, (50, "1h")).any()
        assert jump_rate_mask(s, (49, "1h"))[1:].all()


def test_missing_values_are_skipped_and_widen_the_interval():
    s = pd.Series([0.0, np.nan, np.inf, 30.0], index=at("00:00", "00:15", "00:30", "00:45"))
    # 30 over 45 minutes is 40 per hour.
    assert jump_rate_mask(s, (40, "1h")).tolist() == [False, False, False, False]
    assert jump_rate_mask(s, (39, "1h")).tolist() == [False, False, False, True]


def test_duplicate_timestamps_are_not_compared():
    s = pd.Series([0.0, 100.0, 5.0], index=at("00:00", "00:00", "00:15"))
    # Row 1 has zero elapsed time; row 2 is compared with row 1 (95 in 15 minutes).
    assert jump_rate_mask(s, (50, "1h")).tolist() == [False, False, True]


def test_max_gap_stops_comparison_across_a_gap():
    s = pd.Series([0.0, 12.5, 25.0, 500.0, 512.5], index=INDEX)
    assert jump_rate_mask(s, (50, "1h")).tolist() == [False, False, False, True, False]
    assert not jump_rate_mask(s, (50, "1h"), max_gap="1h").any()


def test_validation():
    assert jump_rate_mask(pd.Series([], dtype=float, index=at()), (50, "1h")).tolist() == []
    for bad in (50, "50 1h", (50,), (50, "1h", 2), None):
        with pytest.raises(TypeError, match="pair"):
            jump_rate_mask(pd.Series([1.0], index=at("00:00")), bad)
    for bad, message in [
        ((0, "1h"), "delta must be"),
        ((np.inf, "1h"), "delta must be"),
        ((50, "0s"), "period must be a positive duration"),
        ((50, "soon"), "period must be a duration"),
    ]:
        with pytest.raises(ValueError, match=message):
            jump_rate_mask(pd.Series([1.0], index=at("00:00")), bad)
    for bad in ((True, "1h"), ("50", "1h"), (50, 3600)):
        with pytest.raises(TypeError):
            jump_rate_mask(pd.Series([1.0], index=at("00:00")), bad)
    with pytest.raises(TypeError, match="DatetimeIndex"):
        jump_rate_mask(pd.Series([1.0, 2.0]), (50, "1h"))


def test_flag_series_combines_with_jump_max_delta():
    s = pd.Series([0.0, 12.5, 25.0, 160.0, 174.0], index=INDEX)
    jump = int(QualityFlag.JUMP)
    flags = flag_series(s, jump_max_rate=(50, "1h"))[FLAG_COLUMN].tolist()
    assert flags == [0, 0, 0, 0, jump]
    both = flag_series(s, jump_max_delta=100, jump_max_rate=(50, "1h"))[FLAG_COLUMN].tolist()
    assert both == [0, 0, 0, jump, jump]  # either limit flags JUMP
    assert not flag_series(s, jump_max_rate=(50, "1h"), max_gap="1h")[FLAG_COLUMN].iloc[3]
    with pytest.raises(ValueError, match="delta must be"):
        flag_series(s, jump_max_rate=(-1, "1h"))
    with pytest.raises(ValueError, match="require a sorted index"):
        flag_series(s.iloc[::-1], jump_max_rate=(50, "1h"))
    flag_series(s, max_gap="1h", jump_max_rate=(50, "1h"))  # a rate alone is enough for max_gap


def test_report_records_the_rate():
    s = pd.Series([0.0, 12.5, 25.0, 160.0, 174.0], index=INDEX, name="kw")
    report = assess_quality(s, jump_max_rate=(50, "90min")).to_dict()
    assert report["parameters"]["jump_max_rate"] == [50.0, "P0DT1H30M0S"]
    assert report["flag_counts"]["JUMP"] == 4  # 8.3 per 15 minutes: every step is too fast
    assert assess_quality(s).to_dict()["parameters"]["jump_max_rate"] is None
    assert isinstance(
        assess_quality(s, jump_max_rate=(np.int64(50), "1h")).to_dict()["parameters"]["jump_max_rate"][0],
        float,
    )


def test_frames_take_the_rate_per_column():
    frame = pd.DataFrame({"a": [0.0, 12.5, 25.0, 160.0, 174.0], "b": [0.0, 1.0, 2.0, 3.0, 4.0]}, index=INDEX)
    report = assess_frame(frame, per_column={"a": {"jump_max_rate": (50, "1h")}}).to_dict()
    assert report["columns"]["a"]["flag_counts"]["JUMP"] == 1
    assert report["columns"]["b"]["parameters"]["jump_max_rate"] is None
    flagged = flag_frame(frame, jump_max_rate=(50, "1h"))
    assert flagged["quality_flag_a"].tolist() == [0, 0, 0, 0, int(QualityFlag.JUMP)]


def test_cli_jump_max_rate(tmp_path):
    path = tmp_path / "data.csv"
    values = [0.0, 12.5, 25.0, 160.0, 174.0]
    path.write_text(
        "timestamp,kw\n" + "".join(f"{t.isoformat()},{v}\n" for t, v in zip(INDEX, values, strict=True))
    )

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        return main(list(argv), stdin=io.StringIO(), stdout=out, stderr=err), out.getvalue(), err.getvalue()

    code, out, _ = run("report", str(path), "--jump-max-rate", "50", "1h")
    data = json.loads(out)
    assert code == 0 and data["flag_counts"]["JUMP"] == 1
    assert data["parameters"]["jump_max_rate"] == [50.0, "P0DT1H0M0S"]
    for argv, message in [
        (("--jump-max-rate", "fast", "1h"), "DELTA must be a number"),
        (("--jump-max-rate", "50", "soon"), "period must be a duration"),
        (("--jump-max-rate", "0", "1h"), "delta must be"),
    ]:
        code, out, err = run("report", str(path), *argv)
        assert code == 2 and out == "" and message in err


def test_pandera_jump_rate_check():
    pa = pytest.importorskip("pandera.pandas")
    from energydata_kit import pandera_checks as pc

    s = pd.Series([0.0, 12.5, 25.0, 160.0, 174.0], index=INDEX)
    ramp = s.iloc[:4]
    pa.SeriesSchema(checks=[pc.jump_rate_check((50, "1h"))]).validate(ramp)
    with pytest.raises(pa.errors.SchemaError, match="faster than 50 per 1h"):
        pa.SeriesSchema(checks=[pc.jump_rate_check((50, "1h"))]).validate(s)
    pc.series_schema(jump_max_rate=(50, "1h")).validate(ramp)
    with pytest.raises(pa.errors.SchemaError):
        pc.series_schema(jump_max_rate=(50, "1h")).validate(s)
    with pytest.raises(ValueError, match="period must be"):
        pc.jump_rate_check((50, "soon"))
    with pytest.raises(ValueError, match="max_gap must be"):
        pc.jump_rate_check((50, "1h"), max_gap="soon")
