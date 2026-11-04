"""Guard against accidental release approval in readiness JSON output."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "release_status_report.py"


def test_report_is_read_only_and_never_approves_publication() -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "solid-soup.release-readiness.v1"
    assert payload["package"] == "energydata-kit"
    assert payload["release_authorized"] is False
    assert len(payload["human_gates"]) == 7
    assert {gate["status"] for gate in payload["human_gates"]} == {"manual_verification_required"}
    assert all({"name", "passed", "detail"} <= set(c) for c in payload["mechanical_checks"])


def test_strict_exit_tracks_mechanical_state_only() -> None:
    normal = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    expected = json.loads(normal.stdout)["mechanical_passed"]
    strict = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(ROOT), "--strict"],
        capture_output=True,
        text=True,
    )
    assert strict.returncode == (0 if expected else 1)


def test_missing_package_fails_strictly_and_never_approves() -> None:
    result = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(ROOT), "--package", "does-not-exist", "--strict"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["release_authorized"] is False
    assert payload["mechanical_passed"] is False
