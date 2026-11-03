"""Tests for canonical report exact parity without claiming scientific validation."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workbench_parity", HERE / "compare_parity.py")
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def base() -> dict:
    """Minimal canonical representative of a quality report."""
    return {"schema_version": "2", "package_version": "0.17.dev0",
            "n_rows": 3, "completeness": 0.5, "flag_counts": {"MISSING": 1},
            "gaps": [{"start": "2026-10-25T00:00:00+00:00",
                      "end": "2026-10-25T00:00:00+00:00", "missing_count": 1}]}


def wrapped(report: dict) -> dict:
    """Known adapter wrapper, with consistent version."""
    return {"adapter_version": "energydata.workbench.python.v1",
            "engine": "python-validated", "package_version": report["package_version"],
            "report": report}


def test_exact_parity_ignores_only_adapter_envelope() -> None:
    """A report is equal whether wrapped or canonical, if its data is identical."""
    expected = base()
    assert module.changes(module.canonical(expected), module.canonical(wrapped(expected))) == []


def test_changed_numeric_and_list_fields_fail() -> None:
    """Even one changed value or one omitted field fails parity."""
    a = base()
    b = base()
    b["gaps"] = []
    b["completeness"] = 0.7
    diff = module.changes(a, b)
    assert any("completeness" in d for d in diff)
    assert any("gaps" in d for d in diff)


def test_rejects_forged_browser_preview_wrapper() -> None:
    """Preview output cannot be relabeled into an accepted Python wrapper."""
    suspect = wrapped(base())
    suspect["engine"] = "browser-preview"
    try:
        module.canonical(suspect)
    except module.ReportError:
        pass
    else:
        raise AssertionError("unsupported wrapper was accepted")


def test_real_files_parity(tmp_path: Path) -> None:
    """Both files must contain complete identical canonical field sets."""
    a, b = tmp_path / "python.json", tmp_path / "pyodide.json"
    a.write_text(json.dumps(wrapped(base())), encoding="utf-8")
    b.write_text(json.dumps(base()), encoding="utf-8")
    assert module.compare_file_paths(a, b) == []
    altered = base()
    altered["flag_counts"]["MISSING"] = 0
    b.write_text(json.dumps(altered), encoding="utf-8")
    assert module.compare_file_paths(a, b)


def test_rejects_nonstandard_nan_json_values(tmp_path: Path) -> None:
    """Never report parity success for NaN/Infinity parsed by permissive JSON."""
    a, b = tmp_path / "local.json", tmp_path / "browser.json"
    a.write_text(json.dumps(base()), encoding="utf-8")
    b.write_text('{"schema_version":"2","completeness":NaN}', encoding="utf-8")
    try:
        module.compare_file_paths(a, b)
    except module.ReportError:
        pass
    else:
        raise AssertionError("NaN constant must be rejected as invalid JSON")
