#!/usr/bin/env python3
"""Read-only GitHub Actions browser-run discovery; never authorizes a release."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Callable

REPOSITORY = "Solid-soup/opensource"
WORKFLOW = "web09-worker-smoke.yml"
BROWSERS = ("chromium", "firefox", "webkit")
SHA_PATTERN = re.compile(r"[a-f0-9]{40}\Z")
MAX_RESPONSE = 1024 * 1024
MAX_PAGES = 5
API = "https://api.github.com"


def api_json(path: str, token: str | None = None) -> dict[str, Any]:
    """Fetch a fixed-path GitHub API JSON object with bounded response size."""
    if not path.startswith("/repos/Solid-soup/opensource/") or "?" in path and not (
        path.startswith(f"/repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs?")
    ):
        raise ValueError("Unsupported GitHub API path")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "solid-soup-rc06-read-only",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(API + path, headers=headers)
    with urllib.request.urlopen(request, timeout=15) as response:
        body = response.read(MAX_RESPONSE + 1)
    if len(body) > MAX_RESPONSE:
        raise ValueError("GitHub response exceeds size limit")
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Expected GitHub JSON object")
    return parsed


def inventory(
    sha: str,
    fetch: Callable[[str], dict[str, Any]],
    pages: int = 2,
) -> dict[str, Any]:
    """Locate candidate runs from trusted metadata without treating them as approval."""
    if SHA_PATTERN.fullmatch(sha) is None or not 1 <= pages <= MAX_PAGES:
        raise ValueError("Invalid candidate SHA or page limit")
    runs: dict[int, dict[str, Any]] = {}
    for page in range(1, pages + 1):
        payload = fetch(
            f"/repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs"
            f"?event=workflow_dispatch&per_page=100&page={page}"
        )
        batch = payload.get("workflow_runs")
        if not isinstance(batch, list):
            raise ValueError("Malformed workflow run list")
        for item in batch:
            if not isinstance(item, dict):
                raise ValueError("Malformed workflow run")
            if item.get("head_sha") != sha or item.get("event") != "workflow_dispatch":
                continue
            run_id = item.get("id")
            if type(run_id) is not int or run_id <= 0:
                raise ValueError("Malformed GitHub run ID")
            runs[run_id] = item
        if len(batch) < 100:
            break

    by_browser: dict[str, list[dict[str, Any]]] = {name: [] for name in BROWSERS}
    for run_id, item in sorted(runs.items(), reverse=True):
        if item.get("status") != "completed" or item.get("conclusion") != "success":
            continue
        response = fetch(f"/repos/{REPOSITORY}/actions/runs/{run_id}/artifacts?per_page=100")
        artifacts = response.get("artifacts")
        if not isinstance(artifacts, list) or response.get("total_count", 0) > 100:
            raise ValueError("Unbounded or malformed artifact list")
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise ValueError("Malformed artifact")
            for browser in BROWSERS:
                if artifact.get("name") != f"web13-review-{browser}-{run_id}":
                    continue
                if artifact.get("expired") is not False:
                    continue
                artifact_id = artifact.get("id")
                if type(artifact_id) is not int or artifact_id <= 0:
                    raise ValueError("Malformed artifact ID")
                by_browser[browser].append(
                    {
                        "run_id": run_id,
                        "artifact_id": artifact_id,
                        "run_url": f"https://github.com/{REPOSITORY}/actions/runs/{run_id}",
                        "artifact_name": artifact["name"],
                        "status": "RUN_METADATA_REVIEW_REQUIRED",
                    }
                )

    return {
        "schema_version": "solid-soup.rc06-browser-run-inventory.v1",
        "source_commit": sha,
        "workflow": WORKFLOW,
        "browsers": {
            browser: {
                "status": "RUN_METADATA_REVIEW_REQUIRED" if matches else "NOT_VERIFIED",
                "candidates": matches,
            }
            for browser, matches in by_browser.items()
        },
        "all_browsers_have_candidates": all(by_browser.values()),
        "publication_authorized": False,
        "customer_data_allowed": False,
        "notice": (
            "Artifact names and successful run metadata are not proof of a valid "
            "receipt or independent runtime review. Download and validate each "
            "receipt with release_candidate_matrix.py on this exact commit."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sha", required=True, help="Full 40-character candidate commit")
    parser.add_argument("--pages", type=int, default=2, help="Up to five pages of recent runs")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any browser lacks evidence")
    args = parser.parse_args(argv)
    try:
        result = inventory(
            args.sha,
            lambda path: api_json(path, os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")),
            args.pages,
        )
    except (ValueError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        print("RC-06: GitHub evidence discovery unavailable; no run verified", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if args.strict and not result["all_browsers_have_candidates"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
