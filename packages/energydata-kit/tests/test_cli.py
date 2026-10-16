import io
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

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
