import io
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

import energydata_kit as ek
from energydata_kit import __version__
from energydata_kit.cli import main

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
        (["--unit", "kW"], "--unit describes one column"),
        (["--value-col", "a"], "only once"),
    ]:
        code, out, err = run(*args, *extra)
        assert code == 2 and out == "" and message in err


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
    assert "  completeness: not checked (no --freq or --resolution)" in out.splitlines()


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
        "  gaps resolved: 1, new: 0",
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


def test_usage_errors_and_version(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["report"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0 and __version__ in capsys.readouterr().out


def test_python_dash_m(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "energydata_kit", "report", str(write(tmp_path, CLEAN)), "--freq", "15min"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and json.loads(result.stdout)["n_rows"] == 8
