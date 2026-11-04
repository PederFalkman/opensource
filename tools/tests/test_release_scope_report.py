"""Offline tests for conservative release scope classification."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "tools" / "release_scope_report.py"
SPEC = importlib.util.spec_from_file_location("release_scope_report", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_workbench_does_not_count_as_package_change() -> None:
    result = MODULE.classify(["apps/workbench/web13_synthetic_review.html", "docs/README.md"])
    assert result["workbench_change_detected"] is True
    assert result["python_implementation_change_detected"] is False
    assert result["python_source_review_required"] is False
    assert result["python_package_files"] == []


def test_version_module_is_disclosed_not_assumed_to_be_version_only() -> None:
    result = MODULE.classify(
        [
            "packages/energydata-kit/src/energydata_kit/__init__.py",
            "packages/energydata-kit/pyproject.toml",
        ]
    )
    assert result["python_source_files"] == ["packages/energydata-kit/src/energydata_kit/__init__.py"]
    assert result["python_implementation_change_detected"] is False
    assert result["python_source_review_required"] is True
    assert "__init__.py" in result["review_notice"]
    assert result["python_package_metadata_or_docs"] == ["packages/energydata-kit/pyproject.toml"]


def test_implementation_change_is_detected_and_paths_deduplicated() -> None:
    result = MODULE.classify(
        [
            "packages/energydata-kit/src/energydata_kit/report.py",
            "packages/energydata-kit/src/energydata_kit/report.py",
            "apps/workbench/index.html",
        ]
    )
    assert result["total_changed_files"] == 2
    assert result["python_implementation_change_detected"] is True
    assert result["python_source_review_required"] is True


def test_ref_failure_is_not_silently_reported_as_empty_diff(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--root",
            str(tmp_path),
            "--base",
            "missing-base",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Cannot establish exact release diff" in result.stderr


def test_actual_report_never_signals_publication_approval() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--root",
            str(ROOT),
            "--base",
            "HEAD",
            "--head",
            "HEAD",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["publication_approved"] is False
    assert payload["scope"]["total_changed_files"] == 0
