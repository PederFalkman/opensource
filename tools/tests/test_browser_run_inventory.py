"""RC-06: GitHub run discovery remains read-only and fail-closed."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "tools/browser_run_inventory.py"
SPEC = importlib.util.spec_from_file_location("browser_run_inventory", PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

SHA = "a" * 40
BASE = "/repos/Solid-soup/opensource"


def stub_fetch(
    runs: list[dict], artifacts: dict[int, list[dict]], total: dict[int, int] | None = None
):
    def fetch(path: str) -> dict:
        if "/workflows/" in path:
            return {"workflow_runs": runs}
        for run_id, entries in artifacts.items():
            if path == f"{BASE}/actions/runs/{run_id}/artifacts?per_page=100":
                return {"artifacts": entries, "total_count": (total or {}).get(run_id, len(entries))}
        raise AssertionError(f"Unexpected path: {path}")
    return fetch


def run(run_id: int, *, sha: str = SHA, status: str = "completed", conclusion: str = "success") -> dict:
    return {"id": run_id, "head_sha": sha, "event": "workflow_dispatch",
            "status": status, "conclusion": conclusion}


def artifact(browser: str, run_id: int, *, expired: bool = False) -> dict:
    return {"id": run_id + 100, "name": f"web13-review-{browser}-{run_id}", "expired": expired}


def test_all_three_candidates_are_only_metadata_not_approval() -> None:
    runs = [run(101), run(102), run(103)]
    artifacts = {101: [artifact("chromium", 101)],
                 102: [artifact("firefox", 102)],
                 103: [artifact("webkit", 103)]}
    result = MODULE.inventory(SHA, stub_fetch(runs, artifacts))
    assert result["all_browsers_have_candidates"] is True
    assert result["publication_authorized"] is False
    assert result["customer_data_allowed"] is False
    assert all(value["status"] == "RUN_METADATA_REVIEW_REQUIRED"
               for value in result["browsers"].values())
    assert result["browsers"]["chromium"]["candidates"][0]["run_id"] == 101


def test_wrong_sha_failed_and_expired_artifacts_are_not_evidence() -> None:
    runs = [run(101, sha="b" * 40), run(102, conclusion="failure"),
            run(103), run(104, status="queued")]
    artifacts = {103: [artifact("webkit", 103, expired=True)]}
    result = MODULE.inventory(SHA, stub_fetch(runs, artifacts))
    assert not result["all_browsers_have_candidates"]
    assert all(value["status"] == "NOT_VERIFIED"
               for value in result["browsers"].values())


@pytest.mark.parametrize("sha", ["x" * 40, "abc", "A" * 40])
def test_invalid_sha_rejected(sha: str) -> None:
    with pytest.raises(ValueError):
        MODULE.inventory(sha, stub_fetch([], {}))


def test_unbounded_artifact_list_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unbounded"):
        MODULE.inventory(SHA, stub_fetch([run(123)], {123: [artifact("chromium", 123)]}, {123: 101}))


def test_wrong_artifact_name_and_empty_sets_not_verified() -> None:
    data = stub_fetch([run(123)], {123: [
        {"id": 1, "name": "web13-review-firefox-456", "expired": False}
    ]})
    result = MODULE.inventory(SHA, data)
    assert all(x["status"] == "NOT_VERIFIED" for x in result["browsers"].values())


def test_no_discovery_can_grant_release() -> None:
    result = MODULE.inventory(SHA, stub_fetch([], {}))
    assert result["publication_authorized"] is False
    assert result["all_browsers_have_candidates"] is False
    assert json.dumps(result).find("NO_GO") < 0  # reports metadata, not an approval decision


def test_invalid_page_limit_rejected() -> None:
    with pytest.raises(ValueError):
        MODULE.inventory(SHA, stub_fetch([], {}), pages=6)


def test_rejects_untrusted_host_path_before_request() -> None:
    with pytest.raises(ValueError):
        MODULE.api_json("/repos/other/org/actions/runs")
