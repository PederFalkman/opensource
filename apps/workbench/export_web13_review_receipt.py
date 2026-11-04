#!/usr/bin/env python3
"""Export a minimal, validated WEB-13 synthetic receipt for manual review.

The raw browser receipt stays on the ephemeral runner. Only strictly
allowlisted fields are written to the short-lived review artifact.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

MAX_BYTES = 256 * 1024
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
BROWSERS = ("chromium", "firefox", "webkit")


def validator():
    path = Path(__file__).with_name("render_web13_evidence_summary.py")
    spec = importlib.util.spec_from_file_location("rc02_web13_validator", path)
    if spec is None or spec.loader is None:
        raise ValueError("WEB-13 validator unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validated


def export_receipt(
    data: dict[str, object], commit: str, browser: str, run_id: str | None = None
) -> dict[str, object]:
    if COMMIT.fullmatch(commit) is None or browser not in BROWSERS:
        raise ValueError("Invalid expected run identity")
    if run_id is not None and (not run_id.isascii() or not run_id.isdecimal() or int(run_id) <= 0):
        raise ValueError("Invalid GitHub run ID")
    ok, reason = validator()(data, commit, browser)
    if not ok:
        raise ValueError(f"WEB-13 receipt is not a verified synthetic pass: {reason}")
    cases = data["cases"]
    assert isinstance(cases, list)
    negatives = data["negative_checks"]
    assert isinstance(negatives, list)
    # The result remains in the exact schema consumed by RC-01; only the
    # fields required by that validator are retained. No hosts, browser
    # errors, raw CSV, arbitrary text or runtime data may enter the artifact.
    return {
        "evidence_schema": "energydata.workbench.manual-browser-smoke.v1",
        "classification": "internal-synthetic-unattested",
        "synthetic_only": True,
        "browser": browser,
        "source_commit": commit,
        **({"github_run_id": run_id} if run_id is not None else {}),
        "wheel_sha256": data["wheel_sha256"],
        "result": "PASS",
        "page_errors": [],
        "cases": [
            {
                "scenario": item["scenario"],
                "status": "PASS",
                "parity": "PASS",
                "export": "PASS",
                "field_differences": 0,
            }
            for item in cases
        ],
        "negative_checks": sorted(negatives),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-browser", choices=BROWSERS, required=True)
    parser.add_argument("--run-id", required=True, help="GitHub Actions run ID")
    args = parser.parse_args(argv)
    try:
        if args.input.stat().st_size > MAX_BYTES:
            raise ValueError("Receipt exceeds size limit")
        data = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Receipt must be a JSON object")
        result = export_receipt(data, args.expected_commit, args.expected_browser, args.run_id)
        serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if len(serialized.encode("utf-8")) > 8192:
            raise ValueError("Sanitized receipt unexpectedly large")
        args.output.write_text(serialized, encoding="utf-8")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        # Avoid displaying raw input contents in GitHub job logs.
        print(f"WEB-13 review receipt not exported: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
