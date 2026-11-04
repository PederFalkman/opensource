"""Fast offline contract tests for optional WEB-13 Playwright smoke."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "web13_browser_smoke.py"
SPEC = importlib.util.spec_from_file_location("web13_browser_smoke", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_candidate_manifest_is_review_only(tmp_path: Path) -> None:
    wheel = tmp_path / "energydata_kit-0.17.0.dev0-py3-none-any.whl"
    payload = b"test-only wheel bytes; not an installable wheel"
    wheel.write_bytes(payload)
    result = MODULE.manifest_for(wheel)
    assert result["status"] == "candidate-not-approved"
    assert result["purpose"] == "review-only-static-asset-inventory"
    assert result["total_bytes"] == len(payload)
    assert result["assets"] == [{
        "path": wheel.name, "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }]


@pytest.mark.parametrize("browser", ("chrome", "safari", "", "../webkit"))
def test_unsupported_engine_fails_before_playwright(browser: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported browser"):
        MODULE.run(tmp_path / "missing.whl", browser, 1000)


def test_missing_wheel_fails_before_playwright(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="wheel required"):
        MODULE.run(tmp_path / "missing.whl", "chromium", 1000)


def test_staged_assets_are_only_existing_review_components() -> None:
    assert set(MODULE.ASSETS) == {
        "web13_synthetic_review.html", "web13_pilot_state.mjs",
        "web14_evidence.mjs", "web09_candidate_loader.mjs",
        "web09_engine_worker.mjs",
    }
    assert len(MODULE.SCENARIOS) == 4


@pytest.mark.parametrize("scenario,expected_count", [
    ("baseline", 96), ("dst_fall", 6), ("dst_spring", 5), ("mixed_offsets", 5),
])
def test_independent_reference_fixture_shape(scenario: str, expected_count: int) -> None:
    rows = MODULE.reference_rows(scenario)
    assert len(rows) == expected_count
    assert rows[0] == ["timestamp", "power_kw"]
    assert all(len(row) == 2 for row in rows)
    assert all(row[0].endswith(("Z", "+01:00", "+02:00")) for row in rows[1:])


def test_baseline_fixture_has_gap_duplicate_and_missing_value() -> None:
    rows = MODULE.reference_rows("baseline")
    timestamps = [row[0] for row in rows[1:]]
    assert len(timestamps) > len(set(timestamps))
    assert any(row[1] == "" for row in rows[1:])
    assert "2026-10-19T07:00:00.000Z" not in timestamps
    assert "2026-10-19T07:15:00.000Z" not in timestamps


def test_fixtures_cover_distinct_dst_instants_and_reject_unknown_scenarios() -> None:
    fall = MODULE.reference_rows("dst_fall")
    assert any("+02:00" in row[0] for row in fall[1:])
    assert any("+01:00" in row[0] for row in fall[1:])
    with pytest.raises(ValueError, match="Unsupported synthetic scenario"):
        MODULE.reference_rows("user-file")


def test_browser_harness_requires_synthetic_receipt_and_negative_pin_checks() -> None:
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "reviewed_pin = hashlib.sha256(manifest_bytes).hexdigest()" in text
    assert 'page.locator("#reviewPin").fill(reviewed_pin)' in text
    assert "Candidate asset requested before review pin supplied" in text
    assert "Incorrect review pin was not rejected" in text


def test_web20_wheel_cancel_and_retry_are_covered_by_manual_smoke() -> None:
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert 'page.route("**/candidate-assets/*.whl", hold_wheel)' in source
    assert 'page.unroute("**/candidate-assets/*.whl", hold_wheel)' in source
    assert "Wheel request was not intercepted" in source
    assert "Export enabled after wheel cancellation" in source
    assert "Run disabled after wheel cancellation" in source
    assert "Late wheel response resurrected cancelled run" in source
    assert source.index('page.unroute("**/candidate-assets/*.whl", hold_wheel)') < source.index("for scenario in SCENARIOS:")
