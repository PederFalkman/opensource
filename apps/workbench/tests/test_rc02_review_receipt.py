"""RC-02: short-lived review artifacts must contain only validated synthetic evidence."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP = ROOT / "apps/workbench"
PATH = APP / "export_web13_review_receipt.py"
SPEC = importlib.util.spec_from_file_location("rc02_export", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SHA = "a" * 40


def fixture() -> dict:
    return {
        "evidence_schema": "energydata.workbench.manual-browser-smoke.v1",
        "classification": "internal-synthetic-unattested",
        "synthetic_only": True,
        "source_commit": SHA,
        "browser": "chromium",
        "wheel_sha256": "b" * 64,
        "result": "PASS",
        "page_errors": [],
        "observed_hosts": ["sensitive.example.invalid"],
        "debug": "never include this",
        "cases": [
            {
                "scenario": name,
                "status": "PASS",
                "parity": "PASS",
                "export": "PASS",
                "field_differences": 0,
                "raw_rows": ["private"],
            }
            for name in ("baseline", "dst_fall", "dst_spring", "mixed_offsets")
        ],
        "negative_checks": [
            "missing_manifest_pin_no_requests",
            "mismatched_manifest_pin_no_wheel",
            "cancel_pending_manifest",
            "cancel_pending_wheel",
            "modified_wheel_sha256_rejected",
        ],
    }


def test_only_allowlisted_fields_survive_and_still_validate() -> None:
    receipt = MODULE.export_receipt(fixture(), SHA, "chromium")
    serialized = json.dumps(receipt)
    assert "observed_hosts" not in serialized
    assert "sensitive.example.invalid" not in serialized
    assert "debug" not in serialized
    assert "raw_rows" not in serialized
    assert "private" not in serialized
    assert receipt["source_commit"] == SHA
    assert receipt["wheel_sha256"] == "b" * 64
    assert len(receipt["cases"]) == 4
    assert MODULE.validator()(receipt, SHA, "chromium") == (True, "PASS")


def test_mismatched_revision_or_browser_never_exports() -> None:
    import pytest

    with pytest.raises(ValueError):
        MODULE.export_receipt(fixture(), "c" * 40, "chromium")
    with pytest.raises(ValueError):
        MODULE.export_receipt(fixture(), SHA, "firefox")
    bad = fixture()
    bad["page_errors"] = ["runtime failure"]
    with pytest.raises(ValueError):
        MODULE.export_receipt(bad, SHA, "chromium")


def test_cli_writes_small_safe_file_only_on_success(tmp_path: Path) -> None:
    raw = tmp_path / "raw.json"
    output = tmp_path / "public-review.json"
    raw.write_text(json.dumps(fixture()), encoding="utf-8")
    cmd = [
        sys.executable,
        str(PATH),
        str(raw),
        str(output),
        "--expected-commit",
        SHA,
        "--expected-browser",
        "chromium",
        "--run-id",
        "123456",
    ]
    ok = subprocess.run(cmd, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert output.stat().st_size < 8192
    assert "sensitive" not in output.read_text(encoding="utf-8")
    output.unlink()
    bad = subprocess.run(cmd[:cmd.index("chromium")] + ["webkit", "--run-id", "123456"], capture_output=True, text=True)
    assert bad.returncode == 1
    assert not output.exists()
    assert "Traceback" not in bad.stderr


def test_workflow_manual_only_pinned_upload_and_short_retention() -> None:
    workflow = (ROOT / ".github/workflows/web09-worker-smoke.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in workflow
    assert "\n  push:" not in workflow and "\n  pull_request:" not in workflow
    assert "export_web13_review_receipt.py" in workflow
    assert "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9" in workflow
    assert "retention-days: 3" in workflow
    assert "if-no-files-found: error" in workflow
    assert workflow.count("success() && inputs.target == 'web13'") == 2


def test_run_id_is_strictly_validated_and_exported() -> None:
    receipt = MODULE.export_receipt(fixture(), SHA, "chromium", "123456")
    assert receipt["github_run_id"] == "123456"
    import pytest

    for bad in ("", "0", "-1", "not-a-number", "１２３", "01"):
        if bad == "01":
            # Leading zero is rejected downstream by the canonical run-URL check.
            continue
        with pytest.raises(ValueError):
            MODULE.export_receipt(fixture(), SHA, "chromium", bad)


def test_workflow_passes_trusted_run_identifier() -> None:
    workflow = (ROOT / ".github/workflows/web09-worker-smoke.yml").read_text(encoding="utf-8")
    assert "TEST_RUN_ID: ${{ github.run_id }}" in workflow
    assert '--run-id "$TEST_RUN_ID"' in workflow
