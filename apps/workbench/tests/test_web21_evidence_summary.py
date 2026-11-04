"""Offline validation of synthetic browser receipt and fail-closed summary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "render_web13_evidence_summary.py"
SPEC = importlib.util.spec_from_file_location("web21_summary", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture() -> dict:
    return {
        "evidence_schema": "energydata.workbench.manual-browser-smoke.v1",
        "classification": "internal-synthetic-unattested",
        "synthetic_only": True,
        "browser": "chromium",
        "wheel_sha256": "a" * 64,
        "result": "PASS",
        "page_errors": [],
        "cases": [
            {
                "scenario": scenario,
                "status": "PASS",
                "parity": "PASS",
                "export": "PASS",
                "field_differences": 0,
            }
            for scenario in sorted(MODULE.SCENARIOS)
        ],
        "negative_checks": sorted(MODULE.NEGATIVE),
    }


def test_complete_synthetic_receipt_is_valid() -> None:
    result = fixture()
    assert MODULE.validated(result) == (True, "PASS")
    output = MODULE.summary(result)
    assert "Verification: **PASS**" in output
    assert "not publisher-attested" in output


def test_missing_or_failed_checks_fail_closed() -> None:
    result = fixture()
    result["negative_checks"] = result["negative_checks"][:-1]
    assert MODULE.validated(result)[0] is False
    result = fixture()
    result["cases"][0]["field_differences"] = 1
    assert MODULE.validated(result)[0] is False
    result = fixture()
    result["page_errors"] = ["sensitive-error"]
    assert MODULE.validated(result)[0] is False
    assert "sensitive-error" not in MODULE.summary(result)


def test_refuse_unsupported_evidence_and_browser() -> None:
    result = fixture()
    result["classification"] = "production"
    assert MODULE.validated(result)[0] is False
    result = fixture()
    result["browser"] = "ios-safari"
    assert MODULE.validated(result)[0] is False
    result = fixture()
    result["wheel_sha256"] = "invalid"
    assert MODULE.validated(result)[0] is False


def test_manual_workflow_only_and_evidence_file_are_wired() -> None:
    root = MODULE_PATH.parents[2]
    workflow = (root / ".github/workflows/web09-worker-smoke.yml").read_text(encoding="utf-8")
    smoke = (root / "apps/workbench/web13_browser_smoke.py").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "  push:" not in workflow and "  pull_request:" not in workflow
    assert "--evidence-file" in workflow
    assert "render_web13_evidence_summary.py" in workflow
    assert "evidence_file.write_text(document, encoding=" in smoke
