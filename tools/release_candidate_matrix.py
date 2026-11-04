#!/usr/bin/env python3
"""Read-only release-candidate evidence matrix; never grants publication approval.

Browser receipts must refer to the exact checked-out commit. GitHub run URLs
are reviewer-supplied references, not independent API verification.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

from release_status_report import report as package_report

BROWSERS = ("chromium", "firefox", "webkit")
RUN_URL = re.compile(r"https://github\.com/Solid-soup/opensource/actions/runs/[1-9][0-9]*\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_RECEIPT_BYTES = 256 * 1024


def load_validator(root: Path):
    path = root / "apps" / "workbench" / "render_web13_evidence_summary.py"
    spec = importlib.util.spec_from_file_location("rc01_web13_validator", path)
    if spec is None or spec.loader is None:
        raise ValueError("WEB-13 evidence validator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validated


def head_sha(root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    sha = proc.stdout.strip()
    if SHA.fullmatch(sha) is None:
        raise ValueError("Unable to resolve full commit SHA")
    return sha


def browser_matrix(
    expected_sha: str,
    receipts: dict[str, Path],
    run_urls: dict[str, str],
    validator,
) -> dict[str, dict[str, str | None]]:
    results = {}
    for browser in BROWSERS:
        result = {"status": "NOT_VERIFIED", "run_url": None, "reason": "No receipt supplied"}
        path = receipts.get(browser)
        if path is not None:
            try:
                if path.stat().st_size > MAX_RECEIPT_BYTES:
                    raise ValueError("Receipt exceeds size limit")
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("Receipt must be a JSON object")
                ok, reason = validator(data, expected_sha, browser)
                if not ok:
                    result["reason"] = reason
                else:
                    link = run_urls.get(browser)
                    if link is None:
                        result["reason"] = "No reviewer-supplied GitHub run URL"
                    elif RUN_URL.fullmatch(link) is None:
                        result["reason"] = "Invalid GitHub run URL"
                    else:
                        result = {
                            "status": "RECEIPT_VALID_REVIEW_REQUIRED",
                            "run_url": link,
                            "reason": "Receipt and run URL not independently verified via GitHub API",
                        }
            except (OSError, UnicodeError, ValueError):
                result["reason"] = "Receipt unreadable or malformed"
        results[browser] = result
    return results


def parse_pairs(pairs: list[str], flag: str) -> dict[str, str]:
    values = {}
    for pair in pairs:
        browser, sep, value = pair.partition("=")
        if not sep or browser not in BROWSERS or not value or browser in values:
            raise ValueError(f"{flag}: expected unique browser=value")
        values[browser] = value
    return values


def candidate(root: Path, receipts: dict[str, Path], urls: dict[str, str]) -> dict[str, object]:
    sha = head_sha(root)
    package = package_report(root, "energydata-kit")
    browsers = browser_matrix(sha, receipts, urls, load_validator(root))
    complete = all(item["status"] == "RECEIPT_VALID_REVIEW_REQUIRED" for item in browsers.values())
    blockers = [check["name"] for check in package["mechanical_checks"] if not check["passed"]]
    blockers += [f"browser:{name}" for name, value in browsers.items() if value["status"] == "NOT_VERIFIED"]
    blockers.extend(("human:G1-G7", "workbench:security-privacy-accessibility-runtime-review"))
    return {
        "schema_version": "solid-soup.release-candidate.v1",
        "source_commit": sha,
        "package": {
            "mechanical_passed": package["mechanical_passed"],
            "failed_checks": [check["name"] for check in package["mechanical_checks"] if not check["passed"]],
            "human_gates": package["human_gates"],
            "publication_authorized": False,
        },
        "workbench": {
            "synthetic_browser_matrix": browsers,
            "all_receipts_present_for_review": complete,
            "customer_data_allowed": False,
            "production_authorized": False,
        },
        "go_no_go": "NO_GO",
        "blockers": blockers,
        "notice": "Read-only evidence inventory; supplied run URLs are not GitHub-verified approvals.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--receipt", action="append", default=[], metavar="BROWSER=PATH")
    parser.add_argument("--run-url", action="append", default=[], metavar="BROWSER=URL")
    parser.add_argument("--require-browser-matrix", action="store_true")
    args = parser.parse_args(argv)
    try:
        receipts = {name: Path(path) for name, path in parse_pairs(args.receipt, "--receipt").items()}
        urls = parse_pairs(args.run_url, "--run-url")
        if any(browser not in receipts for browser in urls):
            raise ValueError("Run URL without matching browser receipt")
        result = candidate(args.root, receipts, urls)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Release candidate evidence unavailable: {exc}\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_browser_matrix and not result["workbench"]["all_receipts_present_for_review"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
