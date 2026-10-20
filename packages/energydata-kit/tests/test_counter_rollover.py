"""``counter_rollover`` (P-9): drops that wrap past the register modulus are rollovers, not decreases."""

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
    counter_rollover_mask,
    flag_frame,
    flag_series,
)
from energydata_kit.cli import main

ROLLOVER = int(QualityFlag.COUNTER_ROLLOVER)
DECREASE = int(QualityFlag.COUNTER_DECREASE)


def hourly(values: list[float]) -> pd.Series:
    return pd.Series(values, index=pd.date_range("2024-01-01", periods=len(values), freq="1h", tz="UTC"))


def test_rollover_versus_reset():
    # The design's examples (SCHEMA_2.md): 999 990 -> 10 wraps (+20); 500 000 -> 0 does not.
    s = hourly([999_980.0, 999_990.0, 10.0, 500_000.0, 0.0])
    assert counter_decrease_mask(s).tolist() == [False, False, True, False, True]
    assert counter_rollover_mask(s, 1e6).tolist() == [False, False, True, False, False]


def test_rule_bounds():
    m = 1000.0
    # Implied increase cur + m - prev: just below m/2 is a rollover, m/2 itself is not.
    assert counter_rollover_mask([900.0, 399.9], m).tolist() == [False, True]
    assert not counter_rollover_mask([900.0, 400.0], m).any()
    # An implied increase down to -tolerance is a rollover: the reading after the wrap
    # may be a little low, within the tolerance the caller allows for decreases.
    assert not counter_rollover_mask([1000.5, 0.0], m).any()  # implied -0.5
    assert counter_rollover_mask([1000.5, 0.0], m, tolerance=0.5).tolist() == [False, True]
    # Drops within tolerance are no decrease at all, so no rollover either.
    assert not counter_rollover_mask([10.0, 9.8], m, tolerance=0.5).any()
    # Increases are never rollovers.
    assert not counter_rollover_mask([10.0, 20.0, 999.0], m).any()


def test_missing_values_are_skipped():
    s = [995.0, np.nan, np.inf, 3.0, None]
    assert counter_rollover_mask(s, 1000).tolist() == [False, False, False, True, False]


def test_max_gap_applies():
    index = pd.DatetimeIndex(["2024-01-01T00:00Z", "2024-01-01T01:00Z", "2024-01-01T09:00Z"])
    s = pd.Series([990.0, 995.0, 5.0], index=index)
    assert counter_rollover_mask(s, 1000).tolist() == [False, False, True]
    assert not counter_rollover_mask(s, 1000, max_gap="1h").any()


def test_validation():
    assert counter_rollover_mask([], 1e6).tolist() == []
    for bad in (0, -1, np.inf, np.nan):
        with pytest.raises(ValueError, match="modulus must be a finite number > 0"):
            counter_rollover_mask([], bad)
    for bad in (True, "1e6", None):
        with pytest.raises(TypeError, match="modulus must be a number"):
            counter_rollover_mask([], bad)
    with pytest.raises(ValueError, match="tolerance must be"):
        counter_rollover_mask([], 1e6, tolerance=-1)


def test_flag_series_flags_one_or_the_other():
    s = hourly([999_980.0, 999_990.0, 10.0, 500_000.0, 0.0])
    plain = flag_series(s, cumulative=True)[FLAG_COLUMN].tolist()
    assert plain == [0, 0, DECREASE, 0, DECREASE]
    split = flag_series(s, cumulative=True, counter_rollover=1e6)[FLAG_COLUMN].tolist()
    assert split == [0, 0, ROLLOVER, 0, DECREASE]
    with pytest.raises(ValueError, match="counter_rollover requires cumulative=True"):
        flag_series(s, counter_rollover=1e6)
    with pytest.raises(ValueError, match="counter_rollover must be a finite number > 0"):
        flag_series(s, cumulative=True, counter_rollover=0)
    with pytest.raises(TypeError, match="counter_rollover must be a number"):
        flag_series(s, cumulative=True, counter_rollover="1e6")


def test_report_records_the_modulus_and_counts():
    s = hourly([999_980.0, 999_990.0, 10.0, 500_000.0, 0.0]).rename("kwh")
    report = assess_quality(s, cumulative=True, counter_rollover=np.float64(1e6)).to_dict()
    assert report["parameters"]["counter_rollover"] == 1e6
    assert type(report["parameters"]["counter_rollover"]) is float
    assert report["flag_counts"]["COUNTER_ROLLOVER"] == 1
    assert report["flag_counts"]["COUNTER_DECREASE"] == 1
    off = assess_quality(s, cumulative=True).to_dict()
    assert off["parameters"]["counter_rollover"] is None
    assert off["flag_counts"]["COUNTER_ROLLOVER"] == 0 and off["flag_counts"]["COUNTER_DECREASE"] == 2


def test_frames_take_the_modulus_per_column():
    s = hourly([999_980.0, 999_990.0, 10.0, 500_000.0, 0.0])
    frame = pd.DataFrame({"a": s.to_numpy(), "b": s.to_numpy()}, index=s.index)
    report = assess_frame(frame, cumulative=True, per_column={"a": {"counter_rollover": 1e6}}).to_dict()
    counts = {n: c["flag_counts"]["COUNTER_ROLLOVER"] for n, c in report["columns"].items()}
    assert counts == {"a": 1, "b": 0}
    flagged = flag_frame(frame, cumulative=True, counter_rollover=1e6)
    assert flagged["quality_flag_b"].tolist() == [0, 0, ROLLOVER, 0, DECREASE]


def test_cli_counter_rollover(tmp_path):
    s = hourly([999_980.0, 999_990.0, 10.0, 500_000.0, 0.0])
    path = tmp_path / "data.csv"
    path.write_text("timestamp,kwh\n" + "".join(f"{t.isoformat()},{v}\n" for t, v in s.items()))

    def run(*argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        return main(list(argv), stdin=io.StringIO(), stdout=out, stderr=err), out.getvalue(), err.getvalue()

    code, out, _ = run("report", str(path), "--cumulative", "--counter-rollover", "1e6")
    data = json.loads(out)
    assert code == 0 and data["parameters"]["counter_rollover"] == 1e6
    assert data["flag_counts"]["COUNTER_ROLLOVER"] == 1 and data["flag_counts"]["COUNTER_DECREASE"] == 1
    code, out, err = run("report", str(path), "--counter-rollover", "1e6")
    assert code == 2 and out == "" and "requires cumulative" in err
    code, out, err = run("report", str(path), "--cumulative", "--counter-rollover", "0")
    assert code == 2 and "counter_rollover must be" in err


def test_pandera_counter_check_passes_rollovers():
    pa = pytest.importorskip("pandera.pandas")
    from energydata_kit import pandera_checks as pc

    wrap = hourly([999_980.0, 999_990.0, 10.0, 20.0])
    reset = hourly([999_980.0, 999_990.0, 10.0, 500_000.0, 0.0])
    with pytest.raises(pa.errors.SchemaError):
        pa.SeriesSchema(checks=[pc.counter_check()]).validate(wrap)
    pa.SeriesSchema(checks=[pc.counter_check(rollover=1e6)]).validate(wrap)
    with pytest.raises(pa.errors.SchemaErrors) as exc:
        pa.SeriesSchema(checks=[pc.counter_check(rollover=1e6)]).validate(reset, lazy=True)
    assert list(exc.value.failure_cases["index"]) == [reset.index[4]]  # the reset, not the wrap
    pc.series_schema(cumulative=True, counter_rollover=1e6).validate(wrap)
    with pytest.raises(ValueError, match="counter_rollover requires cumulative=True"):
        pc.series_schema(counter_rollover=1e6)
    with pytest.raises(ValueError, match="modulus must be"):
        pc.counter_check(rollover=0)
