#!/usr/bin/env python3
"""Render a conservative, bounded Markdown summary of synthetic browser evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCENARIOS = frozenset({"baseline", "dst_fall", "dst_spring", "mixed_offsets"})
NEGATIVE = frozenset(
    {
        "missing_manifest_pin_no_requests",
        "mismatched_manifest_pin_no_wheel",
        "cancel_pending_manifest",
        "cancel_pending_wheel",
        "modified_wheel_sha256_rejected",
    }
)
BROWSERS = frozenset({"chromium", "firefox", "webkit"})


def validated(data: dict[str, object]) -> tuple[bool, str]:
    if data.get("evidence_schema") != "energydata.workbench.manual-browser-smoke.v1":
        return False, "Unknown evidence schema"
    if data.get("classification") != "internal-synthetic-unattested":
        return False, "Untrusted evidence classification"
    if data.get("synthetic_only") is not True:
        return False, "Synthetic-only constraint missing"
    if data.get("browser") not in BROWSERS:
        return False, "Unknown browser"
    commit = data.get("source_commit")
    if commit is not None and (
        not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None
    ):
        return False, "Invalid source commit"
    digest = data.get("wheel_sha256")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        return False, "Wheel digest absent"
    if data.get("result") != "PASS" or data.get("page_errors") != []:
        return False, "Browser smoke is not a recorded pass"
    scenarios = data.get("cases")
    if not isinstance(scenarios, list) or len(scenarios) != 4:
        return False, "Four scenarios required"
    if {item.get("scenario") for item in scenarios if isinstance(item, dict)} != SCENARIOS:
        return False, "Unexpected scenario set"
    if any(
        not isinstance(item, dict)
        or item.get("status") != "PASS"
        or item.get("parity") != "PASS"
        or item.get("export") != "PASS"
        or item.get("field_differences") != 0
        for item in scenarios
    ):
        return False, "Scenario parity or export failed"
    negative = data.get("negative_checks")
    if not isinstance(negative, list) or len(negative) != len(NEGATIVE) or set(negative) != NEGATIVE:
        return False, "Required negative checks absent"
    return True, "PASS"


def summary(data: dict[str, object]) -> str:
    ok, reason = validated(data)
    # No raw URL, host, path, customer or free-text browser error is rendered.
    lines = [
        "## WEB-13 synthetic-only real-browser smoke",
        f"- Verification: **{'PASS' if ok else 'NOT VERIFIED'}**",
        "- Evidence scope: internal, synthetic, not publisher-attested",
    ]
    if ok:
        lines.extend(
            [
                f"- Browser: `{data['browser']}` (Linux runner; not iOS Safari)",
                "- Scenarios: four independent Python parity checks and four JSON export checks",
                "- Security negatives: five completed checks",
                f"- Wheel SHA-256: `{data['wheel_sha256']}`",
                f"- Source commit: `{data['source_commit']}`"
                if data.get("source_commit") is not None
                else "- Source commit: not supplied (local test)",
                "- Manual review of runtime network hosts, signed provenance, privacy and accessibility remains required.",
            ]
        )
    else:
        lines.append(f"- Reason: {reason}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.file.stat().st_size > 256 * 1024:
            raise ValueError("Receipt exceeds size limit")
        document = json.loads(args.file.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("Expected JSON object")
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"WEB-13 evidence invalid: {exc}", file=sys.stderr)
        return 2
    print(summary(document), end="")
    return 0 if validated(document)[0] else 1


if __name__ == "__main__":
    sys.exit(main())
