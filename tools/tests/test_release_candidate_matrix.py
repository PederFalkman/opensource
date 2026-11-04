"""Regression tests for read-only release candidate evidence matrix."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
PATH = TOOLS / "release_candidate_matrix.py"
SPEC = importlib.util.spec_from_file_location("release_candidate_matrix", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
SHA = "a" * 40
URL = "https://github.com/Solid-soup/opensource/actions/runs/123456"


def make_receipt(path: Path, browser: str, commit: str = SHA) -> None:
    path.write_text(json.dumps({"browser": browser, "source_commit": commit}), encoding="utf-8")


def validator(data: dict, sha: str, browser: str) -> tuple[bool, str]:
    if data.get("source_commit") != sha or data.get("browser") != browser:
        return False, "Run identity mismatch"
    return True, "PASS"


def test_no_receipts_means_no_verified_browser() -> None:
    matrix = MODULE.browser_matrix(SHA, {}, {}, validator)
    assert set(matrix) == {"chromium", "firefox", "webkit"}
    assert all(x["status"] == "NOT_VERIFIED" for x in matrix.values())


def test_full_matrix_requires_receipts_and_run_links(tmp_path: Path) -> None:
    paths = {browser: tmp_path / (browser + ".json") for browser in MODULE.BROWSERS}
    for browser, path in paths.items():
        make_receipt(path, browser)
    links = {browser: URL for browser in MODULE.BROWSERS}
    result = MODULE.browser_matrix(SHA, paths, links, validator)
    assert all(item["status"] == "RECEIPT_VALID_REVIEW_REQUIRED" for item in result.values())
    del links["firefox"]
    result = MODULE.browser_matrix(SHA, paths, links, validator)
    assert result["firefox"]["status"] == "NOT_VERIFIED"


def test_mismatched_commit_or_browser_rejected(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    make_receipt(path, "webkit", "b" * 40)
    result = MODULE.browser_matrix(SHA, {"chromium": path}, {"chromium": URL}, validator)
    assert result["chromium"]["status"] == "NOT_VERIFIED"


@pytest.mark.parametrize("payload", ["[]", "not-json", '{"cases": {}', "42"])
def test_malformed_json_is_not_accepted(tmp_path: Path, payload: str) -> None:
    path = tmp_path / "receipt.json"
    path.write_text(payload, encoding="utf-8")
    result = MODULE.browser_matrix(SHA, {"chromium": path}, {"chromium": URL}, validator)
    assert result["chromium"]["status"] == "NOT_VERIFIED"


def test_hostile_link_and_duplicate_inputs_refused(tmp_path: Path) -> None:
    path = tmp_path / "receipt.json"
    make_receipt(path, "chromium")
    result = MODULE.browser_matrix(
        SHA, {"chromium": path},
        {"chromium": "https://github.com.evil.test/Solid-soup/opensource/actions/runs/1"},
        validator,
    )
    assert result["chromium"]["status"] == "NOT_VERIFIED"
    with pytest.raises(ValueError):
        MODULE.parse_pairs(["chromium=a", "chromium=b"], "--receipt")
    with pytest.raises(ValueError):
        MODULE.parse_pairs(["unknown=x"], "--receipt")


def test_live_repository_report_never_auto_approves_release() -> None:
    result = subprocess.run(
        [sys.executable, str(PATH), "--root", str(ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "solid-soup.release-candidate.v1"
    assert payload["go_no_go"] == "NO_GO"
    assert payload["package"]["publication_authorized"] is False
    assert payload["workbench"]["customer_data_allowed"] is False
    assert payload["workbench"]["all_receipts_present_for_review"] is False


def test_strict_matrix_option_exits_nonzero_without_receipts() -> None:
    result = subprocess.run(
        [sys.executable, str(PATH), "--root", str(ROOT), "--require-browser-matrix"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["go_no_go"] == "NO_GO"
