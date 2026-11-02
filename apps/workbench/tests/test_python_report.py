"""Test the local WEB-02 bridge against the actual installed EnergyData Kit package."""
from pathlib import Path
import importlib.util

import pandas as pd
import pytest

ADAPTER = Path(__file__).resolve().parents[1] / "python_report.py"
spec = importlib.util.spec_from_file_location("web_python_report", ADAPTER)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def make_csv(tmp_path, times, values):
    path = tmp_path / "meter.csv"
    pd.DataFrame({"timestamp": times, "kwh": values}).to_csv(path, index=False)
    return path


def test_authoritative_quality_report(tmp_path):
    file = make_csv(tmp_path, [
        "2026-01-01T00:00:00Z", "2026-01-01T00:15:00Z",
        "2026-01-01T00:15:00Z", "2026-01-01T00:45:00Z",
    ], [2, 3, 3, ""])
    result = module.analyze_csv(file, value="kwh")
    assert result["engine"] == "python-validated"
    assert result["report"]["schema_version"] == "2"
    assert result["report"]["n_duplicate_timestamps"] >= 1
    assert result["report"]["n_missing_intervals"] >= 1
    assert result["source"] == "meter.csv"


def test_local_dst_offsets_allowed(tmp_path):
    file = make_csv(tmp_path, [
        "2026-10-25T02:00:00+02:00", "2026-10-25T02:00:00+01:00"
    ], [1, 2])
    result = module.analyze_csv(file, value="kwh", interval_minutes=60)
    assert result["report"]["n_duplicate_timestamps"] == 0


@pytest.mark.parametrize("bad", [
    ["2026-01-01 00:00", "2026-01-01 00:15"],
    ["not-a-timestamp", "2026-01-01T00:15:00Z"],
])
def test_rejects_ambiguous_or_invalid_input(tmp_path, bad):
    file = make_csv(tmp_path, bad, [1, 2])
    with pytest.raises(ValueError):
        module.analyze_csv(file, value="kwh")


def test_rejects_bad_interval(tmp_path):
    file = make_csv(tmp_path, ["2026-01-01T00:00:00Z"], [1])
    with pytest.raises(ValueError):
        module.analyze_csv(file, value="kwh", interval_minutes=0)


def test_rejects_missing_columns(tmp_path):
    file = make_csv(tmp_path, ["2026-01-01T00:00:00Z"], [1])
    with pytest.raises(ValueError):
        module.analyze_csv(file, value="unknown")
