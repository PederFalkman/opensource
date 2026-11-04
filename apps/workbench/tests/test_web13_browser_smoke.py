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
