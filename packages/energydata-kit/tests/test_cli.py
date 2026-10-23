import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

import energydata_kit as ek
from energydata_kit import __version__, cli
from energydata_kit.cli import main
from energydata_kit.intervals import to_step

CLEAN = "timestamp,kwh\n" + "".join(
    f"2024-01-01T{h:02d}:{m:02d}:00Z,{h + m / 60:.2f}\n" for h in range(2) for m in (0, 15, 30, 45)
)
# Local wall-clock meter data on the spring-forward day: a gap at 00:30,
# a duplicate at 00:45 and an infinite value.
DEFECTIVE = (
    "time,kwh,quality\n"
    "2024-03-31 00:00,1.0,ok\n"
    "2024-03-31 00:15,1.1,ok\n"
    "2024-03-31 00:45,1.2,ok\n"
    "2024-03-31 00:45,1.2,ok\n"
    "2024-03-31 01:00,inf,ok\n"
)


def write(tmp_path: Path, text: str, name: str = "data.csv") -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def run(*argv: str, stdin: str = "") -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(list(argv), stdin=io.StringIO(stdin), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def test_clean_report(tmp_path):
    code, out, err = run("report", str(write(tmp_path, CLEAN)), "--freq", "15min", "--fail-on-issues")
    assert (code, err) == (0, "")
    data = json.loads(out)
    assert data["series_name"] == "kwh"
    assert data["n_rows"] == 8 and data["completeness"] == 1.0 and data["flag_counts"]["ANY"] == 0


def test_output_is_deterministic(tmp_path):
    path = str(write(tmp_path, CLEAN))
    assert run("report", path, "--freq", "15min")[1] == run("report", path, "--freq", "15min")[1]


def test_defects_options_and_exit_code(tmp_path):
    path = write(tmp_path, DEFECTIVE)
    args = ["report", str(path), "--timestamp-col", "time", "--value-col", "kwh"]
    args += ["--assume-tz", "Europe/Stockholm", "--freq", "15min"]
    code, out, _ = run(*args)
    assert code == 0  # issues alone do not fail without --fail-on-issues
    data = json.loads(out)
    assert data["n_missing_intervals"] == 1 and data["n_duplicate_timestamps"] == 1
    assert data["flag_counts"]["NON_FINITE"] == 1
    assert data["first_timestamp"] == "2024-03-30T23:00:00+00:00"
    assert run(*args, "--fail-on-issues")[0] == 1


def test_metadata_bounds_and_report_file(tmp_path):
    path = write(tmp_path, CLEAN)
    report_path = tmp_path / "report.json"
    code, out, _ = run(
        "report", str(path), "--freq", "15min", "--unit", "kWh", "--aggregation", "sum",
        "--interval-label", "end", "--bounds", "0", "none", "-o", str(report_path),
    )  # fmt: skip
    assert code == 0 and out == ""
    data = json.loads(report_path.read_text())
    assert data["metadata"]["unit"] == "kWh" and data["metadata"]["resolution"] == "15min"
    assert data["parameters"]["bounds"] == [0.0, None]
    assert data["metadata_issues"] == []


def test_jump_max_delta(tmp_path):
    path = write(tmp_path, CLEAN)  # steps of 0.25 kWh
    code, out, _ = run("report", str(path), "--jump-max-delta", "0.2")
    data = json.loads(out)
    assert code == 0 and data["flag_counts"]["JUMP"] == 7
    assert data["parameters"]["jump_max_delta"] == 0.2
    assert json.loads(run("report", str(path), "--jump-max-delta", "1")[1])["flag_counts"]["JUMP"] == 0
    code, out, err = run("report", str(path), "--jump-max-delta", "0")
    assert code == 2 and out == "" and "max_delta must be" in err


def test_stale_and_counter_tuning(tmp_path):
    rows = ["2024-01-01T00:00Z,0", "2024-01-01T01:00Z,0", "2024-01-01T02:00Z,0", "2024-01-01T03:00Z,5"]
    path = write(tmp_path, "timestamp,kwh\n" + "\n".join(rows) + "\n")
    base = ["report", str(path), "--freq", "1h", "--stale-min-run", "3"]
    assert json.loads(run(*base)[1])["flag_counts"]["STALE_VALUE"] == 3
    data = json.loads(run(*base, "--stale-exclude", "0", "--stale-atol", "0.1")[1])
    assert data["flag_counts"]["STALE_VALUE"] == 0
    assert data["parameters"]["stale_exclude"] == [0.0] and data["parameters"]["stale_atol"] == 0.1
    code, out, err = run("report", str(path), "--counter-tolerance", "0.1")
    assert code == 2 and out == "" and "counter_tolerance requires cumulative" in err


def test_multiple_value_columns(tmp_path):
    rows = [f"2024-01-01T{h:02d}:00Z,{h},{10 - h}" for h in range(4)]
    path = write(tmp_path, "timestamp,a,b\n" + "\n".join(rows) + "\n")
    code, out, _ = run("report", str(path), "--value-col", "a", "--value-col", "b", "--freq", "1h")
    data = json.loads(out)
    assert code == 0 and data["column_order"] == ["a", "b"]
    assert data["columns"]["b"]["series_name"] == "b" and data["summary"]["a"]["n_flagged_rows"] == 0
    args = ["report", str(path), "--value-col", "a", "--value-col", "b", "--freq", "1h"]
    assert run(*args, "--fail-on-issues", "--jump-max-delta", "0.5")[0] == 1
    for extra, message in [
        (["--unit", "kW"], "--unit UNIT describes a single column"),
        (["--value-col", "a"], "only once"),
    ]:
        code, out, err = run(*args, *extra)
        assert code == 2 and out == "" and message in err


def test_unit_per_column(tmp_path):
    # P-15: --unit COLUMN=UNIT gives several columns metadata without a schema file.
    rows = [f"2024-01-01T{h:02d}:00Z,{h},{10 - h},{h}" for h in range(4)]
    path = str(write(tmp_path, "timestamp,kwh,pv,other\n" + "\n".join(rows) + "\n"))
    cols = ["--value-col", "kwh", "--value-col", "pv", "--value-col", "other"]
    code, out, err = run(
        "report", path, *cols, "--unit", "kwh=kWh", "--unit", "pv=kW",
        "--resolution", "1h", "--aggregation", "sum",
    )  # fmt: skip
    assert (code, err) == (0, "")
    columns = json.loads(out)["columns"]
    assert columns["kwh"]["metadata"]["unit"] == "kWh" and columns["pv"]["metadata"]["unit"] == "kW"
    for name in ("kwh", "pv"):  # the shared options apply to every named column
        assert columns[name]["metadata"]["resolution"] == "1h"
        assert columns[name]["metadata"]["aggregation"] == "sum"
        assert columns[name]["completeness"] == 1.0
    assert columns["other"]["metadata"] is None  # no unit, no metadata
    # One column named this way is the same as a plain --unit.
    named = run("report", path, "--value-col", "kwh", "--unit", "kwh=kWh", "--resolution", "1h")
    plain = run("report", path, "--value-col", "kwh", "--unit", "kWh", "--resolution", "1h")
    assert named == plain and named[0] == 0
    for extra, message in [
        (["--unit", "kwh=kWh", "--unit", "nope=kW"], "--unit names columns that are not assessed: ['nope']"),
        (["--unit", "kwh=kWh", "--unit", "kwh=kW"], "--unit names column 'kwh' twice"),
        (["--unit", "kWh", "--unit", "pv=kW"], "--unit UNIT describes a single column"),
        (["--unit", "kWh"], "--unit UNIT describes a single column"),
        (["--unit", "=kWh"], "expected COLUMN=UNIT"),
        (["--unit", "kwh="], "expected COLUMN=UNIT"),
    ]:
        code, out, err = run("report", path, *cols, *extra)
        assert code == 2 and out == "" and message in err, (extra, err)


def test_unit_per_column_names_the_value_columns(tmp_path):
    # P-17: without --value-col, the --unit COLUMN=UNIT columns are assessed, in --unit order.
    rows = [f"2024-01-01T{h:02d}:00Z,{h},{10 - h},{h}" for h in range(4)]
    path = str(write(tmp_path, "timestamp,kwh,pv,other\n" + "\n".join(rows) + "\n"))
    units = ["--unit", "pv=kW", "--unit", "kwh=kWh", "--resolution", "1h"]
    code, out, err = run("report", path, *units)
    assert (code, err) == (0, "")
    data = json.loads(out)
    assert data["column_order"] == ["pv", "kwh"]  # "other" has no unit and is not assessed
    assert data["columns"]["pv"]["metadata"]["unit"] == "kW"
    # The same report as naming the columns twice.
    assert run("report", path, "--value-col", "pv", "--value-col", "kwh", *units)[1] == out
    # An explicit --value-col still decides; --unit may then name a subset.
    code, out, _ = run("report", path, "--value-col", "kwh", "--value-col", "other", "--unit", "kwh=kWh")
    assert code == 0 and json.loads(out)["column_order"] == ["kwh", "other"]
    # One named column gives a single-series report.
    code, out, _ = run("report", path, "--unit", "kwh=kWh", "--resolution", "1h")
    assert code == 0 and json.loads(out)["metadata"]["unit"] == "kWh"
    # A plain unit still needs a single value column.
    code, out, err = run("report", path, "--unit", "kWh")
    assert code == 2 and out == "" and "pass --value-col" in err
    code, out, err = run("report", path, "--unit", "kwh=kWh", "--unit", "nope=kW")
    assert code == 2 and out == "" and "--unit names columns that are not in the file: ['nope']" in err


def test_unit_per_column_with_schema_is_refused(tmp_path):
    path = str(write(tmp_path, "timestamp,kwh\n2024-01-01T00:00Z,1\n"))
    schema = ek.to_table_schema(ek.MeasurementMetadata(name="kwh", unit="kWh"))
    schema_path = str(write(tmp_path, json.dumps(schema), "schema.json"))
    code, out, err = run("report", path, "--schema", schema_path, "--unit", "kwh=kWh")
    assert code == 2 and out == "" and "--schema and --unit both set metadata" in err


def test_multiple_value_columns_flags_csv(tmp_path):
    rows = ["2024-01-01T00:00Z,1,9", "2024-01-01T01:00Z,inf,8", "2024-01-01T03:00Z,3,7"]
    path = write(tmp_path, "timestamp,a,b\n" + "\n".join(rows) + "\n")
    flags = tmp_path / "flags.csv"
    args = ["report", str(path), "--value-col", "a", "--value-col", "b", "--freq", "1h"]
    assert run(*args, "--flags-csv", str(flags), "--insert-missing")[0] == 0
    out = pd.read_csv(flags)
    assert list(out.columns) == ["timestamp", "a", "quality_flag_a", "b", "quality_flag_b"]
    assert len(out) == 4  # the absent 02:00 row is inserted once
    assert out["quality_flag_a"].tolist() == [0, 2, 65, 0]
    assert out["quality_flag_b"].tolist() == [0, 0, 65, 0]


def test_compare(tmp_path):
    good = write(tmp_path, CLEAN, "good.csv")
    bad = write(tmp_path, CLEAN.replace("0.25", "inf"), "bad.csv")
    for name, path in (("a.json", good), ("b.json", bad)):
        assert run("report", str(path), "--freq", "15min", "-o", str(tmp_path / name))[0] == 0
    code, out, _ = run("compare", str(tmp_path / "a.json"), str(tmp_path / "b.json"))
    data = json.loads(out)
    assert code == 0 and data["worse"] and data["changes"][""]["flag_counts"]["NON_FINITE"]["delta"] == 1
    assert run("compare", str(tmp_path / "a.json"), str(tmp_path / "b.json"), "--fail-if-worse")[0] == 1
    assert run("compare", str(tmp_path / "b.json"), str(tmp_path / "a.json"), "--fail-if-worse")[0] == 0
    code, out, err = run("compare", str(tmp_path / "a.json"), str(tmp_path / "missing.json"))
    assert code == 2 and "file not found" in err
    code, out, err = run("compare", str(good), str(tmp_path / "a.json"))
    assert code == 2 and "not a JSON report" in err


def test_flags_csv_keeps_rows_and_inserts_missing(tmp_path):
    path = write(tmp_path, DEFECTIVE)
    flags = tmp_path / "flags.csv"
    code, _, _ = run(
        "report", str(path), "--timestamp-col", "time", "--value-col", "kwh",
        "--assume-tz", "Europe/Stockholm", "--freq", "15min",
        "--flags-csv", str(flags), "--insert-missing",
    )  # fmt: skip
    assert code == 0
    table = pd.read_csv(flags)
    assert list(table.columns) == ["time", "kwh", "quality_flag"]
    assert len(table) == 6  # 5 original rows + 1 inserted
    assert table["quality_flag"].tolist() == [0, 0, 65, 8, 8, 2]


def test_flags_csv_uses_the_input_format(tmp_path):
    path = write(tmp_path, CLEAN.replace(",", ";").replace(".", ","), name="eu.csv")
    flags = tmp_path / "flags.csv"
    args = ("report", str(path), "--freq", "15min", "--delimiter", ";", "--decimal", ",")
    assert run(*args, "--flags-csv", str(flags))[0] == 0
    text = flags.read_text()
    assert text.splitlines()[0] == "timestamp;kwh;quality_flag"
    assert ";0,25;0" in text
    table = pd.read_csv(flags, sep=";", decimal=",")
    reference = pd.read_csv(io.StringIO(CLEAN))
    assert table["kwh"].tolist() == reference["kwh"].tolist()
    assert (table["quality_flag"] == 0).all()


def test_calendar_step(tmp_path):
    days = pd.date_range("2024-03-29", periods=5, freq="D", tz="Europe/Stockholm").delete(2)
    text = "timestamp,kwh\n" + "".join(f"{t.isoformat()},1.0\n" for t in days)
    code, out, _ = run("report", str(write(tmp_path, text)), "--freq", "D", "--tz", "Europe/Stockholm")
    data = json.loads(out)
    assert code == 0 and data["n_missing_intervals"] == 1 and data["expected_resolution"] == "D"


def test_stdin(tmp_path):
    code, out, _ = run("report", "-", "--freq", "15min", stdin=CLEAN)
    assert code == 0 and json.loads(out)["n_rows"] == 8


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--freq", "15min"], "pass --assume-tz"),  # naive timestamps
        (["--timestamp-col", "nope"], "timestamp column 'nope' not found"),
        (["--timestamp-col", "time"], "pass --value-col"),
        (["--timestamp-col", "time", "--value-col", "nope"], "value column 'nope' not found"),
        (["--tz", "Europe/Stockholm"], "--tz needs --freq"),
        (["--insert-missing"], "--insert-missing only affects --flags-csv"),
        (["--timestamp-col", "time", "--value-col", "kwh", "--assume-tz", "UTC", "--unit", "nope"], "unit"),
    ],
)
def test_input_errors_exit_2_without_traceback(tmp_path, argv, message):
    path = write(tmp_path, DEFECTIVE if "--timestamp-col" in argv else CLEAN.replace("Z,", ","))
    code, out, err = run("report", str(path), *argv)
    assert code == 2 and out == ""
    assert err.startswith("energydata-kit: error:") and message in err
    assert "Traceback" not in err


def test_known_outage_in_assume_tz(tmp_path):
    # P-30: with --assume-tz, a naive --known-outage is read in that zone, like the data.
    rows = ["2026-01-01 00:00,1", "2026-01-01 01:00,2", "2026-01-01 03:00,4"]
    path = str(write(tmp_path, "timestamp,kwh\n" + "\n".join(rows) + "\n", "naive.csv"))
    base = ["report", path, "--assume-tz", "Europe/Oslo", "--freq", "1h"]
    local = run(*base, "--known-outage", "2026-01-01 02:00", "2026-01-01 02:00")
    offset = run(*base, "--known-outage", "2026-01-01T01:00Z", "2026-01-01T01:00Z")
    assert local == offset and local[0] == 0  # the same report, byte for byte
    data = json.loads(local[1])
    assert data["parameters"]["known_outages"] == [["2026-01-01T01:00:00+00:00"] * 2]
    assert data["n_missing_explained"] == 1
    # DST: a skipped time follows --nonexistent; one repeated time cannot be placed.
    spring = ["--known-outage", "2026-03-29 02:30", "2026-03-29 02:30"]
    shifted = json.loads(run(*base, "--nonexistent", "shift_forward", *spring)[1])
    assert shifted["parameters"]["known_outages"] == [["2026-03-29T01:00:00+00:00"] * 2]
    for argv, message in [
        (spring, "is skipped at the start of DST (see --nonexistent) in Europe/Oslo"),
        (["--known-outage", "2026-10-25 02:30", "2026-10-25 02:30"], "is repeated at the end of DST"),
    ]:
        code, out, err = run(*base, *argv)
        assert code == 2 and out == "" and message in err and "give it with a UTC offset" in err, argv
    # An unknown --assume-tz is reported for the data first, without a traceback.
    code, out, err = run("report", path, "--assume-tz", "Not/AZone", "--freq", "1h", *spring)
    assert code == 2 and out == "" and "could not localize to Not/AZone" in err
    # Without --assume-tz a naive outage is refused as before.
    aware = str(write(tmp_path, "timestamp,kwh\n2026-01-01T00:00Z,1\n2026-01-01T02:00Z,2\n", "aware.csv"))
    code, out, err = run(
        "report", aware, "--freq", "1h", "--known-outage", "2026-01-01 01:00", "2026-01-01 01:00"
    )
    assert code == 2 and out == "" and "known outage must be timezone-aware" in err


def test_time_col(tmp_path):
    # P-34: date and time in separate columns are joined, not read as the date alone.
    split = write(
        tmp_path, "date;time;kwh\n2026-01-01;00:00;1\n2026-01-01;01:00;2\n2026-01-01;03:00;4\n", "s.csv"
    )
    joined = write(
        tmp_path, "date;kwh\n2026-01-01T00:00;1\n2026-01-01T01:00;2\n2026-01-01T03:00;4\n", "j.csv"
    )
    common = ["--delimiter", ";", "--timestamp-col", "date", "--assume-tz", "Europe/Oslo", "--freq", "1h"]
    flags = [tmp_path / "f1.csv", tmp_path / "f2.csv"]
    out = run("report", str(split), *common, "--time-col", "time", "--flags-csv", str(flags[0]))
    same = run("report", str(joined), *common, "--flags-csv", str(flags[1]))
    assert out == same and out[0] == 0  # the same report as from one ISO column
    assert flags[0].read_text() == flags[1].read_text()  # one joined timestamp column, named "date"
    assert json.loads(out[1])["n_missing_intervals"] == 1
    # Without --time-col only the date is read: three rows on one timestamp (the old, silent result).
    alone = json.loads(run("report", str(split), *common[:4], "--value-col", "kwh", "--assume-tz", "UTC")[1])
    assert alone["n_duplicate_timestamps"] == 1
    bad = write(tmp_path, "date;time;kwh\n2026-01-01;23:00;1\n2026-01-01;24:00;2\n2026-01-02;;3\n", "b.csv")
    us = write(tmp_path, "date;time;kwh\n01/02/2026;00:00;1\n", "us.csv")
    for path, extra, message in [
        (bad, [], "2 value(s) in 'time' are not HH:MM or HH:MM:SS, 00:00 to 23:59 (position 1: '24:00'"),
        (us, [], "1 value(s) in 'date' are not YYYY-MM-DD (position 0: '01/02/2026')"),
        (split, ["--time-col", "nope"], "time column 'nope' not found"),
        (split, ["--time-col", "date"], "must name a column other than --timestamp-col"),
        (split, ["--time-col", "time", "--value-col", "time"], "--time-col 'time' is also a value column"),
    ]:
        argv = ["--time-col", "time"] if path is not split else []
        code, out, err = run("report", str(path), *common, *argv, *extra)
        assert code == 2 and out == "" and message in err, (path.name, extra, err)


def test_thousands(tmp_path):
    # P-33: values with a thousands separator are numbers, not NON_NUMERIC flags.
    rows = ["2026-01-01T00:00Z;1.234,5", "2026-01-01T01:00Z;1.240,0", "2026-01-01T03:00Z;999,5"]
    path = str(write(tmp_path, "timestamp;kwh\n" + "\n".join(rows) + "\n", "t.csv"))
    plain = str(
        write(tmp_path, "timestamp;kwh\n" + "\n".join(r.replace(".", "") for r in rows) + "\n", "p.csv")
    )
    base = ["--delimiter", ";", "--decimal", ",", "--freq", "1h"]
    before = json.loads(run("report", path, *base)[1])
    assert before["flag_counts"]["NON_NUMERIC"] == 3  # every row, even 999,5: the old, misleading result
    flags = tmp_path / "flags.csv"
    out = run("report", path, *base, "--thousands", ".", "--flags-csv", str(flags))
    assert out == run("report", plain, *base) and out[0] == 0  # the same report as without separators
    assert flags.read_text().splitlines()[1:3] == [
        "2026-01-01T00:00:00+0000;1234,5;0",
        "2026-01-01T01:00:00+0000;1240,0;0",
    ]
    for sep, text in [("space", "1 234.5"), ("'", "1'234.5"), (",", "1,234.5")]:
        f = str(write(tmp_path, f"timestamp;kwh\n2026-01-01T00:00Z;{text}\n", "s.csv"))
        data = json.loads(run("report", f, "--delimiter", ";", "--thousands", sep)[1])
        assert data["flag_counts"]["NON_NUMERIC"] == 0, sep
    for argv, message in [
        ([path, *base, "--thousands", ","], "--thousands and --decimal are both ','"),
        ([path, "--delimiter", "'", "--thousands", "'"], '--delimiter and --thousands are both "\'"'),
    ]:
        code, out, err = run("report", *argv)
        assert code == 2 and out == "" and message in err, argv


def test_encoding(tmp_path):
    # P-29: a non-UTF-8 export is read with --encoding; the flags and gaps CSVs keep it.
    text = "tid;förbrukning\n2026-01-01T00:00Z;1,5\n2026-01-01T01:00Z;1,5\n2026-01-01T03:00Z;2,5\n"
    path = tmp_path / "latin1.csv"
    path.write_bytes(text.encode("latin-1"))
    utf8 = tmp_path / "utf8.csv"
    utf8.write_text(text, encoding="utf-8")
    options = ["--timestamp-col", "tid", "--delimiter", ";", "--decimal", ",", "--freq", "1h"]
    code, out, err = run("report", str(path), *options)
    assert code == 2 and out == "" and "codec can't decode" in err and "--encoding latin-1" in err
    flags, gaps = tmp_path / "flags.csv", tmp_path / "gaps.csv"
    written = ["--stale-min-run", "2", "--flags-csv", str(flags), "--gaps-csv", str(gaps)]
    code, out, err = run("report", str(path), *options, "--encoding", "latin-1", *written)
    assert (code, err) == (0, "")
    same = run("report", str(utf8), *options, "--stale-min-run", "2")[1]
    assert out == same  # the same report as from the UTF-8 file
    assert flags.read_bytes().startswith("tid;förbrukning;quality_flag\n".encode("latin-1"))
    assert pd.read_csv(gaps, sep=";", encoding="latin-1")["column"].tolist() == ["förbrukning"]
    for argv, message in [
        ([str(path), "--encoding", "no-such-codec"], "unknown encoding: 'no-such-codec'"),
        (["-", "--encoding", "latin-1"], "standard input is read as text already"),
    ]:
        code, out, err = run("report", *argv)
        assert code == 2 and out == "" and message in err, argv


def test_edge_case_files(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    code, _, err = run("report", str(empty))
    assert code == 2 and "could not read CSV" in err

    code, out, err = run("report", str(write(tmp_path, "timestamp,kwh\n")), "--freq", "15min")
    assert (code, err) == (0, "") and json.loads(out)["n_rows"] == 0

    semi = tmp_path / "semi.csv"
    semi.write_text("timestamp;kwh\n2026-01-01T00:00:00Z;1\n")
    code, _, err = run("report", str(semi))
    assert code == 2 and "try --delimiter ';'" in err

    bad = write(tmp_path, "timestamp,kwh\nnot-a-date,1\n2026-01-01T00:15:00Z,2\n")
    code, _, err = run("report", str(bad))
    assert code == 2 and "position 0: 'not-a-date'" in err and "naive" not in err


@pytest.mark.parametrize(("delimiter", "sep"), [(";", ";"), ("tab", "\t"), ("\\t", "\t"), ("|", "|")])
def test_delimiter_gives_the_same_report(tmp_path, delimiter, sep):
    reference = json.loads(run("report", str(write(tmp_path, CLEAN)), "--freq", "15min")[1])
    path = write(tmp_path, CLEAN.replace(",", sep), name="other.csv")
    code, out, err = run("report", str(path), "--freq", "15min", "--delimiter", delimiter)
    assert (code, err) == (0, "") and json.loads(out) == reference


def test_decimal_comma(tmp_path):
    reference = json.loads(run("report", str(write(tmp_path, CLEAN)), "--freq", "15min")[1])
    # "2024-01-01T00:15:00Z;0,25": semicolons between fields, decimal commas in values.
    path = write(tmp_path, CLEAN.replace(",", ";").replace(".", ","), name="eu.csv")
    args = ("report", str(path), "--freq", "15min", "--delimiter", ";")
    code, out, _ = run(*args, "--decimal", ",")
    assert code == 0 and json.loads(out) == reference
    # Without --decimal the values are not numbers, and the report says so.
    assert json.loads(run(*args)[1])["flag_counts"]["NON_NUMERIC"] > 0


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--delimiter", ";;"], "--delimiter must be one character"),
        (["--delimiter", "a"], "--delimiter must be one character"),
        (["--delimiter", '"'], "--delimiter must be one character"),
        (["--delimiter", ",", "--decimal", ","], "--delimiter and --decimal are both ','"),
    ],
)
def test_bad_delimiter(tmp_path, argv, message):
    code, out, err = run("report", str(write(tmp_path, CLEAN)), *argv)
    assert (code, out) == (2, "") and message in err


GAPPY = (
    "timestamp,kwh,pv\n"
    "2026-01-01T00:00:00Z,1,5\n"
    "2026-01-01T00:15:00Z,,5\n"
    "2026-01-01T01:00:00Z,3,5\n"
    "2026-01-01T01:15:00Z,-1,5\n"
)


FIXED = (
    "timestamp,kwh,pv\n"
    "2026-01-01T00:00:00Z,1,5\n"
    "2026-01-01T00:15:00Z,2,5\n"
    "2026-01-01T00:30:00Z,2,5\n"
    "2026-01-01T00:45:00Z,2,5\n"
    "2026-01-01T01:00:00Z,3,5\n"
    "2026-01-01T01:15:00Z,-1,5\n"
)


def test_text_summary(tmp_path):
    path = str(write(tmp_path, GAPPY))
    args = ("report", path, "--value-col", "kwh", "--freq", "15min", "--bounds", "0", "none")
    code, out, err = run(*args, "--format", "text")
    assert (code, err) == (0, "")
    assert out.splitlines() == [
        "kwh: 4 rows, 2026-01-01T00:00:00+00:00 to 2026-01-01T01:15:00+00:00",
        "  completeness: 66.67% (4 of 6 expected); 2 missing in 1 gap(s)",
        "  flagged rows: 2 (MISSING_VALUE 1, OUT_OF_BOUNDS 1)",
        "  gap: 2026-01-01T00:30:00+00:00 to 2026-01-01T00:45:00+00:00 (2 missing)",
        f"fingerprint: {json.loads(run(*args)[1])['fingerprint'][:16]} (energydata-kit {__version__})",
    ]
    # --fail-on-issues and -o work the same as with JSON.
    target = tmp_path / "summary.txt"
    code, out, _ = run(*args, "--format", "text", "-o", str(target), "--fail-on-issues")
    assert (code, out) == (1, "") and target.read_text().startswith("kwh: 4 rows")


def test_text_summary_columns_and_no_step(tmp_path):
    path = str(write(tmp_path, GAPPY))
    both = ("--value-col", "kwh", "--value-col", "pv")
    out = run("report", path, *both, "--freq", "15min", "--format", "text")[1]
    lines = out.splitlines()
    assert lines[0] == "2 column(s)"
    assert "  kwh: 4 rows, 2026-01-01T00:00:00+00:00 to 2026-01-01T01:15:00+00:00" in lines
    assert "    flagged rows: 0" in lines  # pv
    out = run("report", path, "--value-col", "kwh", "--format", "text")[1]
    # The summary names the step the report infers (P-27), so the next run can use it.
    assert (
        "  completeness: not checked (no step: pass --freq, or a resolution with --unit or --schema; "
        "the most common step between timestamps is 15min, used by --freq inferred)" in out.splitlines()
    )


def test_freq_inferred(tmp_path):
    # P-27: --freq inferred uses the most common step as if it were passed, and says so.
    path = str(write(tmp_path, GAPPY))
    given = run("report", path, "--value-col", "kwh", "--freq", "15min")
    inferred = run("report", path, "--value-col", "kwh", "--freq", "inferred")
    assert inferred == given and inferred[0] == 0  # the same report, byte for byte
    assert json.loads(inferred[1])["n_missing_intervals"] == 2
    for fmt, line in [("text", "step: "), ("markdown", "Step: ")]:
        out = run("report", path, "--value-col", "kwh", "--freq", "inferred", "--format", fmt)[1]
        assert line + "15min, inferred (the most common step between timestamps)" in out.splitlines()
        assert line not in run("report", path, "--value-col", "kwh", "--freq", "15min", "--format", fmt)[1]
    # The flags and gaps files use the inferred grid too.
    for freq, name in [("15min", "given"), ("inferred", "inferred")]:
        argv = [
            "--flags-csv",
            str(tmp_path / f"{name}.csv"),
            "--gaps-csv",
            str(tmp_path / f"{name}-gaps.csv"),
        ]
        assert run("report", path, "--value-col", "kwh", "--value-col", "pv", "--freq", freq, *argv)[0] == 0
    for suffix in [".csv", "-gaps.csv"]:
        assert (tmp_path / f"given{suffix}").read_text() == (tmp_path / f"inferred{suffix}").read_text()
    one = str(write(tmp_path, "timestamp,kwh\n2026-01-01T00:00:00Z,1\n", "one.csv"))
    for argv, message in [
        ([one, "--freq", "inferred"], "--freq inferred needs at least two distinct timestamps"),
        (
            [path, "--value-col", "kwh", "--freq", "inferred", "--tz", "Europe/Oslo"],
            "cannot be used with --tz",
        ),
    ]:
        code, out, err = run("report", *argv)
        assert code == 2 and out == "" and message in err, (argv, err)


@pytest.mark.parametrize(
    ("ns", "text"),
    [
        (3_600_000_000_000, "1h"),
        (5_400_000_000_000, "90min"),
        (86_400_000_000_000, "24h"),
        (30_000_000_000, "30s"),
        (100_000_000, "100ms"),
        (5_000, "5us"),
        (7, "7ns"),
    ],
)
def test_step_text(ns, text):
    step = pd.Timedelta(ns, unit="ns")
    assert cli._step_text(step) == text
    assert to_step(text) == step  # a value --freq accepts, for the same step


def test_text_summary_says_why_completeness_is_missing(tmp_path):
    # Not only a missing step leaves completeness empty (OSS-75).
    empty = str(write(tmp_path, "timestamp,kwh\n", "empty.csv"))
    out = run("report", empty, "--freq", "15min", "--format", "text")[1]
    assert "  completeness: not checked (no rows)" in out.splitlines()
    mid_month = str(
        write(tmp_path, "timestamp,kwh\n2026-01-05T00:00:00Z,1\n2026-01-20T00:00:00Z,2\n", "mid.csv")
    )
    out = run("report", mid_month, "--freq", "MS", "--tz", "UTC", "--format", "text")[1]
    assert "  completeness: undefined (no expected interval within the data's time span)" in out.splitlines()


def test_fail_on_removed_columns(tmp_path):
    # P-39: a column that disappears can fail compare; --fail-if-worse alone still passes it.
    reports = {}
    for name, header in [("abc", "a,b,c"), ("ac", "a,c"), ("acd", "a,c,d")]:
        cols = header.split(",")
        rows = "".join(f"2026-01-01T0{h}:00Z," + ",".join("1" for _ in cols) + "\n" for h in range(2))
        path = str(write(tmp_path, f"timestamp,{header}\n{rows}", f"{name}.csv"))
        reports[name] = str(tmp_path / f"{name}.json")
        assert run("report", path, "--freq", "1h", "--all-value-cols", "-o", reports[name])[0] == 0
    code, out, _ = run("compare", reports["abc"], reports["ac"], "--fail-if-worse", "--format", "text")
    assert code == 0 and "columns removed: b" in out  # unchanged without the option
    assert run("compare", reports["abc"], reports["ac"], "--fail-on-removed-columns")[0] == 1
    both = ["--fail-on-removed-columns", "--fail-if-worse"]
    assert run("compare", reports["abc"], reports["ac"], *both)[0] == 1
    # Added columns never fail; nor do unchanged ones.
    assert run("compare", reports["ac"], reports["acd"], "--fail-on-removed-columns")[0] == 0
    assert run("compare", reports["ac"], reports["ac"], "--fail-on-removed-columns")[0] == 0


def test_compare_text_summary(tmp_path):
    gappy, fixed = write(tmp_path, GAPPY, name="gappy.csv"), write(tmp_path, FIXED, name="fixed.csv")
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    cols = ("--value-col", "kwh", "--value-col", "pv", "--freq", "15min", "--bounds", "0", "none")
    assert run("report", str(gappy), *cols, "-o", str(before))[0] == 0
    assert run("report", str(fixed), *cols, "-o", str(after))[0] == 0
    code, out, err = run("compare", str(before), str(after), "--format", "text")
    assert (code, err) == (0, "")
    assert out.splitlines()[:5] == [
        "data changed; not worse",
        "kwh:",
        "  rows 4 -> 6 (+2); missing intervals 2 -> 0 (-2); gaps 1 -> 0 (-1); completeness 66.67% -> 100.00%",
        "  flagged rows 2 -> 1 (-1): MISSING_VALUE 1 -> 0 (-1)",
        "  gaps resolved: 1, new: 0, changed: 0",
    ]
    code, out, _ = run("compare", str(after), str(before), "--format", "text", "--fail-if-worse")
    assert code == 1 and out.startswith("data changed; worse:")
    out = run("compare", str(after), str(after), "--format", "text")[1]
    assert out.splitlines() == ["same data; not worse", "kwh: no changes", "pv: no changes"]


def _schema(tmp_path, *metas):
    schema = ek.to_table_schema(metas[0])
    schema["fields"] += [ek.to_table_schema(m)["fields"][1] for m in metas[1:]]
    path = tmp_path / "data.schema.json"
    path.write_text(json.dumps(schema))
    return str(path)


KWH = ek.MeasurementMetadata(
    name="kwh", unit="kWh", resolution="15min", aggregation="sum", interval_label="end"
)
PV = ek.MeasurementMetadata(name="pv", unit="kW", resolution="15min", aggregation="mean")


def test_schema_sets_metadata_columns_and_step(tmp_path):
    path, schema = str(write(tmp_path, GAPPY)), _schema(tmp_path, KWH, PV)
    flags = tmp_path / "flags.csv"
    code, out, err = run("report", path, "--schema", schema, "--flags-csv", str(flags), "--insert-missing")
    assert (code, err) == (0, "")
    report = json.loads(out)
    assert report["column_order"] == ["kwh", "pv"]  # the schema's columns, no --value-col needed
    assert report["columns"]["kwh"]["metadata"] == KWH.to_dict()
    assert report["columns"]["pv"]["metadata"] == PV.to_dict()
    assert report["columns"]["kwh"]["n_missing_intervals"] == 2  # step from the schema, no --freq
    assert len(pd.read_csv(flags)) == 6  # --flags-csv uses the same step

    # One column: the same metadata as --unit would give, from the schema.
    single = json.loads(run("report", path, "--schema", schema, "--value-col", "kwh")[1])
    assert single["metadata"] == KWH.to_dict() and single["completeness"] == pytest.approx(4 / 6, abs=1e-6)


def test_schema_errors(tmp_path):
    path = str(write(tmp_path, GAPPY))
    schema = _schema(tmp_path, KWH)
    empty = tmp_path / "empty.json"
    empty.write_text('{"fields": []}')
    other = ek.MeasurementMetadata(name="other", unit="kW", resolution="15min")
    elsewhere = tmp_path / "elsewhere.json"
    elsewhere.write_text(json.dumps(ek.to_table_schema(other)))
    hourly = _schema(tmp_path, KWH, ek.MeasurementMetadata(name="pv", unit="kW", resolution="1h"))
    for argv, message in [
        (["--schema", schema, "--unit", "kW"], "--schema and --unit both set metadata"),
        (["--schema", str(tmp_path / "absent.json")], "file not found"),
        (["--schema", str(empty)], "no fields with 'energydata_kit' metadata"),
        (["--schema", str(elsewhere)], "none of the --schema columns ['other'] are in the file"),
        (["--schema", hourly, "--flags-csv", str(tmp_path / "f.csv")], "different resolutions"),
    ]:
        code, _, err = run("report", path, *argv)
        assert code == 2 and message in err, (argv, err)


def test_dst_localization_errors_name_the_cli_option(tmp_path):
    fall = write(tmp_path, "t,kwh\n2024-10-27 02:00,1\n2024-10-27 02:15,1\n2024-10-27 02:00,2\n", "fall.csv")
    spring = write(tmp_path, "t,kwh\n2024-03-31 01:45,1\n2024-03-31 02:15,1\n", "spring.csv")
    base = ("--timestamp-col", "t", "--assume-tz", "Europe/Stockholm")
    code, _, err = run("report", str(fall), *base)
    assert code == 2 and "try --ambiguous infer" in err
    code, _, err = run("report", str(spring), *base)
    assert code == 2 and "see --nonexistent" in err
    assert run("report", str(fall), *base, "--ambiguous", "infer")[0] == 0


def test_text_summary_says_when_gaps_are_not_listed(tmp_path):
    rows = ["timestamp,kwh"] + [f"2026-01-01T{h:02d}:00:00Z,1" for h in (0, 2, 4, 6)]  # three 1-hour gaps
    path = write(tmp_path, "\n".join(rows) + "\n")
    out = run("report", str(path), "--freq", "1h", "--max-listed", "1", "--format", "text")[1]
    lines = out.splitlines()
    assert sum(line.startswith("  gap: ") for line in lines) == 1
    assert "  ... 2 more gap(s); see the JSON report" in lines


def test_file_system_errors_exit_2_without_traceback(tmp_path):
    data = str(write(tmp_path, CLEAN))
    report = tmp_path / "r.json"
    assert run("report", data, "-o", str(report))[0] == 0
    for argv in [
        ["report", str(tmp_path)],  # a directory as input
        ["report", data, "-o", str(tmp_path)],  # a directory as output
        ["report", data, "-o", str(tmp_path / "missing" / "r.json")],
        ["report", data, "--flags-csv", str(tmp_path / "missing" / "f.csv")],
        ["report", data, "--schema", str(tmp_path)],
        ["compare", str(report), str(tmp_path)],
    ]:
        code, _, err = run(*argv)
        assert code == 2 and err.startswith("energydata-kit: error:"), (argv, err)
        assert "Traceback" not in err


def test_missing_file(tmp_path):
    code, _, err = run("report", str(tmp_path / "absent.csv"))
    assert code == 2 and "file not found" in err


def test_compare_rejects_its_own_output_with_exit_2(tmp_path):
    data = write(tmp_path, CLEAN)
    run("report", str(data), "--freq", "15min", "-o", str(tmp_path / "r.json"))
    run("compare", str(tmp_path / "r.json"), str(tmp_path / "r.json"), "-o", str(tmp_path / "c.json"))
    code, out, err = run("compare", str(tmp_path / "c.json"), str(tmp_path / "r.json"), "--fail-if-worse")
    assert (code, out) == (2, "")  # was exit 1, read as "worse"
    assert "before is not a quality report" in err


def test_schema_with_name_inside_namespace_exits_2(tmp_path):
    schema = ek.to_table_schema(ek.MeasurementMetadata(name="kwh", unit="kWh"))
    schema["fields"][1]["energydata_kit"]["name"] = "other"  # was accepted: report labelled "other"
    path = write(tmp_path, json.dumps(schema), "schema.json")
    code, out, err = run("report", str(write(tmp_path, CLEAN)), "--freq", "15min", "--schema", str(path))
    assert (code, out) == (2, "") and "belong on the field" in err


def test_output_files_use_lf_on_every_platform(tmp_path, monkeypatch):
    # Windows: pandas ends CSV lines with os.linesep, and Path.write_text
    # translates "\n" to "\r\n", so files would differ from Linux and macOS.
    monkeypatch.setattr(os, "linesep", "\r\n")  # what pandas sees on Windows
    data = write(tmp_path, CLEAN)
    report, flags = tmp_path / "r.json", tmp_path / "f.csv"
    code, _, err = run("report", str(data), "--freq", "15min", "-o", str(report), "--flags-csv", str(flags))
    assert (code, err) == (0, "")
    run("compare", str(report), str(report), "-o", str(tmp_path / "c.txt"), "--format", "text")
    for path in (report, flags, tmp_path / "c.txt"):
        raw = path.read_bytes()
        assert b"\r" not in raw and raw.endswith(b"\n"), path.name


def _facts(text_summary):
    """(label, value) pairs from --format text, e.g. ("flagged rows", "2 (...)")."""
    return [tuple(line.strip().split(": ", 1)) for line in text_summary.splitlines() if line.startswith("  ")]


@pytest.mark.parametrize(
    "columns", [["--value-col", "kwh"], ["--value-col", "kwh", "--value-col", "quality2"]]
)
def test_markdown_report_has_the_text_summary_facts(tmp_path, columns):
    csv = DEFECTIVE.replace("quality\n", "quality,quality2\n").replace(",ok\n", ",ok,1\n")
    path = str(write(tmp_path, csv))
    common = ["report", path, "--timestamp-col", "time", "--assume-tz", "Europe/Stockholm", "--freq", "15min"]
    _, text, _ = run(*common, *columns, "--format", "text")
    code, md, err = run(*common, *columns, "--format", "markdown")
    assert (code, err) == (0, "")
    assert md.startswith("# Quality report: ") and "Fingerprint `" in md
    for label, value in _facts(text):  # same facts, so the formats cannot drift apart
        if label.startswith(("kwh", "quality2")):
            continue  # per-column headline lines in text; headings in Markdown
        assert f"- **{label}:** {value}" in md or f"- {label}: {value}" in md, (label, value)
    if len(columns) > 2:
        assert "\n## kwh\n" in md and "\n## quality2\n" in md


def test_markdown_escapes_column_names(tmp_path):
    path = write(tmp_path, CLEAN.replace("kwh", "a_b|c*"))
    code, md, _ = run("report", str(path), "--freq", "15min", "--format", "markdown")
    assert code == 0 and md.splitlines()[0] == r"# Quality report: a\_b\|c\*"


def test_column_names_stay_on_one_line(tmp_path):
    # A line break in a column name split the Markdown heading and the text summary line.
    path = write(tmp_path, CLEAN.replace("kwh", '"a\nb&~$"'))
    code, md, _ = run("report", str(path), "--freq", "15min", "--format", "markdown")
    assert code == 0 and md.splitlines()[0] == r"# Quality report: a b\&\~\$"
    _, text, _ = run("report", str(path), "--freq", "15min", "--format", "text")
    assert text.startswith("a b&~$: ")
    s = ek.make_synthetic_series(periods=4)
    before = ek.assess_frame(pd.DataFrame({"x": s}))
    after = ek.assess_frame(pd.DataFrame({"x": s, "a\nb": s}))
    comparison = ek.compare_reports(before, after).to_dict()
    assert "columns added: a b\n" in cli._comparison_summary(comparison)
    assert "Columns added: a b\n" in cli._comparison_summary(comparison, markdown=True)


def test_summary_counts_are_exact_for_long_series():
    # Present intervals were rebuilt from the rounded completeness: above about
    # a million intervals that read "3000001 of 3000001 expected; 1 missing".
    data = ek.assess_quality(ek.make_synthetic_series(periods=4), freq="15min").to_dict()
    data.update(n_expected_intervals=3_000_001, n_missing_intervals=1, n_gaps=1, completeness=1.0)
    assert "(3000000 of 3000001 expected); 1 missing in 1 gap(s)" in cli._summary(data)


def test_markdown_comparison(tmp_path):
    before, after = tmp_path / "b.json", tmp_path / "a.json"
    run("report", str(write(tmp_path, CLEAN)), "--freq", "15min", "-o", str(before))
    run(
        "report",
        str(write(tmp_path, CLEAN.replace("2024-01-01T01:30:00Z,1.50\n", ""), "gap.csv")),
        "--freq",
        "15min",
        "-o",
        str(after),
    )
    code, md, _ = run("compare", str(before), str(after), "--format", "markdown")
    _, text, _ = run("compare", str(before), str(after), "--format", "text")
    assert code == 0
    assert md.splitlines()[:3] == ["# Report comparison", "", f"**{text.splitlines()[0]}**"]
    assert "\n## series\n" in md
    for line in text.splitlines()[2:]:
        assert f"- {line.strip()}" in md
    _, same, _ = run("compare", str(before), str(before), "--format", "markdown")
    assert same.rstrip().endswith("No changes.")


def test_known_outage_option(tmp_path):
    path = str(write(tmp_path, CLEAN.replace("2024-01-01T01:30:00Z,1.50\n", "")))
    outage = ["--known-outage", "2024-01-01T01:15:00+00:00", "2024-01-01T01:45Z"]
    code, out, err = run("report", path, "--freq", "15min", *outage)
    data = json.loads(out)
    assert (code, err) == (0, "")
    assert data["n_missing_explained"] == 1 and data["completeness_excluding_outages"] == 1.0
    assert data["parameters"]["known_outages"] == [["2024-01-01T01:15:00+00:00", "2024-01-01T01:45:00+00:00"]]
    _, text, _ = run("report", path, "--freq", "15min", *outage, "--format", "text")
    assert (
        "  known outages: 1 period(s); 1 of the missing intervals inside; completeness without them 100.00%"
        in text
    )
    _, md, _ = run("report", path, "--freq", "15min", *outage, "--format", "markdown")
    assert "- **known outages:** 1 period(s);" in md
    code, _, err = run(
        "report", path, "--freq", "15min", "--known-outage", "2024-01-01T01:15", "2024-01-01T01:45Z"
    )
    assert code == 2 and "timezone-aware" in err


def _parquet(tmp_path, frame, name="data.parquet"):
    pytest.importorskip("pyarrow")  # optional [parquet] extra
    path = tmp_path / name
    frame.to_parquet(path)
    return str(path)


@pytest.mark.parametrize("timestamps_as", ["datetime", "string", "index"])
def test_parquet_input_gives_the_same_report_as_csv(tmp_path, timestamps_as):
    csv = write(tmp_path, CLEAN.replace("2024-01-01T01:30:00Z,1.50\n", ""))
    frame = pd.read_csv(csv, dtype={"timestamp": str})
    if timestamps_as != "string":
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    if timestamps_as == "index":  # df.to_parquet() keeps a named index; was "column not found"
        frame = frame.set_index("timestamp")
    for suffix in (".parquet", ".PQ"):
        path = _parquet(tmp_path, frame, "data" + suffix)
        code, out, err = run("report", path, "--freq", "15min")
        assert (code, err) == (0, "")
        assert out == run("report", str(csv), "--freq", "15min")[1]  # same bytes, same fingerprint


def test_parquet_rejects_csv_options_and_explains_a_missing_pyarrow(tmp_path, monkeypatch):
    path = _parquet(tmp_path, pd.read_csv(io.StringIO(CLEAN)))
    for option in (["--decimal", ","], ["--encoding", "latin-1"], ["--thousands", ","]):
        code, _, err = run("report", path, *option)
        assert code == 2 and "apply to CSV files only" in err, option

    def no_pyarrow(*args, **kwargs):
        raise ImportError("Unable to find a usable engine; tried using: 'pyarrow'")

    monkeypatch.setattr(pd, "read_parquet", no_pyarrow)
    code, _, err = run("report", path, "--freq", "15min")
    assert code == 2 and "python -m pip install 'energydata-kit[parquet]'" in err


def test_monthly_resolution_from_metadata_in_report_and_flags(tmp_path):
    # Local month starts across the March DST change: complete, nothing flagged (was refused).
    rows = [
        "2024-01-01T00:00+01:00",
        "2024-02-01T00:00+01:00",
        "2024-03-01T00:00+01:00",
        "2024-04-01T00:00+02:00",
    ]
    path = str(write(tmp_path, "timestamp,kwh\n" + "".join(f"{r},1\n" for r in rows)))
    flags = tmp_path / "flags.csv"
    meta = ["--unit", "kWh", "--aggregation", "sum", "--resolution", "MS", "--timezone", "Europe/Stockholm"]
    code, out, err = run("report", path, *meta, "--flags-csv", str(flags))
    assert (code, err) == (0, "")
    assert json.loads(out)["completeness"] == 1.0
    assert [line.rsplit(",", 1)[1] for line in flags.read_text().splitlines()[1:]] == ["0"] * 4


def test_metadata_options_need_unit(tmp_path):
    # --resolution without --unit was ignored: gaps went unreported, with exit 0.
    path = str(write(tmp_path, CLEAN.replace("2024-01-01T01:30:00Z,1.50\n", "")))
    code, out, err = run("report", path, "--resolution", "15min", "--fail-on-issues")
    assert (code, out) == (2, "") and "pass --unit too" in err


def test_flags_csv_step_is_checked_before_the_report_is_written(tmp_path):
    csv = write(tmp_path, "timestamp,a,b\n2024-01-01T00:00Z,1,2\n")
    fields = [
        {"name": c, "energydata_kit": {"unit": "kW", "resolution": r}}
        for c, r in (("a", "15min"), ("b", "1h"))
    ]
    schema = write(tmp_path, json.dumps({"fields": fields}), "schema.json")
    report = tmp_path / "report.json"
    code, _, err = run(
        "report", str(csv), "--schema", str(schema), "--flags-csv", str(tmp_path / "f.csv"), "-o", str(report)
    )
    assert code == 2 and "different resolutions" in err
    assert not report.exists()  # was written before the error


def test_flags_csv_grid_across_schema_columns(tmp_path):
    csv = write(
        tmp_path, "timestamp,a,b\n2024-01-01T00:00Z,1,2\n2024-01-01T01:00Z,1,2\n2024-01-01T03:00Z,1,2\n"
    )

    def schema(b_resolution):
        b = {"unit": "kW"} | ({"resolution": b_resolution} if b_resolution else {})
        fields = [
            {"name": "a", "energydata_kit": {"unit": "kW", "resolution": "60min"}},
            {"name": "b", "energydata_kit": b},
        ]
        return str(write(tmp_path, json.dumps({"fields": fields}), "schema.json"))

    flags = tmp_path / "flags.csv"
    # "60min" and "1h" were refused as "different resolutions"; they are one grid.
    code, _, err = run("report", str(csv), "--schema", schema("1h"), "--flags-csv", str(flags))
    assert (code, err) == (0, "") and flags.exists()
    # A column without a resolution was flagged on the other column's grid while its report had none.
    report = tmp_path / "report.json"
    code, _, err = run(
        "report", str(csv), "--schema", schema(None), "--flags-csv", str(flags), "-o", str(report)
    )
    assert code == 2 and "have no resolution in --schema" in err and not report.exists()


def test_flags_csv_grid_equal_calendar_steps(tmp_path):
    # Calendar steps were compared by spelling, so "MS" and "1MS" (or "W" and "W-SUN") were
    # refused as "different resolutions" (OSS-78); different calendar steps still are.
    csv = write(
        tmp_path, "timestamp,a,b\n2024-01-01T00:00Z,1,2\n2024-02-01T00:00Z,1,2\n2024-04-01T00:00Z,1,2\n"
    )
    flags = tmp_path / "flags.csv"
    for a, b, ok in [("MS", "1MS", True), ("W", "W-SUN", True), ("MS", "W-MON", False), ("MS", "2MS", False)]:
        fields = [
            {"name": c, "energydata_kit": {"unit": "kW", "resolution": r}} for c, r in [("a", a), ("b", b)]
        ]
        schema = str(write(tmp_path, json.dumps({"fields": fields}), "schema.json"))
        code, _, err = run("report", str(csv), "--schema", schema, "--flags-csv", str(flags))
        if ok:
            assert (code, err) == (0, ""), (a, b, err)
        else:
            assert code == 2 and "different resolutions" in err, (a, b)


def test_unknown_time_zone(tmp_path):
    # --tz Mars/Phobos ended in a zoneinfo traceback with exit status 1 ("issues found").
    path = str(write(tmp_path, CLEAN))
    code, out, err = run("report", path, "--freq", "D", "--tz", "Mars/Phobos")
    assert (code, out) == (2, "") and "unknown time zone 'Mars/Phobos'" in err


def test_unreadable_parquet_input(tmp_path):
    pytest.importorskip("pyarrow")
    (tmp_path / "empty.parquet").write_bytes(b"")
    (tmp_path / "text.parquet").write_text(CLEAN)
    (tmp_path / "dir.parquet").mkdir()  # was an IndexError traceback
    for name in ("empty.parquet", "text.parquet"):
        code, out, err = run("report", str(tmp_path / name))
        assert (code, out) == (2, "") and f"could not read Parquet file {tmp_path / name}" in err
    code, _, err = run("report", str(tmp_path / "dir.parquet"))
    assert code == 2 and "is a directory; pass a single Parquet file" in err
    frame = pd.read_csv(io.StringIO(CLEAN), dtype={"timestamp": str})
    frame.index = pd.to_datetime(frame.pop("timestamp"), utc=True).rename(None)
    code, _, err = run("report", _parquet(tmp_path, frame, "unnamed.parquet"), "--freq", "15min")
    assert code == 2 and "the file's timestamps are an unnamed index" in err


def test_usage_errors_and_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["report"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0 and __version__ in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "status_1"),
    [
        ([], "1 issues found (--fail-on-issues, --fail-on, --min-completeness, --fail-if-worse)"),
        (
            ["report"],
            "1 issues found with --fail-on-issues or --fail-on, or completeness below --min-completeness",
        ),
        (["compare"], "1 worse with --fail-if-worse, or a column removed with --fail-on-removed-columns"),
    ],
)
def test_help_lists_exit_status(argv, status_1, capsys, monkeypatch):
    monkeypatch.setenv("COLUMNS", "200")  # keep argparse from wrapping the epilog
    with pytest.raises(SystemExit) as exc:
        main([*argv, "--help"])
    out = capsys.readouterr().out
    assert exc.value.code == 0
    assert f"exit status: 0 OK; {status_1}; 2 usage, input or file error" in out


def test_python_dash_m(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "energydata_kit", "report", str(write(tmp_path, CLEAN)), "--freq", "15min"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and json.loads(result.stdout)["n_rows"] == 8


def test_compare_summary_counts_changed_gaps(tmp_path):
    # A gap that grew from one interval to three is one changed gap (P-10), in both formats.
    before, after = tmp_path / "before.json", tmp_path / "after.json"
    for path, drop in ((before, [10]), (after, [9, 10, 11])):
        series = ek.make_synthetic_series(periods=24, drop=drop)
        path.write_text(ek.assess_quality(series, freq="15min").to_json())
    for fmt in ("text", "markdown"):
        code, out, err = run("compare", str(before), str(after), "--format", fmt)
        assert (code, err) == (0, "")
        assert "gaps resolved: 0, new: 0, changed: 1" in out


GAPPY_TWO = (
    "timestamp,kwh,pv\n"
    "2024-01-01T00:00Z,1,5\n2024-01-01T00:15Z,2,5\n"  # 00:30 and 00:45 missing
    "2024-01-01T01:00Z,3,5\n2024-01-01T01:15Z,4,5\n"  # 01:30 and 01:45 missing
    "2024-01-01T02:00Z,5,5\n"
)


def test_gaps_csv_lists_every_gap_beyond_max_listed(tmp_path):
    # OSS-137 (P-14): the CSV holds every gap; the JSON report keeps its --max-listed cap.
    path, gaps, report = write(tmp_path, GAPPY_TWO), tmp_path / "gaps.csv", tmp_path / "report.json"
    args = ("report", str(path), "--value-col", "kwh", "--freq", "15min", "-o", str(report))
    assert run(*args, "--max-listed", "1", "--gaps-csv", str(gaps))[0] == 0
    data = json.loads(report.read_text())
    assert data["n_gaps"] == 2 and len(data["gaps"]) == 1 and data["truncated"]["gaps"]
    assert gaps.read_bytes() == (
        b"column,start,end,missing_count\n"
        b"kwh,2024-01-01T00:30:00+0000,2024-01-01T00:45:00+0000,2\n"
        b"kwh,2024-01-01T01:30:00+0000,2024-01-01T01:45:00+0000,2\n"
    )
    # Uncapped, the report lists the same gaps as the CSV.
    assert run(*args, "--gaps-csv", str(gaps))[0] == 0
    listed = [(g["start"], g["end"], g["missing_count"]) for g in json.loads(report.read_text())["gaps"]]
    rows = [line.split(",") for line in gaps.read_text().splitlines()[1:]]
    as_report = [(pd.Timestamp(s).isoformat(), pd.Timestamp(e).isoformat(), int(n)) for _, s, e, n in rows]
    assert as_report == listed


def test_gaps_csv_per_column_grid_and_input_format(tmp_path):
    # Each column on its own report grid: kwh at 15 min has two gaps, pv at 1 h none.
    kwh = ek.MeasurementMetadata(name="kwh", unit="kWh", resolution="15min", aggregation="sum")
    pv = ek.MeasurementMetadata(name="pv", unit="kW", resolution="1h")
    schema = _schema(tmp_path, kwh, pv)
    text = GAPPY_TWO.replace(",", ";")
    path, gaps = write(tmp_path, text), tmp_path / "gaps.csv"
    code, _, err = run("report", str(path), "--delimiter", ";", "--schema", schema, "--gaps-csv", str(gaps))
    assert (code, err) == (0, "")
    assert gaps.read_text().splitlines() == [
        "column;start;end;missing_count",
        "kwh;2024-01-01T00:30:00+0000;2024-01-01T00:45:00+0000;2",
        "kwh;2024-01-01T01:30:00+0000;2024-01-01T01:45:00+0000;2",
    ]


def test_gaps_csv_without_a_step_is_refused_before_writing(tmp_path):
    path, gaps, report = write(tmp_path, GAPPY_TWO), tmp_path / "gaps.csv", tmp_path / "report.json"
    code, out, err = run(
        "report", str(path), "--value-col", "kwh", "-o", str(report), "--gaps-csv", str(gaps)
    )
    assert code == 2 and out == "" and "--gaps-csv needs a step" in err
    assert not report.exists() and not gaps.exists()


def test_gaps_csv_with_no_gaps_has_only_the_header(tmp_path):
    gaps = tmp_path / "gaps.csv"
    assert run("report", str(write(tmp_path, CLEAN)), "--freq", "15min", "--gaps-csv", str(gaps))[0] == 0
    assert gaps.read_text() == "column,start,end,missing_count\n"


@pytest.mark.parametrize(
    "options",
    [
        ("--freq", "D", "--tz", "Europe/Stockholm"),  # 23- and 25-hour days across DST
        ("--freq", "1h", "--origin", "2024-03-29T00:30:00Z"),  # grid shifted by origin
    ],
)
def test_gaps_csv_matches_the_report_grid(tmp_path, options):
    days = pd.date_range("2024-03-29", periods=10, freq="D", tz="Europe/Stockholm").delete([2, 3, 6])
    hours = pd.date_range("2024-03-29T00:30Z", periods=40, freq="1h").delete([4, 5, 20])
    index = days.tz_convert("UTC") if "D" in options else hours
    lines = "".join(f"{t.isoformat()},1\n" for t in index)
    path, gaps, report = (
        write(tmp_path, "timestamp,kwh\n" + lines),
        tmp_path / "gaps.csv",
        tmp_path / "r.json",
    )
    assert run("report", str(path), *options, "-o", str(report), "--gaps-csv", str(gaps))[0] == 0
    listed = [(g["start"], g["end"], g["missing_count"]) for g in json.loads(report.read_text())["gaps"]]
    rows = [line.split(",") for line in gaps.read_text().splitlines()[1:]]
    assert (
        listed
        and [(pd.Timestamp(s).isoformat(), pd.Timestamp(e).isoformat(), int(n)) for _, s, e, n in rows]
        == listed
    )


def test_fail_on_issues_ignores_explained_gaps(tmp_path):
    # P-21: a missing interval inside a --known-outage period is explained, not an issue.
    rows = ["2024-01-01T00:00Z,1,1", "2024-01-01T01:00Z,1,1", "2024-01-01T04:00Z,1,1"]  # 02:00, 03:00 missing
    path = str(write(tmp_path, "timestamp,a,b\n" + "\n".join(rows) + "\n"))
    one = ["report", path, "--value-col", "a", "--freq", "1h", "--fail-on-issues"]
    both = ["report", path, "--value-col", "a", "--value-col", "b", "--freq", "1h", "--fail-on-issues"]
    whole = ["--known-outage", "2024-01-01T02:00Z", "2024-01-01T03:00Z"]
    code, out, _ = run(*one, *whole)
    data = json.loads(out)
    assert code == 0 and data["n_missing_intervals"] == data["n_missing_explained"] == 2
    assert run(*both, *whole)[0] == 0
    # Without the outage, or with one covering only part of the gap, the exit status is 1.
    assert run(*one)[0] == 1
    assert run(*one, "--known-outage", "2024-01-01T02:00Z", "2024-01-01T02:00Z")[0] == 1
    # Flagged rows still fail even when every gap is explained.
    flagged = str(write(tmp_path, "timestamp,a\n" + "\n".join(r.rsplit(",", 1)[0] for r in rows[:2]) + "\n"
                        "2024-01-01T04:00Z,inf\n", "flagged.csv"))  # fmt: skip
    assert run("report", flagged, "--freq", "1h", "--fail-on-issues", *whole)[0] == 1


def test_fail_on_empty(tmp_path):
    # P-35: a file without data rows can fail the command; before, it always exited 0.
    empty = str(write(tmp_path, "timestamp,kwh,pv\n", "empty.csv"))
    full = str(write(tmp_path, "timestamp,kwh\n2026-01-01T00:00Z,1\n2026-01-01T01:00Z,2\n", "full.csv"))
    assert run("report", empty, "--value-col", "kwh", "--freq", "1h", "--fail-on", "empty")[0] == 1
    assert run("report", empty, "--value-col", "kwh", "--fail-on", "EMPTY")[0] == 1  # names are case-blind
    both = ["--value-col", "kwh", "--value-col", "pv", "--fail-on", "empty"]
    assert run("report", empty, *both)[0] == 1  # multi-column reports too
    assert run("report", full, "--freq", "1h", "--fail-on", "empty")[0] == 0
    # Opt-in: --fail-on-issues and the other names keep their exit status for an empty file.
    for argv in (["--fail-on-issues"], ["--fail-on", "gaps"], ["--fail-on", "ANY"]):
        assert run("report", empty, "--value-col", "kwh", "--freq", "1h", *argv)[0] == 0, argv


def test_all_value_cols(tmp_path):
    # P-38: every column but the timestamps is assessed, as with one --value-col per column.
    text = "timestamp,a,b,c\n2026-01-01T00:00Z,1,2,x\n2026-01-01T01:00Z,1,inf,y\n2026-01-01T03:00Z,1,2,z\n"
    path = str(write(tmp_path, text))
    assert "pass --value-col" in run("report", path, "--freq", "1h")[2]  # unchanged without the option
    code, out, _ = run("report", path, "--freq", "1h", "--all-value-cols")
    each = run("report", path, "--freq", "1h", "--value-col", "a", "--value-col", "b", "--value-col", "c")
    assert code == each[0] == 0 and out == each[1]
    data = json.loads(out)
    assert list(data["columns"]) == ["a", "b", "c"]
    assert data["columns"]["c"]["flag_counts"]["NON_NUMERIC"] == 3  # a text column is reported, not skipped
    # A --time-col is not a value column; one other column gives a single-column report.
    joined = str(write(tmp_path, "date,time,kwh\n2026-01-01,00:00,1\n2026-01-01,01:00,2\n", "joined.csv"))
    argv = ["report", joined, "--timestamp-col", "date", "--time-col", "time", "--assume-tz", "UTC"]
    assert json.loads(run(*argv, "--all-value-cols")[1])["n_rows"] == 2
    only = str(write(tmp_path, "timestamp\n2026-01-01T00:00Z\n", "only.csv"))
    for argv, message in [
        (["report", path, "--all-value-cols", "--value-col", "a"], "--all-value-cols and --value-col"),
        (["report", only, "--all-value-cols"], "no column besides the timestamps"),
    ]:
        code, out, err = run(*argv)
        assert code == 2 and out == "" and message in err, argv


def test_fail_on_metadata(tmp_path):
    # P-37: metadata issues can fail the command; before, they were reported and it exited 0.
    path = str(write(tmp_path, "timestamp,kw,kwh\n2026-01-01T00:00Z,1,1\n2026-01-01T01:00Z,2,2\n"))
    one = ["report", path, "--value-col", "kw", "--freq", "1h"]
    sum_of_power = ["--unit", "kW", "--aggregation", "sum", "--resolution", "1h"]
    code, out, _ = run(*one, *sum_of_power, "--fail-on", "metadata")
    assert code == 1 and json.loads(out)["metadata_issues"][0]["code"] == "SUM_OF_POWER"
    assert run(*one, *sum_of_power, "--fail-on", "METADATA")[0] == 1  # names are case-blind
    assert run(*one, "--unit", "kW", "--fail-on", "metadata")[0] == 0  # consistent metadata
    assert run(*one, "--fail-on", "metadata")[0] == 0  # no metadata at all
    # Multi-column: one column with an issue fails the command.
    both = ["report", path, "--value-col", "kw", "--value-col", "kwh", "--freq", "1h"]
    units = ["--unit", "kw=kW", "--unit", "kwh=kWh", "--aggregation", "sum", "--resolution", "1h"]
    assert run(*both, *units, "--fail-on", "metadata")[0] == 1
    # Opt-in: --fail-on-issues and the other names keep exit status 0.
    for argv in (["--fail-on-issues"], ["--fail-on", "ANY"], ["--fail-on", "gaps"]):
        assert run(*one, *sum_of_power, *argv)[0] == 0, argv


def test_min_completeness(tmp_path):
    # P-36: the caller's limit between "any gap" (--fail-on gaps) and never failing.
    rows = [f"2024-01-01T{h:02d}:00Z,1,1" for h in range(24) if h != 5]  # 05:00 missing: 23 of 24
    path = str(write(tmp_path, "timestamp,a,b\n" + "\n".join(rows) + "\n"))
    one = ["report", path, "--value-col", "a", "--freq", "1h"]
    assert run(*one, "--min-completeness", "0.95")[0] == 0  # 95.83%
    assert run(*one, "--min-completeness", "0.99")[0] == 1
    assert run(*one, "--min-completeness", "0")[0] == 0
    assert run(*one, "--min-completeness", "1")[0] == 1
    # With a known outage, completeness without it is compared, as compare does (P-24).
    outage = ["--known-outage", "2024-01-01T05:00Z", "2024-01-01T05:00Z"]
    assert run(*one, "--min-completeness", "1", *outage)[0] == 0
    # Multi-column: any column below fails; combines with --fail-on.
    both = ["report", path, "--value-col", "a", "--value-col", "b", "--freq", "1h"]
    assert run(*both, "--min-completeness", "0.99")[0] == 1
    assert run(*both, "--min-completeness", "0.9", "--fail-on", "NON_FINITE")[0] == 0
    assert run(*both, "--min-completeness", "0.9", "--fail-on", "gaps")[0] == 1
    # Not checked is refused (exit 2, no report written), not passed.
    empty = str(write(tmp_path, "timestamp,a\n", "empty.csv"))
    for argv, message in [
        (["report", path, "--value-col", "a"], "completeness is not checked; there is no step"),
        (["report", path, "--value-col", "a", "--value-col", "b"], "for column 'a'; there is no step"),
        (["report", empty, "--freq", "1h"], "there are no rows (to fail on that, use --fail-on empty)"),
        ([*one, "--known-outage", "2024-01-01T00:00Z", "2024-01-01T23:00Z"], "inside the --known-outage"),
    ]:
        code, out, err = run(*argv, "--min-completeness", "0.5")
        assert code == 2 and out == "" and message in err, argv
    for value in ("1.5", "-0.1", "most", "nan"):
        with pytest.raises(SystemExit) as exc:
            run(*one, "--min-completeness", value)
        assert exc.value.code == 2, value


def test_fail_on_chooses_the_issues(tmp_path):
    # P-23: --fail-on NAME fails only on the named issues; --fail-on-issues is unchanged.
    rows = ["2024-01-01T00:00Z,5", "2024-01-01T01:00Z,5", "2024-01-01T02:00Z,5", "2024-01-01T04:00Z,inf"]
    path = str(write(tmp_path, "timestamp,kw\n" + "\n".join(rows) + "\n"))  # stale run, a gap, inf
    base = ["report", path, "--freq", "1h", "--stale-min-run", "3"]
    for names, expected in [
        (["STALE_VALUE"], 1),
        (["non_finite"], 1),  # names are case-insensitive
        (["JUMP"], 0),  # no jump check ran, so nothing to fail on
        (["gaps"], 1),
        (["ANY"], 1),
    ]:
        argv = [a for n in names for a in ("--fail-on", n)]
        assert run(*base, *argv)[0] == expected, names
    outage = ["--known-outage", "2024-01-01T03:00Z", "2024-01-01T03:00Z"]
    assert run(*base, "--fail-on", "gaps", *outage)[0] == 1
    assert run(*base, "--fail-on", "unexplained-gaps", *outage)[0] == 0
    assert run(*base, "--fail-on", "unexplained-gaps")[0] == 1
    # Multi-column: any column with the issue fails the command.
    two = str(write(tmp_path, "timestamp,a,b\n2024-01-01T00:00Z,1,1\n2024-01-01T01:00Z,1,inf\n", "two.csv"))
    assert run("report", two, "--value-col", "a", "--value-col", "b", "--fail-on", "NON_FINITE")[0] == 1
    for argv, message in [
        (["--fail-on", "nope"], "--fail-on 'nope' is not an issue name"),
        (["--fail-on", "MISSING_INTERVAL"], "is not an issue name"),
        (["--fail-on", "gaps", "--fail-on-issues"], "--fail-on-issues and --fail-on both choose"),
    ]:
        code, out, err = run(*base, *argv)
        assert code == 2 and out == "" and message in err, (argv, err)


def test_compare_ignores_explained_gaps(tmp_path):
    # P-24: compare --fail-if-worse agrees with report --fail-on-issues about explained gaps.
    hours = ["2024-01-01T00:00Z", "2024-01-01T01:00Z", "2024-01-01T02:00Z", "2024-01-01T03:00Z"]
    full = write(tmp_path, "timestamp,kw\n" + "".join(f"{h},1\n" for h in hours), "full.csv")
    gap = write(
        tmp_path, "timestamp,kw\n" + "".join(f"{h},1\n" for h in hours if "02:00" not in h), "gap.csv"
    )
    outage = ["--known-outage", "2024-01-01T02:00Z", "2024-01-01T02:00Z"]
    for path, name in [(full, "before.json"), (gap, "after.json")]:
        assert run("report", str(path), "--freq", "1h", *outage, "-o", str(tmp_path / name))[0] == 0
    assert run("report", str(gap), "--freq", "1h", *outage, "--fail-on-issues")[0] == 0
    code, out, _ = run(
        "compare", str(tmp_path / "before.json"), str(tmp_path / "after.json"), "--fail-if-worse"
    )
    assert code == 0 and json.loads(out)["worse"] is False
    # Without the outage, the same gap is worse, as before.
    for path, name in [(full, "b2.json"), (gap, "a2.json")]:
        run("report", str(path), "--freq", "1h", "-o", str(tmp_path / name))
    assert run("compare", str(tmp_path / "b2.json"), str(tmp_path / "a2.json"), "--fail-if-worse")[0] == 1


def test_several_input_files(tmp_path):
    # P-25: several files are read alike and stacked in order, as if they were one file.
    rows = [f"2024-01-01T{h:02d}:00Z,{h}" for h in range(6)]
    whole = write(tmp_path, "timestamp,kw\n" + "\n".join(rows) + "\n", "whole.csv")
    jan = write(tmp_path, "timestamp,kw\n" + "\n".join(rows[:3]) + "\n", "jan.csv")
    feb = write(tmp_path, "timestamp,kw\n" + "\n".join(rows[3:]) + "\n", "feb.csv")
    one = run("report", str(whole), "--freq", "1h", "--flags-csv", str(tmp_path / "f1.csv"))
    two = run("report", str(jan), str(feb), "--freq", "1h", "--flags-csv", str(tmp_path / "f2.csv"))
    assert one == two and one[0] == 0  # the same report, byte for byte
    # The same flags too; only the source column (P-26) is added.
    combined = pd.read_csv(tmp_path / "f2.csv")
    assert list(combined["source"]) == [str(jan)] * 3 + [str(feb)] * 3
    pd.testing.assert_frame_equal(combined.drop(columns="source"), pd.read_csv(tmp_path / "f1.csv"))
    # A row in both files is a duplicate, as within one file.
    overlap = write(tmp_path, "timestamp,kw\n" + "\n".join(rows[2:]) + "\n", "overlap.csv")
    data = json.loads(run("report", str(jan), str(overlap), "--freq", "1h")[1])
    assert data["n_duplicate_timestamps"] == 1
    other = write(tmp_path, "timestamp,kwh\n" + rows[3] + "\n", "other.csv")
    for argv, message in [
        ([str(jan), str(other)], "other.csv has columns ['timestamp', 'kwh']; "),
        ([str(jan), "-"], "standard input ('-') cannot be combined"),
        ([str(jan), str(tmp_path / "x.parquet")], "all CSV or all Parquet"),
        ([str(jan), str(tmp_path / "missing.csv")], "file not found: "),
    ]:
        code, out, err = run("report", *argv, "--freq", "1h")
        assert code == 2 and out == "" and message in err, (argv, err)


def test_flags_csv_names_the_input_file(tmp_path):
    # P-26: with several files, each row of --flags-csv names its file; one file adds nothing.
    rows = [f"2024-01-01T{h:02d}:00Z,{h},{10 * h}" for h in range(6)]
    jan = write(tmp_path, "timestamp,a,b\n" + "\n".join(rows[:2]) + "\n", "jan.csv")
    feb = write(tmp_path, "timestamp,a,b\n" + "\n".join(rows[3:]) + "\n", "feb.csv")
    flags = tmp_path / "flags.csv"
    for columns, flag in [(["--value-col", "a"], "quality_flag"), ([], "quality_flag_a")]:
        argv = [str(jan), str(feb), "--freq", "1h", "--flags-csv", str(flags), "--insert-missing"]
        assert run("report", *argv, *(columns or ["--value-col", "a", "--value-col", "b"]))[0] == 0
        written = pd.read_csv(flags, keep_default_na=False)
        assert list(written.columns)[-1] == "source", columns
        # The row --insert-missing adds for 02:00 comes from no file.
        assert list(written["source"]) == [str(jan)] * 2 + [""] + [str(feb)] * 3
        assert list(written[flag]) == [0, 0, 65, 0, 0, 0]
    # Files out of time order: rows keep the order read, each with its own file.
    assert run("report", str(feb), str(jan), "--value-col", "a", "--flags-csv", str(flags))[0] == 0
    assert list(pd.read_csv(flags)["source"]) == [str(feb)] * 3 + [str(jan)] * 2
    assert run("report", str(jan), "--value-col", "a", "--flags-csv", str(flags))[0] == 0
    assert "source" not in pd.read_csv(flags).columns
    # A column already named source would be ambiguous: refused before anything is written.
    clash = write(tmp_path, "timestamp,source\n" + rows[0].rsplit(",", 1)[0] + "\n", "clash.csv")
    flags.unlink()
    code, out, err = run("report", str(clash), str(clash), "--flags-csv", str(flags))
    assert code == 2 and out == "" and "a column is already named so" in err and not flags.exists()


def test_several_parquet_files(tmp_path):
    pytest.importorskip("pyarrow")
    index = pd.date_range("2024-01-01", periods=6, freq="1h", tz="UTC", name="timestamp")
    frame = pd.DataFrame({"kw": range(6)}, index=index)
    frame.iloc[:3].to_parquet(tmp_path / "a.parquet")
    frame.iloc[3:].to_parquet(tmp_path / "b.parquet")
    frame.to_parquet(tmp_path / "all.parquet")
    two = run("report", str(tmp_path / "a.parquet"), str(tmp_path / "b.parquet"), "--freq", "1h")
    assert two == run("report", str(tmp_path / "all.parquet"), "--freq", "1h") and two[0] == 0
