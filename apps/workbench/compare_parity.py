"""Compare two *canonical* EnergyData Kit quality reports field by field.

Usage:
  python apps/workbench/compare_parity.py local.json browser.json

Inputs may be schema-v2 reports or known adapter wrappers. No data is uploaded.
A matching result is *numerical/serialization parity*, not data provenance,
authenticity, engineering assurance or browser-runtime validation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class ReportError(ValueError):
    """The supplied JSON is not a supported report."""


def canonical(report: object) -> dict[str, Any]:
    """Extract the canonical v2 report, rejecting unsupported input shapes."""
    if not isinstance(report, dict):
        raise ReportError("Expected a JSON object")
    if "report" in report:
        if report.get("engine") != "python-validated" or report.get("adapter_version") != "energydata.workbench.python.v1":
            raise ReportError("Unrecognized adapter")
        inner = report["report"]
        if not isinstance(inner, dict) or inner.get("package_version") != report.get("package_version"):
            raise ReportError("Adapter version mismatch")
        report = inner
    if report.get("schema_version") != "2":
        raise ReportError("Expected canonical schema version 2")
    return report


def changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Return exact semantic differences without silently ignoring fields."""
    differences: list[str] = []

    def visit(a: Any, b: Any, path: str) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                label = f"{path}.{key}"
                if key not in a or key not in b:
                    differences.append(f"{label}: field missing in one report")
                else:
                    visit(a[key], b[key], label)
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                differences.append(f"{path}: list lengths differ ({len(a)} vs {len(b)})")
            else:
                for n, (left, right) in enumerate(zip(a, b)):
                    visit(left, right, f"{path}[{n}]")
        elif isinstance(a, bool) != isinstance(b, bool) or a != b:
            differences.append(f"{path}: mismatch")

    visit(before, after, "report")
    return differences


def compare_file_paths(local: Path, browser: Path) -> list[str]:
    """Compare actual JSON files and return all canonical report differences."""
    if any(not p.is_file() or p.stat().st_size > 2 * 1024 * 1024 for p in (local, browser)):
        raise ReportError("Both reports must exist and be at most 2 MiB each")
    def reject_non_json_number(value: str) -> None:
        raise ReportError(f"Invalid JSON number: {value}")

    a, b = (
        canonical(json.loads(p.read_text(encoding="utf-8"), parse_constant=reject_non_json_number))
        for p in (local, browser)
    )
    return changes(a, b)


def main(argv: list[str] | None = None) -> int:
    """Validate and compare local versus experimental browser engine reports."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local", type=Path)
    parser.add_argument("browser", type=Path)
    args = parser.parse_args(argv)
    try:
        differences = compare_file_paths(args.local, args.browser)
    except (ReportError, ValueError, OSError) as e:
        print(f"Invalid input: {e}", file=sys.stderr)
        return 2
    if differences:
        for difference in differences[:100]:
            print(difference)
        print(f"PARITY FAIL: {len(differences)} field differences")
        return 1
    print("PARITY PASS: identical canonical schema-v2 report fields (not authentication)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
