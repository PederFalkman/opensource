"""Offline validation of synthetic browser receipt and fail-closed summary."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
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


def test_valid_source_commit_is_displayed_and_malformed_commit_is_rejected() -> None:
    result = fixture()
    result["source_commit"] = "1" * 40
    assert MODULE.validated(result)[0] is True
    assert "Source commit: " in MODULE.summary(result)
    result["source_commit"] = "<untrusted>"
    assert MODULE.validated(result)[0] is False
    assert "<untrusted>" not in MODULE.summary(result)


def test_malformed_nested_fields_never_crash_or_generate_pass() -> None:
    malformed = [
        {"browser": {"name": "chromium"}},
        {"browser": ["chromium"]},
        {"cases": [{"scenario": []}] * 4},
        {"cases": [{"scenario": {"unexpected": 1}}] * 4},
        {"negative_checks": [{"unexpected": 1}] * 5},
        {"negative_checks": [["nested"]] * 5},
        {"cases": [42, 42, 42, 42]},
    ]
    for update in malformed:
        receipt = fixture()
        receipt.update(update)
        assert MODULE.validated(receipt)[0] is False
        assert "Verification: **NOT VERIFIED**" in MODULE.summary(receipt)


def test_boolean_difference_counter_is_rejected() -> None:
    receipt = fixture()
    receipt["cases"][0]["field_differences"] = False
    assert MODULE.validated(receipt)[0] is False


def test_cli_malformed_nested_json_fails_cleanly(tmp_path: Path) -> None:
    receipt = fixture()
    receipt["negative_checks"][0] = {"not": "a check"}
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(MODULE_PATH), str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "NOT VERIFIED" in result.stdout
    assert "Traceback" not in result.stderr


def test_receipt_must_match_exact_workflow_commit_and_browser() -> None:
    receipt = fixture()
    receipt["source_commit"] = "a" * 40
    assert MODULE.validated(receipt, "a" * 40, "chromium")[0] is True
    assert MODULE.validated(receipt, "b" * 40, "chromium")[0] is False
    assert MODULE.validated(receipt, "a" * 40, "firefox")[0] is False
    assert MODULE.validated(receipt, "not-a-sha", "chromium")[0] is False
    assert MODULE.validated(fixture(), "a" * 40, "chromium")[0] is False
    assert "NOT VERIFIED" in MODULE.summary(receipt, "a" * 40, "webkit")


def test_cli_workflow_binding_fail_closed(tmp_path: Path) -> None:
    import json
    import subprocess
    import sys

    path = tmp_path / "synthetic-receipt.json"
    receipt = fixture()
    receipt["source_commit"] = "a" * 40
    path.write_text(json.dumps(receipt), encoding="utf-8")
    command = [
        sys.executable,
        str(MODULE_PATH),
        str(path),
        "--expected-commit",
        "a" * 40,
        "--expected-browser",
        "chromium",
    ]
    passed = subprocess.run(command, capture_output=True, text=True)
    assert passed.returncode == 0
    assert "Verification: **PASS**" in passed.stdout
    wrong = subprocess.run(command[:-1] + ["firefox"], capture_output=True, text=True)
    assert wrong.returncode == 1
    assert "NOT VERIFIED" in wrong.stdout


def test_manual_workflow_checks_exact_revision() -> None:
    root = MODULE_PATH.parents[2]
    workflow = (root / ".github/workflows/web09-worker-smoke.yml").read_text(encoding="utf-8")
    assert "TEST_COMMIT: ${{ github.sha }}" in workflow
    assert '--expected-commit "$TEST_COMMIT" --expected-browser "$TEST_BROWSER"' in workflow
