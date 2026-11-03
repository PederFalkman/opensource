"""Offline end-to-end: actual browser fixture -> CSV -> Python engine -> browser reader.

Requires Node (bundled on GitHub-hosted CI runners) and the installed energydata-kit.
No backend or user data leaves the machine.
"""
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

from test_python_report import module as python_adapter

APP = Path(__file__).resolve().parents[1]
HTML = APP / "index.html"

EXTRACT_FIXTURE = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const text = fs.readFileSync(process.argv[1], "utf8");
const begin = text.indexOf("function syntheticGrid() {");
const end = text.indexOf("\nfunction downloadText(", begin);
if (begin < 0 || end <= begin) throw Error("missing browser fixture");
const ctx = vm.createContext({});
vm.runInContext(text.slice(begin, end), ctx);
process.stdout.write(JSON.stringify(ctx.syntheticGrid()));
"""

VERIFY_REPORT = r"""
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync(process.argv[1], "utf8");
const begin = html.indexOf("function readCanonicalReport(input) {");
const end = html.indexOf('\n$("loadPython").onclick', begin);
if (begin < 0 || end <= begin) throw Error("missing browser report validator");
const ctx = vm.createContext({});
vm.runInContext(html.slice(begin, end), ctx);
const report = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const result = ctx.readCanonicalReport(report);
if (result.report.n_missing_intervals !== 2 ||
    result.report.n_duplicate_timestamps !== 1 ||
    result.report.n_rows !== 95 ||
    result.report.schema_version !== "2") {
  throw Error("canonical report not preserved end-to-end");
}
"""

def run_node(script: str, *args: str) -> str:
    """Run a deterministic Node script with the actual Workbench HTML."""
    result = subprocess.run(
        ["node", "-e", script, *args],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return result.stdout


def test_synthetic_fixture_passes_through_python_and_browser(tmp_path: Path) -> None:
    """Validate both engine and viewer with the actual exported fixture."""
    grid = json.loads(run_node(EXTRACT_FIXTURE, str(HTML)))
    assert grid[0] == ["timestamp", "power_kw"]
    assert len(grid) == 96
    csv_file = tmp_path / "synthetic-example.csv"
    with csv_file.open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows(grid)
    result = python_adapter.analyze_csv(csv_file, timestamp="timestamp", value="power_kw")
    assert result["engine"] == "python-validated"
    report = result["report"]
    assert report["schema_version"] == "2"
    assert report["n_rows"] == 95
    assert report["n_duplicate_timestamps"] == 1
    assert report["n_missing_intervals"] == 2
    path = tmp_path / "report.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    run_node(VERIFY_REPORT, str(HTML), str(path))
