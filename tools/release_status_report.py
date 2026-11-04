#!/usr/bin/env python3
"""Read-only JSON evidence for release readiness; never grants approval.

Outputs mechanical checks and explicitly unresolved human gates for a package.
No releases, tags, uploads, classifier changes or approval decisions occur.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from check_release_readiness import check_package

HUMAN_GATES = (
    ("G1", "Ownership and distribution rights"),
    ("G2", "Licence approval and packaged licence review"),
    ("G3", "Technical IP boundary sign-off"),
    ("G4", "Third-party dependency and licence review"),
    ("G5", "CI and security evidence on release commit"),
    ("G6", "Documentation and release-note sign-off"),
    ("G7", "Owner publication decision D6 for exact version"),
)


def report(root: Path, package: str) -> dict[str, object]:
    checks = check_package(root, package)
    mechanical = [{"name": check.name, "passed": check.ok, "detail": check.detail} for check in checks]
    # Never infer a human approval from a passing mechanical gate, nor repeat
    # the approval from a prior release version.
    return {
        "schema_version": "solid-soup.release-readiness.v1",
        "package": package,
        "release_authorized": False,
        "mechanical_passed": bool(checks) and all(check.ok for check in checks),
        "mechanical_checks": mechanical,
        "human_gates": [
            {"id": gate, "name": title, "status": "manual_verification_required"}
            for gate, title in HUMAN_GATES
        ],
        "notice": (
            "Read-only preparation report. Owner sign-off and strict checks "
            "on the exact release commit are required. No publication approved."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--package", default="energydata-kit")
    parser.add_argument("--strict", action="store_true", help="exit 1 if mechanical checks fail")
    args = parser.parse_args(argv)
    if not args.package or "/" in args.package or "\\" in args.package or args.package in {".", ".."}:
        parser.error("Package must be a single directory name")
    payload = report(args.root, args.package)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if args.strict and not payload["mechanical_passed"] else 0


if __name__ == "__main__":
    sys.exit(main())
